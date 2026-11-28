# Người dùng thử *(bonus)*

> Điền ở guide bước 4.3 — 2–3 người ngoài nhóm, ~10 phút / người, theo 5 nhịp: làm quen · bối cảnh · giao việc · quan sát · hỏi sau. Ôn lại: ngày 5, ngày 13. Chấm ở rubric Bonus.
> Không ghi tên: ghi vai. Hành vi quan sát được nặng hơn lời nói; toàn lời khen = phiên chưa đạt, giao việc khó hơn.
> Người dùng thử **không thay được** bằng chứng pain ở `evidence/`.

| Người thử (vai) | Việc giao (theo kết quả, không theo nút) | Quan sát (làm gì đầu tiên, chỗ do dự, chỗ hiểu sai) | Trích nguyên văn | Mức nghiêm trọng (cao / vừa / thấp) |
|---|---|---|---|---|
| Người mua camera, cần wifi ổn định để xem lại khi vắng nhà | Quyết định có nên mua mẫu camera 3,3 sao không | Đọc phần rủi ro thấy để trống và báo có nhiễu vừa phải dù cả 12/12 review xếp vào trải nghiệm thật. Phải đọc xuống các thẻ mới thấy r1, r8, r12 nói về kết nối yếu và lỗi xem lại. | r8: "Nhờ kỹ thuật xem giúp, cam ko xem phát lại dc" | cao — phần tóm tắt báo sai ý và thiếu lỗi chính |
| Người mua serum, muốn biết điểm thấp do hàng hay do giao hàng | Đọc riêng ý kiến về chất lượng serum trước khi mua | Chọn mẫu oan shipper và bấm soi đánh giá. Trong 5 câu, r3 và r4 chỉ nói về giao hàng nhưng app vẫn ghi 5/5 là trải nghiệm thật, 0 câu vận chuyển, điểm giữ ở 3,4/5 thay vì 5,0/5. | r4: "Đơn vị vận chuyển làm móp nát vỏ thùng carton bên ngoài, giao quá chậm." | cao — chạy thiếu cấu hình api nên không tách được lỗi giao hàng |
| | | | | |

Câu hỏi sau: *"Nếu mai không được dùng nữa, bạn thấy: rất tiếc / hơi tiếc / không sao?"* → __ / __ / __

## Tổng hợp

- Chủ đề lặp nhiều nhất: Khi chưa gắn file cấu hình api, app tự chạy chế độ giả lập nên không tách lỗi giao hàng và để trống rủi ro mà không báo rõ; câu mô tả mức trung bình luôn ghi có nhiễu dù tỷ lệ trải nghiệm thật là 100%.
- Sửa gì trước demo (ghi `spec.md` §10): Thêm dòng báo rõ ngay đầu trang khi đang chạy chế độ giả lập; sửa câu mô tả mức trung bình khi tỷ lệ trải nghiệm thật cao; tự xóa kết quả cũ khi đổi sản phẩm trên danh sách chọn; bật api thật trước khi demo.
- Giữ gì và vì sao: Giữ danh sách thẻ review gốc kèm mã câu và trích dẫn nguyên văn vì giúp người mua tự kiểm chứng nhanh ngay cả khi phần tóm tắt còn thiếu.
- Để dành sau: Thêm bộ đếm câu lặp gần giống trong mã nguồn và nhờ người ngoài nhóm bấm thử khi đã bật api thật.
