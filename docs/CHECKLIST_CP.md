# CHECKLIST TIẾN ĐỘ CP1 – CP4 — Nhóm AnhNhoEM (ReviewShield · Track D)

Tài liệu theo dõi tiến độ từng mốc Checkpoint (CP1–CP4) và đầu việc cụ thể của 4 thành viên. Đánh dấu `[x]` ngay khi hoàn thành và đã merge vào `main`.

* **Đội trưởng (`2A202603362`):** Dương Quang Bảo — Module 1 (`codebase/ai.py`, `agent.py`, `spec.md`, merge & nộp CP)
* **Thành viên 2 (`2A202603427`):** Nguyễn Vũ Khanh — Module 2 (`codebase/tools.py`, `app.py`)
* **Thành viên 3 (`2A202603646`):** Nguyễn Mạnh Tường — Module 3 (`data/samples/`, `evidence/`, `eval/`)
* **Thành viên 4 (`2A202603483`):** Đặng Long Nhật — Module 4 (`cost/`, `validation/`, `canvas.md`, `slides/`, video demo)

---

## CP1 — 17:00 Thứ Sáu 27/11 (3 điểm)

- [x] Tạo GitHub Repo Public đúng tên `K5-Day15-L3A-AnhNhoEm` từ `starter-repo/` *(Bảo)*
- [x] Điền đủ 4 thành viên vào `TEAMS.md` (Đội trưởng dòng 1), chạy `python run.py check` đạt 0 cảnh báo phần `TEAMS.md` *(Cả nhóm)*
- [x] Điền đầy đủ `canvas.md` (bài toán 1–2 câu KHÔNG dùng chữ AI + lát cắt 1 câu + Track D) *(Bảo & Nhật)*
- [x] Mở thử link `https://github.com/wadiobao/K5-Day15-L3A-AnhNhoEm` bằng **Tab Ẩn Danh** xác nhận không lỗi 404 *(Bảo)*
- [x] Nộp **Form 2 → Nhánh CP1** trước 17:00 *(Bảo)*

---

## CP2 — 19:30 Thứ Sáu 27/11 (4 điểm · KHÓA CHUẨN ĐẠT)

> **CẢNH BÁO CỨNG:** Sau 19:30 Thứ Sáu 27/11, **TUYỆT ĐỐI KHÔNG SỬA** `spec.md §7` và `eval/metric_spec.yaml`.

### Tài liệu & Chuẩn đạt
- [x] `eval/metric_spec.yaml` có đủ 4 metric đo được (≥3 metric) *(Tường)*
- [x] `data/DATA_CARD.md` hoàn thiện *(Tường)*
- [x] Chốt cứng chuẩn "Đạt" bằng số tại `spec.md §7` khớp 100% `eval/metric_spec.yaml` *(Bảo)*
- [x] Bổ sung **sơ đồ khối kiến trúc AI** (`Input → AI Core → Chặn rủi ro → Output`) vào `spec.md §4` *(Bảo)*
- [x] Cập nhật dòng 8 (mốc CP2) trong `canvas.md` *(Nhật — PR #5)*

### Dữ liệu & Benchmark (mốc CP2)
- [x] Xóa 3 dòng mẫu `(ví dụ)` `B01–B03` trong `eval/benchmark.csv` *(Tường)*
- [x] Điền tối thiểu **≥10 câu thử thật** (`RS01–RS14`, đã ẩn danh `user_XX`) vào `eval/benchmark.csv` và mở PR `data/2a202603646-samples-evidence-eval` *(Tường)*
- [x] Đưa 10 mẫu sản phẩm đầu tiên vào `data/samples/sp_21.json` … `sp_30.json` *(Tường)*

### Code khung chạy hết luồng (mock hoặc thật đều đạt CP2)
- [x] Hoàn thiện `codebase/ai.py` (hỗ trợ Gemini/OpenAI/Anthropic/Ollama bằng `urllib`) và `codebase/agent.py` (pipeline 3 chặng + Guardrails + Retry JSON) trên nhánh `feat/2a202603362-core-ai-agent` *(Bảo)*
- [x] Hoàn thiện 3 `@tool` trong `codebase/tools.py` (`preprocess_reviews`, `verify_grounding`, `compute_real_trust_score`) trên nhánh `feat/2a202603427-tools-and-ui` và mở PR trước 18:45 *(Khanh)*
- [x] Merge PR #1 (Bảo) và PR #2 (Khanh) vào `main`; chạy `python run.py` xác nhận đi hết luồng 3 chặng không lỗi *(Bảo)*
- [x] Merge PR #3 (`data/2a202603646-samples-evidence-eval` — 14 câu benchmark thật của Tường) và PR #4 (`fix/2a202603362-fake-mode-json`) vào `main` *(Bảo)*
- [x] Nộp **Form 2 → Nhánh CP2** trước 19:30 *(Bảo)*

---

## CP3 — 10:00 Sáng Thứ Bảy 28/11 (4 điểm · GỌI AI THẬT)

### Bằng chứng Pain (`evidence/`)
- [ ] Hoàn thiện `evidence/data-mining.md` (thống kê `x/N`, `%`, cách đếm chạy lại được, ≥5 ví dụ ẩn danh) *(Tường)*
- [ ] Hoàn thiện phỏng vấn (≥3 người ngoài nhóm trong `evidence/interviews/P1.md..P3.md`) và/hoặc khảo sát (≥20 người trong `evidence/survey/`) *(Nhật)*
- [ ] Tổng hợp đầy đủ `evidence/summary.md` (đạt ngưỡng **≥1 nguồn** + **≥5 trích dẫn nguyên văn** ẩn tên) *(Tường)*

### Mở rộng dữ liệu & Benchmark (20–30 câu)
- [ ] Đủ 25–30 mẫu sản phẩm thật ẩn danh trong `data/samples/` (Shopee + Tiki + TikTok Shop/Lazada) *(Tường & Nhật)*
- [ ] Mở rộng `eval/benchmark.csv` lên **20–30 câu thử thật** (đủ **≥5 câu `kho`** và **≥2 câu `tu_choi` / tấn công**) *(Tường)*
- [ ] Chạy `python run.py check` đạt **0 cảnh báo toàn bộ** *(Tường & Bảo)*

### Bản chạy thử gọi AI thật & Eval Lượt 1
- [ ] Nối `.env` bằng **Gemini thật** (`MODEL_PROVIDER=gemini`, `MODEL_NAME=gemini-3.6-flash` hoặc `gemini-3.5-flash-lite`, không commit `.env`) và chạy `python run.py eval --try` báo `"Nối model được"` *(Bảo)*
- [ ] Hoàn thiện giao diện demo 1 màn hình Streamlit trong `codebase/app.py` *(Khanh)*
- [ ] Chạy `python run.py eval` tạo kết quả **Lượt 1** (`eval/run-1.csv` + `traces/run-1.jsonl`, ghi nhận `Run ID`) *(Bảo)*
- [ ] Chấm đủ cột `pass` (`1`/`0`) và `ghi_chu` trong `eval/run-1.csv`, chạy `python run.py score eval/run-1.csv` *(Tường & Bảo)*
- [ ] Quay **Video 30 giây** bản chạy thử gọi **AI THẬT** (không lộ `.env`/API key), tải YouTube Unlisted / Drive công khai và kiểm tra bằng **Tab Ẩn Danh** *(Nhật)*
- [ ] Nộp **Form 2 → Nhánh CP3** trước 10:00 *(Bảo)*

---

## CP4 — 14:30 Chiều Thứ Bảy 28/11 (4 điểm · CHỐT DEMO)

### Vòng lặp Cải tiến & Eval Lượt 2
- [ ] Đọc các câu trượt ở `eval/run-1.csv` → chọn **1 cải tiến rõ ràng** trong prompt/code (`agent.py` hoặc `tools.py`), ghi nhật ký vào `spec.md §10` *(Bảo & Khanh)*
- [ ] Chạy lại `python run.py eval` tạo **Lượt 2** (`eval/run-2.csv`), chấm `pass` & chạy `python run.py score eval/run-2.csv` *(Bảo & Tường)*
- [ ] Hoàn thiện bảng so sánh **Lượt 1 → Lượt 2** trong `eval/report.md` và tóm tắt vào `spec.md §8` *(Tường & Bảo)*

### Mô phỏng Chi phí & Kiểm thử Người dùng
- [ ] Chạy mô phỏng chi phí ≥50 phiên thật bằng đúng model đã chấm Lượt 2:
  ```bash
  python run.py simulate --rate-from eval/run-2.csv
  ```
  *(Nhật & Bảo)*
- [ ] Dán bảng chi phí vào `cost/cost-estimate.md` (có chi phí/task thành công + tên model) và tóm tắt vào `spec.md §9` *(Nhật)*
- [ ] *(Bonus)* Tổ chức test 2–3 người dùng thật ngoài nhóm và ghi log vào `validation/log.md`; fix lỗi ưu tiên cao trước demo *(Nhật & Khanh)*

### Slide, Video Dự Phòng & Nộp bài
- [ ] Đẩy file **`demo-slides.pdf`** vào **thư mục gốc repo** (`./demo-slides.pdf`) *(Nhật)*
- [ ] Quay **Video Demo dự phòng** (2 phút, chạy AI thật, kiểm Tab Ẩn Danh) và cập nhật link vào `README.md` *(Nhật)*
- [ ] Hoàn thiện `docs/ai-usage.md` và mục "Dùng AI vào việc gì" trong `README.md` *(Nhật & Cả nhóm)*
- [ ] Hoàn thiện `reflection/<ten>.md` (hạn chót 23:59 Thứ Bảy 28/11) *(Cả nhóm)*
- [ ] Kiểm tra `git status`, `python run.py check`, push toàn bộ lên `main` và nộp **Form 2 → Nhánh CP4** (tick đủ 4 điều kiện cứng xét giải) trước 14:30 *(Bảo)*
