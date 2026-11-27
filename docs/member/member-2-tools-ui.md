# Task Specification — Thành viên 2: Công cụ Tất định & Giao diện Demo

* **Phụ trách:** Thành viên 2 (`2A202603427`)
* **Module:** `Deterministic Tools & Demo UI`
* **Nhánh Git:** `feat/2a202603427-tools-and-ui`
* **File được sửa:** `codebase/tools.py`, `codebase/app.py` (nếu thêm thư viện UI như `streamlit`/`gradio`, báo Đội trưởng cập nhật `requirements.txt`)
* **File cấm sửa:** `run.py`, `codebase/tracing.py`, `eval/run_eval.py`, `cost/simulate.py`

---

## 1. Đầu vào (Input)

### 1.1. `codebase/tools.py`
* `preprocess_reviews(raw_input: str)`: Chuỗi JSON (schema `data/samples/*.json`) hoặc văn bản tự do nhiều dòng dạng `[số sao] nội dung`.
* `verify_grounding(original_reviews: list[dict], llm_reviews: list[dict])`: Danh sách review gốc (có `id`, `text`) và danh sách phân loại từ LLM (có `id`, `label`, `confidence`, `evidence_quote`, `short_reason`).
* `compute_real_trust_score(reviews: list[dict], platform_rating: float | None = None)`: Danh sách review đã có `rating` (1–5) và `label` (1 trong 4 nhãn hợp lệ), kèm `platform_rating` gốc nếu có.

### 1.2. `codebase/app.py`
* Danh sách file mẫu từ thư mục `data/samples/*.json`.
* Hoặc văn bản / JSON do người dùng dán trực tiếp trên giao diện.

---

## 2. Đầu ra (Output)

### 2.1. `codebase/tools.py`
Mỗi hàm bắt buộc gắn decorator `@tool` (từ `tracing`) và có docstring ghi đủ 4 ý: **tên · input · output · không tác động ra ngoài**.
* `preprocess_reviews` → `dict` gồm `product_name`, `platform_rating`, `total_raw`, `removed_empty`, `reviews` (mỗi item có `id`, `rating`, `text`, `duplicate_group_size`), `warnings`.
* `verify_grounding` → `dict` gồm `reviews` (mỗi item có `evidence_quote` đảm bảo 100% là chuỗi con nguyên văn của `text` gốc, cờ `grounded: True`), `grounding_rate: 100.0`, `fallback_count: int`.
* `compute_real_trust_score` → `dict` gồm `platform_rating`, `real_trust_score` (`float | None`), `score_delta` (`float | None`), `direction` (`near_platform` / `lower_than_platform` / `higher_than_platform` / `insufficient_data`), `verified_ratio`, `trust_level` (`high` / `medium` / `low` / `insufficient_data`), `label_counts`, `logistics_warning`.

### 2.2. `codebase/app.py`
* Giao diện 1 màn hình (CLI nâng cao hoặc web local nhẹ khởi chạy được qua lệnh `python run.py` mà không sửa `run.py`) hiển thị rõ:
  1. Khu vực chọn mẫu từ `data/samples/` hoặc dán review tùy chỉnh.
  2. Khối so sánh trực diện: **Điểm sàn** vs **Điểm tin cậy thực**, độ lệch `score_delta`, tỷ lệ `verified_ratio`, mức tin cậy `trust_level`.
  3. **Top 3 rủi ro thực tế** kèm ID review dẫn chứng.
  4. **3 câu hỏi kiểm chứng shop** (ghi rõ là bản nháp, có nút/chỉ dẫn copy, không tự gửi).
  5. Bảng chi tiết từng review: nhãn màu/ký hiệu rõ ràng, trích dẫn `evidence_quote` nguyên văn, lý do ngắn.

---

## 3. Logic xử lý (Processing Logic)

### 3.1. `preprocess_reviews(raw_input: str)`
1. Thử `json.loads(raw_input)`. Nếu thất bại, parse từng dòng bằng regex hỗ trợ các dạng phổ biến: `[5] text`, `[5 sao] text`, `5* - text`, `5 sao: text`.
2. Loại bỏ review có `text` trống hoặc chỉ gồm khoảng trắng/emoji vô nghĩa; ghi nhận `removed_empty`.
3. Kiểm tra `rating`: phải là số nguyên trong `[1, 5]`; nếu ngoài khoảng thì cảnh báo và loại/báo lỗi rõ ràng (theo FR-02).
4. Chuẩn hóa khoảng trắng liên tiếp (`re.sub(r"\s+", " ", text).strip()`), giữ nguyên lỗi chính tả/tiếng Việt không dấu của người mua.
5. Tính `duplicate_group_size`: so sánh chuỗi sau khi hạ chữ thường + bỏ dấu câu nhẹ; gán số lượng review trùng lặp vào từng review trong nhóm.
6. Cắt lô tối đa **20 review**: nếu tổng > 20, ưu tiên lấy mẫu phân tầng (stratified) giữ đủ các mức 1–5 sao để không mất nhóm review tiêu cực.

### 3.2. `verify_grounding(original_reviews, llm_reviews)`
1. Tạo map `orig_map = {r["id"]: r["text"] for r in original_reviews}`.
2. Định nghĩa hàm chuẩn hóa so khớp `norm(s)`: hạ chữ thường và gộp nhiều khoảng trắng thành 1.
3. Với mỗi review trong `llm_reviews`:
   * Nếu `evidence_quote` khác rỗng và `norm(evidence_quote) in norm(orig_text)` → giữ nguyên `evidence_quote`, `grounded = True`.
   * Nếu KHÔNG khớp (AI tự viết lại hoặc bịa từ) → **Fallback tất định**: trích đoạn câu đầu tiên (hoặc 12 từ đầu tiên) nguyên văn từ `orig_text`, tăng `fallback_count += 1`, đánh dấu `grounded = True`.
4. Kết hợp lại đầy đủ trường `rating` và `text` gốc vào output để truyền thẳng sang `compute_real_trust_score`.

### 3.3. `compute_real_trust_score(reviews, platform_rating)`
Theo đúng `docs/AI_PROMPT_AND_SCORING.md`:
1. `WEIGHT_MAP = {"verified_insight": 1.00, "low_signal": 0.15, "suspicious_pattern": 0.10, "logistics_only": 0.00}`.
2. Nếu `platform_rating is None`, tính mặc định bằng trung bình cộng `rating` của toàn bộ `reviews` (làm tròn 1 chữ số thập phân).
3. Tính `weighted_sum` và `total_weight`.
4. **Xử lý biên chia cho 0:** Nếu `total_weight == 0` (toàn bộ review là `logistics_only`):
   * `real_trust_score = None`, `score_delta = None`, `direction = "insufficient_data"`, `trust_level = "insufficient_data"`, `logistics_warning = True`.
5. Nếu `total_weight > 0`:
   * `real_trust_score = round(weighted_sum / total_weight, 1)`
   * `score_delta = round(real_trust_score - platform_rating, 1)`
   * `verified_ratio = round(100.0 * count_verified / len(reviews), 1)`
   * Xác định `direction`:
     * `abs(score_delta) <= 0.3` → `"near_platform"`
     * `score_delta < -0.3` → `"lower_than_platform"`
     * `score_delta > 0.3` → `"higher_than_platform"`
   * Xác định `trust_level`:
     * `high`: `verified_ratio >= 50.0` và `abs(score_delta) <= 0.3` và `real_trust_score >= 4.0`
     * `low`: `verified_ratio < 35.0` hoặc `score_delta <= -0.7` hoặc `real_trust_score < 3.5`
     * `medium`: các trường hợp còn lại.
   * `logistics_warning = True` nếu có ít nhất 1 review `logistics_only`.

---

## 4. Quy tắc nghiệp vụ (Business Rules)

1. **100% tất định:** Không gọi bất kỳ model AI nào trong `codebase/tools.py`.
2. **Grounding Guard tuyệt đối:** Không bao giờ trả về một `evidence_quote` không tồn tại nguyên văn trong văn bản review gốc (`citation_grounding == 100%`).
3. **Không phình scope UI:** Không làm đăng nhập, không lưu database ngoài, không tự gửi tin nhắn shop.
4. **Giữ tương thích `python run.py`:** `codebase/app.py` vẫn phải khởi chạy được qua `python run.py` (không sửa `run.py`).

---

## 5. Tiêu chí đánh giá (Acceptance Criteria)

* Cả 3 hàm trong `codebase/tools.py` có `@tool`, type hints, docstring đủ 4 ý và được `tracing.py` ghi nhận khi chạy.
* `citation_grounding == 100%` kể cả khi cố tình truyền `evidence_quote` sai từ LLM.
* Không lỗi `ZeroDivisionError` khi toàn bộ đầu vào là `logistics_only` hoặc danh sách rỗng.
* `codebase/app.py` hiển thị đầy đủ 4 khối thông tin trên 1 màn hình, xử lý lỗi mượt mà (giữ nguyên dữ liệu đã nhập khi API lỗi).

---

## 6. Kế hoạch kiểm thử (Testing Checklist)

Chạy script test cục bộ (không commit file test tạm) cho các ca sau trước khi mở PR:
1. **Unit test `preprocess_reviews`:**
   * Input có 3 review trống + 3 review giống hệt nhau → `removed_empty == 3`, 3 review trùng có `duplicate_group_size == 3`.
   * Input 35 review (đủ 1–5 sao) → cắt còn 20 review và vẫn còn review 1–2 sao.
   * Input có rating = 0 hoặc 6 → báo lỗi rõ ràng.
2. **Unit test `verify_grounding`:**
   * Quote đúng nguyên văn (khác chữ hoa/khoảng trắng) → giữ nguyên, `fallback_count == 0`.
   * Quote bị LLM sửa chữ / bịa → kích hoạt fallback, `fallback_count == 1`, kết quả cuối vẫn nằm nguyên văn trong `orig_text`.
3. **Unit test `compute_real_trust_score`:**
   * Case hàng tốt thật (toàn `verified_insight` 4–5 sao) → `direction == "near_platform"`, `trust_level == "high"`.
   * Case seeding dày (nhiều 5 sao `low_signal`/`suspicious_pattern`, vài 1–2 sao `verified_insight`) → `direction == "lower_than_platform"`, `trust_level == "low"`.
   * Case oan do shipper (1 sao `logistics_only`, 5 sao `verified_insight`) → `direction == "higher_than_platform"`, `logistics_warning == True`.
   * Case 100% `logistics_only` → `real_trust_score is None`, không crash.
4. **Smoke test UI:** Chạy `python run.py`, chọn 1 mẫu trong `data/samples/` và dán thử 1 cụm review tay, xác nhận hiển thị đúng không vỡ layout/encoding tiếng Việt.
