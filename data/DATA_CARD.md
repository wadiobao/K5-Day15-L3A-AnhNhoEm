# DATA CARD — Dữ Liệu Dự Án ReviewShield

## 1. Nguồn dữ liệu
* **Loại dữ liệu:** Đánh giá sản phẩm công khai trên các sàn thương mại điện tử phổ biến tại Việt Nam (Shopee, TikTok Shop, Tiki...) do nhóm tự thu thập phục vụ Track D.
* **Quy mô:** 25–30 cụm đánh giá sản phẩm (mỗi cụm gồm 6–15 bình luận tiêu biểu trải đều từ 1 đến 5 sao), phân bổ trên 4–5 ngành hàng tiêu dùng phổ biến.

## 2. Quy trình làm sạch & Ẩn danh (Privacy & Compliance)
* **Không lưu thông tin cá nhân (PII):** Toàn bộ tên tài khoản, số điện thoại, địa chỉ, mã đơn hàng và ảnh có khuôn mặt người mua đều bị loại bỏ trước khi đưa vào repo; tên tác giả được thay bằng mã ẩn danh (`user_01`, `user_02`...).
* **Không commit dữ liệu cấm:** Không lưu file dữ liệu nội bộ của BTC hoặc dữ liệu có bản quyền hạn chế.
* **Giữ nguyên ngôn ngữ tự nhiên:** Giữ nguyên lỗi chính tả, tiếng Việt không dấu và teencode đặc trưng của người mua để bài kiểm thử phản ánh đúng điều kiện thực tế.

## 3. Cấu trúc tệp lưu trữ
* `data/samples/*.json`: Kho sản phẩm mẫu có sẵn dùng cho màn hình demo `codebase/app.py`.
* `eval/benchmark.csv`: Bộ kiểm thử hơn 20 tình huống có cột đáp án chuẩn phục vụ `python run.py eval`.

## 4. Giới hạn dữ liệu
* Chỉ phản ánh nội dung văn bản đánh giá tại thời điểm thu thập; không chứa lịch sử tài khoản người viết hay siêu dữ liệu nội bộ của sàn TMĐT.
