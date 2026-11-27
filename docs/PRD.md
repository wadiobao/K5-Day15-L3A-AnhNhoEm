# PRD — Tài Liệu Yêu Cầu Sản Phẩm (ReviewShield)

## 1. Thông tin chung
* **Sản phẩm:** ReviewShield (Làn D — Thương mại điện tử)
* **Kho lưu trữ:** `K5-Day15-L3A-AnhNhoEm`
* **Mục tiêu MVP:** Ship nhanh sản phẩm chạy ổn định trên khung Python của repo (`run.py`, `codebase/`), gọi API AI thật, giải quyết nỗi đau review nhiễu đạt ngưỡng, vượt qua bộ thử hơn 20 tình huống (`eval/benchmark.csv`) và có slide/video demo rõ ràng.

## 2. Vấn đề & Giá trị cốt lõi
* **Vấn đề:** Điểm sao trung bình trên sàn TMĐT bị nhiễu bởi review nhận xu, lặp mẫu seeding và đánh giá 1 sao do lỗi vận chuyển, khiến người mua dễ chọn nhầm hàng và tốn thời gian lọc nhược điểm thật.
* **Giá trị cốt lõi:**
  1. Phân loại từng review vào 4 tín hiệu (`verified_insight`, `low_signal`, `suspicious_pattern`, `logistics_only`) kèm trích dẫn nguyên văn.
  2. Tính lại **Điểm tin cậy thực (Real Trust Score)** so sánh trực diện với điểm hiển thị trên sàn.
  3. Tổng hợp **Top 3 rủi ro thực tế** và sinh **3 câu hỏi kiểm chứng shop** (chỉ gợi ý bản nháp, không tự gửi).

## 3. Phạm vi MVP (In-Scope vs Out-of-Scope)
| Hạng mục | Trong phạm vi (In-Scope) | Ngoài phạm vi (Out-of-Scope) |
| :--- | :--- | :--- |
| **Đầu vào** | Chọn từ 25–30 mẫu thật trong `data/samples/` hoặc dán trực tiếp cụm review text/JSON. | Server-side crawler tự cào link Shopee/TikTok Shop. |
| **Lõi AI** | Gọi API LLM thật qua `codebase/ai.py` (Structured Output JSON) + kiểm tra trích dẫn & tính điểm bằng Python tại `codebase/tools.py`. | Huấn luyện hoặc fine-tune mô hình riêng. |
| **Giao diện & Kiểm thử** | Giao diện 1 màn hình (`codebase/app.py`) + chạy chuẩn khung `python run.py eval`, `score`, `simulate`. | Đăng nhập, thanh toán, lưu lịch sử đa người dùng, app di động. |

## 4. Tiêu chí thành công (Khớp `spec.md §7` và `eval/metric_spec.yaml`)
* `label_accuracy >= 85%`
* `direction_match >= 85%`
* `citation_grounding == 100%`
* `actionable_quality >= 80%`
* Chạy vượt qua toàn bộ kiểm tra của `python run.py check`, `eval`, `simulate`.
