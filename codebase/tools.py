"""Công cụ tất định của ReviewShield — Thành viên 2 (2A202603427).

Toàn bộ công cụ trong file này chạy 100% bằng Python tất định (không gọi LLM),
gắn decorator @tool từ tracing để tự động ghi trace và không gây tác động ra ngoài.
"""
from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from typing import Any

from tracing import TOOLS, tool  # noqa: F401

WEIGHT_MAP: dict[str, float] = {
    "verified_insight": 1.00,
    "low_signal": 0.15,
    "suspicious_pattern": 0.10,
    "logistics_only": 0.00,
}

VALID_LABELS: tuple[str, ...] = tuple(WEIGHT_MAP.keys())
MAX_REVIEWS_PER_BATCH: int = 20

# Khớp các dạng văn bản review phổ biến theo dòng:
# "[5] nội dung", "[5 sao] nội dung", "5* - nội dung", "5 sao: nội dung", "5★: nội dung", "5⭐ nội dung"
_LINE_REVIEW_RE = re.compile(
    r"^\s*(?:"
    r"\[\s*(?P<r1>-?\d+)\s*(?:sao|\*|★|⭐|☆)?\s*\]"
    r"|(?P<r2>-?\d+)\s*(?:sao|\*|★|⭐|☆|/5)"
    r")\s*[-:–—|.]*\s*(?P<text>.*)$",
    flags=re.IGNORECASE,
)

# Ngắt câu theo dấu câu kết thúc thực sự (không cắt giữa số thập phân như 1.5, 4.8) hoặc xuống dòng
_SENTENCE_END_RE = re.compile(r"(?:[.!?](?=\s|$)|\n)")


def _to_nfc(text: str) -> str:
    """Chuẩn hóa Unicode tiếng Việt về dạng dựng sẵn (NFC)."""
    return unicodedata.normalize("NFC", text)


def _normalize_ws(text: str) -> str:
    """Gộp nhiều khoảng trắng liên tiếp thành 1 khoảng trắng, giữ nguyên dấu/chính tả."""
    return re.sub(r"\s+", " ", _to_nfc(text)).strip()


def _is_meaningless_text(text: str) -> bool:
    """Trả True nếu chuỗi rỗng hoặc chỉ chứa khoảng trắng, dấu câu, emoji vô nghĩa."""
    return re.search(r"[^\W_]", text, flags=re.UNICODE) is None


def _duplicate_key(text: str) -> str:
    """Chuẩn hóa nhẹ (NFC + hạ chữ thường + bỏ dấu câu) để phát hiện review trùng lặp."""
    cleaned = re.sub(r"[^\w\s]", " ", _to_nfc(text).lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _find_exact_span(orig_text: str, quote: str) -> str | None:
    """Tìm và trả về đúng đoạn nguyên văn trong `orig_text` khớp với `quote` (bỏ qua hoa/thường & khoảng trắng)."""
    orig_nfc = _to_nfc(orig_text)
    tokens = _to_nfc(quote).strip().split()
    if not orig_nfc or not tokens:
        return None
    pattern = r"\s+".join(re.escape(tok) for tok in tokens)
    match = re.search(pattern, orig_nfc, flags=re.IGNORECASE)
    return match.group(0) if match else None


def _parse_rating(value: Any) -> int | None:
    """Ép kiểu rating về số nguyên trong [1, 5]; trả None nếu không hợp lệ."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if 1 <= value <= 5 else None
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r"\d+", s):
            num = int(s)
            return num if 1 <= num <= 5 else None
    return None


def _parse_platform_rating(value: Any) -> float | None:
    """Ép kiểu platform_rating về float trong [1.0, 5.0]; trả None nếu không hợp lệ."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if 1.0 <= num <= 5.0:
        return round(num, 1)
    return None


def _stratified_cap(
    reviews: list[dict[str, Any]], limit: int = MAX_REVIEWS_PER_BATCH
) -> list[dict[str, Any]]:
    """Cắt tối đa `limit` review theo lấy mẫu phân tầng ưu tiên giữ đủ 1–5 sao."""
    if len(reviews) <= limit:
        return reviews

    buckets: dict[int, list[int]] = {star: [] for star in (1, 2, 3, 4, 5)}
    for idx, item in enumerate(reviews):
        buckets[item["rating"]].append(idx)

    selected_indices: list[int] = []
    # Lấy vòng tròn theo thứ tự 1★ -> 5★ để không làm mất nhóm đánh giá tiêu cực
    while len(selected_indices) < limit:
        progressed = False
        for star in (1, 2, 3, 4, 5):
            if buckets[star] and len(selected_indices) < limit:
                selected_indices.append(buckets[star].pop(0))
                progressed = True
        if not progressed:
            break

    selected_indices.sort()
    return [reviews[i] for i in selected_indices]


def _extract_verbatim_fallback(orig_text: str) -> str:
    """Trích câu đầu tiên (không cắt giữa số thập phân) hoặc tối đa 12 từ đầu tiên nguyên văn."""
    stripped = _to_nfc(orig_text).strip()
    if not stripped:
        return ""

    sent_match = _SENTENCE_END_RE.search(stripped)
    first_sentence = stripped[: sent_match.start()].strip() if sent_match else stripped
    words_in_sent = list(re.finditer(r"\S+", first_sentence))

    if 3 <= len(words_in_sent) <= 12:
        return first_sentence

    all_words = list(re.finditer(r"\S+", stripped))
    if len(all_words) <= 12:
        return stripped
    return stripped[: all_words[11].end()].strip()


@tool
def preprocess_reviews(raw_input: str) -> dict[str, Any]:
    """Tên: preprocess_reviews.
    Input: raw_input (str) — chuỗi JSON theo schema data/samples/*.json hoặc văn bản review nhiều dòng.
    Output: dict gồm product_name, platform_rating, total_raw, removed_empty, reviews (tối đa 20), warnings.
    Tác động ra ngoài: Không (chỉ xử lý chuỗi trong bộ nhớ).
    """
    warnings: list[str] = []
    product_name = "Sản phẩm chưa đặt tên"
    platform_rating: float | None = None
    raw_items: list[dict[str, Any]] = []

    if not isinstance(raw_input, str) or not raw_input.strip():
        return {
            "product_name": product_name,
            "platform_rating": None,
            "total_raw": 0,
            "removed_empty": 0,
            "reviews": [],
            "warnings": ["Đầu vào rỗng, không có đánh giá nào để phân tích."],
        }

    text_input = _to_nfc(raw_input).strip()
    parsed_json: Any = None
    first_line = text_input.splitlines()[0]
    json_attempted = (
        (text_input.startswith("{") or text_input.startswith("["))
        and not _LINE_REVIEW_RE.match(first_line)
    )
    if json_attempted:
        try:
            parsed_json = json.loads(text_input)
        except json.JSONDecodeError:
            warnings.append("JSON đầu vào không hợp lệ, hệ thống chuyển sang đọc từng dòng văn bản.")

    if isinstance(parsed_json, dict):
        name_val = parsed_json.get("product_name")
        if isinstance(name_val, str) and name_val.strip():
            product_name = _normalize_ws(name_val)
        if "platform_rating" in parsed_json and parsed_json.get("platform_rating") is not None:
            platform_rating = _parse_platform_rating(parsed_json.get("platform_rating"))
            if platform_rating is None:
                warnings.append("platform_rating ngoài khoảng [1.0, 5.0], sẽ tính lại từ danh sách review.")
        reviews_field = parsed_json.get("reviews")
        if isinstance(reviews_field, list):
            for item in reviews_field:
                if isinstance(item, dict):
                    raw_items.append(item)
                else:
                    warnings.append("Bỏ qua một phần tử review không đúng dạng đối tượng JSON.")
        else:
            warnings.append("Thiếu danh sách 'reviews' hợp lệ trong JSON đầu vào.")
    elif isinstance(parsed_json, list):
        for item in parsed_json:
            if isinstance(item, dict):
                raw_items.append(item)
            else:
                warnings.append("Bỏ qua một phần tử review không đúng dạng đối tượng JSON.")
    else:
        lines = [line for line in text_input.splitlines() if line.strip()]
        for idx, line in enumerate(lines, start=1):
            match = _LINE_REVIEW_RE.match(line)
            if not match:
                warnings.append(f"Dòng {idx} không đúng định dạng '[số sao] nội dung' nên đã bỏ qua.")
                continue
            rating_str = match.group("r1") or match.group("r2")
            raw_items.append(
                {
                    "id": f"r{idx}",
                    "rating": rating_str,
                    "text": match.group("text") or "",
                }
            )

    total_raw = len(raw_items)
    removed_empty = 0
    cleaned_reviews: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for idx, item in enumerate(raw_items, start=1):
        raw_id = item.get("id")
        review_id = str(raw_id).strip() if raw_id is not None and str(raw_id).strip() else f"r{idx}"
        if review_id in seen_ids:
            new_id = f"{review_id}_{idx}"
            warnings.append(f"Trùng ID review '{review_id}', đã đổi thành '{new_id}'.")
            review_id = new_id
        seen_ids.add(review_id)

        raw_text = item.get("text")
        text_str = raw_text if isinstance(raw_text, str) else ""

        if _is_meaningless_text(text_str):
            removed_empty += 1
            continue

        rating = _parse_rating(item.get("rating"))
        if rating is None:
            warnings.append(
                f"Review '{review_id}' có rating không hợp lệ ({item.get('rating')!r}, cần số nguyên 1–5) nên đã loại."
            )
            continue

        cleaned_reviews.append(
            {
                "id": review_id,
                "rating": rating,
                "text": _normalize_ws(text_str),
            }
        )

    dup_counts = Counter(_duplicate_key(r["text"]) for r in cleaned_reviews)
    for r in cleaned_reviews:
        r["duplicate_group_size"] = dup_counts[_duplicate_key(r["text"])]

    if len(cleaned_reviews) > MAX_REVIEWS_PER_BATCH:
        warnings.append(
            f"Số review hợp lệ ({len(cleaned_reviews)}) vượt giới hạn {MAX_REVIEWS_PER_BATCH}; "
            f"đã lấy mẫu phân tầng giữ đủ các mức 1–5 sao."
        )
        cleaned_reviews = _stratified_cap(cleaned_reviews, MAX_REVIEWS_PER_BATCH)

    return {
        "product_name": product_name,
        "platform_rating": platform_rating,
        "total_raw": total_raw,
        "removed_empty": removed_empty,
        "reviews": cleaned_reviews,
        "warnings": warnings,
    }


@tool
def verify_grounding(
    original_reviews: list[dict[str, Any]],
    llm_reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    """Tên: verify_grounding.
    Input: original_reviews (list[dict] có id, text, rating) và llm_reviews (list[dict] từ LLM).
    Output: dict gồm reviews (100% evidence_quote nguyên văn, grounded=True, giữ rating & text), grounding_rate, fallback_count.
    Tác động ra ngoài: Không (chỉ đối chiếu chuỗi trong bộ nhớ).
    """
    orig_map: dict[str, dict[str, Any]] = {}
    for item in original_reviews or []:
        if isinstance(item, dict) and item.get("id") is not None:
            orig_map[str(item["id"])] = item

    verified_reviews: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    fallback_count = 0

    for item in llm_reviews or []:
        if not isinstance(item, dict):
            continue
        review_id = str(item.get("id", "")).strip()
        if orig_map and review_id not in orig_map:
            # Bỏ qua ID ảo không tồn tại trong danh sách review gốc
            continue
        if review_id and review_id in seen_ids:
            # Bỏ qua ID trùng lặp trong kết quả từ LLM
            continue
        if review_id:
            seen_ids.add(review_id)

        orig = orig_map.get(review_id)
        orig_text = _to_nfc(str(orig.get("text", ""))) if orig else ""
        orig_rating = orig.get("rating") if orig else item.get("rating")

        raw_label = str(item.get("label", "")).strip()
        label = raw_label if raw_label in WEIGHT_MAP else "low_signal"

        raw_conf = item.get("confidence", 0.0)
        try:
            confidence = round(max(0.0, min(1.0, float(raw_conf))), 2)
        except (TypeError, ValueError):
            confidence = 0.0

        raw_quote = item.get("evidence_quote")
        quote = raw_quote.strip() if isinstance(raw_quote, str) else ""
        short_reason = str(item.get("short_reason", "")).strip()

        exact_span = _find_exact_span(orig_text, quote) if quote else None
        is_fallback = exact_span is None
        if not is_fallback:
            final_quote = exact_span
        else:
            final_quote = _extract_verbatim_fallback(orig_text)
            fallback_count += 1

        verified_reviews.append(
            {
                "id": review_id,
                "rating": orig_rating,
                "text": orig_text,
                "label": label,
                "confidence": confidence,
                "evidence_quote": final_quote,
                "short_reason": short_reason,
                "grounded": True,
                "is_fallback": is_fallback,
            }
        )

    grounding_rate = 100.0 if verified_reviews else 0.0
    return {
        "reviews": verified_reviews,
        "grounding_rate": grounding_rate,
        "fallback_count": fallback_count,
    }


@tool
def compute_real_trust_score(
    reviews: list[dict[str, Any]],
    platform_rating: float | None = None,
) -> dict[str, Any]:
    """Tên: compute_real_trust_score.
    Input: reviews (list[dict] có rating 1–5 và label thuộc 4 nhãn chuẩn), platform_rating (float | None).
    Output: dict gồm platform_rating, real_trust_score, score_delta, direction, verified_ratio, trust_level, label_counts, logistics_warning.
    Tác động ra ngoài: Không (chỉ tính toán toán học tất định).
    """
    label_counts: dict[str, int] = {label: 0 for label in VALID_LABELS}
    valid_reviews: list[dict[str, Any]] = []

    for item in reviews or []:
        if not isinstance(item, dict):
            continue
        rating = _parse_rating(item.get("rating"))
        if rating is None:
            continue
        raw_label = str(item.get("label", "")).strip()
        label = raw_label if raw_label in WEIGHT_MAP else "low_signal"
        label_counts[label] += 1
        valid_reviews.append({"rating": rating, "label": label})

    resolved_platform = _parse_platform_rating(platform_rating)
    if resolved_platform is None and valid_reviews:
        resolved_platform = round(
            sum(r["rating"] for r in valid_reviews) / len(valid_reviews), 1
        )

    logistics_warning = label_counts["logistics_only"] >= 1

    if not valid_reviews:
        return {
            "platform_rating": resolved_platform,
            "real_trust_score": None,
            "score_delta": None,
            "direction": "insufficient_data",
            "verified_ratio": 0.0,
            "trust_level": "insufficient_data",
            "label_counts": label_counts,
            "logistics_warning": False,
        }

    weighted_sum = sum(r["rating"] * WEIGHT_MAP[r["label"]] for r in valid_reviews)
    total_weight = sum(WEIGHT_MAP[r["label"]] for r in valid_reviews)
    verified_ratio = round(100.0 * label_counts["verified_insight"] / len(valid_reviews), 1)

    if total_weight == 0:
        return {
            "platform_rating": resolved_platform,
            "real_trust_score": None,
            "score_delta": None,
            "direction": "insufficient_data",
            "verified_ratio": verified_ratio,
            "trust_level": "insufficient_data",
            "label_counts": label_counts,
            "logistics_warning": logistics_warning,
        }

    real_trust_score = round(weighted_sum / total_weight, 1)
    score_delta = (
        round(real_trust_score - resolved_platform, 1)
        if resolved_platform is not None
        else None
    )

    if score_delta is None:
        direction = "insufficient_data"
    elif abs(score_delta) <= 0.3:
        direction = "near_platform"
    elif score_delta < -0.3:
        direction = "lower_than_platform"
    else:
        direction = "higher_than_platform"

    if (
        score_delta is not None
        and verified_ratio >= 50.0
        and abs(score_delta) <= 0.3
        and real_trust_score >= 4.0
    ):
        trust_level = "high"
    elif (
        verified_ratio < 35.0
        or (score_delta is not None and score_delta <= -0.7)
        or real_trust_score < 3.5
    ):
        trust_level = "low"
    else:
        trust_level = "medium"

    return {
        "platform_rating": resolved_platform,
        "real_trust_score": real_trust_score,
        "score_delta": score_delta,
        "direction": direction,
        "verified_ratio": verified_ratio,
        "trust_level": trust_level,
        "label_counts": label_counts,
        "logistics_warning": logistics_warning,
    }
