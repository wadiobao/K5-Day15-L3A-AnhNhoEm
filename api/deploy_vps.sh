#!/usr/bin/env bash
# Script tự động deploy Backend API ReviewShield (FastAPI) lên VPS Ubuntu
# dùng chung domain HTTPS https://hackathonane.duckdns.org với Streamlit hiện có.
#
# Cách chạy trên VPS (đứng trong thư mục gốc repo):
#   bash api/deploy_vps.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN="${DOMAIN:-hackathonane.duckdns.org}"
API_PORT="${API_PORT:-8000}"
RUN_USER="${SUDO_USER:-$(whoami)}"

echo "==> [1/6] Kiểm tra repo tại: $REPO_DIR (user: $RUN_USER)"
if [[ ! -f "$REPO_DIR/api/server.py" ]]; then
  echo "LỖI: Không thấy api/server.py trong $REPO_DIR"
  exit 1
fi
if [[ ! -f "$REPO_DIR/.env" ]]; then
  echo "CẢNH BÁO: Chưa thấy file .env trong $REPO_DIR — API sẽ chạy chế độ fake cho tới khi tạo .env có API_KEY."
fi

# Tìm Python venv có sẵn
if [[ -x "$REPO_DIR/.venv/bin/python" ]]; then
  VENV_PY="$REPO_DIR/.venv/bin/python"
elif [[ -x "$REPO_DIR/venv/bin/python" ]]; then
  VENV_PY="$REPO_DIR/venv/bin/python"
else
  echo "==> Tạo mới .venv vì chưa thấy trong repo..."
  python3 -m venv "$REPO_DIR/.venv"
  VENV_PY="$REPO_DIR/.venv/bin/python"
fi

echo "==> [2/6] Cài thư viện Backend API từ api/requirements-api.txt..."
"$VENV_PY" -m pip install --upgrade pip >/dev/null
"$VENV_PY" -m pip install -r "$REPO_DIR/api/requirements-api.txt"

echo "==> [3/6] Cài dịch vụ systemd reviewshield-api (chạy bền bỉ cổng 127.0.0.1:${API_PORT})..."
SERVICE_FILE="/etc/systemd/system/reviewshield-api.service"
sudo tee "$SERVICE_FILE" >/dev/null <<EOF
[Unit]
Description=ReviewShield Extension Backend API (FastAPI)
After=network.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${REPO_DIR}
ExecStart=${VENV_PY} -m uvicorn api.server:app --host 127.0.0.1 --port ${API_PORT}
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable reviewshield-api
sudo systemctl restart reviewshield-api

echo "==> [4/6] Chờ FastAPI khởi động và kiểm tra local /api/health..."
for i in $(seq 1 15); do
  if curl -fsS "http://127.0.0.1:${API_PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "http://127.0.0.1:${API_PORT}/api/health"
echo ""

echo "==> [5/6] Cập nhật Caddyfile giữ nguyên Streamlit và mở tuyến /api/*..."
# Tự động phát hiện cổng Streamlit đang cấu hình trong Caddyfile cũ (mặc định 8501)
STREAMLIT_PORT="8501"
if [[ -f /etc/caddy/Caddyfile ]]; then
  sudo cp /etc/caddy/Caddyfile "/etc/caddy/Caddyfile.bak.$(date +%Y%m%d_%H%M%S)"
  DETECTED_PORT="$(grep -Eo 'reverse_proxy\s+[^ ]+:([0-9]+)' /etc/caddy/Caddyfile | grep -v ":${API_PORT}" | head -n1 | awk -F: '{print $NF}' || true)"
  if [[ -n "$DETECTED_PORT" ]]; then
    STREAMLIT_PORT="$DETECTED_PORT"
  fi
fi
echo "    Streamlit upstream phát hiện: 127.0.0.1:${STREAMLIT_PORT}"

sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
${DOMAIN} {
    encode gzip

    handle /api/* {
        reverse_proxy 127.0.0.1:${API_PORT}
    }

    handle {
        reverse_proxy 127.0.0.1:${STREAMLIT_PORT}
    }
}
EOF

sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy

echo "==> [6/6] Kiểm tra trực tiếp qua HTTPS công khai: https://${DOMAIN}/api/health"
curl -fsS "https://${DOMAIN}/api/health"
echo ""
echo "HOÀN TẤT! Mở lại Extension ReviewShield → chọn VPS HTTPS (https://${DOMAIN}) → Lưu & Kiểm tra."
