# AGENTS.md — Quy Tắc Làm Việc Cho Coding Agent & Nhóm ReviewShield

Tài liệu này hợp nhất **quy tắc bắt buộc của khung repo AI20K** và **quy chuẩn kỹ thuật riêng của dự án ReviewShield (Làn D — Thương mại điện tử)**. Mọi coding agent (Cursor, Claude Code, Codex, Antigravity) và thành viên nhóm phải tuân thủ tuyệt đối.

## 1. Cấu trúc code: File được sửa vs File khung không được sửa

### File nhóm ĐƯỢC sửa
* `codebase/agent.py`: Chứa hàm `answer(text) -> {"output": str}` điều phối pipeline 3 chặng của ReviewShield (tiền xử lý -> gọi AI thật -> Grounding Guard & Real Trust Score).
* `codebase/ai.py`: Chứa hàm `call_model(system, user) -> {"text", "model", "tokens_in", "tokens_out"}`. Bắt buộc giữ nguyên decorator `@model_call` và lấy đúng `tokens_in`, `tokens_out` từ trường `usage` thực tế của API provider.
* `codebase/tools.py`: Chứa các công cụ hỗ trợ (tiền xử lý review, kiểm tra trích dẫn nguyên văn Grounding Guard, tính Điểm tin cậy thực). Mỗi công cụ bắt buộc gắn `@tool` và có docstring đầy đủ mô tả đầu vào/đầu ra.
* `codebase/app.py`: Giao diện chạy demo 1 màn hình ReviewShield.
* `requirements.txt`: Khung gốc chỉ dùng thư viện chuẩn Python; nếu thêm bất kỳ thư viện ngoài nào phải khai báo đầy đủ vào `requirements.txt`.

### File khung CẤM sửa
* `run.py`
* `codebase/tracing.py`
* `eval/run_eval.py`
* `cost/simulate.py`

## 2. Các quy tắc CẤM tuyệt đối (BTC Hard Rules)

1. **Không lộ bí mật hoặc dữ liệu nhạy cảm:** Không commit `.env`, API key, dữ liệu cá nhân thật của người mua (phải ẩn danh thành `user_01`, `user_02`), hoặc nguyên file dữ liệu BTC cấp.
2. **Không chỉnh sửa kết quả đã chạy:** Không sửa các file kết quả trong `eval/run-*.csv`, `cost/simulate-*.csv`, `traces/*` (chỉ được điền cột `pass`, `ghi_chu` theo quy trình chấm của khung).
3. **Không sửa chuẩn "đạt" sau CP2:** Sau mốc CP2 (19:30 Thứ Sáu 27/11), tuyệt đối không sửa `spec.md` §7 và `eval/metric_spec.yaml`; không xóa câu thử bị trượt và không sửa cột `expected` cho khớp với output.
4. **Không bịa bằng chứng người dùng:** Không bịa người phỏng vấn, trích dẫn, khảo sát hay số liệu. Mọi con số không có nguồn trực tiếp phải ghi rõ *(tự ước tính)*.
5. **An toàn với công cụ có tác động bên ngoài:** Công cụ có tác động ra ngoài (gửi tin nhắn cho shop, sửa dữ liệu, chấm điểm) chỉ được tạo bản nháp chờ người dùng duyệt.
6. **Không gian lận benchmark:** Không hardcode đáp án hoặc viết điều kiện so khớp nguyên văn input của bộ câu thử `eval/benchmark.csv` vào trong code hay prompt.

## 3. Quy tắc kỹ thuật riêng của dự án ReviewShield

1. **Bắt buộc gọi AI thật:** Không để chế độ mock khi chạy đánh giá chính thức hoặc quay video demo; kiểm tra `.env` (`MODEL_PROVIDER`, `MODEL_NAME`, `API_KEY`) trước khi chạy `python run.py eval`.
2. **Tách biệt AI và toán học tất định:** LLM chỉ phân loại 4 nhãn (`verified_insight`, `low_signal`, `suspicious_pattern`, `logistics_only`), trích dẫn nguyên văn `evidence_quote`, rút Top 3 rủi ro và sinh 3 câu hỏi kiểm chứng shop. Mọi phép tính `real_trust_score`, `score_delta`, `verified_ratio` và kiểm tra chuỗi trích dẫn phải viết bằng code Python tất định trong `codebase/tools.py`.
3. **Ngôn ngữ trung lập, không phán quyết "giả 100%":** Luôn giải thích theo tín hiệu thông tin và dẫn chứng ngôn ngữ gốc.
4. **Chống phình scope:** Không xây server-side crawler cào trực tiếp sàn TMĐT, không làm đăng nhập/tài khoản, không dựng database ngoài trước khi đạt đủ 4 checkpoint (CP1–CP4).

## 4. Quy ước chung xuyên suốt dự án

* **Ngôn ngữ trả lời người dùng:** Tiếng Việt rõ ràng, ngắn gọn, khách quan.
* **Phong cách code & đặt tên:** Python `snake_case`, có type hints và docstring ngắn gọn; mọi tên trường JSON bám sát `docs/AI_PROMPT_AND_SCORING.md`.
* **Thống nhất Model khi chạy `eval` & `simulate`:** Toàn nhóm chốt **cùng 1 cặp `MODEL_PROVIDER` + `MODEL_NAME`** cho các lượt chạy chính thức (vì `cost/simulate.py` yêu cầu lượt `eval` đã chấm và lượt `simulate` phải dùng cùng 1 model để tính *Chi phí / task thành công*).
* **Quy ước đặt mã định danh (ID):**
  * File mẫu sản phẩm: `data/samples/sp_01.json` … `sp_30.json` (`product_id`: `sp_01`..`sp_30`).
  * Review ID: `r1`, `r2`, … (liên tiếp trong mỗi sản phẩm).
  * Tác giả ẩn danh: `user_01`, `user_02`, … (tuyệt đối không lưu tên/nickname thật).
  * Câu thử benchmark: `RS01` … `RS30` (thay toàn bộ `B01–B03` mẫu).
  * Phỏng vấn: `P1`, `P2`, `P3`… (`evidence/interviews/P1.md`).
* **Quy ước từ chối (`tu_choi`) & đầu vào lỗi:** Mọi yêu cầu ngoài phạm vi (cào link sàn trực tiếp, tự gửi tin nhắn shop, prompt injection) luôn trả về đủ 2 ý: **(1) Từ chối rõ lý do giới hạn** + **(2) Hướng dẫn cách dùng thay thế** (chọn mẫu hoặc dán review).
* **Quy ước Encoding:** Mọi file `.py`, `.md`, `.json`, `.csv`, `.yaml` bắt buộc lưu **UTF-8** (khi chỉnh CSV bằng Excel phải chọn *CSV UTF-8* để không vỡ dấu tiếng Việt).
* **Người duyệt code trước khi merge vào `main`:** Dương Quang Bảo (`2A202603362` — Đội trưởng).

## 5. Quy tắc Git: Tạo nhánh, Commit & Merge

### 5.1. Quy tắc tạo nhánh mới
1. **Không làm việc trực tiếp trên `main`:** Luôn cập nhật `main` mới nhất rồi mới tách nhánh:
   ```bash
   git checkout main && git pull origin main
   git checkout -b <type>/<ma-hv>-<mo-ta-ngan>
   ```
2. **Quy ước đặt tên nhánh** (dùng **mã học viên viết thường**, không dấu, ngăn cách bằng dấu `-`, không khoảng trắng):
   * `feat/<ma-hv>-<task>`: thêm tính năng / code mới (vd: `feat/2a202603362-core-ai-agent`, `feat/2a202603427-tools-and-ui`).
   * `fix/<ma-hv>-<task>`: sửa lỗi (vd: `fix/2a202603362-json-retry`).
   * `data/<ma-hv>-<task>`: thêm/cập nhật dữ liệu mẫu, benchmark, evidence (vd: `data/2a202603646-samples-evidence-eval`).
   * `docs/<ma-hv>-<task>`: cập nhật tài liệu, `spec.md`, `canvas.md`, slide (vd: `docs/2a202603483-cost-validation-slides`).
   * `chore/<ma-hv>-<task>`: cấu hình, `requirements.txt`, dọn dẹp repo (vd: `chore/2a202603362-add-sdk`).
3. **Phạm vi nhánh:** Mỗi nhánh chỉ giải quyết **1 đầu việc cụ thể**. Báo trước trong nhóm khi sửa các file dùng chung (`codebase/agent.py`, `eval/benchmark.csv`, `spec.md`) để tránh xung đột.

### 5.2. Quy tắc khi commit
1. **Cú pháp commit message (Conventional Commits):** `<type>(<scope>): <mô tả ngắn gọn <= 72 ký tự>`
   * `type`: `feat`, `fix`, `data`, `docs`, `refactor`, `test`, `chore`.
   * `scope` (khuyến nghị): `ai`, `tools`, `agent`, `app`, `eval`, `cost`, `evidence`, `docs`.
   * Ví dụ chuẩn:
     * `feat(tools): cai dat verify_grounding va compute_real_trust_score`
     * `fix(agent): them retry 1 lan khi LLM tra JSON loi cu phap`
     * `data(eval): bo sung 15 cau thu that cho moc CP2`
     * `docs(teams): dien thong tin thanh vien vao TEAMS.md`
2. **Commit gọn, tách bạch (atomic):** Tách riêng commit code với commit dữ liệu/tài liệu; tránh gom nhiều thay đổi không liên quan vào 1 commit để dễ review và rollback.
3. **Checklist bắt buộc trước khi chạy `git commit`:**
   * Chạy `git status` và `git diff --cached` để soát toàn bộ file sắp commit.
   * **Không commit bí mật & file rác:** Tuyệt đối không đưa `.env`, API key, thông tin cá nhân (PII) chưa ẩn danh, `__pycache__/`, hay file tạm vào commit.
   * **Không chạm file cấm sửa:** Kiểm tra không có thay đổi trong `run.py`, `codebase/tracing.py`, `eval/run_eval.py`, `cost/simulate.py` và các file log/kết quả đã chạy (`eval/run-*.csv`, `cost/simulate-*.csv`, `traces/*`).
   * **Tuân thủ mốc khóa CP2:** Sau 19:30 Thứ Sáu 27/11, không commit thay đổi vào `spec.md §7` và `eval/metric_spec.yaml`.
   * **Kiểm tra trước khi commit:** Chạy `python run.py check` đảm bảo không phát sinh lỗi mới; nếu sửa file trong `codebase/`, kiểm tra code nạp được và không lỗi cú pháp.

### 5.3. Quy tắc Push, PR & Merge
1. **Không `git push --force`** lên `main` hoặc nhánh đang có người khác dùng chung.
2. **Mở Pull Request vào `main`** với mô tả ngắn: nội dung thay đổi + kết quả chạy `python run.py check` (hoặc lệnh test liên quan).
3. **Nhánh `main` luôn phải xanh:** Chỉ merge khi đã được người phụ trách duyệt và `python run.py check` chạy thành công.
4. **Dọn nhánh sau merge:** Xóa nhánh phụ trên local và remote sau khi đã merge xong.
