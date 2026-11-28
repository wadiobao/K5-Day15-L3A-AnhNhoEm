# ReviewShield Chrome Extension (Manifest V3) & Backend API

Phiên bản mở rộng sau hackathon giúp người mua **lấy đánh giá trực tiếp trên trang sản phẩm đang mở** (Shopee, Tiki, Điện Máy Xanh / TGDĐ hoặc văn bản bôi đen), **ẩn danh PII 100% tại trình duyệt**, xuất JSON chuẩn ReviewShield và gọi API AI phân tích ngay trong **Chrome Side Panel**.

> **An toàn & tuân thủ:** Không xây server-side crawler, không vượt CAPTCHA/anti-bot, không nhúng `API_KEY` vào Extension. Khóa API chỉ lưu trong `.env` trên máy chủ Backend.

---

## 1. Chạy Backend API

### 1.1. Chạy thử cục bộ (trên máy Windows)
```powershell
.\.venv\Scripts\python.exe -m pip install -r api/requirements-api.txt
.\.venv\Scripts\python.exe -m uvicorn api.server:app --host 127.0.0.1 --port 8000 --reload
```
Kiểm tra sức khỏe API tại `http://127.0.0.1:8000/api/health` (không lộ `API_KEY`).

### 1.2. Deploy lên VPS Google Cloud (`https://hackathonane.duckdns.org`)
Trên VPS Ubuntu đã clone repo và có `.env` (chứa `MODEL_PROVIDER=gemini`, `MODEL_NAME=gemini-3.5-flash-lite`, `API_KEY=...`), chỉ cần chạy script có sẵn (tự cài `api/requirements-api.txt`, dựng dịch vụ `systemd` bền bỉ trên `127.0.0.1:8000`, sao lưu và cập nhật Caddy để định tuyến `/api/*` → FastAPI trong khi vẫn giữ nguyên Streamlit ở `/`):
```bash
cd ~/K5-Day15-L3A-AnhNhoEm
git fetch origin
git checkout feat/2a202603483-chrome-extension
git pull origin feat/2a202603483-chrome-extension
bash api/deploy_vps.sh
```
Kiểm tra nhanh log dịch vụ khi cần:
```bash
sudo systemctl status reviewshield-api
curl https://hackathonane.duckdns.org/api/health
```

---

## 2. Cài thử Chrome Extension ngay lập tức (`Load unpacked` — 1 phút)

1. Mở Chrome/Edge, truy cập `chrome://extensions/`.
2. Bật **Chế độ dành cho nhà phát triển (Developer mode)** ở góc trên bên phải.
3. Bấm **Tải tiện ích đã giải nén (Load unpacked)** → chọn thư mục **`extension/`** trong repo.
4. Ghim biểu tượng **ReviewShield** lên thanh công cụ và bấm để mở **Side Panel**.
5. Giữ mặc định **`https://hackathonane.duckdns.org`** (khi đã deploy lên VPS) hoặc bấm nhãn trạng thái API → chọn **`Localhost :8000`** → **`Lưu & Kiểm tra`** khi test máy cá nhân.

### Cách dùng Tự động cuộn & gom cân bằng (không cần vuốt tay)
1. Mở trang sản phẩm Shopee / Tiki / Điện Máy Xanh (đứng ngay đầu trang, không cần cuộn xuống).
2. Chọn số lượng mục tiêu (**20 / 30 / 50 review**) và bật **`Tự lấy cân bằng 5★ + 1–3★`**.
3. Bấm **`Tự động quét review`**: Extension tự cuộn tải mục Đánh giá, ưu tiên lọc *Có Bình Luận* và gom thêm *1–3 Sao*, ẩn danh 100% PII ngay tại trình duyệt (`user_01…`), rồi cuộn trả về đầu trang (tự động dừng nếu có CAPTCHA/đăng nhập hoặc bạn bấm **`Dừng`**).
4. Bấm **`Sao chép JSON`** / **`Tải file .json`** nếu muốn kiểm tra 0 PII, rồi bấm **`Soi đánh giá bằng AI`**.

---

## 3. Đóng gói & Checklist đăng lên Chrome Web Store

### 3.1. Tạo gói `.zip` sạch
**Windows (PowerShell — đứng tại thư mục gốc repo):**
```powershell
Compress-Archive -Path extension/manifest.json,extension/background.js,extension/content.js,extension/sidepanel.html,extension/sidepanel.css,extension/sidepanel.js,extension/icons -DestinationPath reviewshield-extension.zip -Force
```
*(Không commit file `reviewshield-extension.zip` lên Git.)*

### 3.2. Checklist nộp Chrome Web Store Developer Dashboard
- [ ] Đăng ký tài khoản Chrome Web Store Developer (phí 1 lần \$5).
- [ ] Tải lên `reviewshield-extension.zip` (Manifest V3, version `1.0.0`).
- [ ] Gắn link công khai tới `extension/PRIVACY_POLICY.md` (vd URL GitHub raw hoặc trang docs của repo).
- [ ] Khai báo mục **Data usage**: chỉ chọn *Website content* (văn bản đánh giá sản phẩm đã ẩn danh khi người dùng bấm nút), xác nhận không dùng cho quảng cáo/theo dõi.
- [ ] Chuẩn bị 1–3 ảnh chụp màn hình Side Panel (1280×800) và icon 128×128 (`extension/icons/icon128.png`).

### 3.3. Mẫu giải trình quyền cho đội ngũ duyệt của Google
- **`activeTab`:** Only accesses the active tab at the exact moment the user clicks the "Scan visible reviews" button inside the Side Panel; never runs automatically in the background.
- **`scripting`:** Injects `content.js` on-demand into the active tab to extract visible product reviews and scrub PII client-side before displaying the anonymized JSON preview to the user.
- **`sidePanel`:** Provides the ReviewShield analysis interface alongside e-commerce product pages without modifying page layout.
- **`storage`:** Stores only the user's preferred backend API URL locally via `chrome.storage.local`.
- **Host permissions (`https://hackathonane.duckdns.org/*`):** Required to send anonymized review JSON payloads to the ReviewShield analysis API and check `/api/health`.
