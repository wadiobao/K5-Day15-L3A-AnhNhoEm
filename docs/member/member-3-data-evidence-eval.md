# Task Specification — Thành viên 3: Dữ liệu Mẫu, Bằng chứng Pain & Bộ Eval

* **Phụ trách:** Nguyễn Mạnh Tường (`2A202603646`)
* **Module:** `Data, Evidence & Evaluation`
* **Nhánh Git:** `data/2a202603646-samples-evidence-eval`
* **File được sửa:** `data/samples/*.json`, `data/DATA_CARD.md`, `evidence/data-mining.md`, `evidence/interviews/*`, `evidence/survey/*`, `evidence/summary.md`, `eval/benchmark.csv`, `eval/metric_spec.yaml` (chỉ trước CP2), `eval/report.md`
* **File cấm sửa:** `eval/run_eval.py`, `run.py`, và tuyệt đối không sửa nội dung các file kết quả `eval/run-*.csv` (ngoài việc điền cột chấm `pass`, `ghi_chu` theo quy trình khung)

---

## 1. Đầu vào (Input)

* **Dữ liệu review thật từ các sàn TMĐT Việt Nam** (phân bổ đủ 3–4 sàn thật, tổng 25–30 sản phẩm trên 4–5 ngành hàng: phụ kiện điện tử, đồ gia dụng, thời trang, mỹ phẩm, đồ cá nhân):
  * **Shopee (10–12 sản phẩm):** Tập trung các sản phẩm có rõ hiện tượng review nhận xu ("chưa dùng cho 5 sao"), seeding lặp mẫu và 1 sao do shipper.
  * **Tiki (8–10 sản phẩm):** Thu thập trực tiếp từ trang sản phẩm hoặc API review công khai (`tiki.vn/api/v2/reviews?product_id=...`).
  * **TikTok Shop / Lazada (5–8 sản phẩm):** Tập trung sản phẩm bán chạy theo trend, nhiều review ngắn/teencode hoặc phàn nàn giao hàng.
* **Phối hợp chia tải:** Nguyễn Mạnh Tường phụ trách chính 15–20 sản phẩm (Tiki + Shopee) và chuẩn hóa toàn bộ kho mẫu; Đặng Long Nhật hỗ trợ gom 10 sản phẩm thật từ Shopee/TikTok Shop bàn giao lại cho Nguyễn Mạnh Tường chuẩn hóa trước CP2.
* Phỏng vấn người mua online thật (ngoài nhóm, tối thiểu 3 người) và/hoặc khảo sát người mua thật (ngoài nhóm, tối thiểu 20 người).
* Kết quả chạy `python run.py eval` sau khi Module 1 + Module 2 hoàn tất tích hợp.

---

## 2. Đầu ra (Output)

1. **Kho mẫu sản phẩm (`data/samples/*.json`):** 25–30 file JSON sản phẩm ẩn danh (mỗi file 6–15 review trải đều 1–5 sao), đúng schema tại `docs/member/README.md §2.1`.
2. **Bằng chứng pain (`evidence/`):**
   * `evidence/data-mining.md`: Thống kê định lượng (`x/N`, `%`, cách đếm lặp lại được, >= 5 ví dụ nguyên văn đã ẩn danh).
   * `evidence/interviews/P1.md`, `P2.md`, `P3.md` (theo `TEMPLATE.md`) và/hoặc `evidence/survey/`.
   * `evidence/summary.md`: Tổng hợp đầy đủ 5 mục, kết luận giả thuyết H1/H2/H3 trong `evidence/hypothesis.md`.
3. **Bộ benchmark (`eval/benchmark.csv`):** Đủ 6 cột `id,input,expected,pass_criterion,type,source`, đã xóa 3 dòng ví dụ `B01–B03`:
   * **Mốc CP2 (19:30 Thứ Sáu 27/11):** Tối thiểu **10 câu thử thật**.
   * **Mốc CP3 (10:00 Thứ Bảy 28/11):** **20–30 câu thử thật**, phân bổ đủ:
     * `thuong`: các sản phẩm đại diện đủ 3 chiều (`near_platform`, `lower_than_platform`, `higher_than_platform`).
     * `kho` (**>= 5 câu**): review mỉa mai, tiếng Việt không dấu/teencode nặng, review hỗn hợp (vừa khen giao nhanh vừa chê sản phẩm lỗi), hoặc sản phẩm 100% `logistics_only`.
     * `tu_choi` (**>= 2 câu**, gồm ít nhất 2 câu tấn công): yêu cầu cào link trực tiếp Shopee/TikTok, yêu cầu tự nhắn tin cho shop, hoặc prompt injection ép chấm 5.0 sao.
4. **Báo cáo đánh giá (`eval/report.md`):** Tổng hợp điểm 4 metric từ `eval/metric_spec.yaml`, phân tích các ca trượt và đề xuất tinh chỉnh prompt cho Module 1.

---

## 3. Logic xử lý (Processing Logic)

### 3.1. Quy trình thu thập, làm sạch & ẩn danh dữ liệu thật đa sàn (`data/samples/`)
1. **Cách thu thập hợp lệ (không vượt CAPTCHA, không nhúng crawler vào `codebase/`):**
   * **Với Tiki:** Gọi endpoint review công khai `tiki.vn/api/v2/reviews?product_id=<ID>&limit=20` bằng script offline hoặc đọc trực tiếp từ trang sản phẩm.
   * **Với Shopee / TikTok Shop / Lazada:** Thành viên mở trực tiếp trang sản phẩm trên trình duyệt thật, lọc đủ dải 1–5 sao (mỗi sản phẩm lấy 6–15 review tiêu biểu gồm cả 5 sao nhận xu/seeding, 4–5 sao chi tiết và 1–3 sao phàn nàn chất lượng/shipper), copy văn bản gốc vào file thô cục bộ rồi chạy bước chuẩn hóa sang JSON.
2. **Ghi nhận siêu dữ liệu gốc:** `product_name`, `category`, `platform` (`Shopee` / `TikTok Shop` / `Tiki` / `Lazada`), `platform_rating` hiển thị trên sàn tại thời điểm thu thập.
3. **Quét và xóa 100% PII:** Loại bỏ toàn bộ tên tài khoản, số điện thoại, địa chỉ, mã đơn hàng, link cá nhân; thay tác giả bằng `user_01`, `user_02`... Không commit file thô chưa ẩn danh lên Git.
4. **Giữ nguyên ngôn ngữ tự nhiên:** Không sửa lỗi chính tả, không thêm dấu tiếng Việt, giữ nguyên teencode để phản ánh đúng thực tế.
5. **Gắn nhãn chuẩn thủ công (ground truth):** Đánh dấu `expected_direction` cho từng sản phẩm và gán nhãn chuẩn từng review làm cơ sở tạo `eval/benchmark.csv` và thống kê `evidence/data-mining.md`.

### 3.2. Quy trình chạy & chấm Eval
1. Kiểm tra cấu trúc bằng `python run.py check` (đảm bảo không còn cảnh báo thiếu câu/dòng mẫu).
2. Sau khi Module 1 + 2 merge, chạy `python run.py eval` (bắt buộc chạy với model thật trong `.env`).
3. Chấm cột `pass` và `ghi_chu` trong file `eval/run-*.csv` mới sinh theo đúng `pass_criterion`, không chỉnh sửa cột `output` hay số token.
4. Chạy `python run.py score` và tổng hợp kết quả vào `eval/report.md` (gửi tóm tắt cho Đội trưởng dán vào `spec.md §8`).

---

## 4. Quy tắc nghiệp vụ (Business Rules)

1. **Không bịa bằng chứng (BTC Hard Rule):** Tuyệt đối không bịa người phỏng vấn, trích dẫn hay số liệu khảo sát. Nếu chưa kịp phỏng vấn, ưu tiên đạt ngưỡng mạnh ở nguồn đào data công khai (`evidence/data-mining.md`).
2. **Bảo vệ quyền riêng tư:** 100% file trong `data/` và `evidence/` không chứa tên thật hoặc thông tin nhận diện cá nhân.
3. **Mốc khóa CP2 (19:30 Thứ Sáu 27/11):** Sau mốc này tuyệt đối KHÔNG sửa `eval/metric_spec.yaml`, KHÔNG xóa câu thử bị trượt và KHÔNG sửa cột `expected` cho khớp output của AI.
4. **Tính khách quan nguồn dữ liệu:** Tỷ lệ câu thử có nguồn `nguoi_dung` hoặc `data_that` chiếm đa số trong `eval/benchmark.csv`.

---

## 5. Tiêu chí đánh giá (Acceptance Criteria)

* `python run.py check` báo **0 cảnh báo** ở phần `Kiểm eval/benchmark.csv` (đủ số lượng câu, đủ `kho >= 5`, đủ `tu_choi >= 2`, không còn dòng `(ví dụ)`).
* Có >= 25 file JSON hợp lệ trong `data/samples/` (parse được bằng `json.loads`, đủ trường bắt buộc, không lộ PII).
* `evidence/summary.md` có ít nhất 1 nguồn đạt ngưỡng rubric R1 (khuyến nghị mạnh: đào data + phỏng vấn/khảo sát đối chiếu nhau) và >= 5 trích dẫn nguyên văn có nguồn.
* `eval/report.md` có đầy đủ số đo 4 metric khớp `eval/metric_spec.yaml` (`label_accuracy >= 85%`, `direction_match >= 85%`, `citation_grounding == 100%`, `actionable_quality >= 80%`).

---

## 6. Kế hoạch kiểm thử (Testing Checklist)

1. **Kiểm tra JSON mẫu:** Chạy lệnh kiểm tra parse toàn bộ `data/samples/*.json` đảm bảo 100% hợp lệ UTF-8, `rating` nằm trong `1..5`, `author` khớp mẫu `user_XX`.
2. **Kiểm tra cấu trúc benchmark:** Chạy `python run.py check` sau mỗi lần cập nhật `eval/benchmark.csv`.
3. **Soát PII thủ công:** Tìm kiếm nhanh các từ khóa SĐT (`09`, `03`, `08`, `07`, `@gmail`, địa chỉ) trong `data/` và `evidence/` đảm bảo trả về 0 kết quả.
4. **Kiểm tra chạy eval thật:** Chạy `python run.py eval` và `python run.py score`, xác nhận có file `eval/run-*.csv` mới với model thật (`model != fake`).
