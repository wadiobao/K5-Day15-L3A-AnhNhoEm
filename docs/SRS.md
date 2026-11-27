# SRS — Đặc Tả Yêu Cầu Phần Mềm (ReviewShield)

## 1. Yêu cầu chức năng (Functional Requirements)

| Mã | Tên chức năng | Mô tả & Ánh xạ file trong repo | Tiêu chí nghiệm thu |
| :--- | :--- | :--- | :--- |
| **FR-01** | Nạp mẫu sản phẩm thật | Đọc danh sách 25–30 sản phẩm mẫu ẩn danh từ `data/samples/` hiển thị trên `codebase/app.py`. | Chọn mẫu là nạp ngay tên sản phẩm, điểm sàn và danh sách review gốc. |
| **FR-02** | Nhập review tùy chỉnh | Cho phép dán văn bản review (`[số sao] nội dung`) hoặc JSON trực tiếp vào `codebase/app.py` / `agent.py`. | Báo lỗi rõ nếu rỗng hoặc rating ngoài 1–5; hỗ trợ 3–50 review/lượt. |
| **FR-03** | Tiền xử lý tất định | `@tool preprocess_reviews` trong `codebase/tools.py` lọc dòng trống, chuẩn hóa khoảng trắng và đếm `duplicate_group_size`. | Review rỗng bị loại trước khi gửi AI; review trùng lặp có `duplicate_group_size >= 2`. |
| **FR-04** | Gọi API AI thật | `call_model(system, user)` trong `codebase/ai.py` (giữ `@model_call`) gọi LLM thật với Structured Output JSON. | Trả về đủ `text`, `model`, `tokens_in`, `tokens_out` lấy từ `usage` thực tế của API. |
| **FR-05** | Kiểm chứng trích dẫn | `@tool verify_grounding` trong `codebase/tools.py` đối chiếu `evidence_quote` với nội dung review gốc. | Đạt 100% `citation_grounding`; tự động fallback câu gốc ngắn nhất nếu AI lệch ký tự. |
| **FR-06** | Tính Điểm tin cậy thực | `@tool compute_real_trust_score` trong `codebase/tools.py` tính điểm trung bình có trọng số và `score_delta`. | Làm tròn 1 chữ số thập phân; không chia cho 0 khi toàn bộ là `logistics_only`. |
| **FR-07** | Tổng hợp rủi ro & câu hỏi | Trích xuất tối đa 3 rủi ro từ `verified_insight` kèm `source_review_ids` và 3 câu hỏi kiểm chứng shop. | Mọi rủi ro đều có ID review thật làm dẫn chứng; không tự bịa nhược điểm khi hàng tốt. |
| **FR-08** | Tương thích khung Eval & Cost | `codebase/agent.py` giữ đúng chữ ký `answer(text) -> {"output": str}` để `eval/run_eval.py` và `cost/simulate.py` gọi trực tiếp. | `python run.py check`, `eval --try`, `simulate --try` chạy không lỗi. |

## 2. Yêu cầu phi chức năng (Non-Functional Requirements)
* **Hiệu năng:** Thời gian phản hồi trung bình dưới 4 giây cho lô 15–20 review; timeout 25 giây.
* **Độ tin cậy:** Retry tối đa 1 lần nếu LLM trả JSON lỗi cú pháp.
* **Bảo mật & Riêng tư:** Khóa API chỉ đặt trong `.env` (`MODEL_PROVIDER`, `MODEL_NAME`, `API_KEY`); dữ liệu mẫu ẩn danh 100%.
* **Khả năng cài đặt:** Tuân thủ khung Python 3.10+; mọi thư viện ngoài khai báo rõ trong `requirements.txt`.
