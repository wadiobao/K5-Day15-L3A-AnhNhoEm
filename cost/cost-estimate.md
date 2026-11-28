# Chi phí khi dùng thật — ReviewShield

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Chấm ở rubric R6.
> Toàn bộ số liệu token và chi phí được trích trực tiếp từ `cost/simulate-1-summary.md` (`simulate-1@20261128-123636`, không sửa tay file kết quả).

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 nhóm người mua — `mua_it` (50%, 4 phiên/tháng, 1 lượt/phiên), `mua_vua` (35%, 10 phiên/tháng, 3 lượt/phiên), `san_sale_nhieu` (15%, 20 phiên/tháng, 5 lượt/phiên). Nguồn: *(tự ước tính)* cho giai đoạn MVP.
- **Số người dùng thật** 3 kịch bản: thấp **300** · cơ sở **700** · cao **1.000**. Nguồn: *(tự ước tính)* quy mô người mua online mục tiêu giai đoạn MVP.
- **Giá** 2 mức model trả phí (Paid Tier, xem ngày `2026-11-27` tại `https://ai.google.dev/gemini-api/docs/pricing`):
  - Model rẻ (chính): `gemini-3.5-flash-lite` — vào `$0.30/1M` · ra `$2.50/1M`
  - Model mạnh (đối chiếu): `gemini-3.1-pro-preview` — vào `$2.00/1M` · ra `$12.00/1M`
- **Tỉ lệ đạt** dùng để tính: **13/30 (43%)** — lượt `eval/run-2.csv` (`run-2@20261128-073745`, chạy bằng `--rate-from eval/run-2.csv`).
- **Đo token trên model `gemini-3.5-flash-lite`**, tính giá trên 2 mức model `gemini-3.5-flash-lite` và `gemini-3.1-pro-preview` *(lưu ý: khác bộ tách token có thể lệch nhẹ số token thực tế nếu đổi sang model khác)*.
- **Tỷ giá quy đổi:** `1 USD = 25.500 ₫` *(tự ước tính)*.

## 2. Kết quả mô phỏng

Lượt mô phỏng: `cost/simulate-1.csv` · Run ID `simulate-1@20261128-123636` · 50 phiên (44 phiên thành công, 6/50 phiên lỗi HTTP 503 high demand không tính vào trung bình) · seed `42`.

### Token đo thực tế theo Persona
| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| `mua_it` | 25 | 1 | 1965 | 1233 | 1.0 | 3.0 |
| `mua_vua` | 17 | 3 | 5544 | 3565 | 2.9 | 8.8 |
| `san_sale_nhieu` | 2 | 5 | 8966 | 5528 | 4.5 | 14.0 |

### Bảng chi phí vận hành (dán từ `cost/simulate-1-summary.md`)

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (700 người) | Chi phí / tháng — cao (1.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `gemini-3.5-flash-lite` (vào 0.3 · ra 2.5 $/1M) | $0.0069 (≈ 177 ₫) | $0.0160 (≈ 407 ₫) | $0.0082 (≈ 208 ₫) | $28.17 (≈ 718.238 ₫) | $65.72 (≈ 1.675.889 ₫) | $93.89 (≈ 2.394.128 ₫) | **$0.0939 (≈ 2.394 ₫)** |
| `gemini-3.1-pro-preview` (vào 2.0 · ra 12.0 $/1M) | $0.0353 (≈ 900 ₫) | $0.0814 (≈ 2.076 ₫) | $0.0417 (≈ 1.062 ₫) | $143.64 (≈ 3.662.728 ₫) | $335.15 (≈ 8.546.366 ₫) | $478.79 (≈ 12.209.095 ₫) | $0.4788 (≈ 12.209 ₫) |

*Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt (`43%`) — không coi như đạt 100%.*

## 3. So với impact

- **Impact / người / tháng (`spec.md §2` & `evidence/summary.md`):** Chỉ cần giúp người mua tránh **1 đơn hàng điện tử/gia dụng lỗi** (trị giá phổ biến 200.000–500.000 ₫, *(tự ước tính)*) hoặc tiết kiệm thời gian lọc review 1 sao ở các sản phẩm giá trị trung bình–cao, giá trị mang lại cao gấp hàng trăm lần chi phí AI.
- **Chi phí / người / tháng (cơ sở 700 người, model `gemini-3.5-flash-lite`):** **2.394 ₫/người/tháng** (`$0.0939`), tương đương **407 ₫ / task thành công** (kể cả khi đã chia cho tỉ lệ đạt 43%).
- **Kết luận một dòng — đáng làm không:** **Rất đáng làm** với `gemini-3.5-flash-lite` (~1,68 triệu ₫/tháng cho 700 người dùng cơ sở); không nên chạy mặc định `gemini-3.1-pro-preview` (~8,55 triệu ₫/tháng, đắt gấp 5,1 lần) trừ khi dùng làm tầng fallback cho ca khó.

## 4. Tối ưu khi đưa lên Production *(tự ước tính)*

- **Redis Cache theo `(product_id, reviews_hash)` (TTL 12–24h):** Nhiều người cùng xem 1 sản phẩm bán chạy chỉ tốn token 1 lần → ước tính giảm **70–85%** chi phí API (từ ~1,68 triệu ₫/tháng xuống còn ~250.000–500.000 ₫/tháng cho 700 người dùng).
- **Cắt ngữ cảnh & định tuyến model:** Giữ trần 20 review/lượt (`preprocess_reviews`) giúp ổn định ~1.965 input tokens/lượt; khi tỉ lệ đạt tăng từ 43% lên ≥75% sau khi thêm fuzzy near-duplicate trong `tools.py`, chi phí / task thành công sẽ giảm thêm gần một nửa (còn ~230 ₫/task).
