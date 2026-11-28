# Báo cáo đánh giá — lượt 1 → một cải tiến → lượt 2

> Người viết: Nguyễn Mạnh Tường (`2A202603646`) · 28/11/2026. Số lấy từ `python3 run.py score eval/run-1.csv`, `run-2.csv` và `python3 eval/grade_helper.py` (script gợi ý, không tự điền `pass`). Cùng bộ 30 câu thử, cùng cách chấm, cùng model `gemini-3.5-flash-lite`.
> Không sửa chuẩn "đạt", không bỏ câu trượt, không sửa `expected`, không sửa kết quả lượt đã chạy.

## 1. Kết quả

| Lượt | Run ID | Đạt / tổng | % | thuong | kho | tu_choi | So với chuẩn "đạt" |
|---|---|---|---|---|---|---|---|
| 1 | `run-1@20261127-184552` | 10/30 | 33% | 5/21 | 2/6 | 3/3 | **chưa** (`label_accuracy` 71,0% < 85%) |
| 2 | `run-2@20261128-073745` | 13/30 | 43% | 6/21 | 4/6 | 3/3 | **chưa** (`label_accuracy` 79,8% < 85%) |

Kết quả từng câu: `eval/run-1.csv`, `eval/run-2.csv`. Trace: `traces/run-1.jsonl`, `traces/run-2.jsonl`.

Bốn chỉ số theo `spec.md` §7 (tính trên toàn bộ review, không phải từng câu):

| Chỉ số | Ngưỡng | Lượt 1 | Lượt 2 |
|---|---|---|---|
| `label_accuracy` | ≥ 85% | 71,0% (225/317) ❌ | **79,8%** (253/317) ❌ |
| `direction_match` | ≥ 85% | 88,5% (23/26) ✅ | **92,3%** (24/26) ✅ |
| `citation_grounding` | = 100% | 100% (305/305) ✅ | 100% (317/317) ✅ |
| `actionable_quality` | ≥ 80% | chưa đo | 9/9 câu sản phẩm đạt ở lượt 2 được Claude đối chiếu là sát (xem §4; **chưa đo trên các câu trượt**) |

Một câu "đạt" khi đồng thời: đúng `direction`, ≥85% nhãn review khớp `expected`, mọi trích dẫn nằm nguyên văn trong review gốc, và Top rủi ro + 3 câu hỏi sát phàn nàn thật (`eval/README.md` §3). Với ngưỡng 85% áp dụng cho **từng câu**, khó đạt hơn ngưỡng 85% trên toàn bộ, nên số câu đạt (43%) thấp hơn nhiều so với `label_accuracy` chung.

**Lượt 1 có 1 lỗi kỹ thuật:** `RS08` bị HTTP 503 (Gemini quá tải), tính 0 nhãn đúng. Lượt 2 không còn lỗi kỹ thuật.

### Độ chính xác theo từng nhãn (nhãn chuẩn → AI gán đúng)

| Nhãn chuẩn | Lượt 1 | Lượt 2 |
|---|---|---|
| `verified_insight` (V) | 170/187 (91%) | 183/195 (94%) |
| `low_signal` (L) | 47/65 (72%) | 47/67 (70%) |
| `suspicious_pattern` (S) | **6/48 (12%)** | **19/49 (39%)** |
| `logistics_only` (G) | 2/5 (40%) | 4/6 (67%) |

(Lượt 1 chỉ tính 25 câu sản phẩm không lỗi; lượt 2 tính 26 câu. G chỉ có 6 review trong cả benchmark nên số này rất nhiễu.)

### Đối chiếu với phương án ngây thơ ("luôn đoán V")

Một hệ thống gán **mọi review là `verified_insight`** đạt `label_accuracy` 61,5% và `direction_match` 84,6% (22/26) trên cùng bộ thử. Hai điều rút ra:
- `direction_match` **gần như không phân biệt được** hệ thống tốt hay dở: chiều điểm chủ yếu do tỷ lệ số sao trong mẫu quyết định (ví dụ sản phẩm toàn review 5★ luôn ra `near_platform`). Vì vậy **`label_accuracy` là chỉ số đo năng lực thật**.
- Lượt 2 (79,8%) hơn phương án ngây thơ 18,3 điểm phần trăm, nhưng vẫn chưa đạt ngưỡng.

## 2. Lỗi lượt 1 — gom thành nhóm có tên

| Nhóm lỗi | Số review / câu | Câu |
|---|---|---|
| **Không nhận ra `suspicious_pattern`** (khen theo khuôn mẫu bị coi là trải nghiệm thật) | 42/48 review S bị gán sai: 24 → V, 12 → L, 6 → G | `RS28` (2/12 nhãn đúng), `RS30` (0/12), `RS29` (8/12), `RS19`, `RS20` |
| **Nhầm ranh giới V ↔ L** | 16 review V → L và 16 review L → V | rải đều ở nhiều câu `thuong` và `kho` (`RS15`, `RS21`, `RS23`, `RS25`…) |
| **Chiều điểm sai do sát ngưỡng ±0,3** | 2 câu | `RS26`, `RS27` |
| **Lỗi kỹ thuật API** (HTTP 503) | 1 câu | `RS08` |

**≥3 lỗi cụ thể:**

| Câu | Input | Output | Vì sao sai |
|---|---|---|---|
| `RS28` (lượt 1) | 12 review 5★ của một bộ đồ nam, trong đó cùng một câu *"Mình đã nhận được hàng, chất vải mềm mịn, hình sắc nét, shop giao hàng nhanh rất ưng ý sẽ ủng hộ shop tiếp nữa nhé"* xuất hiện **3 lần** trong 2 ngày | 10/12 review gán `verified_insight`, chỉ 2 gán `suspicious_pattern` → **2/12 nhãn đúng** | AI đọc từng review riêng lẻ, coi "chất vải mềm mịn" là chi tiết thật, không đối chiếu chéo giữa các review để thấy khuôn mẫu lặp |
| `RS30` (lượt 1) | 12 review 5★ của một máy xay sinh tố, văn khen dài, "mọi người yên tâm mua", "chất lượng điểm 10" | gán lẫn `low_signal`, `logistics_only`, `verified_insight`; **0/12 nhãn đúng** | Văn quảng cáo thuần khen bị hiểu thành khen chung chung (L) hoặc nói giao hàng (G); prompt chưa nói rõ "giọng quảng cáo → S" |
| `RS26` (cả 2 lượt) | Loa Bluetooth, điểm sàn 3,9, 12 review | AI tính Điểm thực **4,3** (+0,4) → `higher_than_platform`; nhãn chuẩn cho 4,2 (+0,3) → `near_platform`. Ở lượt 1 AI đúng 11/12 nhãn | **Chỉ lệch 1 nhãn** nhưng độ lệch điểm vượt ngưỡng 0,3 nên `direction` đổi; phép tính tất định của hệ thống không sai, ngưỡng cứng khuếch đại sai số nhỏ của nhãn |
| `RS10`, `RS22` (**lượt 2, mới tệ đi**) | Hai câu `thuong` đạt ở lượt 1 | Lượt 2 gán nhầm `logistics_only` cho 3 review của `RS10` (đều đúng ở lượt 1) và 4 review của `RS22` (3 review đúng ở lượt 1); nhãn đúng giảm 13/14 → 10/14 và 11/12 → 8/12 | Sau khi sửa prompt, AI gán G quá tay cho review có nhắc giao hàng/đóng gói kèm nhận xét sản phẩm |

## 3. Một lần cải tiến

- **Nhắm vào nhóm lỗi:** không nhận ra `suspicious_pattern` (6/48). Đây là nhóm **đau nhất với người dùng**: sản phẩm seeding toàn 5★ vẫn ra Điểm thực = điểm sàn (5,0); chỉ `trust_level` và `verified_ratio` thấp mới lộ vấn đề, nên nếu AI không gán đúng S thì người mua không được cảnh báo.
- **Đã sửa gì** (Bảo & Khanh, PR #8, #12, #13, chi tiết ở `spec.md` §10): (1) System Prompt v2 trong `codebase/agent.py`: kiểm tra `suspicious_pattern` **trước**, bắt AI đối chiếu chéo toàn cụm review, nêu rõ quy ước "giọng quảng cáo/khuôn mẫu → S dù có nhắc tính năng", tách rõ ranh giới G; (2) retry exponential backoff 3 lần cho HTTP 429/503 trong `codebase/ai.py`. Không hardcode đáp án và không so khớp input benchmark.
- **Kết quả:** nhóm lỗi đó 6/48 → **19/49** nhãn S đúng (12% → 39%); `RS28` 2/12 → 9/12, `RS30` 0/12 → 6/12; tổng `label_accuracy` 71,0% → 79,8%; số câu đạt 10 → 13 (33% → 43%); `RS08` hết lỗi 503.
- **Câu nào tệ đi sau khi sửa:** `RS10` và `RS22` (từ đạt xuống trượt) do gán G quá tay; `L` đúng 47/65 → 47/67 (không cải thiện). Có 5 câu từ trượt thành đạt (`RS01`, `RS03`, `RS06`, `RS23`, `RS27`) và 2 câu từ đạt thành trượt, tổng +3.

**Cảnh báo về tính độc lập của cải tiến:** quy ước ưu tiên S ở prompt v2 **trùng với tiêu chí được dùng để gán nhãn chuẩn** (`data/DATA_CARD.md` §5). Đó là cùng một bộ định nghĩa, không phải so khớp với câu thử cụ thể, nhưng một phần mức tăng ở S phản ánh việc prompt đã bám sát tiêu chí của người gán nhãn.

## 4. Giới hạn của chính bộ đánh giá

- **Nhãn chuẩn do AI gán** (Claude Code, Codex) theo tiêu chí do Thành viên 3 đặt, có rà các dòng ranh giới. Nhãn đo lượng thông tin về sản phẩm, không kết luận review thật hay giả.
- **Độ đồng thuận người – nhãn chuẩn chỉ 60%.** Thành viên 3 tự gán độc lập 30 review (lấy cân theo nhãn: 10 V · 6 L · 10 S · 4 G, seed 42) rồi so với nhãn chuẩn: **khớp 18/30 (60%)**. Theo nhãn: V 8/10, L 2/6, S 6/10, G 2/4. Phần lớn lệch (10/12) là người chọn V ở chỗ nhãn chuẩn là L, S hoặc G, tức **ranh giới V/L/S/G là chỗ mơ hồ nhất**, và định nghĩa V "có chi tiết về sản phẩm" khác với cách hiểu "giọng người thật". Với cùng 29 review, Gemini lượt 1 khớp nhãn chuẩn 18/29 nhưng chỉ khớp nhãn tay 14/29. Hệ quả: ngưỡng `label_accuracy` ≥ 85% có thể vượt quá độ đồng thuận giữa hai người chấm, nên một phần "lỗi" của AI nằm ở ranh giới mơ hồ. Thành viên 3 quyết định giữ nhãn hiện có làm chuẩn vì nhãn đó bám đúng định nghĩa chính thức ở `docs/AI_PROMPT_AND_SCORING.md`, không phải vì đã được chứng minh là đúng. Mẫu 30 này lấy cân, **chỉ đọc theo từng nhãn**, không phải tỷ lệ tự nhiên.
- **Chưa có người gán nhãn thứ hai** độc lập trên toàn bộ 317 review.
- **`actionable_quality` chỉ được kiểm trên tập con và do AI chấm:** Claude Code đọc Top 3 rủi ro và 3 câu hỏi của **9 câu sản phẩm đạt ở lượt 2** (`RS01`, `RS03`, `RS05`, `RS06`, `RS07`, `RS16`, `RS23`, `RS24`, `RS27`) và đối chiếu với review 1–3★ thật của từng sản phẩm: **9/9 sát** — mọi rủi ro dẫn `source_review_ids` có thật và nội dung review đó đúng với rủi ro nêu; câu hỏi bám theo các rủi ro. Điểm yếu nhỏ: `RS27` rủi ro 1 chỉ dựa vào 1 review; `RS23` bỏ sót phàn nàn "hư ron báo thay 500 nghìn" (review 1★); `RS24` rủi ro 3 ("cơm khô") lấy từ một review 5★ chỉ nhắc nhẹ. Hạn chế: (1) người chấm là AI, **chưa có người đọc độc lập**; (2) tập này **đã lọc** bằng các tiêu chí nhãn/direction nên có thiên lệch chọn lọc, chưa đo trên 17 câu trượt; (3) vì vậy con số 9/9 **không đủ để khẳng định** ngưỡng ≥80% trên toàn bộ bộ thử. Một phát hiện đáng giữ: ở `RS16`, hệ thống rút ra rủi ro "phồng pin" từ **3 review 5★** có nội dung phàn nàn mà số sao cao.
- **Mất cân bằng nhãn:** V chiếm ~61,5%; G chỉ 6/317 (1,9%), nên độ chính xác nhãn G rất nhiễu. `seeding_heavy` chỉ 3 câu và `logistics_bias` 2 câu, ít hơn mục tiêu 8 và 5.
- **"Điểm sàn" của 13 sản phẩm Điện Máy Xanh** là điểm suy ra (trung bình review trong bộ dữ liệu), không phải điểm hiển thị trên web.
- Lượt 1 và 2 chạy ở hai thời điểm khác nhau trên cùng model nhưng không chạy lặp lại để đo độ dao động giữa các lần chạy; chênh lệch 1–2 câu có thể nằm trong nhiễu.

## 5. Còn lại

- **Lỗi chưa sửa và nguy hiểm thế nào:**
  - `label_accuracy` 79,8% < 85%, **chưa đạt chuẩn** `spec.md` §7.
  - `suspicious_pattern` vẫn sai 30/49 (61%): với sản phẩm seeding, người mua vẫn có thể thấy tỷ lệ "trải nghiệm thật" cao hơn thực tế.
  - Gán G quá tay ở một số câu sau prompt v2 (`RS10`, `RS22`) làm mất tín hiệu của review có chi tiết sản phẩm.
  - Chiều điểm dễ lật khi sát ngưỡng ±0,3 (`RS26`).
- **Nếu có thêm 1 tuần:**
  1. Phát hiện lặp mẫu bằng **code tất định** (so khớp gần trùng giữa các review của cùng sản phẩm, mở rộng `duplicate_group_size`) thay vì chỉ trông vào prompt.
  2. Thêm ví dụ minh họa (few-shot) lấy từ dữ liệu **ngoài** bộ benchmark.
  3. Có người thứ hai gán nhãn độc lập để đo độ đồng thuận trên toàn bộ benchmark và làm rõ ranh giới V/L/S/G.
  4. Thêm sản phẩm `seeding_heavy` và `logistics_bias`, chạy mỗi lượt nhiều lần để đo độ dao động.
  5. Đo `actionable_quality` bằng người đọc độc lập trên cả câu đạt lẫn câu trượt.
