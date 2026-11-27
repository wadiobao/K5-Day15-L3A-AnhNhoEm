# Dàn Ý 7 Slide Pitch, Kịch Bản Video 2 Phút & Bộ Q&A BGK — ReviewShield

## 1. Dàn ý 7 Slide thuyết trình (3–5 phút)

| Slide | Tiêu đề hành động (Action Title) | Nội dung cốt lõi |
| :--- | :--- | :--- |
| **Slide 1** | **ReviewShield — Đừng tin 4.9 sao nếu chưa biết bao nhiêu người thực sự đã dùng** | Tên dự án, Track D (Thương mại điện tử), định vị 1 câu và ảnh chụp thẻ Điểm sàn vs Điểm thực. |
| **Slide 2** | **Người mua mất thời gian và dễ mua nhầm vì 3 lớp nhiễu trên điểm sao sàn TMĐT** | Bằng chứng thật từ `evidence/summary.md` + 3 ví dụ thực tế (nhận xu, lặp mẫu, 1 sao do shipper). |
| **Slide 3** | **ReviewShield phân loại 4 tín hiệu có dẫn chứng và tính lại Điểm tin cậy thực** | Sơ đồ 4 nhãn kèm trọng số (`1.00`, `0.15`, `0.10`, `0.00`), Top 3 rủi ro và 3 câu hỏi kiểm chứng shop. |
| **Slide 4** | **Kiến trúc chuẩn khung AI20K: AI thật hiểu ngữ nghĩa + Python tất định kiểm chứng & tính điểm** | Sơ đồ luồng `agent.py` -> `ai.py` (`@model_call`) -> `tools.py` (`@tool` Grounding Guard & Trust Score). |
| **Slide 5** | **Demo trực tiếp: Sản phẩm 4.9 sao lộ điểm thực và rủi ro ẩn chỉ trong vài giây** | Ảnh/video chạy thật trên `codebase/app.py`, khoanh đỏ trích dẫn nguyên văn và câu hỏi kiểm chứng shop. |
| **Slide 6** | **Kết quả kiểm thử 25+ tình huống thật & Ước tính chi phí vận hành** | Số liệu thật từ `eval/report.md` (Label Accuracy, Direction Match, Citation Grounding 100%) + bảng chi phí từ `cost/cost-estimate.md`. |
| **Slide 7** | **Giới hạn MVP & Lộ trình lên Production: Chrome Extension + Redis Cache** | Nêu rõ giới hạn MVP (chọn mẫu/dán tay, không dùng server scraper); lộ trình Production: Chrome Extension đọc DOM 1-click tại trình duyệt người dùng (ẩn danh PII tại client), hỗ trợ ảnh chụp màn hình/OCR cho mobile, đóng gói REST API + Redis Cache `(product_id, hash)` giảm 70–85% chi phí token và hướng Partner API cho B2B. |

## 2. Kịch bản Video Demo 120 giây (2 phút)

| Mốc thời gian | Cảnh quay trên màn hình | Lời dẫn gợi ý |
| :--- | :--- | :--- |
| **0:00 – 0:15** | Hình ảnh 1 sản phẩm 4.9 sao đầy review "giao nhanh, chưa dùng cho 5 sao". | "Thấy 4.9 sao ta thường yên tâm bấm mua. Nhưng nếu hơn nửa số đó là review nhận xu hoặc seeding thì điểm thật của sản phẩm này là bao nhiêu?" |
| **0:15 – 0:50** | Mở `codebase/app.py`, chọn sản phẩm mẫu, bấm **Phân tích bằng AI** (gọi API thật). | "ReviewShield gọi API AI thật với đầu ra JSON chuẩn để phân loại từng review theo 4 tín hiệu và tính lại Điểm tin cậy thực bằng công thức tất định. Chỉ sau vài giây, sản phẩm 4.9 sao lộ điểm thực là [X.X] sao cùng Top 3 rủi ro người mua thực sự gặp phải." |
| **0:50 – 1:20** | Lọc từng nhãn, chiếu phần trích dẫn nguyên văn và 3 câu hỏi kiểm chứng shop. | "Hệ thống không phán bừa review giả. Mọi nhãn đều đi kèm trích dẫn nguyên văn từ câu chữ gốc đã qua lớp Grounding Guard, tách riêng lỗi shipper và gợi ý sẵn 3 câu hỏi để người mua nhắn hỏi shop." |
| **1:20 – 1:45** | Chiếu kết quả `python run.py eval` / `eval/report.md` và `cost/cost-estimate.md`. | "Trên bộ thử [25+] cụm review thật, ReviewShield đạt [XX]% độ chính xác nhãn, 100% trích dẫn khớp văn bản gốc và chi phí vận hành chỉ khoảng [X] đồng mỗi lượt phân tích." |
| **1:45 – 2:00** | Màn hình tổng kết tên dự án ReviewShield & lộ trình Chrome Extension. | "ReviewShield giúp người mua ra quyết định trung thực trong 30 giây và sẵn sàng mở rộng thành tiện ích trình duyệt ngay sau hackathon." |

## 3. Bộ câu hỏi xoáy của BGK & Cách trả lời gọn

| Câu hỏi xoáy | Trả lời ngắn gọn (dưới 30 giây) |
| :--- | :--- |
| **"Làm sao chắc 100% review đó là seeding?"** | "Nhóm không phán quyết cứng thật hay giả. Hệ thống đo mức độ thông tin hữu ích và tín hiệu lặp mẫu, luôn trích dẫn nguyên văn để người mua tự kiểm chứng." |
| **"Sao không dán link Shopee vào tự cào? Lên Production thì sao?"** | "Sàn chặn server scraper bằng captcha nên dễ chết demo. Trong hackathon nhóm dồn lực vào lõi AI + Grounding Guard; lên Production sẽ dùng Chrome Extension đọc DOM 1-click ngay trên trình duyệt người dùng (ẩn danh PII tại client), thêm Redis Cache theo sản phẩm để giảm 70–85% chi phí token, và mở rộng OCR ảnh chụp cho mobile." |
| **"Khác gì AI tóm tắt review của sàn?"** | "Sàn tối ưu tỷ lệ chốt đơn nên tóm tắt chung chung. ReviewShield đứng về phía người mua: giảm trọng số review nhận xu, tách lỗi shipper để tính lại Điểm tin cậy thực và sinh câu hỏi kiểm chứng shop." |
| **"Nếu AI bịa trích dẫn hoặc tính sai số thì sao?"** | "Mọi phép tính điểm đều chạy bằng code Python tất định trong `tools.py`, không giao cho LLM; đồng thời có lớp Grounding Guard kiểm tra 100% trích dẫn phải nằm trong văn bản gốc." |
