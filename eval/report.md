# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Điền ở guide bước 4.1. Lượt 1 trước **CP3 10:00 Thứ Bảy 28/11**, lượt 2 trước **CP4 14:30 Thứ Bảy 28/11**, cùng bộ 30 câu thử (`eval/benchmark.csv`), cùng chuẩn đạt (`spec.md §7`, `eval/metric_spec.yaml`), cùng model thật `gemini-3.5-flash-lite`. Chấm ở rubric R5.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" (`spec.md §7`) |
|---|---|---|---|---|---|---|---|
| 1 | `run-1@20261127-184552` | 10/30 | 33% | 5/21 (24%) | 2/6 (33%) | 3/3 (100%) | Đạt 2/3 metric code (`citation_grounding` 100,0%, `direction_match` 88,5%); chưa đạt `label_accuracy` (71,0% < 85%); có 1 lỗi HTTP 503 (`RS08`) |
| 2 | `run-2@20261128-073745` | **13/30** | **43%** | **6/21 (29%)** | **4/6 (67%)** | **3/3 (100%)** | **0 lỗi kỹ thuật**; Đạt 2/3 metric code (`citation_grounding` 100,0%, `direction_match` 92,3%); `label_accuracy` tăng mạnh **+8,8%** lên **79,8%** (tiến sát ngưỡng 85%) |

### So sánh chi tiết 4 metric tổng trên 26 sản phẩm (317 review)

| Metric (`eval/metric_spec.yaml`) | Ngưỡng chốt | Lượt 1 (`run-1`) | Lượt 2 (`run-2`) | Thay đổi |
| :--- | :-: | :-: | :-: | :-: |
| `label_accuracy` (`code`) | `>= 85%` | 225/317 (71,0%) | **253/317 (79,8%)** | **+8,8%** (+28 review đúng) |
| `direction_match` (`code`) | `>= 85%` | 23/26 (88,5%) | **24/26 (92,3%)** | **+3,8%** (Đạt) |
| `citation_grounding` (`code`) | `== 100%` | 305/305 (100,0%) | **317/317 (100,0%)** | **100,0%** (Đạt) |
| `schema_compliance` (kỹ thuật) | `== 100%` | 29/30 (96,7% — 1 lỗi 503) | **30/30 (100,0%)** | **+3,3%** (0 lỗi) |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

---

## 2. Lỗi lượt 1 — gom thành nhóm có tên

Trên 20 câu trượt ở Lượt 1 (`eval/run-1.csv`, tổng 80 review phân loại lệch + 1 câu lỗi API), các lỗi gom thành **4 nhóm chính**:

| Nhóm lỗi | Số câu bị ảnh hưởng | Câu tiêu biểu |
|---|---|---|
| **1. Bỏ sót `suspicious_pattern` (lặp thân câu khác tiền tố / văn mẫu quảng cáo)** | 10 câu (42/80 review lệch: 24 nhầm `verified_insight`, 12 `low_signal`, 6 `logistics_only`) | `RS28` (2/12), `RS30` (0/12), `RS01` (8/14), `RS04` (8/10), `RS29` (8/12) |
| **2. Nhầm ranh giới `verified_insight` ↔ `low_signal` (câu ngắn có thuộc tính vs khen chung)** | 11 câu (32/80 review lệch: 16 `V→L`, 16 `L→V`) | `RS27` (direction sai, 9/12), `RS26` (direction sai, 11/12), `RS15` (8/12), `RS20` (8/12), `RS23` (9/12) |
| **3. Nhầm 5★ "giao nhanh, chưa dùng" sang `logistics_only`** | 3 câu | `RS30` (`r2`), `RS29` |
| **4. Lỗi kỹ thuật API quá tải (`HTTP 503 high demand`)** | 1 câu | `RS08` (0/12 do retry 1 lần chưa đủ) |

**≥3 lỗi cụ thể ở Lượt 1:**

| Câu | Input (trích từ cụm review thật) | Output Lượt 1 | Vì sao sai |
|---|---|---|---|
| `RS28` (`sp_17`) | 3 review 5★ lặp nguyên đoạn thân *"Mình đã nhận được hàng, chất vải mềm mịn, hình sắc nét, shop giao hàng nhanh rất ưng ý..."* nhưng khác tiền tố `Màu sắc:` / `Chất liệu:` | Gán 10/12 câu thành `verified_insight` (chỉ đúng 2/12) | Khác tiền tố Shopee nên `duplicate_group_size == 1`; prompt Lượt 1 chưa nhắc đối chiếu khung câu lặp trong cùng lô. |
| `RS30` (`sp_19`) | Review 5★ trùng lặp (`r1`/`r10`, `r3`/`r9`: *"Hàng chất lượng, xịn lắm mọi người yên tâm mua nhé!!!"*) và câu `r2` *"ship nhanh... sản phẩm chưa dùng nên sẽ đánh giá sau"* | Đúng 0/12: gán nhầm `suspicious_pattern` sang `low_signal` / `logistics_only`; gán `r2` sang `logistics_only` | Prompt Lượt 1 chưa đặt thứ tự ưu tiên bắt `suspicious_pattern` trước và chưa tách rõ 5★ chưa dùng thuộc `low_signal`. |
| `RS27` (`sp_16`) | Review ngắn có thuộc tính sản phẩm thật: `r3` (*"dễ kết nối"*), `r5` (*"pin đc lâu"*), `r7` (*"Chất âm sống động"*) | Gán `r3`, `r5`, `r7` thành `low_signal` → kéo sai `direction` (`near_platform` thay vì `higher_than_platform`) | Prompt Lượt 1 quá khắt khe với review ngắn dù có nêu đặc tính kỹ thuật cụ thể. |
| `RS08` (`sp_28`) | Cụm 12 review thật bộ dụng cụ vệ sinh laptop | `RuntimeError: HTTP 503 (high demand)` | `codebase/ai.py` ở Lượt 1 chỉ retry 1 lần (2s) nên chưa vượt qua đợt quá tải ngắn của Gemini API. |

---

## 3. Một lần cải tiến

* **Nhắm vào nhóm lỗi:** **Nhóm 1 (bỏ sót `suspicious_pattern`) & Nhóm 2 (ranh giới `verified_insight` ↔ `low_signal`)** kèm độ bền gọi API — đây là nhóm **đau nhất với người dùng** vì nếu sản phẩm seeding lặp mẫu (`RS28`, `RS30`) bị gán nhầm thành `verified_insight`, người mua sẽ thấy `verified_ratio` cao giả tạo và tiếp tục bị đánh lừa bởi điểm 5.0★.
* **Đã sửa gì:**
  1. Nâng cấp `SYSTEM` prompt trong `codebase/agent.py` (Prompt v2 — hoàn toàn theo quy ước nghiệp vụ tổng quát, không hardcode câu thử): đặt **thứ tự ưu tiên phân định 3 bước (A → B → C)**: kiểm tra `suspicious_pattern` trước (bắt cả lặp đoạn thân khác tiền tố, văn phong quảng cáo/kêu gọi mua hàng, nội dung lạc đề sang sản phẩm khác); tách rõ 5★ *"giao nhanh, chưa dùng"* thuộc `low_signal`; ghi nhận câu ngắn có ≥1 thuộc tính sản phẩm thật là `verified_insight`.
  2. Nâng `post_json()` trong `codebase/ai.py` lên `DEFAULT_MAX_RETRIES = 3` với exponential backoff (`2s → 4s → 8s`) cho HTTP 429/503 (PR #8).
* **Kết quả:**
  * Nhóm lỗi nặng nhất cải thiện rõ: `RS28` tăng **2/12 → 9/12**, `RS30` tăng **0/12 → 6/12**, `RS08` hết lỗi (**0/12 → 9/12**), `RS27` chuyển từ sai `direction` (9/12) sang **đúng `direction` & 11/12**, `RS23` đạt **12/12 (100%)**.
  * 5 câu chuyển từ Trượt → Đạt: `RS01`, `RS03`, `RS06`, `RS23`, `RS27`.
  * Metric tổng: `label_accuracy` **71,0% → 79,8%** (+8,8%), `direction_match` **88,5% → 92,3%** (+3,8%), `citation_grounding` giữ vững **100,0%** (317/317), tổng số câu đạt **33% (10/30) → 43% (13/30)**, riêng nhóm `kho` tăng mạnh **33% (2/6) → 67% (4/6)**.
* **Câu bị tệ đi sau khi sửa (2 câu):**
  * `RS10` (`sp_30`): giảm từ `13/14 (92,9%)` xuống `10/14 (71,4%)` (vẫn đúng `direction = lower_than_platform` và grounding 100%).
  * `RS22` (`sp_11`): giảm từ `11/12 (91,7%)` xuống `8/12 (66,7%)` (vẫn đúng `direction = lower_than_platform` và grounding 100%).
  * *Nguyên nhân:* Quy tắc bắt `suspicious_pattern` siết chặt hơn làm một số câu khen 5★ tự nhiên dài có cảm xúc tích cực bị đẩy sang `suspicious_pattern` hoặc `low_signal`.

---

## 4. Còn lại

* **Lỗi chưa sửa + mức độ nguy hiểm:**
  * `label_accuracy` đạt **79,8%** (còn thiếu 5,2% so với ngưỡng 85% chốt ở `spec.md §7`), tập trung chủ yếu ở ranh giới nhạy cảm giữa *khen 5★ tự nhiên* và *văn mẫu seeding không lặp nguyên văn* (`RS30`: 6/12, `RS04`: 7/10, `RS21`: sai `direction` do 1 câu biên).
  * *Mức độ nguy hiểm:* **Trung bình** — nhờ `direction_match` đã đạt **92,3%** (24/26) và `citation_grounding` đạt **100%**, người mua vẫn nhận đúng hướng cảnh báo và luôn tự kiểm chứng được bằng trích dẫn nguyên văn (không bịa dẫn chứng).
* **Nếu có thêm 1 tuần:**
  1. Bổ sung **bộ phát hiện trùng lặp gần giống (fuzzy / n-gram similarity bỏ tiền tố `Màu sắc:/Chất liệu:`)** bằng Python tất định trong `codebase/tools.py` để tính `near_duplicate_group_size` gửi kèm vào LLM (giải quyết triệt để cụm `RS28`/`RS30` mà không làm siết oan review thật ở `RS10`/`RS22`).
  2. Thử nghiệm so sánh A/B với model mạnh hơn (`gemini-2.5-flash` / `gemini-3.1-pro-preview`) trên cùng bộ 30 câu để cân bằng giữa độ chính xác nhãn (`>= 85%`) và chi phí/task thành công.
