# SPEC — Đặc Tả Hệ Thống AI: ReviewShield

> Lộ trình mốc: Chốt `§7` trước CP2 (19:30 Thứ Sáu 27/11) • Nộp `§0–§7` tại CP3 (10:00 Thứ Bảy 28/11) • Đủ `§0–§10` tại CP4 (14:30 Thứ Bảy 28/11).

## §0. Bối cảnh & Bài toán hiện tại
Người mua hàng trên các sàn thương mại điện tử thường dựa vào điểm sao hiển thị (4.8–5.0 sao) để quyết định nhanh. Thực tế, điểm này thường bị bóp méo bởi đánh giá nhận xu ("giao nhanh, chưa dùng nhưng cho 5 sao"), đánh giá lặp mẫu nghi vấn seeding và đánh giá 1–2 sao chỉ phàn nàn về shipper.

## §1. Người dùng mục tiêu & Bằng chứng Pain
* **Người dùng chính:** Người mua hàng online phổ thông cần thẩm định nhanh độ tin cậy của sản phẩm trước khi đặt mua.
* **Bằng chứng pain:** Tổng hợp từ dữ liệu đào review công khai (`evidence/data-mining.md`), phỏng vấn người mua (`evidence/interviews/`) và khảo sát (`evidence/survey/`), xem chi tiết tại `evidence/summary.md`.

## §2. Giải pháp & Lát cắt MVP
**ReviewShield** nhận một cụm đánh giá sản phẩm (từ kho 25–30 mẫu thật đã ẩn danh hoặc người dùng dán trực tiếp), thực hiện:
1. Tiền xử lý loại bỏ review trống và đếm số lượng review trùng lặp hoàn toàn.
2. Gọi mô hình ngôn ngữ thật (Structured Output JSON) để phân loại từng review vào 1 trong 4 nhãn tín hiệu (`verified_insight`, `low_signal`, `suspicious_pattern`, `logistics_only`) kèm trích dẫn nguyên văn `evidence_quote`.
3. Chạy lớp **Grounding Guard** kiểm chứng 100% trích dẫn phải xuất hiện trong review gốc.
4. Tính **Điểm tin cậy thực (Real Trust Score)** bằng công thức trọng số tất định, tổng hợp Top 3 rủi ro thực tế từ nhóm `verified_insight` và sinh 3 câu hỏi kiểm chứng shop.

## §3. Phạm vi Không làm (Out of Scope)
* Không xây crawler phía server tự động cào link Shopee/TikTok Shop (tránh captcha và rủi ro sập demo).
* Không phán quyết tuyệt đối "review giả 100%".
* Không tự gửi tin nhắn tới shop hoặc can thiệp trực tiếp vào tài khoản sàn của người dùng.

## §4. Kiến trúc luồng & Ánh xạ vào `codebase/`
* `codebase/ai.py`: Cài đặt `call_model(system, user)` nối API LLM thật (theo `docs/connect-model.md`), giữ nguyên `@model_call` và trả về đúng `text`, `model`, `tokens_in`, `tokens_out`.
* `codebase/tools.py`: Khai báo các `@tool` gồm `preprocess_reviews`, `verify_grounding`, `compute_real_trust_score` (tất định 100%, không giao phép tính cho LLM).
* `codebase/agent.py`: Hàm `answer(text)` nhận đầu vào review (JSON hoặc text), gọi các tool và `call_model`, tổng hợp câu trả lời có cấu trúc rõ ràng kèm bảng Điểm sàn vs Điểm thực, Top 3 rủi ro, 3 câu hỏi kiểm chứng và chi tiết nhãn từng review.
* `codebase/app.py`: Giao diện web 1 màn hình phục vụ demo trực tiếp.

## §5. Đặc tả Prompt, Nhãn & Công thức Điểm
Chi tiết đầy đủ nằm tại `docs/AI_PROMPT_AND_SCORING.md`. Tóm tắt trọng số chất lượng:
* `verified_insight` (Trải nghiệm cụ thể): trọng số `1.00`
* `low_signal` (Nhận xu / Thiếu thông tin): trọng số `0.15`
* `suspicious_pattern` (Nghi vấn lặp mẫu): trọng số `0.10`
* `logistics_only` (Lỗi vận chuyển): trọng số `0.00` (tách riêng cảnh báo vận chuyển)

## §6. Quản trị rủi ro & An toàn
* **Rủi ro AI bịa trích dẫn:** Chặn bằng `verify_grounding` trong `codebase/tools.py`.
* **Rủi ro AI tính sai điểm:** Chặn bằng `compute_real_trust_score` tính hoàn toàn bằng Python.
* **Rủi ro lộ dữ liệu cá nhân:** Toàn bộ dữ liệu mẫu đều ẩn danh người viết thành `user_01`, `user_02`.

## §7. Chuẩn "Đạt" (Khóa trước CP2 — khớp `eval/metric_spec.yaml`)
Hệ thống đạt chuẩn phát hành MVP khi chạy `python run.py eval` trên bộ `eval/benchmark.csv` (>= 25 tình huống thật, đủ 4 nhóm kịch bản) thỏa mãn đồng thời 4 ngưỡng (và điều kiện kỹ thuật `schema_compliance = 100%` không vỡ định dạng JSON):
1. **`label_accuracy` >= 85%**: Tỷ lệ phân loại đúng nhãn 4 nhóm so với nhãn chuẩn.
2. **`direction_match` >= 85%**: Tỷ lệ case dự đoán đúng chiều biến động của Điểm tin cậy thực so với điểm sàn (`near_platform`, `lower_than_platform`, `higher_than_platform`).
3. **`citation_grounding` = 100%**: Mọi `evidence_quote` hiển thị cho người dùng phải khớp nguyên văn chuỗi con trong review gốc.
4. **`actionable_quality` >= 80%**: Đánh giá bởi người chấm xem Top 3 rủi ro và 3 câu hỏi kiểm chứng shop có sát với phàn nàn thực tế trong cụm review hay không.

## §8. Kết quả đánh giá thực tế (Điền tại CP3–CP4)
* `[Dán tóm tắt kết quả từ eval/report.md sau khi chạy python run.py eval và python run.py score]`

## §9. Ước tính chi phí vận hành (Điền tại CP4)
* `[Dán bảng mô phỏng từ cost/simulate-N-summary.md sau khi chạy python run.py simulate]`

## §10. Nhật ký thay đổi (Changelog — cập nhật đến 23:59 Thứ Bảy 28/11)
* **2026-11-27 (CP1):** Khởi tạo đặc tả ReviewShield (Track D), chốt kiến trúc 3 chặng và bộ 4 nhãn tín hiệu.
* `[Cập nhật tiếp các mốc chỉnh prompt, chạy eval và sửa lỗi đến hạn cuối]`
