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

| Đếm gì | x / N | % | Ghi chú |
|---|---|---|---|
| | | | |
| | | | |

Ghi dạng "x/N (y%)". "Nhiều bạn…" không phải số.
(Điền riêng A, B-natural, B-natural+added, C, D; ghi mẫu số và thời điểm chạy từng dòng.)

## 4. ≥5 ví dụ cụ thể (mã dòng / mã đã ẩn danh, không đoán ai là ai)

(Chép nguyên văn từ dữ liệu đã ẩn danh, kèm `sp_XX/rX`, sao và `picked`; không dùng ví dụ minh họa làm bằng chứng.)

1.
2.
3.
4.
5.

## 5. Giới hạn của data

Data cho biết người ta **làm gì**, không cho biết **vì sao**. Thiếu gì, lệch về phía nào: __
→ Kiểm lại bằng phỏng vấn / khảo sát nào: __
(Nêu mẫu mục tiêu 25–30 sản phẩm do nhóm chọn, thiên về hàng bán chạy; văn bản tại thời điểm chép; nhãn do một người gán; đối chiếu H2 bằng dữ liệu người mua thật.)
