# Khai báo dùng AI

README của nhóm có mục "Dùng AI vào việc gì" (2–3 dòng, bắt buộc). Ghi chi tiết vào bảng dưới đây.

> Luật của đề: dùng AI để làm bài thoải mái, nhưng **ai không giải thích được phần có tên mình thì phần đó nhận 0 điểm**. Khai thiếu không bị trừ; giấu mới bị.

| Việc | Công cụ AI | AI làm gì | Người kiểm/sửa gì | Ai phụ trách |
|---|---|---|---|---|
| Code bản chạy thử | Codex (gpt-6.1-sol) + Claude Code | Viết script dữ liệu `data/scripts/*`, `evidence/count_reviews.py`, `eval/grade_helper.py` | Nguyễn Mạnh Tường chạy và đọc lại script; trạng thái kiểm tra từng script: __ | Nguyễn Mạnh Tường (`2A202603646`) — phần script dữ liệu/eval |
| Prompt / thiết kế lời gọi mô hình | | | | |
| Đào data (viết script đếm, gán nhãn nháp) | Codex (gpt-6.1-sol) + Claude Code | Sol viết script đếm. Claude gán nhãn nháp sp_21–sp_30 theo tiêu chí do Nguyễn Mạnh Tường đưa ra + bảng ranh giới §1 | Nguyễn Mạnh Tường đặt tiêu chí, rà các dòng ranh giới: đã xem bảng kết quả, sửa 0/121 nhãn · sản phẩm tự thu gán tay · Kiểm tay __ dòng, khớp __ | Nguyễn Mạnh Tường (`2A202603646`) |
| Rà câu hỏi phỏng vấn / khảo sát | Codex (gpt-6.1-sol) + Claude Code | Soạn nháp câu hỏi | Người rà câu dẫn dắt: Nguyễn Mạnh Tường; trạng thái rà: __ | Nguyễn Mạnh Tường (`2A202603646`) |
| Viết câu thử (benchmark) | Codex (gpt-6.1-sol) + Claude Code | Script ghép câu từ dữ liệu thật và nhãn người gán; AI soạn bốn câu `X01–X04`, ghi `source=tu_viet` | Nguyễn Mạnh Tường đối chiếu input/expected với dữ liệu và nhãn tay; mỗi câu có `source`, câu sản phẩm ghi `data_that` | Nguyễn Mạnh Tường (`2A202603646`) |
| Sinh data `synthetic` (nếu có) | | | Seed __ · kiểm tay __ dòng | |
| Chấm cột `pass` bằng LLM (nếu có) | | | Kiểm tra thủ công __ câu thử, khớp __/__ | |
| Slide, văn bản | | | | |

**Không dùng AI để:** tạo người được phỏng vấn, trích dẫn, câu trả lời khảo sát; sửa kết quả các lượt đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/`).
