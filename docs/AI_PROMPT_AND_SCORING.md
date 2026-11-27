# AI_PROMPT_AND_SCORING — Đặc Tả Prompt AI, 4 Nhãn & Công Thức Tính Điểm

Tài liệu này là nguồn chuẩn để cài đặt prompt trong `codebase/agent.py` / `codebase/ai.py` và logic tất định trong `codebase/tools.py`.

## 1. Bảng 4 nhãn tín hiệu & trọng số chất lượng

| Mã nhãn (`label`) | Tên hiển thị | Trọng số (`weight`) | Quy tắc phân định ranh giới |
| :--- | :--- | :---: | :--- |
| `verified_insight` | Trải nghiệm cụ thể | **1.00** | Nêu ít nhất 1 chi tiết thực tế về bản thân sản phẩm (chất liệu, kích cỡ, độ bền, hiệu năng, mùi vị, trải nghiệm sau khi dùng). |
| `low_signal` | Nhận xu / Thiếu thông tin | **0.15** | Khen/chê chung chung, chưa sử dụng ("giao nhanh, chưa dùng cho 5 sao"), nhận xu, chèn thơ hoặc ký tự vô nghĩa. |
| `suspicious_pattern` | Nghi vấn lặp mẫu | **0.10** | Lặp cấu trúc câu bất thường (`duplicate_group_size >= 2`) hoặc văn phong quảng cáo gượng ép giống mô tả shop. |
| `logistics_only` | Lỗi vận chuyển | **0.00** | Chỉ nói về shipper, thời gian giao hàng hoặc vỏ hộp ngoài, không nhận xét chất lượng sản phẩm bên trong. |

## 2. System Prompt chuẩn

```text
Bạn là bộ máy phân tích tín hiệu đánh giá sản phẩm thương mại điện tử của hệ thống ReviewShield.

NHIỆM VỤ:
Đọc danh sách đánh giá sản phẩm (JSON) và trả về kết quả phân tích dưới dạng JSON hợp lệ theo đúng schema.

QUY TẮC BẮT BUỘC:
1. Gán mỗi review vào ĐÚNG 1 trong 4 nhãn:
   - "verified_insight": Có chi tiết trải nghiệm thực tế về sản phẩm.
   - "low_signal": Khen/chê chung chung, chưa dùng, nhận xu, chèn chữ vô nghĩa.
   - "suspicious_pattern": Trùng lặp mẫu câu bất thường (đặc biệt khi duplicate_group_size >= 2) hoặc văn phong quảng cáo gượng ép.
   - "logistics_only": Chỉ nói về shipper, giao hàng hoặc bao bì vận chuyển, không đánh giá chất lượng hàng.
2. Trích dẫn bằng chứng (`evidence_quote`):
   - PHẢI sao chép NGUYÊN VĂN một cụm từ ngắn (3–18 từ) có thật trong trường `text` của review đó.
   - TUYỆT ĐỐI không viết lại, không sửa chính tả, không bịa từ.
3. Lý do ngắn (`short_reason`): Tối đa 15 từ tiếng Việt, trung lập, không khẳng định tuyệt đối "giả 100%".
4. Tổng hợp rủi ro (`top_risks`): Tối đa 3 nhược điểm thực tế từ nhóm "verified_insight", kèm `source_review_ids` thật. Nếu không có nhược điểm, trả về `[]`.
5. Câu hỏi kiểm chứng shop (`questions_for_seller`): Sinh đúng 3 câu hỏi ngắn gọn, thực tế để người mua nhắn hỏi shop trước khi đặt hàng.
6. Chỉ trả về JSON thuần, không kèm văn bản ngoài JSON.
```

## 3. JSON Schema đầu ra từ LLM

```json
{
  "reviews": [
    {
      "id": "r1",
      "label": "low_signal",
      "confidence": 0.95,
      "evidence_quote": "chưa dùng nhưng cho shop 5 sao",
      "short_reason": "Chưa trải nghiệm thực tế sản phẩm."
    }
  ],
  "top_risks": [
    {
      "title": "Pin tụt nhanh hơn mô tả",
      "detail": "Người dùng thực tế phản hồi pin chỉ dùng khoảng 1.5 tiếng.",
      "severity": "high",
      "source_review_ids": ["r2"]
    }
  ],
  "questions_for_seller": [
    "Thời lượng pin nghe liên tục thực tế ở mức âm lượng 70% là bao lâu?",
    "Shop có bảo hành đổi mới nếu pin yếu hoặc mic bị rè không?",
    "Sản phẩm đi kèm cáp sạc loại nào và thời gian sạc đầy mất bao lâu?"
  ]
}
```

## 4. Công thức Điểm tin cậy thực (`codebase/tools.py`)

```python
WEIGHT_MAP = {
    "verified_insight": 1.00,
    "low_signal": 0.15,
    "suspicious_pattern": 0.10,
    "logistics_only": 0.00,
}

# weighted_sum = sum(r["rating"] * WEIGHT_MAP[r["label"]] for r in reviews)
# total_weight = sum(WEIGHT_MAP[r["label"]] for r in reviews)
# real_trust_score = round(weighted_sum / total_weight, 1) if total_weight > 0 else None
# score_delta = round(real_trust_score - platform_rating, 1) if real_trust_score is not None else None
# verified_ratio = round(100.0 * sum(1 for r in reviews if r["label"] == "verified_insight") / len(reviews), 1)
```

### Quy tắc phân mức cảnh báo (`trust_level`)
* `high`: `verified_ratio >= 50%` và `abs(score_delta) <= 0.3` và `real_trust_score >= 4.0`.
* `low`: `verified_ratio < 35%` hoặc `score_delta <= -0.7` hoặc `real_trust_score < 3.5`.
* `medium`: Các trường hợp còn lại.
