"""Luồng chính của ReviewShield — Pipeline 3 chặng (Module 1: Core AI & Orchestration).

`python run.py`, `python run.py eval` và `python run.py simulate` đều gọi answer(text).

Hợp đồng:
    answer(text: str) -> dict có khoá "output" (str) và khoá phụ "data" (dict cho UI).
    Pipeline 3 chặng:
        Chặng 0: Kiểm tra phạm vi & an toàn đầu vào (chặn cào link, tự gửi tin shop, prompt injection).
        Chặng 1: preprocess_reviews() trong codebase/tools.py (tiền xử lý tất định).
        Chặng 2: call_model() trong codebase/ai.py (AI thật trả JSON theo schema, retry tối đa 1 lần).
        Chặng 3: verify_grounding() + compute_real_trust_score() trong codebase/tools.py (tất định 100%).
"""
import json
import re

import tools
from ai import call_model
from tracing import note

VALID_LABELS = frozenset(
    ("verified_insight", "low_signal", "suspicious_pattern", "logistics_only")
)
MAX_JSON_RETRIES = 1

SYSTEM = """Bạn là bộ máy phân tích tín hiệu đánh giá sản phẩm thương mại điện tử của hệ thống ReviewShield.

NHIỆM VỤ:
Đọc danh sách đánh giá sản phẩm (JSON) và trả về kết quả phân tích dưới dạng JSON hợp lệ theo đúng schema.

QUY TẮC BẮT BUỘC:
1. Gán mỗi review vào ĐÚNG 1 trong 4 nhãn theo THỨ TỰ ƯU TIÊN PHÂN ĐỊNH RANH GIỚI sau:
   - Bước A — Kiểm tra "suspicious_pattern" TRƯỚC cho các review khen 5 sao:
     Gán "suspicious_pattern" nếu có BẤT KỲ dấu hiệu nào:
     (a) `duplicate_group_size >= 2` (trùng lặp nguyên văn trong lô); HOẶC
     (b) Có từ 2 review trở lên trong cùng lô lặp lại cùng một khung câu/đoạn thân rất giống nhau (kể cả khi khác tiền tố phân loại ở đầu như "Màu sắc:", "Chất liệu:", "Đúng với mô tả:"); HOẶC
     (c) Văn phong quảng cáo/kêu gọi mua hàng sáo rỗng, tâng bốc quá mức, văn hoa như kịch bản có sẵn (vd: hô hào mọi người yên tâm mua ủng hộ shop, khen điểm 10/hoàn hảo chung chung) hoặc nội dung lạc đề mô tả nhầm sang sản phẩm khác không khớp `product_name`.
   - Bước B — Kiểm tra "logistics_only":
     Gán "logistics_only" khi review CHỈ phản ánh về shipper, thời gian giao hàng, đóng gói vận chuyển, thợ lắp đặt hoặc dịch vụ cửa hàng mà KHÔNG đánh giá chất lượng bản thân sản phẩm.
     Lưu ý ranh giới: Review 5 sao kiểu "giao hàng nhanh, chưa dùng nên đánh giá sau / cho 5 sao lấy xu" PHẢI gán "low_signal", KHÔNG gán "logistics_only".
   - Bước C — Phân định "verified_insight" vs "low_signal":
     * "verified_insight": Nêu ÍT NHẤT 1 chi tiết/thuộc tính thực tế về bản thân sản phẩm (chất liệu, kích cỡ, độ bền, thời lượng pin, kết nối, chất âm, hiệu năng, mùi vị, lỗi kỹ thuật, cảm giác sử dụng thực tế). Dù câu ngắn nhưng có chi tiết sản phẩm cụ thể vẫn là "verified_insight".
     * "low_signal": Khen/chê chung chung không nêu chi tiết sản phẩm ("tốt", "đẹp", "ổn", "ok", "đáng tiền"), chỉ khen thái độ nhân viên/tư vấn, đặt câu hỏi bảo hành, chưa sử dụng ("chưa dùng cho 5 sao"), nhận xu, chèn thơ hoặc ký tự vô nghĩa.
2. Trích dẫn bằng chứng (`evidence_quote`):
   - PHẢI sao chép NGUYÊN VĂN một cụm từ ngắn (3–18 từ) có thật trong trường `text` của review đó.
   - TUYỆT ĐỐI không viết lại, không sửa chính tả, không bịa từ.
3. Lý do ngắn (`short_reason`): Tối đa 15 từ tiếng Việt, trung lập, không khẳng định tuyệt đối "giả 100%".
4. Tổng hợp rủi ro (`top_risks`): Tối đa 3 nhược điểm thực tế từ nhóm "verified_insight", kèm `source_review_ids` thật. Nếu không có nhược điểm, trả về `[]`.
5. Câu hỏi kiểm chứng shop (`questions_for_seller`): Sinh đúng 3 câu hỏi ngắn gọn, thực tế để người mua nhắn hỏi shop trước khi đặt hàng.
6. Chỉ trả về JSON thuần theo đúng schema sau, không kèm văn bản ngoài JSON:
{
  "reviews": [
    {
      "id": "r1",
      "label": "verified_insight | low_signal | suspicious_pattern | logistics_only",
      "confidence": 0.95,
      "evidence_quote": "cụm từ nguyên văn trong text",
      "short_reason": "lý do ngắn tối đa 15 từ"
    }
  ],
  "top_risks": [
    {
      "title": "tiêu đề ngắn",
      "detail": "mô tả ngắn dựa trên review thực tế",
      "severity": "high | medium | low",
      "source_review_ids": ["r2"]
    }
  ],
  "questions_for_seller": [
    "câu hỏi 1",
    "câu hỏi 2",
    "câu hỏi 3"
  ]
}"""

_INJECTION_PATTERNS = (
    r"bỏ qua (mọi |tất cả |các )?hướng dẫn",
    r"ignore (all |previous |prior )?instructions",
    r"tiết lộ (system )?prompt",
    r"in ra system prompt",
    r"reveal (your )?system prompt",
    r"(hãy |bắt buộc |phải )?chấm 5(\.0)? sao cho tất cả",
    r"đổi tất cả nhãn thành verified_insight",
)
_ECOMMERCE_URL_RE = re.compile(
    r"https?://[^\s]*(shopee|tiktok|tiki|lazada|sendo)", re.IGNORECASE
)
_SEND_MESSAGE_PATTERNS = (
    r"(hãy |tự |giúp tôi )?(gửi|nhắn) tin( nhắn)? (trực tiếp )?(cho|tới) shop",
    r"tự động nhắn (cho|tới) shop",
    r"tự động đặt hàng",
)


def _refusal_response(reason: str, note_tag: str) -> dict:
    """Tạo phản hồi từ chối chuẩn 2 ý theo AGENTS.md §4 (lý do giới hạn + hướng dẫn thay thế)."""
    note(f"tu_choi: {note_tag}")
    output = (
        f"[ReviewShield] Không thể thực hiện yêu cầu này: {reason}\n"
        "Hướng dẫn thay thế: Bạn hãy chọn một sản phẩm mẫu có sẵn trong kho dữ liệu "
        "hoặc dán trực tiếp danh sách đánh giá (dạng `[5 sao] nội dung...` hoặc JSON) "
        "để ReviewShield phân tích tín hiệu và tính Điểm tin cậy thực."
    )
    return {"output": output, "data": {"refused": True, "reason": note_tag}}


def _is_json_review_payload(text: str) -> bool:
    """Kiểm tra nhanh xem chuỗi đầu vào có phải JSON chứa danh sách reviews hợp lệ không."""
    stripped = text.strip()
    if not stripped.startswith("{"):
        return False
    try:
        obj = json.loads(stripped)
        return isinstance(obj, dict) and isinstance(obj.get("reviews"), list)
    except Exception:
        return False


def _check_scope_and_safety(text: str) -> dict | None:
    """Chặng 0: Kiểm tra đầu vào rỗng, yêu cầu ngoài phạm vi và prompt injection."""
    if not text or not text.strip():
        return _refusal_response(
            "Đầu vào đang trống nên chưa có dữ liệu đánh giá để phân tích.",
            "empty_input",
        )

    lowered = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return _refusal_response(
                "ReviewShield không bỏ qua quy tắc phân tích, không tiết lộ hướng dẫn hệ thống "
                "và không chấm điểm theo yêu cầu áp đặt.",
                "prompt_injection",
            )

    if _is_json_review_payload(text):
        return None

    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    if _ECOMMERCE_URL_RE.search(text) and len(non_empty_lines) <= 3:
        return _refusal_response(
            "ReviewShield không hỗ trợ tự động cào link trực tiếp từ sàn TMĐT (Shopee, TikTok Shop, Tiki, Lazada).",
            "crawl_url_out_of_scope",
        )

    for pattern in _SEND_MESSAGE_PATTERNS:
        if re.search(pattern, lowered):
            return _refusal_response(
                "ReviewShield không tự gửi tin nhắn tới shop hay thao tác thay trên tài khoản sàn; "
                "hệ thống chỉ tạo bản nháp 3 câu hỏi để người mua tự duyệt.",
                "external_action_out_of_scope",
            )

    return None


def _extract_json_object(raw_text: str) -> dict:
    """Parse JSON từ phản hồi LLM (hỗ trợ bóc code fence markdown) và kiểm tra khóa bắt buộc."""
    cleaned = (raw_text or "").strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        cleaned = fence_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Phản hồi không chứa đối tượng JSON hợp lệ.")
        parsed = json.loads(cleaned[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("JSON đầu ra phải là một object.")
    for required_key in ("reviews", "top_risks", "questions_for_seller"):
        if required_key not in parsed or not isinstance(parsed[required_key], list):
            raise ValueError(f"Thiếu hoặc sai kiểu khóa bắt buộc '{required_key}' (phải là list).")
    return parsed


def _normalize_llm_reviews(raw_reviews: list, orig_reviews: list[dict]) -> list[dict]:
    """Chuẩn hóa danh sách phân loại từ LLM, đảm bảo mọi review gốc đều có nhãn hợp lệ."""
    by_id: dict[str, dict] = {}
    for item in raw_reviews:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("id") or "").strip()
        if not rid:
            continue
        label = str(item.get("label") or "").strip()
        if label not in VALID_LABELS:
            label = "low_signal"
        try:
            confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        by_id[rid] = {
            "id": rid,
            "label": label,
            "confidence": round(confidence, 2),
            "evidence_quote": str(item.get("evidence_quote") or "").strip(),
            "short_reason": str(item.get("short_reason") or "").strip() or "Phân loại theo tín hiệu nội dung.",
        }

    normalized = []
    for orig in orig_reviews:
        rid = orig["id"]
        if rid in by_id:
            normalized.append(by_id[rid])
        else:
            normalized.append(
                {
                    "id": rid,
                    "label": "low_signal",
                    "confidence": 0.5,
                    "evidence_quote": "",
                    "short_reason": "Thiếu phân loại chi tiết từ mô hình.",
                }
            )
    return normalized


def _filter_top_risks(raw_risks: list, grounded_reviews: list[dict]) -> list[dict]:
    """Giữ tối đa 3 rủi ro thực tế có nguồn dẫn chứng thật thuộc nhóm verified_insight."""
    verified_ids = {r["id"] for r in grounded_reviews if r.get("label") == "verified_insight"}
    filtered = []
    for item in raw_risks:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        detail = str(item.get("detail") or "").strip()
        sources = [str(rid).strip() for rid in (item.get("source_review_ids") or []) if str(rid).strip() in verified_ids]
        if not title or not sources:
            continue
        severity = str(item.get("severity") or "medium").strip().lower()
        if severity not in ("high", "medium", "low"):
            severity = "medium"
        filtered.append(
            {
                "title": title,
                "detail": detail,
                "severity": severity,
                "source_review_ids": sources,
            }
        )
        if len(filtered) >= 3:
            break
    return filtered


def _normalize_questions(raw_questions: list) -> list[str]:
    """Chuẩn hóa đúng tối đa 3 câu hỏi kiểm chứng shop."""
    cleaned = [str(q).strip() for q in raw_questions if str(q or "").strip()]
    defaults = [
        "Sản phẩm thực tế có đúng thông số và chất liệu như mô tả không?",
        "Shop có chính sách đổi trả hoặc bảo hành như thế nào nếu hàng gặp lỗi sau khi sử dụng?",
        "Sản phẩm có đi kèm đầy đủ phụ kiện và hướng dẫn sử dụng không?",
    ]
    for fallback_q in defaults:
        if len(cleaned) >= 3:
            break
        if fallback_q not in cleaned:
            cleaned.append(fallback_q)
    return cleaned[:3]


def _format_output(
    product_name: str,
    scores: dict,
    top_risks: list[dict],
    questions: list[str],
    grounded_reviews: list[dict],
) -> str:
    """Định dạng chuỗi đầu ra khớp 100% template tại docs/member/README.md §2.3."""
    platform_rating = scores.get("platform_rating")
    real_score = scores.get("real_trust_score")
    delta = scores.get("score_delta")
    direction = scores.get("direction", "insufficient_data")
    verified_ratio = scores.get("verified_ratio", 0.0)
    trust_level = scores.get("trust_level", "insufficient_data")

    platform_str = f"{platform_rating:.1f}/5.0" if isinstance(platform_rating, (int, float)) else "Chưa rõ"
    if isinstance(real_score, (int, float)):
        delta_sign = "+" if isinstance(delta, (int, float)) and delta > 0 else ""
        delta_str = f"{delta_sign}{delta:.1f}" if isinstance(delta, (int, float)) else "0.0"
        score_line = f"- Điểm sàn: {platform_str} | Điểm tin cậy thực: {real_score:.1f}/5.0 (Chênh lệch: {delta_str})"
    else:
        score_line = (
            f"- Điểm sàn: {platform_str} | Điểm tin cậy thực: Chưa đủ đánh giá về chất lượng sản phẩm "
            "(toàn bộ đánh giá thuộc nhóm lỗi vận chuyển)"
        )

    lines = [
        f"[ReviewShield] Kết quả phân tích: {product_name}",
        score_line,
        f"- Chiều biến động (direction): {direction}",
        f"- Tỷ lệ trải nghiệm thật (verified_ratio): {verified_ratio:.1f}% | Mức tin cậy: {trust_level}",
    ]
    if scores.get("logistics_warning"):
        lines.append("- Cảnh báo vận chuyển: Có đánh giá chỉ phản ánh lỗi shipper/giao hàng (đã tách khỏi điểm chất lượng sản phẩm).")

    lines.append("")
    lines.append("Top 3 rủi ro thực tế:")
    if top_risks:
        for idx, risk in enumerate(top_risks, start=1):
            src = ", ".join(risk["source_review_ids"])
            detail_part = f": {risk['detail']}" if risk.get("detail") else ""
            lines.append(f"{idx}. {risk['title']}{detail_part} (Nguồn: {src})")
    else:
        lines.append("- Chưa ghi nhận nhược điểm lặp lại từ nhóm đánh giá trải nghiệm cụ thể.")

    lines.append("")
    lines.append("3 câu hỏi kiểm chứng shop (Bản nháp gợi ý — người mua tự duyệt trước khi gửi):")
    for idx, q in enumerate(questions, start=1):
        lines.append(f"{idx}. {q}")

    lines.append("")
    lines.append("Chi tiết phân loại review:")
    for rev in grounded_reviews:
        rating_val = rev.get("rating", "?")
        lines.append(
            f'- [{rev["id"]} | {rating_val}★ | {rev["label"]}] '
            f'"{rev.get("evidence_quote", "")}" — {rev.get("short_reason", "")}'
        )

    return "\n".join(lines)


def _require_tools() -> tuple:
    """Lấy 3 công cụ tất định từ codebase/tools.py theo đúng hợp đồng docs/member/README.md §2.2."""
    preprocess = getattr(tools, "preprocess_reviews", None)
    verify = getattr(tools, "verify_grounding", None)
    score = getattr(tools, "compute_real_trust_score", None)
    missing = [
        name
        for name, fn in (
            ("preprocess_reviews", preprocess),
            ("verify_grounding", verify),
            ("compute_real_trust_score", score),
        )
        if fn is None
    ]
    if missing:
        raise NotImplementedError(
            "Thiếu công cụ %s trong codebase/tools.py — cần merge nhánh feat/2a202603427-tools-and-ui."
            % ", ".join(missing)
        )
    return preprocess, verify, score


def answer(text: str) -> dict:
    """Điều phối pipeline 3 chặng của ReviewShield và trả về {"output": str, "data": dict}."""
    # Chặng 0: Chặn yêu cầu ngoài phạm vi, đầu vào rỗng và prompt injection trước khi gọi LLM.
    refusal = _check_scope_and_safety(text)
    if refusal is not None:
        return refusal

    preprocess_reviews, verify_grounding, compute_real_trust_score = _require_tools()

    # Chặng 1: Tiền xử lý tất định.
    preprocessed = preprocess_reviews(text)
    orig_reviews = preprocessed.get("reviews") or []
    if not orig_reviews:
        warnings = preprocessed.get("warnings") or []
        reason = "; ".join(warnings) if warnings else "Không tìm thấy đánh giá hợp lệ sau khi lọc dòng trống."
        return _refusal_response(reason, "no_valid_reviews")

    product_name = str(preprocessed.get("product_name") or "Sản phẩm chưa đặt tên").strip()
    platform_rating = preprocessed.get("platform_rating")

    # Chặng 2: Gọi AI thật trả JSON theo schema, tự động retry tối đa 1 lần nếu JSON lỗi.
    llm_payload = json.dumps(
        {
            "product_name": product_name,
            "platform_rating": platform_rating,
            "reviews": [
                {
                    "id": r["id"],
                    "rating": r["rating"],
                    "text": r["text"],
                    "duplicate_group_size": r.get("duplicate_group_size", 1),
                }
                for r in orig_reviews
            ],
        },
        ensure_ascii=False,
    )

    parsed = None
    last_error = ""
    current_prompt = f"Phân tích danh sách đánh giá sản phẩm sau và chỉ trả về JSON hợp lệ:\n{llm_payload}"
    for attempt in range(MAX_JSON_RETRIES + 1):
        reply = call_model(SYSTEM, current_prompt)
        try:
            parsed = _extract_json_object(reply["text"])
            break
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            if attempt < MAX_JSON_RETRIES:
                note(f"retry_json: {last_error[:80]}")
                current_prompt = (
                    f"Phản hồi trước không đúng JSON hợp lệ ({last_error}). "
                    "Hãy trả lại CHỈ MỘT đối tượng JSON thuần chứa đủ 3 khóa "
                    "`reviews`, `top_risks`, `questions_for_seller` cho dữ liệu sau:\n"
                    f"{llm_payload}"
                )
            else:
                note(f"dừng: json_parse_failed ({last_error[:80]})")
                return {
                    "output": (
                        "[ReviewShield] Không thể đọc định dạng JSON từ mô hình sau 1 lần thử lại. "
                        "Vui lòng thử lại hoặc kiểm tra cấu hình model trong .env."
                    ),
                    "data": {"error": "json_parse_failed", "detail": last_error},
                }

    llm_reviews = _normalize_llm_reviews(parsed["reviews"], orig_reviews)

    # Chặng 3: Grounding Guard + Tính Điểm tin cậy thực tất định bằng Python.
    grounded_result = verify_grounding(orig_reviews, llm_reviews)
    grounded_reviews = grounded_result["reviews"]
    scores = compute_real_trust_score(grounded_reviews, platform_rating)
    top_risks = _filter_top_risks(parsed["top_risks"], grounded_reviews)
    questions = _normalize_questions(parsed["questions_for_seller"])

    output_text = _format_output(product_name, scores, top_risks, questions, grounded_reviews)
    return {
        "output": output_text,
        "data": {
            "product_name": product_name,
            "scores": scores,
            "grounding_rate": grounded_result.get("grounding_rate", 100.0),
            "fallback_count": grounded_result.get("fallback_count", 0),
            "top_risks": top_risks,
            "questions_for_seller": questions,
            "reviews": grounded_reviews,
            "warnings": preprocessed.get("warnings") or [],
        },
    }
