# Đào data — cách đếm và kết quả

> Điền ở guide bước 1.2. Ôn lại: ngày 2, ngày 6 · lab ngày 2, lab ngày 6.
> Không đào data thì xoá file này. Script / công thức đếm để trong repo (vd `evidence/count.py` hoặc ghi công thức Sheets ngay dưới), người khác chạy lại phải ra cùng số.
> Repo chỉ chứa số đã tổng hợp và vài dòng ví dụ — không chép lại nguyên file data.

## 1. Cách đếm — viết TRƯỚC khi chạy

- Data dùng: `data/samples/sp_XX.json` ghép `eval/labels.csv` theo mã sản phẩm/review; review công khai dự kiến thu thủ công ngày 27–28/11/2026. Khoảng ngày thu thực tế: __ đến __. Bản thô ở `raw_reviews/` ngoài repo; cách thu và giới hạn tại `data/DATA_CARD.md`.
- `picked=natural`: review đầu theo thứ tự mặc định; `picked=added`: review lấy thêm bằng bộ lọc sao. Không gộp `added` vào thống kê tỷ lệ tự nhiên. Nhãn theo `docs/AI_PROMPT_AND_SCORING.md §1`: sp_21–sp_30 do Claude Code gán nháp theo tiêu chí của Nguyễn Mạnh Tường, Nguyễn Mạnh Tường đặt tiêu chí và rà các dòng ranh giới; sản phẩm tự thu do Nguyễn Mạnh Tường gán tay. sp_21–sp_30 lấy qua bộ lọc sao nên toàn bộ là `added`.

| Mã | Đếm gì / tử số x | **Mẫu số N** | Tập và cách lọc |
|---|---|---|---|
| A (H1) | Review 5★ có nhãn `low_signal` hoặc `suspicious_pattern` | Tổng review 5★ `picked=natural` | Chỉ `natural`, không tính review thêm bằng lọc sao. |
| B (H3), natural | Review 1–2★ có nhãn `logistics_only` | Tổng review 1–2★ `picked=natural` | Chỉ `natural`. |
| B (H3), natural+added | Review 1–2★ có nhãn `logistics_only` | Tổng review 1–2★ trong `natural+added` | Báo một dòng riêng, không diễn giải là tỷ lệ tự nhiên. |
| C | Sản phẩm có Điểm tin cậy thực thấp hơn điểm sàn quá 0.3 (`lower_than_platform`) | Tổng sản phẩm trong tập đếm | Tính điểm từ nhãn chuẩn bằng công thức §4 trên cụm review đã thu, gồm cả `added` nếu có. |
| D | Review 5★ khớp regex bên dưới, không cần nhãn | Tổng review 5★ trong `natural+added` | Khớp không phân biệt hoa/thường; mỗi review chỉ đếm một lần dù khớp nhiều cụm. |

Regex D (giữ nguyên để chạy lại):

```text
(chưa dùng|chưa sử dụng|chưa xài|chưa dung|chua dung|chua su dung|lấy xu|nhận xu|lay xu|nhan xu)
```

- Script dự kiến: `evidence/count_reviews.py` (sẽ được bàn giao sau). Chạy từ thư mục gốc repo bằng `python3 evidence/count_reviews.py`; không gọi model và không thu dữ liệu trên mạng.
- Báo từng dòng dưới dạng `x/N (y%)`, với `y = 100*x/N`; nếu `N=0`, ghi không có mẫu để tính, không ghi 0%. Với C, ghi riêng số sản phẩm `insufficient_data` nếu có; không tự gán thành `lower_than_platform`.
- A phản ánh nhãn tín hiệu, D chỉ phản ánh cụm từ; cả hai không chứng minh review giả. Chỉ điền kết quả sau khi chạy script và kiểm tay; không ước lượng để lấp ô trống.

## 2. Đọc trước, đếm sau

Đã đọc __ dòng đầu và từ điển cột. Các *kiểu* hành vi thấy được (trước khi định nghĩa thứ cần đếm):
(Ghi sau khi đọc thật; chú ý `rating`, `picked` và mã ghép nhãn.)
- __
- __

## 3. Kết quả

Chạy lúc 2026-11-27 18:34:17 +0700, trên 26 sản phẩm, 317 review (natural 192, added 125). Lệnh: `python3 evidence/count_reviews.py`. **Nhãn do AI gán theo tiêu chí TV3** (xem `docs/ai-usage.md`); `natural` gồm 156 review Điện Máy Xanh + 36 review ViMRHP.

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| A | 72 / 125 | 57.6% | Review 5★ natural; low_signal hoặc suspicious_pattern |
| B-natural | 2 / 35 | 5.7% | Review 1–2★ natural; logistics_only |
| B-natural+added | 5 / 98 | 5.1% | Review 1–2★ gồm added; không phải tỷ lệ tự nhiên |
| C | 15 / 26 | 57.7% | Sản phẩm đủ nhãn; tính cả added; insufficient_data: 0 sản phẩm (vẫn trong mẫu số) |
| D | 1 / 185 | 0.5% | Review 5★ natural+added; khớp regex NFC, không cần nhãn |

Ghi dạng "x/N (y%)". "Nhiều bạn…" không phải số.
(Điền riêng A, B-natural, B-natural+added, C, D; ghi mẫu số và thời điểm chạy từng dòng.)

## 4. ≥5 ví dụ cụ thể (mã dòng / mã đã ẩn danh, không đoán ai là ai)

(Chép nguyên văn từ dữ liệu đã ẩn danh, kèm `sp_XX/rX`, sao và `picked`; không dùng ví dụ minh họa làm bằng chứng.)

1. sp_02/r5 · 5★ · natural · low_signal · "Hàng rất tốt.... dùng rễ ràng"
2. sp_02/r7 · 5★ · natural · low_signal · "Vì sao camera của tôi không có trong danh sách bảo hành"
3. sp_04/r10 · 2★ · natural · logistics_only · "Máy thì không có vấn đề. Mua ở dmx chủ yếu do bao gồm công lắp đặt. Mà thợ lắp đặt làm ăn làm quá chán. Lắp qua loa xong bỏ về trong. Dây điện cấn kênh không để ý, lắp méo xẹo. Rồi bên trong có cái núm chỉnh hướng gió, nhà không có ống thông thì phải xoay núm qua hướng tuần hoàn phía trước. Vậy mà thợ mà không làm, quạt chạy ù ù mà không có tí gió nào mà cũng bỏ về được. Tốn cả buổi tự khoan tường rồi lắp. Biết vậy mua chỗ khác rồi tự lắp cho rẻ mà còn đỡ bực."
4. sp_04/r12 · 1★ · natural · logistics_only · "Quá tệ Nhân viên tư vấn 1 đằng, kỹ thuật vào lắp 1 nẻo.Không hộ trợ khoan tủ, tường lắp đặt đường ống thông hơi ra ngoài thì máy này có tác dụng gì Kỹ thuật lắp cho chạy tuần hoàn thì lại không bật sang chế độ chạy tuần hoàn.Riết DMX còn thua cái chợ trời."
5. sp_19/r2 · 5★ · natural · low_signal · "Shop ship hàng nhanh và đóng gói cẩn thận chắc chắn , sản phẩm chưa dùng nên sẽ đáng giá chất lượng sau nè, shipper tận tình dễ thương, hi vọng máy chạy tốt"
6. sp_17/r2, r5, r12 · 5★ · natural · suspicious_pattern · cùng một câu "Mình đã nhận được hàng, chất vải mềm mịn, hình sắc nét, shop giao hàng nhanh rất ưng ý sẽ ủng hộ shop tiếp nữa nhé" lặp 3 lần trong 2 ngày (ViMRHP)

## 5. Giới hạn của data

Data cho biết người ta **làm gì**, không cho biết **vì sao**. Thiếu gì, lệch về phía nào: __
→ Kiểm lại bằng phỏng vấn / khảo sát nào: __
(Nêu mẫu mục tiêu 25–30 sản phẩm do nhóm chọn, thiên về hàng bán chạy; văn bản tại thời điểm chép; nhãn do một người gán; đối chiếu H2 bằng dữ liệu người mua thật.)
