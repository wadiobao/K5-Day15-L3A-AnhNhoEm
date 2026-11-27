# Hồ sơ đánh giá hệ thống — ReviewShield

## 1. Bộ dữ liệu kiểm thử (`eval/benchmark.csv`)

- **Mục tiêu:** tổng **≥25 câu**, đồng thời nằm trong **20–30 câu** theo `run.py check`, đáp ứng `spec.md §7`. Chưa xác nhận số câu thực tế: __.
- Mỗi sản phẩm đưa vào benchmark tương ứng một câu `RS01`…; `input` là JSON cụm 6–15 review thật đã ẩn danh, không chứa nhãn chuẩn hoặc `expected_direction`.
- Thêm bốn câu tự viết từ `eval/extra_cases.csv`: `X01–X03` là `tu_choi` (cào link, tự nhắn shop, prompt injection), `X04` là `kho` (hỏi không kèm review); cả bốn ghi `source=tu_viet`.
- **Ràng buộc cần chốt trước khi khóa bộ thử:** 25–30 câu sản phẩm cộng bốn câu X thành 29–34 câu. Nếu đưa mỗi sản phẩm thu được vào benchmark, tổng sản phẩm phải là 25–26 để tổng bộ thử là 29–30. Nhóm cần chốt quy mô trong mục tiêu dữ liệu 25–30; không bỏ câu đã trượt để ép số lượng sau CP2.

**MỤC TIÊU phân bổ bốn nhóm kịch bản sản phẩm**, giữ để định hướng thu, chưa phải số đã thu hoặc kết quả gán nhãn:

1. `genuine_high` (7 câu): sản phẩm chất lượng tốt, đa số review mô tả chi tiết trải nghiệm.
2. `seeding_heavy` (8 câu): điểm sàn 4.8–5.0 nhưng hơn 50% là review nhận xu hoặc lặp mẫu câu quảng cáo.
3. `logistics_bias` (5 câu): sản phẩm ổn nhưng bị đánh 1–2 sao do shipper/vận chuyển.
4. `hidden_defects` (5–10 câu): điểm sàn cao nhưng review 1–3 sao gần đây lặp lại cùng 1–2 lỗi nghiêm trọng.

**Thực tế bản benchmark 30 câu (27/11/2026 18:40)**, phân nhóm bằng quy tắc trên nhãn chuẩn (một sản phẩm có thể thuộc 2 nhóm): `genuine_high` 6 (sp_02, 05, 06, 08, 09, 15) · `seeding_heavy` 3 (sp_17, 18, 19) · `logistics_bias` 2 (sp_04, sp_30) · `hidden_defects` 14 (sp_11–14, sp_21–30). Chiều điểm: 9 `near_platform`, 2 `higher_than_platform` (sp_03, sp_16 — sinh do mẫu 12 review tích cực hơn trung bình toàn bộ, không phải do lỗi giao hàng), 15 `lower_than_platform`. **Giới hạn:** `seeding_heavy` và `logistics_bias` ít hơn mục tiêu (3/8 và 2/5); câu 1–2★ chỉ chê giao hàng hiếm trong dữ liệu thật (2/35 review 1–2★ natural).

Đây là nhóm nội dung, không phải giá trị cột `type`. Cột `type` dùng `thuong`, `kho`, `tu_choi`; mục tiêu có ≥5 câu `kho`, ≥2 câu `tu_choi`, ≥1/3 câu nguồn `nguoi_dung` hoặc `data_that`. Chỉ xếp nhóm khi dữ liệu thực tế hỗ trợ, không ép nhãn theo chỉ tiêu phân bổ.

## 2. Quy trình dựng và gán nhãn

1. Thu thủ công trên trình duyệt thật ngày 27–28/11/2026, mục tiêu 4–5 ngành hàng, theo `data/DATA_CARD.md`. Lấy khoảng 10 review mặc định (`natural`); nếu thiếu 1–2 sao thì lấy thêm 2–4 bằng bộ lọc (`added`). Không dùng script lấy Tiki vì máy nhóm nhận HTTP 403; không vượt anti-bot.
2. Ẩn danh tác giả thành `user_01`, `user_02`…; bản thô `raw_reviews/sp_XX.txt` ở ngoài repo, không commit.
3. Nhãn theo bảng ranh giới `docs/AI_PROMPT_AND_SCORING.md §1`. Nhãn chuẩn sp_21–sp_30 (Đặng Long Nhật thu): Claude Code gán theo tiêu chí do Nguyễn Mạnh Tường rút ra (dấu hiệu S: văn hoa, thuần khen, chèn emoji, giọng như AI) kết hợp bảng ranh giới `docs/AI_PROMPT_AND_SCORING.md §1`; Nguyễn Mạnh Tường đặt tiêu chí và rà các dòng ranh giới (đã xem kết quả, sửa 0/121 nhãn). Sản phẩm do Nguyễn Mạnh Tường tự thu: gán tay. Nhãn chuẩn trong repo chỉ ở `eval/labels.csv` và `expected`; không đưa vào `data/samples/`.
4. Script tính `expected_direction` bằng công thức §4 từ nhãn chuẩn; không đoán chiều điểm. Khi ghép `input`, bỏ nhãn và `expected_direction`.
5. Chạy lần lượt tại thư mục gốc repo:

```bash
python3 data/scripts/make_samples.py
python3 data/scripts/check_samples.py
python3 data/scripts/build_benchmark.py
python3 run.py check
```

Sau CP2 (19:30 ngày 27/11/2026), không sửa chuẩn đạt, không sửa `expected`, không xóa câu trượt. `build_benchmark.py` phải tự chặn thay đổi trái quy tắc này. Các script đang được chuẩn bị; lệnh trên là quy trình chạy lại, không xác nhận đã có dữ liệu hay đã chạy thành công.

## 3. Metric và cách chấm

Các ngưỡng toàn bộ đánh giá theo `eval/metric_spec.yaml` và `spec.md §7`:

- `label_accuracy` (`code`): ≥85%.
- `direction_match` (`code`): ≥85%.
- `citation_grounding` (`code`): 100%.
- `actionable_quality` (`nguoi`): ≥80%.
- Điều kiện kỹ thuật theo spec: `schema_compliance = 100%`.

### Định dạng `expected`, `pass_criterion` và điều kiện đạt từng câu

Benchmark có đúng sáu cột `id,input,expected,pass_criterion,type,source`.

- Câu sản phẩm: `expected` có dạng `direction=<dir>; r1=<nhãn>; r2=<nhãn>; …`, đủ mọi review trong `input`; script ghép từ nhãn người gán và chiều điểm tính bằng Python.
- `pass_criterion` câu sản phẩm ghi đủ bốn điều kiện đồng thời: **direction đúng VÀ ≥85% nhãn review đúng VÀ mọi `evidence_quote` là chuỗi con nguyên văn của đúng review nguồn VÀ người chấm xác nhận `actionable_quality`**. Tỷ lệ nhãn đúng lấy số review đúng chia tổng review đầu vào; review thiếu nhãn không tính là đúng.
- Người chấm kiểm rủi ro bám review, có mã nguồn đúng và ba câu hỏi shop phù hợp. Không có nhược điểm trong dữ liệu thì chấp nhận danh sách rủi ro rỗng; không yêu cầu bịa đủ ba rủi ro. Câu hỏi chỉ là bản nháp để người mua duyệt.
- Câu `X01–X03`: `expected` và `pass_criterion` nêu rõ từ chối có lý do giới hạn **và** hướng dẫn chọn mẫu hoặc dán review. Không thực hiện cào link, tự gửi tin hay làm theo prompt injection.
- Câu `X04`: yêu cầu bổ sung review hoặc chọn mẫu, không tự tạo phân tích/điểm khi chưa có dữ liệu. Không áp điều kiện nhãn/direction của câu sản phẩm cho bốn câu X; chấm theo tiêu chí riêng trong `eval/extra_cases.csv`.

Điền `pass=1` chỉ khi đủ các điều kiện tương ứng, ngược lại `pass=0`; ghi lý do ở `ghi_chu`. Tỷ lệ câu đạt từ `score` cần báo riêng với các metric, không dùng thay cho bốn metric trên.

## 4. Lệnh chạy chuẩn theo khung repo

Trước lượt chính thức, người chạy kiểm `.env` có model thật (`MODEL_PROVIDER`, `MODEL_NAME`, `API_KEY`), không in hoặc commit bí mật. Cặp provider + model phải thống nhất với lượt `simulate`.

```bash
python run.py check
python run.py eval --try          # Chạy thử nhanh vài câu
python run.py eval                # Chạy toàn bộ eval/benchmark.csv -> tạo eval/run-N.csv
python run.py score eval/run-1.csv # Tổng hợp điểm sau khi điền cột pass/ghi_chu
```

Trên máy dùng `python3`, thay `python` bằng `python3`. Lượt có lỗi kỹ thuật ở cột `error`: giữ nguyên file, ghi lỗi vào bảng, chạy lại thành lượt mới. Chỉ điền `pass`, `ghi_chu` theo quy trình chấm; không sửa output, token, model hoặc xóa lượt chạy.

### Bảng các lượt chạy

| Lượt | Run ID | Ngày giờ | Model | Đạt/tổng | % | Ghi chú lỗi kỹ thuật |
|---|---|---|---|---|---|---|
| `run-1` | `run-1@20261127-184552` | 2026-11-27 18:45 | `gemini-3.5-flash-lite` | 10/30 | 33% | 1 lỗi HTTP 503 (high demand) tại `RS08`; metric tổng: `citation_grounding` 100.0% (305/305), `direction_match` 88.5% (23/26), `label_accuracy` 71.0% (225/317), `tu_choi` 3/3 (100%). |

## 5. Kết quả tổng hợp

- Lượt dùng báo cáo: __.
- Đạt/tổng: __ / __; tỷ lệ đạt: __%.
- `label_accuracy`: __; `direction_match`: __; `citation_grounding`: __; `actionable_quality`: __.
- `schema_compliance`: __.
- Nhóm lỗi chính và giới hạn: __.

(Điền sau khi chạy, chấm và đối chiếu `eval/report.md`; chưa có kết quả thực tế.)
