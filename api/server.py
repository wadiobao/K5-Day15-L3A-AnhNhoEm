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
import json
import os
import re
import sys
import threading
import time
from collections import OrderedDict, deque
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODEBASE_DIR = os.path.join(ROOT_DIR, "codebase")
if CODEBASE_DIR not in sys.path:
    sys.path.insert(0, CODEBASE_DIR)

import agent  # noqa: E402
import ai  # noqa: E402
import tracing  # noqa: E402

MAX_PAYLOAD_BYTES = 64 * 1024
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", str(12 * 3600)))
CACHE_MAX_ENTRIES = int(os.environ.get("CACHE_MAX_ENTRIES", "500"))
RATE_LIMIT_PER_MIN = int(os.environ.get("RATE_LIMIT_PER_MIN", "15"))
RATE_LIMIT_WINDOW_SECONDS = 60.0
REDIS_URL = (os.environ.get("REDIS_URL") or "").strip()


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
    reviews: list[ReviewItem] | None = Field(default=None, min_length=1, max_length=50)
    raw_text: str | None = Field(default=None, min_length=1, max_length=60000)
    bypass_cache: bool = False

    @model_validator(mode="after")
    def _ensure_input_present(self) -> "AnalyzeRequest":
        if not self.reviews and not (self.raw_text and self.raw_text.strip()):
            raise ValueError("Cần cung cấp danh sách `reviews` (1–50 câu) hoặc `raw_text` hợp lệ.")
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


@app.middleware("http")
async def _enforce_payload_limit(request: Request, call_next):
    if request.method == "POST":
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > MAX_PAYLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Dữ liệu gửi lên vượt quá giới hạn 64KB. Vui lòng giữ tối đa 20–50 đánh giá mỗi lượt."},
            )
        body = await request.body()
        if len(body) > MAX_PAYLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Dữ liệu gửi lên vượt quá giới hạn 64KB. Vui lòng giữ tối đa 20–50 đánh giá mỗi lượt."},
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

    agent_input = build_agent_input(req)
    tracing.begin("extension_api")
    try:
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

    # Chỉ lưu cache khi phân tích thành công (không lưu lỗi parse JSON hoặc lỗi tạm).
    is_error = isinstance(data_obj, dict) and bool(data_obj.get("error"))
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
