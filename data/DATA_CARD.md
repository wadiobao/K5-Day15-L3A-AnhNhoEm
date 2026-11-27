# DATA CARD — Dữ liệu dự án ReviewShield

**Phụ trách:** Nguyễn Mạnh Tường (`2A202603646`). Bảng §2 ghi cả mục tiêu và số thực tế (cập nhật 27/11/2026 18:40).

## 1. Nguồn và cách thu

- Nguồn: review sản phẩm công khai trên Shopee, Tiki, TikTok Shop / Lazada; thu **thủ công trên trình duyệt thật**, dự kiến ngày **27–28/11/2026**.
- Theo ghi nhận của nhóm ngày 27/11/2026, mọi yêu cầu tự động từ máy nhóm tới `tiki.vn` (cả trang chủ và `api/v2`) đều trả **HTTP 403**. Vì vậy không dùng script lấy Tiki; không vượt chặn anti-bot theo `AGENTS.md`.
- Người thu ghi tên sản phẩm, sàn, ngành hàng, điểm sàn đang hiển thị và thời điểm chép trong ghi chép nguồn ngoài repo. Script chỉ chuẩn hóa dữ liệu đã chép, không truy cập sàn.

### Nguồn thứ hai: bộ dữ liệu công khai

- **Bộ dữ liệu công khai `p-storm/vietnamese-electronics-product-reviews`** (Hugging Face, giấy phép **apache-2.0**, nguồn **Điện Máy Xanh + Thế Giới Di Động**, **32.099 review** theo bản JSONL đã chuyển và `../raw_reviews/public/README_dataset.md`). Chỉ đọc bản có sẵn ngoài repo, không truy cập mạng hoặc cào sàn.
- Chạy từ gốc repo: `python3 data/scripts/import_public.py --candidates` để xem thống kê, `python3 data/scripts/import_public.py --select` để xem bộ chọn, rồi `python3 data/scripts/import_public.py --write` để ghi bảng ngoài repo. Có thể đổi JSONL bằng `--input <đường_dẫn>`. Mặc định không cờ chỉ in hướng dẫn.
- Gom theo `(source, product_id)`, sắp `row_order` tăng dần. **12 review không rỗng đầu theo thứ tự file gốc = natural**, không phải thứ tự mặc định hiện tại của website. Khi xuất bỏ review nghi SĐT/email/link, mã dài hoặc tài khoản và lấy review kế tiếp; nếu 12 dòng hợp lệ không có 1–2★, thêm tối đa 2 review 1–2★ tiếp theo, đánh dấu `added` bằng `x` ở “Lọc thêm”.
- Quy tắc chọn (quota cuối: 4 `higher` vì bộ dữ liệu chỉ có 4 ứng viên đạt, 6 `near`, 4 `lower`, 2 `kho`): ứng viên `higher` có ít nhất 2 review 1–2★ nhắc giao/lắp nhưng không nhắc từ khóa lỗi; 6 `near` có tối đa 2 review 1–2★ và độ dài trung bình ít nhất 60 ký tự; 4 `lower` có `platform_rating >= 4.0` và ít nhất 3 review 1–2★ nhắc lỗi; 2 `kho` ưu tiên tỷ lệ chữ không dấu cao nhất. Mọi chỉ số nhóm dùng 12 review không rỗng đầu. Tỷ lệ không dấu là số chữ cái ASCII chia tổng chữ cái, không tính số/dấu câu; đây chỉ là chỉ số gần đúng cho không dấu/teencode.
- Chọn tất định, không ngẫu nhiên: xét nhóm ít ứng viên so với quota trước; ưu tiên category chưa dùng, nguồn đang ít hơn, rồi điểm phù hợp và ID/nguồn theo thứ tự cố định; riêng `kho` ưu tiên tỷ lệ không dấu trước. Mỗi category tối đa 2 sản phẩm, ưu tiên đa dạng gia dụng/điện tử và cân bằng hai nguồn khi dữ liệu cho phép. Thiếu metadata không tự suy ID/category hoặc gom mọi ID rỗng thành một sản phẩm; không đủ quota thì dừng, không nới tiêu chí. Nhóm ứng viên chỉ phục vụ chọn mẫu, **không phải nhãn V/L/S/G hoặc chiều điểm chuẩn**.
- **`platform_rating` là điểm suy ra**: trung bình rating của **toàn bộ review sản phẩm trong bộ dữ liệu**, kể cả dòng không được xuất, làm tròn 1 chữ số thập phân. **Không phải điểm đang hiển thị trên web**; review trong bộ có thể đã được người tạo bộ lọc trước. Không dùng điểm này để kết luận điểm sàn sai.
- Gộp khoảng trắng, escape dấu `|`, thay tên người sau từ xưng hô/nghề bằng **`[tên]`** và giữ từ xưng hô; in từng vị trí đã thay để người kiểm xem, không in lại tên gốc. V/L/S/G để trống cho người gán rà lại. Regex không bảo đảm loại hết tên/địa chỉ; vẫn phải kiểm tay trước khi đưa mẫu vào repo.
- Bản JSONL gốc, bảng `sp_XX.md` và `public/selection_log.md` nằm trong `../raw_reviews/` **ngoài repo**. Không commit nguyên bộ dữ liệu; bảng đã có nội dung được bảo vệ khỏi ghi đè, không đụng `sp_21–sp_30`. Chưa ghi số sản phẩm thực tế của nguồn này; người phụ trách điền sau khi rà dữ liệu.

### Nguồn thứ ba: ViMRHP (Shopee, bộ công khai)

- **`trucmtnguyen/ViMRHP`** (Hugging Face, giấy phép **CC BY-NC-ND 4.0**): review Shopee thật cào năm 2023–2024 kèm `CommentDate`. Dùng cho nhóm kịch bản `seeding_heavy` (sp_17 thời trang, sp_18 khẩu trang, sp_19 máy xay sinh tố).
- Mỗi sản phẩm lấy **12 review mới nhất theo `CommentDate`** (natural); bỏ hẳn review có SĐT/email/link (không gặp trường hợp nào). Chỉ giữ số sao, nội dung, tên sản phẩm; **bỏ** `UserId`, `ShopId`, `UserShopId` và trường `Response` (do AI sinh trong bộ gốc).
- **Tuân thủ giấy phép:** NC — dùng cho bài lab phi thương mại; BY — ghi nguồn tại đây; ND — **giữ nguyên văn nội dung review**, chỉ gộp xuống dòng thành dấu cách để đưa vào bảng/JSON, không sửa chữ, không che tên (review cần che sẽ bị loại thay vì sửa). `platform_rating` = trung bình rating của toàn bộ review sản phẩm đó trong bộ (24 review/sản phẩm).
- Sản phẩm đã nhập nhưng **không đưa vào benchmark** (bảng thô để riêng ở `../raw_reviews/loai_khoi_benchmark/`, không có JSON trong `data/samples`): sp_01, sp_07, sp_10 — để benchmark giữ 30 câu, cân bằng 4 nhóm kịch bản và giữ 2 ca `higher_than_platform`.

## 2. Quy mô mục tiêu và thực tế

| Hạng mục | Mục tiêu | Thực tế sau kiểm tra |
|---|---|---|
| Tổng sản phẩm | 25–30 | 26 (sp_02–sp_06, sp_08, sp_09, sp_11–sp_19, sp_21–sp_30) |
| Shopee | 10–12 | 13 (sp_21–sp_30 Đặng Long Nhật thu thủ công; sp_17–sp_19 từ ViMRHP) |
| Tiki | 8–10 | 0 |
| TikTok Shop / Lazada (gộp) | 5–8 | 0 — thay bằng Điện Máy Xanh: 13 (bộ p-storm, sp_02–sp_16) |
| Ngành hàng | 4–5 | 16 (vd phu_kien_dien_tu, gia_dung, thoi_trang, suc_khoe_lam_dep, tu_lanh, may_lanh, noi_com_dien…) |
| Review / sản phẩm | 6–15 | 10–14 (tổng 317) |
| Tổng review `natural` | (điền sau khi thu dữ liệu) | 192 (Điện Máy Xanh + ViMRHP) |
| Tổng review `added` | (điền sau khi thu dữ liệu) | 125 (121 của sp_21–sp_30 lấy qua bộ lọc sao + 4 review 1–2★ bổ sung) |
| Ngày bắt đầu / kết thúc thu | 27–28/11/2026 | 27/11/2026 / 27/11/2026 (bản benchmark CP2–CP3) |

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
