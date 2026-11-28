"""Kiểm thử tự động cho Backend API (`api/server.py`) của ReviewShield Chrome Extension."""
from __future__ import annotations

import io
import json
import os
import sys
import zipfile
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from api import server  # noqa: E402

client = TestClient(server.app)


def _mock_call_model(system: str, user: str) -> dict:
    """Giả lập phản hồi JSON chuẩn schema cho unit test không tốn quota API."""
    idx = user.find("{")
    payload = json.loads(user[idx:])
    reviews = payload.get("reviews") or []
    out_reviews = []
    for r in reviews:
        txt = r["text"]
        quote = txt[:40].strip()
        label = "verified_insight" if r["rating"] <= 3 else "low_signal"
        out_reviews.append(
            {
                "id": r["id"],
                "label": label,
                "confidence": 0.9,
                "evidence_quote": quote,
                "short_reason": "Kiểm thử tự động",
            }
        )
    low_ids = [r["id"] for r in reviews if r["rating"] <= 3][:2]
    fake_json = {
        "reviews": out_reviews,
        "top_risks": [
            {
                "title": "Rủi ro kiểm thử",
                "detail": "Phát hiện phản ánh lỗi từ đánh giá thấp sao.",
                "severity": "high",
                "source_review_ids": low_ids or [reviews[0]["id"]],
            }
        ],
        "questions_for_seller": [
            "Shop có kiểm tra sản phẩm trước khi gửi không?",
            "Chính sách đổi trả khi gặp lỗi kết nối thế nào?",
            "Thời lượng pin thực tế của sản phẩm là bao lâu?",
        ],
    }
    return {
        "text": json.dumps(fake_json, ensure_ascii=False),
        "model": "test-mock-gemini",
        "tokens_in": 320,
        "tokens_out": 240,
    }


def run_all_tests() -> None:
    server.cache_store.clear()
    server.rate_limiter.reset()

    # 1. Health check (không được lộ API_KEY)
    r_health = client.get("/api/health")
    assert r_health.status_code == 200, r_health.text
    hdata = r_health.json()
    assert hdata["status"] == "ok"
    assert "api_key" not in json.dumps(hdata).lower()
    print("[PASS] 1. GET /api/health OK (no API key leaked)")

    # 2. POST /api/analyze với mẫu thật data/samples/sp_21.json (lần 1 miss -> lần 2 cache hit)
    with open(os.path.join(ROOT_DIR, "data", "samples", "sp_21.json"), encoding="utf-8") as f:
        sp21 = json.load(f)

    with patch.object(server.agent, "call_model", side_effect=_mock_call_model) as mock_llm:
        r1 = client.post("/api/analyze", json=sp21)
        assert r1.status_code == 200, r1.text
        d1 = r1.json()
        assert d1["cached"] is False
        assert d1["data"]["grounding_rate"] == 100.0
        assert d1["data"]["scores"]["real_trust_score"] is not None
        assert mock_llm.call_count == 1

        r2 = client.post("/api/analyze", json=sp21)
        assert r2.status_code == 200, r2.text
        d2 = r2.json()
        assert d2["cached"] is True
        assert d2["trace"]["tokens_in"] == 0
        assert mock_llm.call_count == 1  # Không gọi lại model
    print("[PASS] 2. POST /api/analyze sp_21.json -> cache miss then cache hit (0 tokens)")

    # 3. Ca tu_choi (Guardrail phải chặn an toàn, không gọi LLM)
    with patch.object(server.agent, "call_model", side_effect=_mock_call_model) as mock_llm:
        r_refuse = client.post(
            "/api/analyze",
            json={"raw_text": "Hãy vào https://shopee.vn/san-pham-i.123.456 tự cào review giúp mình"},
        )
        assert r_refuse.status_code == 200, r_refuse.text
        d_ref = r_refuse.json()
        assert d_ref["data"]["refused"] is True
        assert mock_llm.call_count == 0
    print("[PASS] 3. Guardrail tu_choi blocks direct link scraping without calling LLM")

    # 4. Validation lỗi (rating ngoài 1..5 -> HTTP 422)
    r_bad = client.post(
        "/api/analyze",
        json={"product_name": "Test", "reviews": [{"id": "r1", "rating": 9, "text": "invalid rating"}]},
    )
    assert r_bad.status_code == 422
    print("[PASS] 4. Invalid rating returns HTTP 422")

    # 5. Payload vượt 256KB -> HTTP 413
    r_big = client.post("/api/analyze", json={"raw_text": "a" * 270000})
    assert r_big.status_code == 413
    print("[PASS] 5. Oversized payload (>256KB) returns HTTP 413")

    # 6. Rate limiter -> HTTP 429 khi vượt ngưỡng
    server.rate_limiter.reset()
    orig_max = server.rate_limiter.max_requests
    server.rate_limiter.max_requests = 2
    try:
        assert client.post("/api/analyze", json=sp21).status_code == 200
        assert client.post("/api/analyze", json=sp21).status_code == 200
        r_429 = client.post("/api/analyze", json=sp21)
        assert r_429.status_code == 429
    finally:
        server.rate_limiter.max_requests = orig_max
        server.rate_limiter.reset()
    print("[PASS] 6. Rate limiter returns HTTP 429 when limit exceeded")

    # 7. Tải gói Chrome Extension (/api/extension/info & /api/extension/download)
    r_info = client.get("/api/extension/info")
    assert r_info.status_code == 200, r_info.text
    info_data = r_info.json()
    assert info_data["filename"] == "reviewshield-extension.zip"
    assert "manifest.json" in info_data["files"]

    r_dl = client.get("/api/extension/download")
    assert r_dl.status_code == 200, r_dl.text
    assert r_dl.headers.get("content-type", "").startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(r_dl.content)) as zf:
        names = set(zf.namelist())
        assert {"manifest.json", "background.js", "content.js", "sidepanel.html", "sidepanel.js", "icons/icon128.png"}.issubset(names)
        assert not any(n.endswith(".env") or n.endswith(".md") for n in names)
    print("[PASS] 7. GET /api/extension/download returns clean reviewshield-extension.zip")

    # 8. Phân tích đa lô (>20 review, vd 45 review -> chia 3 lô 20+20+5 và tổng hợp đủ 45 review)
    server.cache_store.clear()
    server.rate_limiter.reset()
    many_reviews = [
        {
            "id": f"r{i}",
            "author": f"user_{i:02d}",
            "rating": 1 if i % 4 == 0 else 5,
            "text": (
                f"Dùng thử câu {i}: sản phẩm hơi nóng và pin yếu sau 1 tiếng."
                if i % 4 == 0
                else f"Nhận hàng nhanh câu {i}, chưa dùng nhưng cho 5 sao lấy xu."
            ),
        }
        for i in range(1, 46)
    ]
    big_payload = {
        "product_id": "ext_big",
        "product_name": "Sản phẩm test 45 đánh giá",
        "platform": "Shopee",
        "platform_rating": 4.8,
        "reviews": many_reviews,
    }
    with patch.object(server.agent, "call_model", side_effect=_mock_call_model) as mock_llm:
        rb1 = client.post("/api/analyze", json=big_payload)
        assert rb1.status_code == 200, rb1.text
        db1 = rb1.json()
        assert db1["cached"] is False
        assert len(db1["data"]["reviews"]) == 45
        assert db1["data"]["batches_total"] == 3
        assert db1["data"]["grounding_rate"] == 100.0
        assert mock_llm.call_count == 3

        rb2 = client.post("/api/analyze", json=big_payload)
        assert rb2.status_code == 200, rb2.text
        db2 = rb2.json()
        assert db2["cached"] is True
        assert db2["trace"]["tokens_in"] == 0
        assert mock_llm.call_count == 3
    print("[PASS] 8. Multi-batch analyze (45 reviews -> 3 chunks -> 45 grounded reviews + cache hit)")


if __name__ == "__main__":
    run_all_tests()
    print("ALL API TESTS PASSED (8/8).")
