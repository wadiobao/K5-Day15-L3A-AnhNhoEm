# Chi phí khi dùng thật — ReviewShield

> Điền ở guide bước 4.2, nộp ở CP4 14:30 Thứ Bảy 28/11. Chấm ở rubric R6.
> Toàn bộ số liệu token và chi phí dưới đây được trích nguyên bản từ `cost/simulate-1-summary.md` (`simulate-1@20261128-123751`, chạy `python run.py simulate --rate-from eval/run-2.csv --wait 2`, không sửa tay file kết quả).
> Lúc build dùng gói miễn phí / tài khoản thử nghiệm nhưng toàn bộ bảng tính theo **giá gói trả phí (Paid Tier)** cho kịch bản vận hành thật.

## 1. Đầu vào

- **Persona** (`cost/personas.yaml`): 3 nhóm người mua online:
  - `mua_it` — tỉ lệ `50%`, `4` phiên/tháng, `1` lượt hỏi/phiên.
  - `mua_vua` — tỉ lệ `35%`, `10` phiên/tháng, `3` lượt hỏi/phiên.
  - `san_sale_nhieu` — tỉ lệ `15%`, `20` phiên/tháng, `5` lượt hỏi/phiên.
  - **Nguồn:** *(tự ước tính)* cho giai đoạn MVP; có đối chiếu thực tế từ 3 phỏng vấn `P1–P3` tại `evidence/summary.md` (P1 mua 6–7 đơn/tháng nhưng chỉ đọc kỹ review 1–2 đơn; P3 mua 1 đơn/tháng; P2 hầu như không mua online → xác nhận người dùng mục tiêu tập trung vào nhóm mua hàng giá trị trung bình–cao / cần đọc kỹ review).
- **Số người dùng thật** 3 kịch bản: thấp **300** · cơ sở **700** · cao **1.000**. Nguồn: *(tự ước tính)* quy mô người mua mục tiêu giai đoạn MVP.
- **Giá** 2 mức model trả phí (Paid Tier, nguồn `https://ai.google.dev/gemini-api/docs/pricing`, xem ngày `2026-11-27`):
  - **Mức rẻ (model chính):** `gemini-3.5-flash-lite` — Input `$0.30 / 1M tokens` · Output `$2.50 / 1M tokens` (đã gồm thinking tokens).
  - **Mức mạnh (đối chiếu):** `gemini-3.1-pro-preview` — Input `$2.00 / 1M tokens` · Output `$12.00 / 1M tokens` (áp dụng prompt ≤ 200K tokens).
- **Tỉ lệ đạt** dùng để tính: **13/30 (43%)** — lượt `eval/run-2.csv` (`run-2@20261128-073745`, chạy cùng model `gemini-3.5-flash-lite`).
- **Phạm vi đo:** Đo token thực tế trên model `gemini-3.5-flash-lite`, tính giá cho 2 mức model `gemini-3.5-flash-lite` và `gemini-3.1-pro-preview` *(lưu ý: nếu đổi hãng/bộ tách token khác, số token thực tế có thể chênh lệch nhẹ)*.
- **Tỷ giá quy đổi:** `1 USD = 25.500 ₫` *(tự ước tính)*.

## 2. Kết quả mô phỏng

- **Lượt mô phỏng:** `cost/simulate-1.csv` · Run ID `simulate-1@20261128-123751` · **50 phiên** (49/50 phiên thành công; 1/50 phiên lỗi tạm thời HTTP 503 high demand tại `S039` không tính vào trung bình) · `seed = 42`.
- **Hiệu năng đo được trên 49 phiên thành công:** Tổng `189.229` token vào, `119.725` token ra; độ trễ trung bình **7,52 giây / lượt phân tích** (~15,19 giây / phiên trung bình 2,0 lượt hỏi).

### Token và số lần gọi đo thực tế theo Persona

| Persona | Số phiên mô phỏng | Lượt hỏi / phiên | Token vào / phiên | Token ra / phiên | Gọi model / phiên | Gọi công cụ / phiên |
|---|---:|---:|---:|---:|---:|---:|
| `mua_it` | 27 | 1 | 1988 | 1230 | 1.0 | 3.0 |
| `mua_vua` | 19 | 3 | 5584 | 3575 | 2.9 | 8.8 |
| `san_sale_nhieu` | 3 | 5 | 9817 | 6195 | 5.0 | 14.3 |

### Bảng chi phí vận hành (chép nguyên văn từ `cost/simulate-1-summary.md`)

| Model (giá) | Chi phí / phiên | Chi phí / task thành công | Chi phí / câu hỏi đạt | Chi phí / tháng — thấp (300 người) | Chi phí / tháng — cơ sở (700 người) | Chi phí / tháng — cao (1.000 người) | Chi phí / người / tháng (cơ sở) |
|---|---:|---:|---:|---:|---:|---:|---:|
| gemini-3.5-flash-lite (vào 0.3 · ra 2.5 $/1M) | $0.0073 (≈ 185 ₫) | $0.0168 (≈ 428 ₫) | $0.0083 (≈ 212 ₫) | $29.94 (≈ 763.360 ₫) | $69.85 (≈ 1.781.174 ₫) | $99.79 (≈ 2.544.535 ₫) | $0.0998 (≈ 2.545 ₫) |
| gemini-3.1-pro-preview (vào 2.0 · ra 12.0 $/1M) | $0.0370 (≈ 945 ₫) | $0.0855 (≈ 2.180 ₫) | $0.0423 (≈ 1.079 ₫) | $152.59 (≈ 3.891.063 ₫) | $356.04 (≈ 9.079.147 ₫) | $508.64 (≈ 12.970.210 ₫) | $0.5086 (≈ 12.970 ₫) |

*Chi phí / task thành công = chi phí trung bình mỗi phiên ÷ tỉ lệ đạt (`43%`) — **không coi như đạt 100%**.*

## 3. So với impact

- **Impact / người / tháng (`spec.md §2` & `evidence/summary.md`):** Dữ liệu đào thực tế cho thấy **44,9%** review 5★ tự nhiên trên Điện Máy Xanh ít thông tin/lặp mẫu và **15/26 sản phẩm (57,7%)** có Điểm tin cậy thực thấp hơn điểm sàn quá 0,3 sao. Chỉ cần giúp người mua tránh **1 đơn hàng điện tử/gia dụng lỗi** (trị giá phổ biến 200.000–500.000 ₫, *(tự ước tính)*) hoặc rút ngắn thời gian lọc review thủ công (~10 phút/đơn như P1 chia sẻ) xuống còn ~7–8 giây, giá trị tiết kiệm vượt xa chi phí AI gấp hàng trăm lần.
- **Chi phí / người / tháng (cơ sở 700 người, model `gemini-3.5-flash-lite`):** **2.545 ₫ / người / tháng** (`$0.0998`), tương đương **185 ₫ / phiên** và **428 ₫ / task thành công** (đã chia cho tỉ lệ đạt 43%).
- **Kết luận một dòng — đáng làm không:** **Rất đáng làm** với `gemini-3.5-flash-lite` (~1,78 triệu ₫/tháng cho 700 người dùng cơ sở); không nên mặc định chạy `gemini-3.1-pro-preview` (~9,08 triệu ₫/tháng, đắt gấp **5,1 lần**) trừ khi dùng làm tầng dự phòng cho các ca khó.

## 4. Phân tích độ nhạy & Cần gạt tối ưu khi lên Production *(tự ước tính)*

| Cần gạt tối ưu | Cách hoạt động | Mức tác động ước tính *(tự ước tính)* |
| :--- | :--- | :--- |
| **1. Redis Cache theo `(product_id, reviews_hash)`** | Lưu kết quả phân tích sản phẩm bán chạy trong TTL 12–24 giờ; nhiều người mua cùng soi 1 sản phẩm chỉ tốn token 1 lần. | Giảm **70–85%** chi phí API → kịch bản 700 người còn khoảng **270.000–535.000 ₫/tháng**. |
| **2. Giới hạn lô ≤ 20 review (`preprocess_reviews`)** | Đã cài sẵn trong `codebase/tools.py`: lọc review trống và lấy mẫu phân tầng tối đa 20 review/lượt. | Giữ ổn định ~1.988 input tokens/lượt, chặn bùng nổ token ở sản phẩm có hàng nghìn review. |
| **3. Nâng chất lượng phân loại (giảm chi phí/task đạt)** | Khi cải tiến thêm phát hiện near-duplicate trong `tools.py` giúp tỉ lệ đạt tăng từ 43% lên ~75–80%. | Chi phí / task thành công giảm gần **1 nửa** (từ 428 ₫ xuống còn ~230–250 ₫/task). |
| **4. Chọn tầng model hợp lý** | Giữ `gemini-3.5-flash-lite` làm mặc định thay vì `gemini-3.1-pro-preview`. | Tiết kiệm **~80,4%** chi phí ngay lập tức (~7,30 triệu ₫/tháng ở mức 700 người). |

- **Chi phí ngoài model *(tự ước tính)*:** Hosting backend nhẹ + Redis (15–30 USD/tháng ≈ 380.000–765.000 ₫/tháng); không phát sinh chi phí nhân sự duyệt từng lượt vì 3 câu hỏi kiểm chứng là bản nháp do người mua tự quyết.
- **Ngưỡng quy mô còn đáng làm:** Với mô hình Chrome Extension miễn phí kèm gói trả phí nhẹ hoặc affiliate/partner B2B, mức chi phí **~2.545 ₫/người/tháng** (chưa cache) và **~400–800 ₫/người/tháng** (sau cache) hoàn toàn khả thi ở quy mô từ vài trăm đến hàng chục nghìn người dùng.
