# Reflection — Nguyễn Mạnh Tường

> Bản nháp do Claude Code soạn từ những gì có trong repo và lịch sử làm việc, để tôi đọc, sửa cho đúng giọng của mình rồi nộp. Tôi chịu trách nhiệm về nội dung dưới đây.

1. **Vai trò + phần mình làm (trỏ tới file / commit):**
   Thành viên 3, phụ trách dữ liệu, bằng chứng và đánh giá (Track D, ReviewShield). Tôi làm: kho mẫu `data/samples/` (26 sản phẩm, 317 review từ Shopee và Điện Máy Xanh, kèm `data/DATA_CARD.md`); bộ câu thử `eval/benchmark.csv` (30 câu, `RS01–RS30`) và nhãn chuẩn `eval/labels.csv` (PR #3, #6); các script `data/scripts/*`, `evidence/count_reviews.py`, `eval/grade_helper.py`; bằng chứng pain `evidence/data-mining.md` và `evidence/summary.md` (PR #7); báo cáo `eval/report.md` (PR #14). Dữ liệu 10 sản phẩm Shopee (`sp_21–sp_30`) do Đặng Long Nhật thu, tôi chuẩn hóa và gán nhãn.

2. **AI hỗ trợ mình thế nào (việc gì, công cụ gì, chỗ nào phải sửa lại output AI):**
   Claude Code điều phối và Codex (gpt-6.1-sol) viết script; nhãn V/L/S/G của các sản phẩm do AI gán theo tiêu chí tôi rút ra (S: dài, văn hoa, thuần khen, chèn emoji, giọng như quảng cáo hoặc lặp mẫu), tôi xem kết quả và quyết định giữ nhãn. Chỗ phải sửa lại: bộ lọc tên tự động bỏ sót tên nhân viên viết thường ở `sp_07` nên phải che bằng tay; benchmark ban đầu toàn chiều `lower_than_platform` nên phải đổi bớt sản phẩm; tôi dùng tiêu chí hơi khác định nghĩa chính thức nên khi tự gán độc lập 30 review chỉ khớp nhãn chuẩn 18/30 (60%), và tôi ghi con số đó vào `eval/report.md` thay vì chỉnh nhãn.

3. **Một câu thử trượt của nhóm và mình học được gì từ nó:**
   `RS28` (12 review 5★ của một bộ đồ nam, cùng một câu khen lặp lại 3 lần). Lượt 1 chỉ đúng 2/12 nhãn vì AI đọc từng review riêng lẻ và coi "chất vải mềm mịn" là chi tiết thật. Sau khi sửa prompt (kiểm tra mẫu lặp trước, đối chiếu chéo cả cụm) lượt 2 lên 9/12 nhưng nhãn S toàn bộ vẫn chỉ đúng 19/49. Tôi học được: (a) điểm tin cậy thực của sản phẩm toàn 5★ vẫn bằng điểm sàn, nên phải nhìn `trust_level` và tỷ lệ trải nghiệm thật; (b) chỉ số `direction_match` gần như không phân biệt được AI giỏi hay dở (đoán toàn V vẫn đạt 84,6%), nên phải dùng `label_accuracy`; (c) phát hiện mẫu lặp nên làm bằng code tất định chứ không chỉ trông vào prompt.
