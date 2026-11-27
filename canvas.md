# Canvas Dự Án — ReviewShield (Làn D: Thương Mại Điện Tử)

> Mốc CP1 (17:00 Thứ Sáu 27/11): Nộp bản đầu tiên (7 dòng).
> Mốc CP2 (19:30 Thứ Sáu 27/11): Cập nhật dòng cuối với bằng chứng thật và lát cắt đã chốt.

| Hạng mục | Nội dung |
| :--- | :--- |
| **1. Track & lát cắt dự kiến** | **Track D — Thương mại điện tử.** Lát cắt: Bóc tách tín hiệu review nhận xu/seeding, tách lỗi vận chuyển và tính lại Điểm tin cậy thực (Real Trust Score) kèm câu hỏi kiểm chứng shop. |
| **2. Người dùng chính** | Người mua hàng online phổ thông trên các sàn TMĐT (Shopee, TikTok Shop, Tiki...) thường cân nhắc các sản phẩm 4.6–5.0 sao trước khi bấm đặt hàng. |
| **3. Pain một câu** | Người mua dễ chọn nhầm hàng kém chất lượng và tốn nhiều thời gian đọc lọc vì điểm sao trung bình trên sàn bị nhiễu nặng bởi review nhận xu/seeding và lỗi vận chuyển không liên quan chất lượng sản phẩm. |
| **4. Bằng chứng đầu** | `[Cập nhật trước CP2/CP3 từ evidence/data-mining.md, interviews và survey thật — không bịa số liệu]` |
| **5. Lát cắt MỘT CÂU** | Nhận một cụm đánh giá sản phẩm (chọn mẫu có sẵn hoặc dán trực tiếp), gọi AI phân loại theo 4 tín hiệu kèm trích dẫn nguyên văn, tính lại Điểm tin cậy thực và xuất Top 3 rủi ro cùng 3 câu hỏi nên nhắn hỏi shop. |
| **6. Mức độ AI tự làm & lý do chịu trách nhiệm** | **AI hỗ trợ phân tích & gợi ý bản nháp (Human-in-the-loop):** AI phân loại tín hiệu ngôn ngữ, trích dẫn câu gốc và soạn 3 câu hỏi kiểm chứng; hệ thống không tự phán quyết "review giả 100%" và không tự gửi tin nhắn cho shop để người mua tự kiểm chứng và chịu trách nhiệm quyết định mua. |
| **7. Phân công có tên** | - Module 1 — Lõi AI & Prompt (`codebase/ai.py`, `agent.py`, `spec.md`): Dương Quang Bảo (`2A202603362` — Đội trưởng)<br>- Module 2 — Tools tính điểm, Grounding Guard & UI (`tools.py`, `app.py`): Thành viên 2 (`2A202603427`)<br>- Module 3 — Dữ liệu, Evidence, Eval (`data/samples/`, `evidence/`, `eval/`): Thành viên 3 (`2A202603646`)<br>- Module 4 — Cost, Validation, Slide & Video Demo (`cost/`, `validation/`, `slides/`): Thành viên 4 (`2A202603483`) |
| **8. Cập nhật CP2 (19:30 Thứ Sáu 27/11)** | `[Cập nhật sau khi có bằng chứng đầu từ data-mining/khảo sát và chốt khóa eval/metric_spec.yaml + spec.md §7]` |
