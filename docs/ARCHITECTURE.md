# ARCHITECTURE — Kiến Trúc Hệ Thống ReviewShield Trên Khung AI20K

## 1. Sơ đồ kiến trúc tích hợp với khung `K5-Day15-L3A-AnhNhoEm`

```text
[ Người dùng / BGK ]              [ Khung chấm tự động BTC ]
        |                            |                  |
        v                            v                  v
  codebase/app.py             eval/run_eval.py   cost/simulate.py
        |                            |                  |
        +-------------+--------------+------------------+
                      |  Gọi chung: answer(text) -> {"output": str}
                      v
             codebase/agent.py  (Điều phối pipeline 3 chặng)
             /        |        \
            v         v         v
   codebase/tools.py  |   codebase/ai.py (@model_call -> Real LLM API)
   (@tool)            |         |
   - preprocess       |         v
   - verify_grounding |   codebase/tracing.py (Tự động ghi log & token)
   - trust_score      |
                      v
              data/samples/*.json & eval/benchmark.csv
```

## 2. Luồng xử lý 3 chặng bên trong `codebase/agent.py`

1. **Chặng 1 — Tiền xử lý (`preprocess_reviews` trong `tools.py`):**
   * Đọc đầu vào dạng JSON hoặc văn bản danh sách review.
   * Lọc bình luận rỗng, chuẩn hóa khoảng trắng và tính `duplicate_group_size`.
   * Cắt lô tối đa 20 review tiêu biểu (giữ đủ dải 1–5 sao) để giữ độ trễ dưới 4 giây.
2. **Chặng 2 — Phân tích ngữ nghĩa bằng AI thật (`call_model` trong `ai.py`):**
   * Gọi API LLM thật (OpenAI / Gemini / Claude theo `docs/connect-model.md`) với `temperature = 0.1` và yêu cầu trả JSON đúng schema tại `docs/AI_PROMPT_AND_SCORING.md`.
   * Ghi nhận chính xác `tokens_in`, `tokens_out` để `tracing.py` và `cost/simulate.py` tính chi phí thật.
3. **Chặng 3 — Kiểm chứng & Tính điểm (`verify_grounding` + `compute_real_trust_score` trong `tools.py`):**
   * Xác minh 100% `evidence_quote` tồn tại nguyên văn trong văn bản gốc.
   * Tính `real_trust_score`, `score_delta`, `verified_ratio`, `trust_level` hoàn toàn bằng Python tất định.
   * Định dạng kết quả đầu ra rõ ràng cho cả UI (`app.py`) và bộ chấm (`eval/run_eval.py`).

## 3. Xử lý lỗi & Bảo vệ Demo
* Nếu JSON từ LLM lỗi cú pháp: tự động retry 1 lần với thông điệp nhắc sửa định dạng JSON.
* Nếu toàn bộ review đầu vào là `logistics_only`: trả về `real_trust_score = null` và thông báo "Chưa đủ đánh giá về chất lượng sản phẩm" thay vì chia cho 0.
* Nếu API quá tải (429): đợi ngắn (backoff) rồi thử lại; trên UI hiển thị thông báo tiếng Việt rõ ràng và giữ nguyên dữ liệu đã nhập.

## 4. Lộ trình mở rộng lên Production (Sau giai đoạn Hackathon CP1–CP4)

Trong phạm vi MVP (CP1–CP4), hệ thống chỉ nhận mẫu có sẵn (`data/samples/`) hoặc văn bản dán tay để đảm bảo ổn định 100% khi chấm và demo. Khi đưa lên Production, toàn bộ lõi 3 chặng (`tools.py`, `ai.py`, `agent.py`) được giữ nguyên và nâng cấp lớp thu thập & vận hành như sau:

1. **Kênh lấy dữ liệu hợp lệ (không dùng server-side crawler dễ vướng CAPTCHA):**
   * **Browser Extension (Chrome/Edge — Kênh chủ lực B2C):** Người dùng mở trang sản phẩm Shopee/TikTok Shop/Tiki trên trình duyệt thật và bấm 1-click; Extension đọc phần review đang hiển thị trên DOM, ẩn danh tên tác giả ngay tại client rồi gửi mảng JSON về API.
   * **Paste text / Ảnh chụp màn hình (Web & Mobile):** Hỗ trợ người mua trên app di động dán review hoặc tải ảnh chụp màn hình (kết hợp OCR) rồi đẩy qua cùng pipeline 3 chặng.
   * **Official Partner API (Hướng B2B):** Tích hợp qua API chính thức với nền tảng quản lý bán hàng hoặc đối tác sàn cho gian hàng chính hãng.
2. **Đóng gói API & Tối ưu chi phí token:**
   * Đóng gói `agent.py` + `tools.py` thành REST API (`POST /v1/analyze` với FastAPI/Cloud Run).
   * Bổ sung **Redis Cache** theo khóa `(product_id, reviews_hash)` với TTL 12–24 giờ để nhiều người xem cùng một sản phẩm hot chỉ tốn token LLM một lần (ước tính giảm 70–85% chi phí API).
3. **Độ tin cậy, Bảo mật & Giám sát (Production Hardening):**
   * Rate limiting theo user/IP, circuit breaker và fallback đa model (ví dụ: Gemini Flash ↔ GPT-4o-mini) khi nhà cung cấp quá tải (429/timeout).
   * Ẩn danh PII ngay tại client/gateway, không lưu lịch sử tài khoản mua hàng, quản lý API key bằng Secret Manager và theo dõi telemetry (`grounding_rate`, độ trễ, chi phí/lượt).
