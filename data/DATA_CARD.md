# DATA CARD — Dữ liệu dự án ReviewShield

**Phụ trách:** Nguyễn Mạnh Tường (`2A202603646`). Các con số dưới đây là mục tiêu; bảng thực tế chỉ điền sau khi thu và kiểm dữ liệu.

## 1. Nguồn và cách thu

- Nguồn: review sản phẩm công khai trên Shopee, Tiki, TikTok Shop / Lazada; thu **thủ công trên trình duyệt thật**, dự kiến ngày **27–28/11/2026**.
- Theo ghi nhận của nhóm ngày 27/11/2026, mọi yêu cầu tự động từ máy nhóm tới `tiki.vn` (cả trang chủ và `api/v2`) đều trả **HTTP 403**. Vì vậy không dùng script lấy Tiki; không vượt chặn anti-bot theo `AGENTS.md`.
- Người thu ghi tên sản phẩm, sàn, ngành hàng, điểm sàn đang hiển thị và thời điểm chép trong ghi chép nguồn ngoài repo. Script chỉ chuẩn hóa dữ liệu đã chép, không truy cập sàn.

## 2. Quy mô mục tiêu và thực tế

| Hạng mục | Mục tiêu | Thực tế sau kiểm tra |
|---|---|---|
| Tổng sản phẩm | 25–30 | 10 (bản CP2, 27/11 17:20) |
| Shopee | 10–12 | 10 (sp_21–sp_30, Đặng Long Nhật thu) |
| Tiki | 8–10 | 0 |
| TikTok Shop / Lazada (gộp) | 5–8 | 0 |
| Ngành hàng | 4–5 | 1 (`phu_kien_dien_tu`) |
| Review / sản phẩm | 6–15 | 10–14 (tổng 121) |
| Tổng review `natural` | (điền sau khi thu dữ liệu) | 0 |
| Tổng review `added` | (điền sau khi thu dữ liệu) | 121 (sp_21–sp_30 lấy 5★ và 1★ qua bộ lọc sao) |
| Ngày bắt đầu / kết thúc thu | 27–28/11/2026 | 27/11/2026 (nhận bản thu sp_21–sp_30) / __ |

Phân bổ sàn phải đồng thời nằm trong tổng 25–30 sản phẩm. Ngành hàng dự kiến: phụ kiện điện tử, gia dụng, thời trang, mỹ phẩm, đồ ăn vặt.

## 3. Chọn review và đánh dấu nguồn chọn

1. Lấy khoảng 10 review đầu theo **thứ tự mặc định** của trang, không lọc sao: `picked=natural`.
2. Nếu thiếu review 1–2 sao, dùng bộ lọc sao lấy thêm 2–4 review: `picked=added`. Tổng mỗi sản phẩm giữ trong 6–15 review.
3. Với `raw_reviews/sp_XX.md` (bảng, hướng dẫn ở `sp00.md`), ô “Lọc thêm” trống là `natural`, có đánh dấu là `added`. Với `sp_XX.txt` theo mẫu thô `sp_00_MAU.txt`, sao không có dấu `+` là `natural`; sao có dấu `+` là `added`. Giữ dấu này để script lưu cách chọn, không trộn hai tập khi báo cáo.

Thống kê nhằm hạn chế thiên lệch do lọc sao chỉ dùng `natural`; mẫu này vẫn không phải mẫu ngẫu nhiên. Chỉ số B báo riêng `natural` và `natural+added`; D đếm trên toàn bộ review đã thu và ghi rõ mẫu số. Điểm sản phẩm dùng cụm review đã thu, có thể gồm `added`, nên phải nêu giới hạn này khi diễn giải.

## 4. Làm sạch và ẩn danh PII

- Không chép tên/nickname thật, SĐT, email, địa chỉ, mã đơn hàng, link cá nhân hoặc ảnh người mua vào dữ liệu. Tác giả dùng `user_01`, `user_02`…; review dùng `r1`, `r2`… liên tiếp trong từng sản phẩm.
- Nếu văn bản chứa PII, che phần nhận diện trước khi đưa vào repo và kiểm tay lại. Không giữ bảng đối chiếu mã với danh tính thật trong repo.
- Giữ nguyên phần văn bản còn lại: lỗi chính tả, không dấu, teencode, emoji. Không viết lại lời người mua. Grounding kiểm trên văn bản đã ẩn danh trong mẫu.
- Dữ liệu thô nằm ngoài repo và không commit; không đưa `.env`, API key hoặc nguyên file dữ liệu BTC cấp vào repo.

## 5. Nhãn chuẩn và chiều điểm kỳ vọng

Mỗi review một nhãn theo `docs/AI_PROMPT_AND_SCORING.md §1`. Nhãn chuẩn sp_21–sp_30 (Đặng Long Nhật thu): Claude Code gán theo tiêu chí do Nguyễn Mạnh Tường rút ra (dấu hiệu S: văn hoa, thuần khen, chèn emoji, giọng như AI) kết hợp bảng ranh giới `docs/AI_PROMPT_AND_SCORING.md §1`; Nguyễn Mạnh Tường đặt tiêu chí và rà các dòng ranh giới (đã xem kết quả, sửa 0/121 nhãn). Sản phẩm do Nguyễn Mạnh Tường tự thu: gán tay. Quy ước khi mâu thuẫn: giọng quảng cáo / khuôn mẫu → `suspicious_pattern` dù có nhắc tính năng; nhãn đo lượng thông tin, không đo thật/giả:

| Nhãn | Ranh giới |
|---|---|
| `verified_insight` | Có ít nhất một chi tiết thực tế về bản thân sản phẩm: chất liệu, kích cỡ, độ bền, hiệu năng, mùi vị, trải nghiệm sau dùng. |
| `low_signal` | Khen/chê chung chung, chưa dùng, nhận xu, thơ hoặc ký tự vô nghĩa. |
| `suspicious_pattern` | Lặp cấu trúc bất thường với review khác hoặc văn phong quảng cáo gượng ép; không kết luận người viết là giả. |
| `logistics_only` | Chỉ nói shipper, giao hàng, vỏ hộp ngoài; không nhận xét chất lượng sản phẩm. |

Review vừa nói giao hàng vừa nêu chi tiết sản phẩm không thuộc `logistics_only`. Trường hợp chưa rõ giữ `?` trong bản thô TXT hoặc để trống cả bốn ô V/L/S/G trong bảng Markdown, người gán đọc lại trước khi đưa vào benchmark.

Trong repo, nhãn chuẩn chỉ nằm ở **`eval/labels.csv` và cột `expected` của benchmark**, không nằm trong `data/samples/` vì app gửi nguyên file cho AI. Nhãn đã gán trong bản thô ngoài repo được script chuyển vào bảng nhãn.

`expected_direction` trong mẫu được **tính**, không đoán: áp dụng trọng số `1.00 / 0.15 / 0.10 / 0.00` tương ứng bốn nhãn, tính điểm và `score_delta` bằng công thức Python tại `docs/AI_PROMPT_AND_SCORING.md §4`. Chênh lệch thấp hơn `-0.3` là `lower_than_platform`, cao hơn `0.3` là `higher_than_platform`, còn lại là `near_platform`; tổng trọng số bằng 0 thì `insufficient_data`. Khi dựng benchmark, loại `expected_direction` và mọi nhãn chuẩn khỏi `input`.

## 6. Cấu trúc tệp

| Đường dẫn | Vai trò |
|---|---|
| `../raw_reviews/sp_XX.md` hoặc `../raw_reviews/sp_XX.txt` (ngoài repo) | Bản chép thủ công dạng bảng Markdown (hướng dẫn ở `sp00.md`) hoặc TXT theo `sp_00_MAU.txt`, có nhãn tay và dấu chọn thêm; không commit. |
| `data/samples/sp_XX.json` | Mẫu sản phẩm ẩn danh cho demo; có `expected_direction` tính từ nhãn, KHÔNG có nhãn chuẩn từng review và không có dấu `natural/added` (hai thông tin này nằm ở `eval/labels.csv`). |
| `eval/labels.csv` | Bảng nhãn chuẩn để kiểm tra, đếm và dựng đáp án; ghép với mẫu theo mã sản phẩm/review. |
| `data/scripts/make_samples.py` | Chuẩn hóa bản thô thành mẫu và bảng nhãn. |
| `data/scripts/check_samples.py` | Kiểm dữ liệu mẫu và tính nhất quán với bảng nhãn. |
| `data/scripts/build_benchmark.py` | Ghép câu sản phẩm và câu tự viết thành benchmark, chặn thay đổi trái quy tắc khóa CP2. |
| `eval/benchmark.csv` | Sáu cột `id,input,expected,pass_criterion,type,source`; câu sản phẩm mang ID `RS01`… và `source=data_that`. |
| `eval/extra_cases.csv` | Bốn câu tự viết `X01–X04`, `source=tu_viet`: ba ca từ chối và một ca khó thiếu review. |

Đây là quy trình dự kiến; việc mô tả script không xác nhận script đã hoàn tất hoặc dữ liệu đã được thu.

## 7. Quy trình chạy lại

Chạy tại thư mục gốc repo, sau khi đã chép và gán nhãn dữ liệu thật vào thư mục `raw_reviews` ngoài repo:

```bash
python3 data/scripts/make_samples.py
python3 data/scripts/check_samples.py
python3 data/scripts/build_benchmark.py
python3 run.py check
```

Chỉ tiếp tục khi bước trước hợp lệ; không đưa file hướng dẫn `sp00.md` và mẫu minh họa `sp_00_MAU.txt` vào dữ liệu thật. Chạy đếm sau khi script được bàn giao:

```bash
python3 evidence/count_reviews.py
```

Định nghĩa A–D và mẫu số nằm ở `evidence/data-mining.md §1`. Sau CP2 (19:30 ngày 27/11/2026), không sửa `expected` hoặc xóa câu trượt; `build_benchmark.py` phải tự chặn. Tổng benchmark cần nằm trong 25–30 câu, tính cả bốn câu X; xem ràng buộc số câu tại `eval/README.md §1` trước khi khóa bộ thử.

## 8. Giới hạn và thiên lệch

- Mẫu mục tiêu 25–30 sản phẩm do nhóm chọn, thiên về sản phẩm bán chạy; không đại diện toàn sàn hay toàn thị trường.
- Thứ tự mặc định do sàn quyết định; `natural` vẫn có thiên lệch xếp hạng. `added` cố ý tăng review ít sao, không dùng chung để ước lượng tỷ lệ tự nhiên.
- Review chỉ là văn bản tại thời điểm chép; không có lịch sử tài khoản, dữ liệu xác minh giao dịch hoặc cơ sở kết luận gian lận.
- Nhãn do một người gán, có thể lệch ở trường hợp ranh giới. Nhãn mô tả tín hiệu thông tin, không xác nhận tác giả thật/giả.
- Điểm tính trên cụm review nhỏ khác phạm vi điểm sàn. Chênh lệch không chứng minh điểm sàn sai hoặc phản ánh chất lượng toàn bộ sản phẩm.
