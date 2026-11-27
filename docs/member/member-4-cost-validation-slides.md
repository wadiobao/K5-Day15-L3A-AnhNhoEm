# Task Specification — Thành viên 4: Chi phí, Kiểm thử Người dùng, Canvas & Slide Demo

* **Phụ trách:** Đặng Long Nhật (`2A202603483`)
* **Module:** `Cost Simulation, User Validation & Pitch/Demo`
* **Nhánh Git:** `docs/2a202603483-cost-validation-slides`
* **File được sửa:** `cost/personas.yaml`, `cost/cost-estimate.md`, `validation/log.md`, `canvas.md`, `slides/outline.md`, `docs/ai-usage.md`, `reflection/`
* **File cấm sửa:** `cost/simulate.py`, `run.py`, và tuyệt đối không sửa số liệu trong các file kết quả `cost/simulate-*.csv`

---

## 1. Đầu vào (Input)

* Bản chạy thử đã tích hợp (Module 1 + Module 2) có `.env` gọi API LLM thật.
* Số liệu bằng chứng pain từ Module 3 (`evidence/summary.md`) và kết quả đánh giá (`eval/report.md`).
* Phản hồi trực tiếp từ người dùng thật khi dùng thử `codebase/app.py`.
* Nhật ký quá trình sử dụng công cụ AI của cả 4 thành viên.

---

## 2. Đầu ra (Output)

1. **Mô phỏng & ước tính chi phí (`cost/`):**
   * Kết quả chạy `python run.py simulate` (sinh file `cost/simulate-*.csv` và `cost/simulate-*-summary.md`).
   * `cost/cost-estimate.md`: Bảng chi phí theo 3 kịch bản người dùng (`low: 300`, `base: 700`, `high: 1000`), chi phí/lượt phân tích, độ trễ trung bình và nhận xét khả năng tối ưu token.
   * Gửi bảng tóm tắt cho Đội trưởng cập nhật `spec.md §9`.
2. **Nhật ký kiểm thử người dùng (`validation/log.md`):**
   * Ghi nhận tối thiểu 3 phiên dùng thử thực tế (người dùng ngoài nhóm hoặc kịch bản mua hàng thật): tác vụ đã thử, kết quả quan sát, lỗi/điểm gây khó hiểu, và trạng thái đã sửa sau khi phản hồi lại Module 1–2.
3. **Tài liệu sản phẩm & trình bày:**
   * `canvas.md`: Hoàn thiện đủ 8 dòng (điền tên 4 thành viên, số liệu bằng chứng thật từ Module 3, cập nhật mốc CP2).
   * `slides/outline.md`: Dàn ý slide đầy đủ (Vấn đề & Bằng chứng → Lát cắt MVP & Kiến trúc Grounding Guard → Demo trực tiếp → Kết quả Eval & Chi phí → Giới hạn & Hướng phát triển).
   * Kịch bản & video demo ngắn (rõ ràng, không lộ API key, gọi AI thật).
   * `docs/ai-usage.md`: Ghi chép trung thực cách nhóm dùng AI trong code/prompt/tài liệu và phần con người tự kiểm chứng.
   * `reflection/`: Hoàn thiện bài thu hoạch cá nhân/nhóm theo `reflection/TEMPLATE.md`.

---

## 3. Logic xử lý (Processing Logic)

### 3.1. Quy trình mô phỏng chi phí
1. Rà soát lại `cost/personas.yaml` (tỷ lệ 3 nhóm `mua_it` 50%, `mua_vua` 35%, `san_sale_nhieu` 15%; `sessions: 50`, `seed: 42`).
2. Chạy thử `python run.py simulate --try` để xác nhận luồng chạy không lỗi và có token thật.
3. Chạy chính thức `python run.py simulate` bằng model thật.
4. Trích xuất số liệu `tokens_in`, `tokens_out`, đơn giá model theo bảng giá nhà cung cấp, tính chi phí/phiên và chi phí/tháng ở 3 mức `300 / 700 / 1000` người dùng, điền vào `cost/cost-estimate.md`.

### 3.2. Quy trình hỗ trợ gom data thật, Validation & chuẩn bị Demo
1. **Hỗ trợ gom data thật (trước khi chạy `simulate`):** Trong lúc chờ Module 1+2 code xong, tự mở trình duyệt gom 10 sản phẩm thật từ Shopee & TikTok Shop (mỗi sản phẩm 6–15 review đủ 1–5 sao, ghi rõ tên SP + điểm sàn, không lưu tên người mua) gửi Nguyễn Mạnh Tường chuẩn hóa vào `data/samples/*.json` và `evidence/data-mining.md`.
2. **User Validation:** Cho người dùng thật thao tác trực tiếp trên `codebase/app.py` với ít nhất 3 loại sản phẩm (hàng tốt thật, hàng seeding dày, hàng bị 1 sao do shipper).
3. Ghi lại nguyên văn phản hồi (không chỉnh sửa cho đẹp) vào `validation/log.md`.
4. Tổng hợp danh sách bug/UX issue gửi Module 1–2 sửa trước mốc CP4, sau đó xác minh lại và cập nhật trạng thái `Đã sửa` trong `validation/log.md`.
5. Dựng kịch bản demo 2–3 phút theo đúng luồng 3 sản phẩm tiêu biểu + 1 ca dán review trực tiếp.

---

## 4. Quy tắc nghiệp vụ (Business Rules)

1. **Minh bạch số liệu:** Mọi số liệu giả định vận hành (số user/tháng, tỷ lệ persona) phải ghi rõ *(tự ước tính)*; số liệu token/chi phí phải trích trực tiếp từ kết quả chạy `python run.py simulate` với model thật.
2. **Không sửa log đã chạy:** Tuyệt đối không chỉnh tay `cost/simulate-*.csv` hoặc `traces/*`.
3. **An toàn khi quay demo & làm slide:** Không để lộ `.env`, API key hoặc thông tin cá nhân thật trên màn hình quay video hay ảnh chụp slide.
4. **Khớp số liệu toàn repo:** Số liệu trên `canvas.md`, `slides/outline.md`, `cost/cost-estimate.md` phải nhất quán 100% với `evidence/summary.md`, `eval/report.md` và `spec.md`.

---

## 5. Tiêu chí đánh giá (Acceptance Criteria)

* Có kết quả `python run.py simulate` chạy bằng model thật (`model != fake`, `tokens_in > 0`, `tokens_out > 0`).
* `cost/cost-estimate.md` đầy đủ bảng 3 kịch bản `low/base/high` và phân tích tính khả thi kinh tế.
* `validation/log.md` ghi nhận rõ phiên test thực tế, có bằng chứng vòng lặp phản hồi → sửa lỗi.
* `canvas.md`, `slides/outline.md`, `docs/ai-usage.md` không còn placeholder `[Điền ...]` hoặc `____`.

---

## 6. Kế hoạch kiểm thử (Testing Checklist)

1. **Kiểm tra mô phỏng chi phí:** Chạy `python run.py simulate --try` trước, sau đó chạy `python run.py simulate`; mở file summary vừa sinh kiểm tra không có dòng `error` và `model != fake`.
2. **Kiểm tra nhất quán tài liệu:** Đối chiếu chéo các con số (số mẫu review, % pain, 4 ngưỡng metric, chi phí/tháng) giữa `canvas.md`, `spec.md`, `cost/cost-estimate.md` và `slides/outline.md`.
3. **Diễn tập demo (Dry-run):** Chạy trọn vẹn kịch bản demo từ `python run.py` trong <= 3 phút, kiểm tra không lỗi hiển thị tiếng Việt, không lộ `.env`/API key.
4. **Kiểm tra trước khi mở PR:** Chạy `python run.py check` và `git status` để chắc chắn không commit file tạm/video dung lượng lớn hoặc `.env`.
