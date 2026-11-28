# Chính sách Quyền riêng tư / Privacy Policy — ReviewShield Chrome Extension

*Cập nhật lần cuối / Last updated: 2026-11-28*  
*Đơn vị phát triển / Developer: Nhóm AnhNhoEM (ReviewShield · Track D)*

---

## Phần 1 — Tiếng Việt

### 1. Dữ liệu ReviewShield thu thập và xử lý
ReviewShield **không chạy ngầm** và **không tự động thu thập dữ liệu duyệt web**. Tiện ích chỉ đọc phần văn bản đánh giá sản phẩm đang hiển thị trên trang hiện tại **khi người dùng chủ động bấm nút "Quét review đang hiển thị"** trong Side Panel.

Trước khi gửi dữ liệu lên máy chủ phân tích (`https://hackathonane.duckdns.org/api/analyze` hoặc máy chủ cục bộ do người dùng tự cấu hình), mã `content.js` chạy ngay trên trình duyệt của người dùng sẽ:
- **Loại bỏ** tên tài khoản, ảnh đại diện người mua và phản hồi người bán.
- **Ẩn danh tự động** số điện thoại, địa chỉ email, đường dẫn cá nhân và chuỗi số mã đơn hàng dài thành `[đã ẩn ...]`, gắn mã ẩn danh `user_01`, `user_02`…
- **Hiển thị trước bản JSON** để người dùng có thể tự kiểm tra trước khi bấm **"Soi đánh giá bằng AI"**.

### 2. Dữ liệu ReviewShield KHÔNG thu thập
- Không thu thập thông tin đăng nhập, mật khẩu, cookie, phiên sàn TMĐT hay lịch sử duyệt web.
- Không thu thập tên thật, địa chỉ, số điện thoại, thông tin thanh toán của người dùng hay người viết đánh giá.
- Không bán, chia sẻ hoặc sử dụng dữ liệu người dùng cho quảng cáo hay huấn luyện mô hình riêng.

### 3. Lưu trữ tạm thời (Cache) & Cài đặt cục bộ
- Tiện ích chỉ dùng `chrome.storage.local` để lưu **địa chỉ Backend URL** do người dùng chọn.
- Máy chủ Backend có thể lưu tạm kết quả phân tích sản phẩm đã ẩn danh trong bộ nhớ đệm (TTL tối đa 12 giờ) theo mã băm nội dung review nhằm tiết kiệm chi phí gọi AI; không lưu bất kỳ định danh cá nhân nào.

### 4. Giải trình quyền sử dụng (Chrome Permissions)
- `activeTab` & `scripting`: chỉ đọc DOM của tab hiện tại đúng tại thời điểm người dùng bấm nút quét.
- `sidePanel`: hiển thị giao diện phân tích cạnh trang sản phẩm.
- `storage`: lưu địa chỉ Backend API mà người dùng cài đặt.

---

## Part 2 — English (For Chrome Web Store Review)

### 1. What Data ReviewShield Processes
ReviewShield **does not run background scraping** and **does not track browsing history**. It only reads visible product review text on the currently active tab **when the user explicitly clicks "Quét review đang hiển thị"** in the Side Panel.

Before sending any text to the configured analysis backend (`https://hackathonane.duckdns.org/api/analyze` or a user-configured local endpoint), client-side code (`content.js`) strips buyer usernames/avatars and redacts phone numbers, email addresses, personal links, and long order numbers into anonymized placeholders (`user_01`, `user_02`, …). Users can inspect the anonymized JSON before submitting.

### 2. Data We Do NOT Collect
- We do **not** collect account credentials, cookies, browsing history, personal identity information (PII), or financial/payment data.
- We do **not** sell or transfer user data to third parties for advertising or profiling.

### 3. Caching & Local Storage
- `chrome.storage.local` stores only the user's selected backend endpoint URL.
- The backend may temporarily cache anonymized product analysis results (up to 12 hours TTL) keyed by a SHA-256 hash of anonymized review text to reduce duplicate LLM token usage.

### 4. Permission Justification
- `activeTab` & `scripting`: strictly on-demand DOM extraction on the active tab when triggered by user click.
- `sidePanel`: renders the ReviewShield analysis UI alongside the shopping page.
- `storage`: persists the user's backend URL preference locally.
