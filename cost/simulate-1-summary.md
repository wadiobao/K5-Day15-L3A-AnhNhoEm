# Tóm tắt mô phỏng simulate-1@20261128-123636

Do `python run.py simulate` sinh ra — không sửa tay. Chép bảng sang `cost/cost-estimate.md`.

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| mua_it | 25 | 1 | 1965 | 1233 | 1.0 | 3.0 |
| mua_vua | 17 | 3 | 5544 | 3565 | 2.9 | 8.8 |
| san_sale_nhieu | 2 | 5 | 8966 | 5528 | 4.5 | 14.0 |

Tỉ lệ đạt dùng để tính: 13/30 (43%) — lượt run-2@20261128-073745

- Tỉ lệ đạt lấy từ lượt nhóm chọn: eval/run-2.csv (--rate-from).

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (700 người) | Chi phí / tháng — cao (1.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.5-flash-lite (vào 0.3 · ra 2.5 $/1M) | $0.0069 (≈ 177 ₫) | $0.0160 (≈ 407 ₫) | $0.0082 (≈ 208 ₫) | $28.17 (≈ 718.238 ₫) | $65.72 (≈ 1.675.889 ₫) | $93.89 (≈ 2.394.128 ₫) | $0.0939 (≈ 2.394 ₫) |
| gemini-3.1-pro-preview (vào 2.0 · ra 12.0 $/1M) | $0.0353 (≈ 900 ₫) | $0.0814 (≈ 2.076 ₫) | $0.0417 (≈ 1.062 ₫) | $143.64 (≈ 3.662.728 ₫) | $335.15 (≈ 8.546.366 ₫) | $478.79 (≈ 12.209.095 ₫) | $0.4788 (≈ 12.209 ₫) |

- Chi phí / task thành công = chi phí / phiên ÷ tỉ lệ đạt. Chi phí / câu hỏi đạt = chi phí / phiên ÷ số lượt hỏi trung bình mỗi phiên (2.0) ÷ tỉ lệ đạt — tỉ lệ đạt đo theo từng câu thử.
- Token đo trên model: gemini-3.5-flash-lite. Giá tính theo từng model trong bảng — model khác bộ tách token thì số token thật có thể lệch; ghi rõ "đo trên model X, tính giá model Y" trong cost/cost-estimate.md.
- Phiên lỗi (không tính vào trung bình): 6/50.
- Tỷ giá: 1 USD = 25.500 ₫ ((tự ước tính) Tỷ giá tham khảo USD/VND).
