# docs/member — Hợp Đồng Giao Tiếp & Phân Công Task Theo Thành Viên

Thư mục này chứa tài liệu giao việc chi tiết cho 4 thành viên nhóm **AnhNhoEM** (`L3A — Track D: ReviewShield`), bám sát `TEAMS.md`, `spec.md`, `docs/SRS.md`, `docs/ARCHITECTURE.md` và `docs/AI_PROMPT_AND_SCORING.md`.

## 1. Danh sách tài liệu task theo thành viên

| STT | Thành viên | Mã HV | Module | File tài liệu | Nhánh Git |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | Dương Quang Bảo (Đội trưởng) | `2A202603362` | Lõi AI & Điều phối Pipeline | `member-1-core-ai-agent.md` | `feat/2a202603362-core-ai-agent` |
| 2 | Thành viên 2 | `2A202603427` | Công cụ Tất định & Demo UI | `member-2-tools-ui.md` | `feat/2a202603427-tools-and-ui` |
| 3 | Thành viên 3 | `2A202603646` | Dữ liệu, Evidence & Eval | `member-3-data-evidence-eval.md` | `data/2a202603646-samples-evidence-eval` |
| 4 | Thành viên 4 | `2A202603483` | Cost, Validation & Slide Demo | `member-4-cost-validation-slides.md` | `docs/2a202603483-cost-validation-slides` |

## 2. Hợp đồng giao tiếp dùng chung (Shared Contracts)

Để 4 thành viên code và chuẩn bị dữ liệu song song không xung đột, mọi module phải tuân thủ 3 hợp đồng sau:

### 2.1. Schema file mẫu `data/samples/*.json` (Module 3 tạo → Module 2 & 1 đọc)
```json
{
  "product_id": "sp_01",
  "product_name": "Tai nghe Bluetooth X100",
  "category": "phu_kien_dien_tu",
  "platform": "Shopee",
  "platform_rating": 4.9,
  "expected_direction": "lower_than_platform",
  "reviews": [
    {
      "id": "r1",
      "author": "user_01",
      "rating": 5,
      "text": "Giao hàng nhanh, chưa dùng nhưng cho shop 5 sao lấy xu"
    }
  ]
}
```
* `platform_rating`: float trong `[1.0, 5.0]`.
* `author`: bắt buộc ẩn danh (`user_01`, `user_02`...), tuyệt đối không chứa tên thật/SĐT.
* `rating`: int trong `[1, 5]`.

### 2.2. Chữ ký hàm trong `codebase/tools.py` (Module 2 viết → Module 1 gọi)
```python
@tool
def preprocess_reviews(raw_input: str) -> dict:
    # Return:
    # {
    #   "product_name": str,
    #   "platform_rating": float | None,
    #   "total_raw": int,
    #   "removed_empty": int,
    #   "reviews": [{"id": "r1", "rating": 5, "text": "...", "duplicate_group_size": 1}],
    #   "warnings": [str]
    # }

@tool
def verify_grounding(original_reviews: list[dict], llm_reviews: list[dict]) -> dict:
    # Return:
    # {
    #   "reviews": [{"id": "r1", "label": "...", "confidence": 0.9, "evidence_quote": "...", "short_reason": "...", "grounded": True}],
    #   "grounding_rate": float,   # 0.0 -> 100.0 (phải đạt 100.0 sau fallback)
    #   "fallback_count": int
    # }

@tool
def compute_real_trust_score(reviews: list[dict], platform_rating: float | None = None) -> dict:
    # Return:
    # {
    #   "platform_rating": float,
    #   "real_trust_score": float | None,
    #   "score_delta": float | None,
    #   "direction": str,          # "near_platform" | "lower_than_platform" | "higher_than_platform" | "insufficient_data"
    #   "verified_ratio": float,   # 0.0 -> 100.0
    #   "trust_level": str,        # "high" | "medium" | "low" | "insufficient_data"
    #   "label_counts": {"verified_insight": int, "low_signal": int, "suspicious_pattern": int, "logistics_only": int},
    #   "logistics_warning": bool
    # }
```

### 2.3. Hợp đồng `answer(text)` & Mẫu định dạng `"output"` (Module 1 viết → Module 2 UI, `eval/run_eval.py`, `cost/simulate.py` gọi)
* `answer(text: str) -> dict` luôn trả về dict có khóa `"output": str` theo cấu trúc cố định dưới đây để TV3 viết `pass_criterion` trong `eval/benchmark.csv` khớp 100%:
```text
[ReviewShield] Kết quả phân tích: <product_name>
- Điểm sàn: <platform_rating>/5.0 | Điểm tin cậy thực: <real_trust_score>/5.0 (Chênh lệch: <score_delta>)
- Chiều biến động (direction): <near_platform | lower_than_platform | higher_than_platform | insufficient_data>
- Tỷ lệ trải nghiệm thật (verified_ratio): <X>% | Mức tin cậy: <high | medium | low | insufficient_data>

Top 3 rủi ro thực tế:
1. <title>: <detail> (Nguồn: rX, rY)

3 câu hỏi kiểm chứng shop (Bản nháp gợi ý — người mua tự duyệt trước khi gửi):
1. <câu hỏi 1>
2. <câu hỏi 2>
3. <câu hỏi 3>

Chi tiết phân loại review:
- [r1 | <rating>★ | <label>] "<evidence_quote>" — <short_reason>
```
* Có thể đính kèm thêm khóa phụ `"data": dict` (structured payload gồm `scores`, `top_risks`, `questions_for_seller`, `reviews`) để `codebase/app.py` render UI mà không cần parse lại text; khung `run_eval.py` và `simulate.py` chỉ đọc khóa `"output"`.
* **Ca từ chối (`tu_choi`):** Trả về đủ 2 ý: (1) Nêu rõ giới hạn không thực hiện (không cào link trực tiếp / không tự nhắn shop / không bỏ qua quy tắc an toàn) + (2) Hướng dẫn chọn mẫu có sẵn hoặc dán văn bản review.

## 3. Quy ước định danh, Model & Encoding dùng chung
* **Định danh ID:** `product_id` (`sp_01`..`sp_30`), `review_id` (`r1`, `r2`...), `author` (`user_01`, `user_02`...), `benchmark_id` (`RS01`..`RS30`), phỏng vấn (`P1`, `P2`, `P3`...).
* **Model thống nhất:** TV1, TV3 (`eval`) và TV4 (`simulate`) phải chạy **cùng 1 cặp `MODEL_PROVIDER` + `MODEL_NAME`** trong `.env` để `cost/simulate.py` ghép được tỷ lệ đạt và tính *Chi phí / task thành công*.
* **Encoding:** Toàn bộ `.py`, `.json`, `.csv`, `.yaml`, `.md` bắt buộc lưu **UTF-8** (Excel xuất *CSV UTF-8*).

## 4. Phân bổ thu thập dữ liệu thật đa sàn (Offline, không nhúng crawler vào app)
* **Tổng mục tiêu:** 25–30 sản phẩm thật ẩn danh trong `data/samples/*.json` (**Shopee:** 10–12 SP, **Tiki:** 8–10 SP, **TikTok Shop / Lazada:** 5–8 SP).
* **Phân công:** Thành viên 3 chủ trì thu thập 15–20 SP (Tiki API công khai + Shopee) và chuẩn hóa toàn bộ schema/ẩn danh PII; Thành viên 4 hỗ trợ gom 10 SP từ Shopee/TikTok Shop trong lúc chờ Module 1+2 hoàn thiện để chạy `simulate`.
* **Nguyên tắc:** Không xây server-side crawler trong `codebase/`, không vượt CAPTCHA/anti-bot, không commit dữ liệu thô chưa ẩn danh.

## 5. Quy tắc chung bắt buộc
* Đọc và tuân thủ toàn bộ `AGENTS.md` (đặc biệt Mục 2 — BTC Hard Rules và Mục 5 — Quy tắc Git).
* Tuyệt đối không sửa 4 file khung: `run.py`, `codebase/tracing.py`, `eval/run_eval.py`, `cost/simulate.py`.
* Mọi PR vào `main` phải chạy qua `python run.py check` trước khi gửi duyệt.
