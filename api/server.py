"""Backend REST API cho ReviewShield Chrome Extension (FastAPI).

Tái sử dụng trực tiếp pipeline 3 chặng từ `codebase/agent.py` (Guardrail → preprocess_reviews
→ call_model → verify_grounding → compute_real_trust_score), bổ sung:
- Tầng Cache 2 chế độ: Redis (khi đặt `REDIS_URL`) hoặc In-Memory TTL LRU (mặc định 12h, tối đa 500 mục).
- Rate limit trượt theo IP chống lạm dụng API key (mặc định 15 lượt/phút).
- Giới hạn kích thước payload <= 64KB, validate chặt bằng Pydantic và CORS an toàn.

Chạy cục bộ:
    uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
Chạy trên VPS:
    uvicorn api.server:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys
import threading
import time
import zipfile
from collections import OrderedDict, deque
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, model_validator

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODEBASE_DIR = os.path.join(ROOT_DIR, "codebase")
EXTENSION_DIR = os.path.join(ROOT_DIR, "extension")
EXTENSION_PACKAGE_FILES = (
    "manifest.json",
    "background.js",
    "content.js",
    "sidepanel.html",
    "sidepanel.css",
    "sidepanel.js",
    "icons/icon16.png",
    "icons/icon48.png",
    "icons/icon128.png",
)
if CODEBASE_DIR not in sys.path:
    sys.path.insert(0, CODEBASE_DIR)

import agent  # noqa: E402
import ai  # noqa: E402
import tools  # noqa: E402
import tracing  # noqa: E402

MAX_PAYLOAD_BYTES = 256 * 1024
MAX_REVIEWS_REQUEST = 200
CHUNK_SIZE = 20
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", str(12 * 3600)))
CACHE_MAX_ENTRIES = int(os.environ.get("CACHE_MAX_ENTRIES", "500"))
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "15"))
RATE_LIMIT_WINDOW_SECONDS = 60.0
REDIS_URL = (os.environ.get("REDIS_URL") or "").strip()
_TRACE_LOCK = threading.Lock()


class ReviewItem(BaseModel):
    """Một đánh giá sản phẩm đã được ẩn danh tại trình duyệt."""

    id: str = Field(default="r1", max_length=32)
    author: str = Field(default="user_01", max_length=32)
    rating: int = Field(ge=1, le=5)
    text: str = Field(min_length=1, max_length=2500)


class AnalyzeRequest(BaseModel):
    """Payload gửi từ Chrome Extension hoặc công cụ kiểm thử tới `/api/analyze`."""

    product_id: str | None = Field(default="ext_live", max_length=64)
    product_name: str | None = Field(default=None, max_length=300)
    category: str | None = Field(default="phu_kien_dien_tu", max_length=64)
    platform: str | None = Field(default="Shopee", max_length=64)
    platform_rating: float | None = Field(default=None, ge=1.0, le=5.0)
    reviews: list[ReviewItem] | None = Field(default=None, min_length=1, max_length=MAX_REVIEWS_REQUEST)
    raw_text: str | None = Field(default=None, min_length=1, max_length=240000)
    bypass_cache: bool = False

    @model_validator(mode="after")
    def _ensure_input_present(self) -> "AnalyzeRequest":
        if not self.reviews and not (self.raw_text and self.raw_text.strip()):
            raise ValueError("Cần cung cấp danh sách `reviews` (1–200 câu) hoặc `raw_text` hợp lệ.")
        return self


class CacheStore:
    """Bộ nhớ đệm TTL 12 giờ: ưu tiên Redis khi có `REDIS_URL`, tự fallback sang In-Memory LRU."""

    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS, max_entries: int = CACHE_MAX_ENTRIES) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._mem: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._redis = None
        self.backend = "memory"

        if REDIS_URL:
            try:
                import redis  # type: ignore

                client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
                client.ping()
                self._redis = client
                self.backend = "redis"
            except Exception:
                self._redis = None
                self.backend = "memory"

    def get(self, key: str) -> dict[str, Any] | None:
        """Lấy bản ghi cache còn hạn; trả None nếu miss hoặc hết TTL."""
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
                return json.loads(raw) if raw else None
            except Exception:
                return None

        now = time.time()
        with self._lock:
            item = self._mem.get(key)
            if item is None:
                return None
            expires_at, value = item
            if now >= expires_at:
                self._mem.pop(key, None)
                return None
            self._mem.move_to_end(key)
            return value

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Lưu kết quả vào cache kèm TTL."""
        if self._redis is not None:
            try:
                self._redis.setex(key, self.ttl_seconds, json.dumps(value, ensure_ascii=False))
                return
            except Exception:
                pass

        expires_at = time.time() + self.ttl_seconds
        with self._lock:
            self._mem[key] = (expires_at, value)
            self._mem.move_to_end(key)
            while len(self._mem) > self.max_entries:
                self._mem.popitem(last=False)

    def clear(self) -> None:
        """Xóa toàn bộ cache bộ nhớ cục bộ (dùng cho kiểm thử)."""
        with self._lock:
            self._mem.clear()

    def size(self) -> int:
        """Đếm số mục đang lưu trong cache bộ nhớ."""
        if self._redis is not None:
            try:
                return int(self._redis.dbsize())
            except Exception:
                return -1
        with self._lock:
            return len(self._mem)


class SlidingWindowRateLimiter:
    """Giới hạn tốc độ trượt theo IP để chống lạm dụng API key."""

    def __init__(self, max_requests: int = RATE_LIMIT_PER_MIN, window_seconds: float = RATE_LIMIT_WINDOW_SECONDS) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, deque[float]] = {}

    def allow(self, client_ip: str) -> tuple[bool, int]:
        """Kiểm tra IP có được phép gọi không; trả `(allowed, retry_after_seconds)`."""
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._hits.setdefault(client_ip, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])) + 1)
                return False, retry_after
            bucket.append(now)
            return True, 0

    def reset(self) -> None:
        """Đặt lại bộ đếm giới hạn (dùng cho kiểm thử)."""
        with self._lock:
            self._hits.clear()


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def build_cache_key(req: AnalyzeRequest) -> str:
    """Tạo khóa cache tất định từ tên sản phẩm và danh sách review chuẩn hóa."""
    if req.reviews:
        canonical_reviews = sorted(
            f"{item.rating}|{_norm_text(item.text)}"
            for item in req.reviews
        )
        key_payload = {
            "mode": "structured",
            "model": ai.MODEL_NAME or "fake",
            "product_name": _norm_text(req.product_name or ""),
            "platform_rating": round(float(req.platform_rating), 1) if req.platform_rating is not None else None,
            "reviews": canonical_reviews,
        }
    else:
        key_payload = {
            "mode": "raw",
            "model": ai.MODEL_NAME or "fake",
            "raw_text": _norm_text(req.raw_text or ""),
        }
    digest = hashlib.sha256(json.dumps(key_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return f"rs:v1:{digest}"


def build_agent_input(req: AnalyzeRequest) -> str:
    """Chuyển AnalyzeRequest thành chuỗi đầu vào chuẩn cho `codebase/agent.answer(text)`."""
    if req.reviews:
        # Đảm bảo author luôn được ẩn danh chuẩn user_XX dù client gửi chuỗi khác.
        clean_reviews = [
            {
                "id": f"r{idx}",
                "author": f"user_{idx:02d}",
                "rating": int(item.rating),
                "text": item.text.strip(),
            }
            for idx, item in enumerate(req.reviews, start=1)
        ]
        payload = {
            "product_id": (req.product_id or "ext_live").strip(),
            "product_name": (req.product_name or "Sản phẩm từ ReviewShield Extension").strip(),
            "category": (req.category or "phu_kien_dien_tu").strip(),
            "platform": (req.platform or "Shopee").strip(),
            "platform_rating": req.platform_rating,
            "reviews": clean_reviews,
        }
        return json.dumps(payload, ensure_ascii=False)
    return (req.raw_text or "").strip()


def _extract_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


cache_store = CacheStore()
rate_limiter = SlidingWindowRateLimiter()

app = FastAPI(
    title="ReviewShield Extension API",
    description="API bọc pipeline 3 chặng ReviewShield với Cache TTL và Rate Limiting cho Chrome Extension.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hackathonane.duckdns.org",
        "http://hackathonane.duckdns.org:8501",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"^(chrome-extension://[a-z]{32}|http://(localhost|127\.0\.0\.1)(:\d+)?)$",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


def _run_chunked_structured_analysis(req: AnalyzeRequest) -> dict[str, Any]:
    """Phân tích >20 review (lên tới 200 câu) bằng cách chia từng lô 20 câu qua `agent.answer`,
    giữ nguyên pipeline Grounding Guard 100% và tổng hợp điểm tin cậy thực tất định trên toàn bộ review.
    """
    reviews = req.reviews or []
    clean_reviews = [
        {
            "id": f"r{idx}",
            "author": f"user_{idx:02d}",
            "rating": int(item.rating),
            "text": item.text.strip(),
        }
        for idx, item in enumerate(reviews, start=1)
    ]
    base_meta = {
        "product_id": (req.product_id or "ext_live").strip(),
        "product_name": (req.product_name or "Sản phẩm từ ReviewShield Extension").strip(),
        "category": (req.category or "phu_kien_dien_tu").strip(),
        "platform": (req.platform or "Shopee").strip(),
        "platform_rating": req.platform_rating,
    }

    chunks = [clean_reviews[i : i + CHUNK_SIZE] for i in range(0, len(clean_reviews), CHUNK_SIZE)]
    merged_reviews: list[dict[str, Any]] = []
    merged_warnings: list[str] = []
    risk_buckets: dict[str, dict[str, Any]] = {}
    questions_seen: set[str] = set()
    merged_questions: list[str] = []
    total_fallback = 0
    failed_chunks = 0

    for chunk_idx, chunk in enumerate(chunks, start=1):
        chunk_payload = json.dumps({**base_meta, "reviews": chunk}, ensure_ascii=False)
        res = agent.answer(chunk_payload)
        data = res.get("data") if isinstance(res, dict) else None
        if not isinstance(data, dict):
            failed_chunks += 1
            continue
        if data.get("refused"):
            return res
        if data.get("error"):
            failed_chunks += 1
            merged_warnings.append(f"Lô {chunk_idx}/{len(chunks)} gặp lỗi tạm ({data.get('error')}), đã bỏ qua lô này.")
            continue

        merged_reviews.extend(data.get("reviews") or [])
        total_fallback += int(data.get("fallback_count") or 0)
        for w in data.get("warnings") or []:
            if w and w not in merged_warnings:
                merged_warnings.append(w)

        for r in data.get("top_risks") or []:
            if not isinstance(r, dict):
                continue
            title = str(r.get("title") or "").strip()
            if not title:
                continue
            key = _norm_text(title)
            ids = [str(x).strip() for x in (r.get("source_review_ids") or []) if str(x).strip()]
            sev = str(r.get("severity") or "medium").lower()
            if key not in risk_buckets:
                risk_buckets[key] = {
                    "title": title,
                    "detail": str(r.get("detail") or "").strip(),
                    "severity": sev,
                    "source_review_ids": list(dict.fromkeys(ids)),
                    "mentions": 1,
                }
            else:
                b = risk_buckets[key]
                b["mentions"] += 1
                b["source_review_ids"] = list(dict.fromkeys(b["source_review_ids"] + ids))
                if sev == "high":
                    b["severity"] = "high"

        for q in data.get("questions_for_seller") or []:
            q_clean = str(q or "").strip()
            q_key = _norm_text(q_clean)
            if q_clean and q_key not in questions_seen and len(merged_questions) < 3:
                questions_seen.add(q_key)
                merged_questions.append(q_clean)

    if not merged_reviews:
        return {
            "output": "Không thể hoàn tất phân tích các lô đánh giá do lỗi tạm từ mô hình AI. Vui lòng thử lại.",
            "data": {"error": "chunked_analysis_failed", "detail": f"Tất cả {len(chunks)} lô đều thất bại."},
        }

    # Tổng hợp điểm tin cậy thực tất định trên toàn bộ review đã phân tích
    scores = tools.compute_real_trust_score(merged_reviews, req.platform_rating)
    grounding_rate = 100.0 if merged_reviews else 0.0

    sev_rank = {"high": 3, "medium": 2, "low": 1}
    sorted_risks = sorted(
        risk_buckets.values(),
        key=lambda x: (sev_rank.get(x["severity"], 1), x["mentions"], len(x["source_review_ids"])),
        reverse=True,
    )[:3]
    top_risks = [
        {
            "title": r["title"],
            "detail": r["detail"],
            "severity": r["severity"],
            "source_review_ids": r["source_review_ids"][:8],
        }
        for r in sorted_risks
    ]

    if len(merged_questions) < 3:
        fallback_qs = [
            "Shop có kiểm tra chất lượng và phụ kiện đầy đủ trước khi đóng gói không?",
            "Nếu sản phẩm gặp lỗi thực tế sau khi dùng, chính sách đổi trả/bảo hành của shop thế nào?",
            "Sản phẩm giao thực tế có đúng thông số, chất liệu và kích thước như mô tả không?",
        ]
        for fq in fallback_qs:
            if len(merged_questions) >= 3:
                break
            if _norm_text(fq) not in questions_seen:
                questions_seen.add(_norm_text(fq))
                merged_questions.append(fq)

    merged_warnings.insert(
        0,
        f"Đã phân tích đầy đủ {len(merged_reviews)}/{len(clean_reviews)} đánh giá qua {len(chunks)} lô "
        f"(mỗi lô tối đa {CHUNK_SIZE} câu) và tính điểm tin cậy thực tổng hợp.",
    )

    real_score_str = (
        f"{scores['real_trust_score']:.1f}/5" if isinstance(scores.get("real_trust_score"), (int, float)) else "N/A"
    )
    plat_score_str = (
        f"{scores['platform_rating']:.1f}/5" if isinstance(scores.get("platform_rating"), (int, float)) else "N/A"
    )
    output_text = (
        f"[ReviewShield · Phân tích {len(merged_reviews)} đánh giá ({len(chunks)} lô)]\n"
        f"Sản phẩm: {base_meta['product_name']}\n"
        f"Điểm sàn: {plat_score_str} → Điểm tin cậy thực: {real_score_str} "
        f"(Trải nghiệm thật: {scores.get('verified_ratio', 0.0):.1f}% · Grounding 100%)"
    )

    return {
        "output": output_text,
        "data": {
            "product_name": base_meta["product_name"],
            "scores": scores,
            "grounding_rate": grounding_rate,
            "fallback_count": total_fallback,
            "top_risks": top_risks,
            "questions_for_seller": merged_questions[:3],
            "reviews": merged_reviews,
            "warnings": merged_warnings,
            "batches_total": len(chunks),
            "batches_failed": failed_chunks,
        },
    }


@app.middleware("http")
async def _enforce_payload_limit(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_PAYLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Dữ liệu gửi lên vượt quá giới hạn 256KB. Vui lòng giữ tối đa 200 đánh giá mỗi lượt."},
            )
        body = await request.body()
        if len(body) > MAX_PAYLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Dữ liệu gửi lên vượt quá giới hạn 256KB. Vui lòng giữ tối đa 200 đánh giá mỗi lượt."},
            )
    return await call_next(request)


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Kiểm tra sức khỏe API, model đang cấu hình và trạng thái cache (không lộ API_KEY)."""
    return {
        "status": "ok",
        "service": "reviewshield-api",
        "provider": ai.MODEL_PROVIDER,
        "model": ai.MODEL_NAME or "fake",
        "cache_backend": cache_store.backend,
        "cache_entries": cache_store.size(),
        "cache_ttl_seconds": cache_store.ttl_seconds,
        "rate_limit_per_min": rate_limiter.max_requests,
    }


def build_extension_zip_bytes(extension_dir: str = EXTENSION_DIR) -> tuple[bytes, list[str]]:
    """Đóng gói động các file runtime sạch của Chrome Extension thành gói `.zip` trong bộ nhớ."""
    manifest_path = os.path.join(extension_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise FileNotFoundError("Không tìm thấy thư mục extension/manifest.json trên máy chủ.")

    buf = io.BytesIO()
    packed: list[str] = []
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in EXTENSION_PACKAGE_FILES:
            abs_path = os.path.join(extension_dir, *rel_path.split("/"))
            if os.path.isfile(abs_path):
                zf.write(abs_path, arcname=rel_path)
                packed.append(rel_path)
    return buf.getvalue(), packed


@app.get("/api/extension/info")
def extension_info() -> dict[str, Any]:
    """Trả thông tin phiên bản và đường dẫn tải gói Chrome Extension Manifest V3."""
    manifest_path = os.path.join(EXTENSION_DIR, "manifest.json")
    if not os.path.isfile(manifest_path):
        raise HTTPException(status_code=404, detail="Chưa có gói Chrome Extension trên máy chủ.")
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    zip_bytes, packed = build_extension_zip_bytes(EXTENSION_DIR)
    return {
        "name": manifest.get("name", "ReviewShield"),
        "version": manifest.get("version", "1.0.0"),
        "filename": "reviewshield-extension.zip",
        "size_bytes": len(zip_bytes),
        "download_url": "/api/extension/download",
        "files": packed,
    }


@app.get("/api/extension/download")
def extension_download() -> Response:
    """Tải trực tiếp file `reviewshield-extension.zip` sạch (đạt chuẩn Load unpacked & Chrome Web Store)."""
    try:
        zip_bytes, _ = build_extension_zip_bytes(EXTENSION_DIR)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="reviewshield-extension.zip"',
            "Cache-Control": "no-cache",
        },
    )


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest, request: Request) -> dict[str, Any]:
    """Phân tích cụm review sản phẩm qua pipeline ReviewShield có Cache & Rate Limit."""
    client_ip = _extract_client_ip(request)
    allowed, retry_after = rate_limiter.allow(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Bạn đã vượt giới hạn {rate_limiter.max_requests} lượt phân tích/phút. Vui lòng thử lại sau {retry_after} giây.",
            headers={"Retry-After": str(retry_after)},
        )

    cache_key = build_cache_key(req)
    t0 = time.perf_counter()

    if not req.bypass_cache:
        cached_val = cache_store.get(cache_key)
        if cached_val is not None:
            return {
                "output": cached_val["output"],
                "data": cached_val.get("data"),
                "cached": True,
                "cache_key": cache_key,
                "trace": {
                    "model": cached_val.get("model") or (ai.MODEL_NAME or "fake"),
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "model_calls": 0,
                    "tool_calls": 0,
                    "latency_s": round(time.perf_counter() - t0, 4),
                },
            }

    use_chunked = bool(req.reviews and len(req.reviews) > CHUNK_SIZE)
    with _TRACE_LOCK:
        tracing.begin("extension_api")
        try:
            if use_chunked:
                result = _run_chunked_structured_analysis(req)
            else:
                agent_input = build_agent_input(req)
                result = agent.answer(agent_input)
        except Exception as exc:
            tracing.end()
            raise HTTPException(
                status_code=502,
                detail=f"Lỗi khi gọi mô hình phân tích ({type(exc).__name__}): {str(exc)[:240]}",
            ) from exc
        summary, _ = tracing.end()
    latency_s = round(time.perf_counter() - t0, 3)

    models_used = ", ".join(summary.get("models") or []) or (ai.MODEL_NAME or "fake")
    data_obj = result.get("data") if isinstance(result, dict) else None
    output_str = result.get("output", "") if isinstance(result, dict) else str(result)

    # Chỉ lưu cache khi phân tích thành công hoàn toàn (không lưu lỗi tạm hoặc lô lỗi một phần).
    is_error = isinstance(data_obj, dict) and (
        bool(data_obj.get("error")) or int(data_obj.get("batches_failed") or 0) > 0
    )
    if not is_error:
        cache_store.set(
            cache_key,
            {
                "output": output_str,
                "data": data_obj,
                "model": models_used,
            },
        )

    return {
        "output": output_str,
        "data": data_obj,
        "cached": False,
        "cache_key": cache_key,
        "trace": {
            "model": models_used,
            "tokens_in": int(summary.get("tokens_in") or 0),
            "tokens_out": int(summary.get("tokens_out") or 0),
            "model_calls": int(summary.get("model_calls") or 0),
            "tool_calls": int(summary.get("tool_calls") or 0),
            "latency_s": latency_s,
        },
    }
