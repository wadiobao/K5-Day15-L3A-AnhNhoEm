# Tổng hợp bằng chứng pain

> Điền ở guide bước 1.2, xong trước **CP3 10:00 Thứ Bảy 28/11**. Chấm ở rubric R1.
> Ba nguồn ngang nhau — tối thiểu **≥1 nguồn đạt ngưỡng**. Mạnh nhất: đào data ra insight → hỏi người dùng để kiểm lại (hoặc ngược lại).
> Cập nhật 27/11/2026 bởi Nguyễn Mạnh Tường (`2A202603646`). Số liệu chạy lại bằng `python3 evidence/count_reviews.py`; chi tiết cách đếm ở `evidence/data-mining.md`.

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☑ — 26 sản phẩm, 317 review (192 `natural`), script + ≥5 ví dụ nguyên văn | `evidence/data-mining.md` |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☐ — chưa thực hiện (kịch bản sẵn ở `evidence/interviews/guide.md`) | `evidence/interviews/P1.md`… |
| Khảo sát (≥20 người ngoài nhóm, đúng người dùng) | ☐ — chưa thực hiện (bộ câu hỏi sẵn ở `evidence/survey/questions.md`) | `evidence/survey/` |

## 2. Số chính

- **Đào data — H1 (điểm sao bị nhiễu bởi review ít thông tin / lặp mẫu):**
  - **Điện Máy Xanh: 40/89 review 5★ `natural` (44,9%) là `low_signal` hoặc `suspicious_pattern`** (32 L, 8 S). Đây là số chính: 13 sản phẩm chọn theo quy tắc tất định không dựa trên chất lượng review 5★.
  - Gộp mọi review 5★ `natural`: 72/125 (57,6%) — **bị đẩy lên** vì 3 sản phẩm ViMRHP (sp_17–sp_19) được chọn có chủ đích cho nhóm `seeding_heavy` (32/36 = 88,9% L/S); không dùng số gộp làm tỷ lệ chung.
  - Shopee do Nhật thu (lấy qua bộ lọc sao, `added`): 23/60 review 5★ (38,3%) là L/S, trong đó 15 S — chỉ minh họa, không phải tỷ lệ tự nhiên.
  - 15/26 sản phẩm (57,7%) có Điểm tin cậy thực thấp hơn điểm sàn quá 0,3 (tính trên cụm review đã thu, gồm `added`).
- **Đào data — H3 (điểm bị kéo xuống oan do giao hàng):** chỉ **2/35 review 1–2★ `natural` (5,7%)** là `logistics_only` (Điện Máy Xanh); gộp cả `added`: 5/98 (5,1%). Đa số review 1–2★ nêu lỗi sản phẩm cụ thể (29/35 = `verified_insight`).
- **Từ khóa không cần nhãn (D):** 1/185 review 5★ chứa "chưa dùng / nhận xu…" (0,5%) — seeding trong dữ liệu ít khi tự khai "nhận xu", chủ yếu là văn mẫu khen chung.
- Phỏng vấn: __/3 người gặp *(n nhỏ không ghi %)* · số lần / tháng: P1 __, P2 __, P3 __ · mỗi lần mất __–__ phút *(chưa phỏng vấn)*
- Khảo sát: n = __ *(chưa khảo sát)*

Nhãn V/L/S/G do AI (Claude Code, Codex) gán theo tiêu chí do Nguyễn Mạnh Tường đặt, có rà các dòng ranh giới — xem `docs/ai-usage.md`. Nhãn đo **lượng thông tin** về sản phẩm, không kết luận review thật/giả.

| | Vai | Gặp pain? | Số lần / 1 tháng qua | Lần gần nhất mất | Đang xoay xở bằng |
|---|---|---|---|---|---|
| P1 | __ | __ | __ | __ | __ |
| P2 | __ | __ | __ | __ | __ |
| P3 | __ | __ | __ | __ | __ |

## 3. ≥5 trích dẫn hoặc ví dụ nguyên văn (có nguồn, bỏ tên)

1. "Chất liệu:vải mềm mịn Mình đã nhận được hàng, chất vải mềm mịn, hình sắc nét, shop giao hàng nhanh rất ưng ý sẽ ủng hộ shop tiếp nữa nhé" — `sp_17/r2` · 5★ · ViMRHP/Shopee — *seeding: cùng câu này xuất hiện 3 lần (r2, r5, r12) trong 2 ngày*
2. "Hàng đóng gói rất đẹp. Quả nhiên người bán đã gửi gắm rất nhiều tâm tư và tình cảm trong lúc gói hàng. Hộp không có dấu hiệu bị móp, chứng tỏ bộ phận vận chuyển đã nâng như nâng trứng, hứng như hứng hoa. Xin nghiêng mình…" — `sp_21/r5` · 5★ · Shopee (Nhật thu) — *seeding: câu y hệt xuất hiện ở sp_22/r1 — một sản phẩm khác*
3. "“Mình mua vì cần cục pin nhỏ gọn mang đi làm, dùng mấy hôm thấy khá tiện. Nam châm hút chắc, gắn sau máy cầm đi lại không bị tuột. 5000mAh thì không phải kiểu sạc đầy được mấy lần đâu, chủ yếu cứu pin lúc gần hết là hợp…" — `sp_22/r4` · 5★ · Shopee (Nhật thu) — *nội dung nói về cục pin sạc trên trang bàn phím + chuột*
4. "Tốt . Đẹp" — `sp_04/r3` · 5★ · Điện Máy Xanh — *5★ không có thông tin gì về sản phẩm*
5. "Shop ship hàng nhanh và đóng gói cẩn thận chắc chắn , sản phẩm chưa dùng nên sẽ đáng giá chất lượng sau nè, shipper tận tình dễ thương, hi vọng máy chạy tốt" — `sp_19/r2` · 5★ · ViMRHP/Shopee — *5★ nhưng tự nhận chưa dùng sản phẩm*
6. "Máy thì không có vấn đề. Mua ở dmx chủ yếu do bao gồm công lắp đặt. Mà thợ lắp đặt làm ăn làm quá chán. Lắp qua loa xong bỏ về trong. Dây điện cấn kênh không để ý, lắp méo xẹo. Rồi bên trong có cái núm chỉnh hướng gió, n…" — `sp_04/r10` · 2★ · Điện Máy Xanh — *2★ chỉ vì lắp đặt, máy không có vấn đề*

## 4. Các nguồn có khớp nhau không

Hiện mới có **một nguồn (đào data)**, gồm 3 tập: Điện Máy Xanh (chuỗi bán lẻ), Shopee qua ViMRHP và Shopee do nhóm thu. Trong dữ liệu: ở Điện Máy Xanh nhiễu chủ yếu là review 5★ **chung chung** (32 L so với 8 S trên 89 review 5★); ở Shopee có thêm **văn mẫu lặp nguyên câu** (sp_17, sp_19, sp_21/sp_22). Chưa có lời người dùng để kiểm lại — cần phỏng vấn để biết người mua có thật sự bị đánh lừa / mất thời gian lọc không (H2).

## 5. Kết luận

Giả thuyết ở `evidence/hypothesis.md`:
- **H1 — đúng (theo data):** gần một nửa review 5★ tự nhiên ở Điện Máy Xanh (44,9%) không chứa thông tin cụ thể về sản phẩm; ở Shopee có văn mẫu lặp nguyên câu.
- **H3 — phải đổi:** review 1–2★ chỉ vì giao hàng/lắp đặt hiếm (5,7%); điểm thấp chủ yếu do lỗi sản phẩm thật. Nên giảm nhấn mạnh "tách lỗi vận chuyển" trong pitch, giữ như tính năng phụ.
- **H2 — chưa biết:** data không đo được thời gian người mua bỏ ra để lọc review → cần phỏng vấn ≥3 người.

Điều vẫn chưa biết: người mua có tin điểm sao không, mất bao lâu để đọc review, và có đổi quyết định khi thấy Điểm tin cậy thực không. Nhận xét thêm cho nhóm: với sản phẩm seeding mà toàn review 5★ (sp_17–sp_19), Điểm tin cậy thực vẫn bằng điểm sàn (5,0); chỉ `trust_level = low` và `verified_ratio` thấp mới lộ vấn đề → giao diện cần hiển thị nổi bật hai chỉ số này.

## Lịch hẹn (dùng cho CP2 — chỉ ghi vai và giờ, không tên)

| Vai | Giờ hẹn | Đã xong? |
|---|---|---|
| __ | __ | ☐ |
