"""Nối model — chỗ DUY NHẤT trong bản chạy thử gọi model AI (Module 1: ReviewShield).

Hợp đồng (giữ nguyên để khung đo được token):
    call_model(system: str, user: str) -> dict với 4 khoá:
        "text":       str   chữ model trả về
        "model":      str   tên model đã gọi (để tra giá ở bảng giá model)
        "tokens_in":  int   số token vào, lấy từ trường usage trong phản hồi API — KHÔNG ước lượng
        "tokens_out": int   số token ra, gồm cả token suy luận / suy nghĩ nếu API tính riêng
    @model_call (từ tracing.py) tự ghi mỗi lần gọi vào trace.
    Chỉ dùng thư viện chuẩn Python (urllib) theo docs/connect-model.md.
"""
import json
import os
import time
import urllib.error
import urllib.request

from tracing import model_call

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOW_RAW = False
REQUEST_TIMEOUT_SECONDS = 25
RETRYABLE_HTTP_CODES = (429, 503)
RETRY_BACKOFF_SECONDS = 2.0


def load_env(path: str = os.path.join(ROOT, ".env")) -> None:
    """Đọc file .env (KEY=VALUE mỗi dòng) vào biến môi trường, không ghi đè biến đã có."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env()
MODEL_PROVIDER = (os.environ.get("MODEL_PROVIDER") or "fake").strip().lower()
MODEL_NAME = (os.environ.get("MODEL_NAME") or "").strip()
API_KEY = (os.environ.get("API_KEY") or "").strip()
API_BASE_URL = (os.environ.get("API_BASE_URL") or "").strip()


def post_json(
    url: str,
    headers: dict[str, str],
    body: dict,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
    max_retries: int = 1,
) -> dict:
    """Gửi HTTP POST JSON bằng urllib chuẩn, retry 1 lần khi gặp lỗi quá tải 429/503."""
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    merged_headers = {"Content-Type": "application/json", **headers}

    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=payload, method="POST", headers=merged_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if SHOW_RAW:
                print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])
            return data
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", "replace")[:300]
            if exc.code in RETRYABLE_HTTP_CODES and attempt < max_retries:
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            raise RuntimeError(f"HTTP {exc.code}: {err_body}") from exc


def _call_gemini(system: str, user: str) -> dict:
    """Gọi Gemini generateContent API với JSON mode và đọc chính xác usageMetadata."""
    # Truyền API key qua header thay vì query string để tránh lộ key trong log lỗi URL.
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"
    body: dict = {
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    data = post_json(url, {"x-goog-api-key": API_KEY}, body)
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini không trả về candidates hợp lệ.")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    # Bỏ qua phần thought (suy luận nội bộ) nếu model trả riêng để giữ JSON sạch.
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))

    usage = data.get("usageMetadata") or {}
    tokens_in = int(usage.get("promptTokenCount") or 0)
    tokens_out = int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0)
    return {"text": text, "tokens_in": tokens_in, "tokens_out": tokens_out}


def _call_openai(system: str, user: str) -> dict:
    """Gọi OpenAI (hoặc endpoint OpenAI-compatible qua API_BASE_URL) với JSON object mode."""
    url = API_BASE_URL or "https://api.openai.com/v1/chat/completions"
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = {
        "model": MODEL_NAME,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    data = post_json(url, {"Authorization": f"Bearer {API_KEY}"}, body)
    usage = data.get("usage") or {}
    return {
        "text": data["choices"][0]["message"]["content"],
        "tokens_in": int(usage.get("prompt_tokens") or 0),
        "tokens_out": int(usage.get("completion_tokens") or 0),
    }


def _call_anthropic(system: str, user: str) -> dict:
    """Gọi Anthropic Claude Messages API."""
    url = API_BASE_URL or "https://api.anthropic.com/v1/messages"
    body = {
        "model": MODEL_NAME,
        "max_tokens": 2048,
        "temperature": 0.1,
        "system": system or "",
        "messages": [{"role": "user", "content": user}],
    }
    data = post_json(
        url,
        {"x-api-key": API_KEY, "anthropic-version": "2023-06-01"},
        body,
    )
    text = "".join(b.get("text", "") for b in (data.get("content") or []) if b.get("type") == "text")
    usage = data.get("usage") or {}
    return {
        "text": text,
        "tokens_in": int(usage.get("input_tokens") or 0),
        "tokens_out": int(usage.get("output_tokens") or 0),
    }


def _call_ollama(system: str, user: str) -> dict:
    """Gọi Ollama cục bộ với JSON output mode."""
    url = API_BASE_URL or "http://localhost:11434/api/chat"
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }
    data = post_json(url, {}, body, timeout=180)
    return {
        "text": (data.get("message") or {}).get("content", ""),
        "tokens_in": int(data.get("prompt_eval_count") or 0),
        "tokens_out": int(data.get("eval_count") or 0),
    }


def _build_fake_json(user: str) -> str:
    """Sinh JSON mock hợp lệ khi MODEL_PROVIDER=fake để khung `python run.py` chạy thông 3 chặng trước CP2."""
    reviews_out: list[dict] = []
    start = user.find("{")
    end = user.rfind("}")
    if start != -1 and end > start:
        try:
            payload = json.loads(user[start : end + 1])
            for item in payload.get("reviews") or []:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                dup_size = int(item.get("duplicate_group_size") or 1)
                label = "suspicious_pattern" if dup_size >= 2 else "verified_insight"
                reviews_out.append(
                    {
                        "id": str(item["id"]),
                        "label": label,
                        "confidence": 0.5,
                        "evidence_quote": "",
                        "short_reason": "[Chế độ giả — chưa nối model thật]",
                    }
                )
        except Exception:
            reviews_out = []

    return json.dumps(
        {
            "reviews": reviews_out,
            "top_risks": [],
            "questions_for_seller": [
                "[Chế độ giả] Sản phẩm thực tế có đúng thông số như mô tả không?",
                "[Chế độ giả] Shop có chính sách đổi trả nếu sản phẩm lỗi không?",
                "[Chế độ giả] Sản phẩm đi kèm đầy đủ phụ kiện và bảo hành thế nào?",
            ],
        },
        ensure_ascii=False,
    )


@model_call
def call_model(system: str, user: str) -> dict:
    """Gọi model theo cấu hình .env và trả đúng 4 khóa hợp đồng cho tracing.py."""
    if MODEL_PROVIDER == "fake":
        return {
            "text": _build_fake_json(user),
            "model": "fake",
            "tokens_in": 0,
            "tokens_out": 0,
        }

    if not MODEL_NAME:
        raise ValueError("Thiếu MODEL_NAME trong file .env — xem docs/connect-model.md")
    if MODEL_PROVIDER in ("gemini", "openai", "anthropic") and not API_KEY:
        raise ValueError(f"Thiếu API_KEY cho MODEL_PROVIDER={MODEL_PROVIDER} trong file .env")

    if MODEL_PROVIDER == "gemini":
        result = _call_gemini(system, user)
    elif MODEL_PROVIDER == "openai":
        result = _call_openai(system, user)
    elif MODEL_PROVIDER == "anthropic":
        result = _call_anthropic(system, user)
    elif MODEL_PROVIDER == "ollama":
        result = _call_ollama(system, user)
    else:
        raise NotImplementedError(
            f"Chưa hỗ trợ MODEL_PROVIDER={MODEL_PROVIDER} trong codebase/ai.py — hỗ trợ: gemini, openai, anthropic, ollama"
        )

    return {
        "text": result["text"],
        "model": MODEL_NAME,
        "tokens_in": int(result["tokens_in"]),
        "tokens_out": int(result["tokens_out"]),
    }
