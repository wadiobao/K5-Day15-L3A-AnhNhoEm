# Tổng hợp bằng chứng pain

> Điền ở guide bước 1.2, xong trước **CP3 10:00 Thứ Bảy 28/11**. Chấm ở rubric R1.
> Ba nguồn ngang nhau — tối thiểu **≥1 nguồn đạt ngưỡng**. Mạnh nhất: đào data ra insight → hỏi người dùng để kiểm lại (hoặc ngược lại).
> Cập nhật 27/11/2026 bởi Nguyễn Mạnh Tường (`2A202603646` — đào data) và Đặng Long Nhật (`2A202603483` — phỏng vấn P1–P3). Số liệu đào data chạy lại bằng `python3 evidence/count_reviews.py`; chi tiết cách đếm ở `evidence/data-mining.md`.

## 1. Nguồn đã dùng

| Nguồn | Đạt ngưỡng? | File |
|---|---|---|
| Đào data (x/N, %, cách đếm chạy lại được, ≥5 ví dụ) | ☑ — 26 sản phẩm, 317 review (192 `natural`), script + ≥5 ví dụ nguyên văn | `evidence/data-mining.md` |
| Phỏng vấn (≥3 người ngoài nhóm, đúng người dùng) | ☑ — 3 người mua online ngoài nhóm qua tin nhắn (27/11/2026, đã ẩn danh) | `evidence/interviews/P1.md`, `P2.md`, `P3.md` |
| Khảo sát (≥20 người ngoài nhóm, đúng người dùng) | ☐ — chưa thực hiện (bộ câu hỏi sẵn ở `evidence/survey/questions.md`) | `evidence/survey/` |

## 2. Số chính

- **Đào data — H1 (điểm sao bị nhiễu bởi review ít thông tin / lặp mẫu):**
  - **Điện Máy Xanh: 40/89 review 5★ `natural` (44,9%) là `low_signal` hoặc `suspicious_pattern`** (32 L, 8 S). Đây là số chính: 13 sản phẩm chọn theo quy tắc tất định không dựa trên chất lượng review 5★.
  - Gộp mọi review 5★ `natural`: 72/125 (57,6%) — **bị đẩy lên** vì 3 sản phẩm ViMRHP (sp_17–sp_19) được chọn có chủ đích cho nhóm `seeding_heavy` (32/36 = 88,9% L/S); không dùng số gộp làm tỷ lệ chung.
  - Shopee do Nhật thu (lấy qua bộ lọc sao, `added`): 23/60 review 5★ (38,3%) là L/S, trong đó 15 S — chỉ minh họa, không phải tỷ lệ tự nhiên.
  - 15/26 sản phẩm (57,7%) có Điểm tin cậy thực thấp hơn điểm sàn quá 0,3 (tính trên cụm review đã thu, gồm `added`).
- **Đào data — H3 (điểm bị kéo xuống oan do giao hàng):** chỉ **2/35 review 1–2★ `natural` (5,7%)** là `logistics_only` (Điện Máy Xanh); gộp cả `added`: 5/98 (5,1%). Đa số review 1–2★ nêu lỗi sản phẩm cụ thể (29/35 = `verified_insight`).
- **Từ khóa không cần nhãn (D):** 1/185 review 5★ chứa "chưa dùng / nhận xu…" (0,5%) — seeding trong dữ liệu ít khi tự khai "nhận xu", chủ yếu là văn mẫu khen chung.
- **Phỏng vấn (3 người ngoài nhóm, 27/11/2026):** **1/3 người gặp pain trực tiếp khi lọc review** *(P2 lọc 1 sao thấy rất lâu và bỏ mua)*; **2/3 không gặp vướng ở đơn đồ giá rẻ gần nhất** *(P1 mua bấm móng tay, P3 mua kẹp gắp thức ăn — chỉ lướt 7s hoặc bỏ qua; riêng P1 vẫn đọc kỹ 1–2/6–7 đơn/tháng)* *(n nhỏ không ghi %)*. Số lần mua / 1 tháng qua: P1 6–7 lần (đọc kỹ 1–2 lần), P2 0 lần (lần gần nhất ~3 năm trước), P3 1 lần (không đọc kỹ). Thời gian đọc review: P1 10 phút *(theo lời P1)*, P2 không nhớ phút (mô tả *"rất lâu"*), P3 7 giây.
- Khảo sát: n = __ *(chưa khảo sát)*

Nhãn V/L/S/G do AI (Claude Code, Codex) gán theo tiêu chí do Nguyễn Mạnh Tường đặt, có rà các dòng ranh giới — xem `docs/ai-usage.md`. Nhãn đo **lượng thông tin** về sản phẩm, không kết luận review thật/giả.

| | Vai | Gặp pain? | Số lần / 1 tháng qua | Lần gần nhất mất | Đang xoay xở bằng |
|---|---|---|---|---|---|
| P1 | Người mua online ngoài nhóm (mua thường xuyên) | Không ở đơn đồ rẻ gần nhất (chỉ đọc kỹ 1–2/6–7 đơn) | 6–7 lần (đọc kỹ 1–2 lần) | 10 phút *(theo lời P1)* | Bỏ qua review với đồ đơn giản (bấm móng tay); chỉ đọc kỹ ở một số ít đơn |
| P2 | Người mua online ngoài nhóm (rất ít mua online) | Có (bỏ mua vì đọc 1 sao lâu và phân vân) | 0 lần *(lần gần nhất ~3 năm trước)* | Không nhớ phút (mô tả rất lâu) | Lọc thẳng đánh giá 1 sao; thấy rủi ro thì bỏ không mua |
| P3 | Người mua online ngoài nhóm (mua ít) | Không | 1 lần (0 lần đọc kỹ) | 7 giây | Chỉ đọc lướt đúng bình luận đầu tiên rồi đặt ngay |

## 3. ≥5 trích dẫn hoặc ví dụ nguyên văn (có nguồn, bỏ tên)

1. "Chất liệu:vải mềm mịn Mình đã nhận được hàng, chất vải mềm mịn, hình sắc nét, shop giao hàng nhanh rất ưng ý sẽ ủng hộ shop tiếp nữa nhé" — `sp_17/r2` · 5★ · ViMRHP/Shopee — *seeding: cùng câu này xuất hiện 3 lần (r2, r5, r12) trong 2 ngày*
2. "Hàng đóng gói rất đẹp. Quả nhiên người bán đã gửi gắm rất nhiều tâm tư và tình cảm trong lúc gói hàng. Hộp không có dấu hiệu bị móp, chứng tỏ bộ phận vận chuyển đã nâng như nâng trứng, hứng như hứng hoa. Xin nghiêng mình…" — `sp_21/r5` · 5★ · Shopee (Nhật thu) — *seeding: câu y hệt xuất hiện ở sp_22/r1 — một sản phẩm khác*
3. "“Mình mua vì cần cục pin nhỏ gọn mang đi làm, dùng mấy hôm thấy khá tiện. Nam châm hút chắc, gắn sau máy cầm đi lại không bị tuột. 5000mAh thì không phải kiểu sạc đầy được mấy lần đâu, chủ yếu cứu pin lúc gần hết là hợp…" — `sp_22/r4` · 5★ · Shopee (Nhật thu) — *nội dung nói về cục pin sạc trên trang bàn phím + chuột*
4. "Tốt . Đẹp" — `sp_04/r3` · 5★ · Điện Máy Xanh — *5★ không có thông tin gì về sản phẩm*
5. "Shop ship hàng nhanh và đóng gói cẩn thận chắc chắn , sản phẩm chưa dùng nên sẽ đáng giá chất lượng sau nè, shipper tận tình dễ thương, hi vọng máy chạy tốt" — `sp_19/r2` · 5★ · ViMRHP/Shopee — *5★ nhưng tự nhận chưa dùng sản phẩm*
6. "Máy thì không có vấn đề. Mua ở dmx chủ yếu do bao gồm công lắp đặt. Mà thợ lắp đặt làm ăn làm quá chán. Lắp qua loa xong bỏ về trong. Dây điện cấn kênh không để ý, lắp méo xẹo. Rồi bên trong có cái núm chỉnh hướng gió, n…" — `sp_04/r10` · 2★ · Điện Máy Xanh — *2★ chỉ vì lắp đặt, máy không có vấn đề*
7. `"1. gần 3 năm trước, rubik · 2. Đọc 1 sao · 3. Lâu vãi c*** · 4. Có, quyết định đ** mua"` — `P2` (phỏng vấn tin nhắn 27/11/2026, đã che ký tự từ tục) — *lọc thẳng 1 sao, thấy mất nhiều thời gian và bỏ đơn vì rủi ro*
8. `"5. 6-7 lần, đọc đc 1 2 lần"` (`P1`) và `"2. có, đọc được cái comment đầu tiên · 3. 7s"` (`P3`) — phỏng vấn tin nhắn 27/11/2026 — *bằng chứng trái giả thuyết với hàng giá rẻ: mua đồ nhỏ như bấm móng tay/kẹp gắp thức ăn thì lướt rất nhanh hoặc không đọc review*

## 4. Các nguồn có khớp nhau không

Nhóm đã đối chiếu **2 nguồn độc lập (đào data + phỏng vấn 3 người ngoài nhóm)**:
- **Đào data** (Điện Máy Xanh, ViMRHP/Shopee và Shopee do nhóm thu) cho thấy nhiễu trên 5★ rất rõ: ở Điện Máy Xanh nhiễu chủ yếu là review 5★ **chung chung** (32 L so với 8 S trên 89 review 5★); ở Shopee có thêm **văn mẫu lặp nguyên câu** (`sp_17`, `sp_19`, `sp_21`/`sp_22`).
- **Phỏng vấn P1–P3** cho thấy **sự phân hóa quan trọng theo giá trị/rủi ro mặt hàng**: khi xem món cần cân nhắc (P2 xem Rubik), người mua có thói quen lọc thẳng 1 sao, thấy mất rất nhiều thời gian và sẵn sàng bỏ đơn; nhưng với hàng giá rẻ, ít rủi ro (P1 mua bấm móng tay, P3 mua kẹp gắp thức ăn), họ chỉ đọc 7 giây hoặc bỏ qua hoàn toàn (P1 mua 6–7 lần/tháng nhưng chỉ đọc kỹ 1–2 lần).
- **Khớp và lệch:** Hai nguồn khớp nhau ở hành vi người mua không tin ngay 5★ mà hay tìm điểm rủi ro ở 1 sao khi mua món cần cân nhắc; nhưng **lệch ở phạm vi áp dụng** — pain lọc review không xuất hiện ở mọi đơn hàng mà tập trung vào **sản phẩm giá trị trung bình–cao hoặc có rủi ro kỹ thuật** (điện tử, gia dụng điện).

## 5. Kết luận

Giả thuyết ở `evidence/hypothesis.md`:
- **H1 — đúng (theo data):** gần một nửa review 5★ tự nhiên ở Điện Máy Xanh (44,9%) không chứa thông tin cụ thể về sản phẩm; ở Shopee có văn mẫu lặp nguyên câu.
- **H3 — phải đổi:** review 1–2★ chỉ vì giao hàng/lắp đặt hiếm (5,7%); điểm thấp chủ yếu do lỗi sản phẩm thật. Nên giảm nhấn mạnh "tách lỗi vận chuyển" trong pitch, giữ như tính năng phụ.
- **H2 — đúng một phần, cần thu hẹp phân khúc (theo phỏng vấn P1–P3):** 1/3 người (P2) thấy đọc review 1 sao rất lâu và bỏ mua; 2/3 người (P1, P3) không mất thời gian đọc review khi mua đồ nhỏ giá rẻ (bấm móng tay, kẹp gắp), riêng P1 chỉ đọc kỹ 1–2/6–7 đơn/tháng. Do đó ReviewShield cần định vị cho **đơn hàng giá trị trung bình–cao / đồ điện tử–gia dụng**, không phải mọi giao dịch lặt vặt.

Điều vẫn chưa biết: mẫu phỏng vấn còn nhỏ (3 người, trong đó 2 lần mua gần nhất là đồ giá rẻ và 1 người rất ít mua online) nên chưa đo được thời gian trung bình trên nhóm mua đồ điện tử/gia dụng thường xuyên và chưa kiểm chứng người mua có đổi quyết định khi thấy Điểm tin cậy thực không (sẽ kiểm thêm ở bước `validation/log.md` tại CP4). Nhận xét thêm cho nhóm: với sản phẩm seeding mà toàn review 5★ (`sp_17`–`sp_19`), Điểm tin cậy thực vẫn bằng điểm sàn (5,0); chỉ `trust_level = low` và `verified_ratio` thấp mới lộ vấn đề → giao diện cần hiển thị nổi bật hai chỉ số này.

## Lịch hẹn / Thực hiện phỏng vấn (chỉ ghi vai và giờ, không tên)

| Vai | Giờ thực hiện | Đã xong? |
|---|---|---|
| P1 — Người mua online ngoài nhóm (mua thường xuyên) | 27/11/2026 ~22:20 (tin nhắn) | ☑ |
| P2 — Người mua online ngoài nhóm (rất ít mua online) | 27/11/2026 ~22:20 (tin nhắn) | ☑ |
| P3 — Người mua online ngoài nhóm (mua ít) | 27/11/2026 ~22:20 (tin nhắn) | ☑ |
