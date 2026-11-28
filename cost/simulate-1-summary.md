# Tóm tắt mô phỏng simulate-1@20261128-123751

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| mua_it | 27 | 1 | 1988 | 1230 | 1.0 | 3.0 |
| mua_vua | 19 | 3 | 5584 | 3575 | 2.9 | 8.8 |
| san_sale_nhieu | 3 | 5 | 9817 | 6195 | 5.0 | 14.3 |

Tỉ lệ đạt dùng để tính: 13/30 (43%) — lượt run-2@20261128-073745

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-2.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (700 người) | Chi phí / tháng — cao (1.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.5-flash-lite (vào 0.3 · ra 2.5 $/1M) | $0.0073 (≈ 185 ₫) | $0.0168 (≈ 428 ₫) | $0.0083 (≈ 212 ₫) | $29.94 (≈ 763.360 ₫) | $69.85 (≈ 1.781.174 ₫) | $99.79 (≈ 2.544.535 ₫) | $0.0998 (≈ 2.545 ₫) |
| gemini-3.1-pro-preview (vào 2.0 · ra 12.0 $/1M) | $0.0370 (≈ 945 ₫) | $0.0855 (≈ 2.180 ₫) | $0.0423 (≈ 1.079 ₫) | $152.59 (≈ 3.891.063 ₫) | $356.04 (≈ 9.079.147 ₫) | $508.64 (≈ 12.970.210 ₫) | $0.5086 (≈ 12.970 ₫) |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (2.0) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: gemini-3.5-flash-lite. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 1/50.
- Tỷ giá: 1 USD = 25.500 ₫ ((tự ước tính) Tỷ giá tham khảo USD/VND).
