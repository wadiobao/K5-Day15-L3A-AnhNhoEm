"""Entrypoint triển khai ReviewShield lên Streamlit Community Cloud (nhánh deploy/streamlit-cloud).

Nạp biến môi trường từ `st.secrets` TRƯỚC khi import `codebase/app.py` (và `codebase/ai.py`),
vì `codebase/ai.py` đọc `MODEL_PROVIDER`, `MODEL_NAME`, `API_KEY` tại thời điểm import.
Không chứa khóa API; cấu hình bí mật đặt trực tiếp trong Streamlit Cloud -> Settings -> Secrets.
"""
import os
import sys

import streamlit as st

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CODEBASE_DIR = os.path.join(ROOT_DIR, "codebase")

if CODEBASE_DIR not in sys.path:
    sys.path.insert(0, CODEBASE_DIR)

# Nạp secrets từ Streamlit Cloud vào os.environ trước khi import codebase/ai.py
for _key in ("MODEL_PROVIDER", "MODEL_NAME", "API_KEY", "API_BASE_URL"):
    try:
        if _key in st.secrets and str(st.secrets[_key]).strip():
            os.environ[_key] = str(st.secrets[_key]).strip()
    except Exception:
        # Chạy local không có .streamlit/secrets.toml -> codebase/ai.py sẽ tự đọc .env
        pass

import app  # noqa: E402

app.render_streamlit_app()
