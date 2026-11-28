"""Giao diện demo 1 màn hình ReviewShield (Streamlit) — Thành viên 2 (2A202603427).

Phiên bản E-Commerce Sunset Gen Z — lấy cảm hứng trực tiếp từ hệ sinh thái thương mại điện tử
Việt Nam (Cam san hô hoàng hôn – Vàng xu thưởng – Xanh bạc hà kiểm chứng – Xanh giao nhanh
trên nền kem đào ấm và khối Espresso tương phản), thoát hẳn cảm giác phòng lab/hành chính:
- Hiệu ứng chuyển động mượt chuẩn Emil Kowalski (`--ease-out`, `scale(0.97)`, thuần GPU,
  cô lập `@media (hover: hover) and (pointer: fine)` và tôn trọng `prefers-reduced-motion`).
- Nền Aura đa tầng mềm mại ấm áp + Thanh nổi Dynamic Pill (đã chống che bởi Header Streamlit).
- Lăng kính điểm tương tác 60fps: trượt số + thanh sao vàng động + bộ gạt tách nhận xu / seeding / shipper.
- Thẻ sản phẩm phong cách Mall + Preview review bong bóng thật + Liên kết chéo Top 3 rủi ro → Review gốc.

Chạy bằng lệnh duy nhất của bộ khung:
    python run.py

Cơ chế khởi chạy an toàn:
- Khi được import (ví dụ trong harness kiểm thử): KHÔNG khởi động server Streamlit.
- Khi chạy trực tiếp qua `python run.py`: tự bootstrap `streamlit run codebase/app.py`
  với theme sáng cố định (`--theme.base=light`) mà không sửa `run.py`.
- Nếu máy chưa cài `streamlit`: hướng dẫn cài từ `requirements.txt` và hỗ trợ fallback CLI.
"""
from __future__ import annotations

import glob
import html
import io
import json
import os
import re
import subprocess
import sys
import unicodedata
import zipfile
from typing import Any

for _stream in (sys.stdout, sys.stderr, sys.stdin):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CODEBASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CODEBASE_DIR)
SAMPLES_DIR = os.path.join(ROOT_DIR, "data", "samples")
EXTENSION_DIR = os.path.join(ROOT_DIR, "extension")
EXTENSION_PACKAGE_FILES = (
    "manifest.json",
    "background.js",
    "content.js",
    "sidepanel.html",
    "sidepanel.css",
    "sidepanel.js",
    "icons/icon16.png",
    "icons/icon48.png",
    "icons/icon128.png",
)

if CODEBASE_DIR not in sys.path:
    sys.path.insert(0, CODEBASE_DIR)

WEIGHT_MAP: dict[str, float] = {
    "verified_insight": 1.00,
    "low_signal": 0.15,
    "suspicious_pattern": 0.10,
    "logistics_only": 0.00,
}

# Hệ màu TMĐT Việt Nam hiện đại (Xanh bạc hà Mall, Vàng xu thưởng, Cam san hô cảnh báo, Xanh giao nhanh)
LABEL_META: dict[str, dict[str, str]] = {
    "verified_insight": {
        "name": "Trải nghiệm cụ thể",
        "short": "Trải nghiệm thật",
        "tone_class": "tone-mint",
        "bar_var": "var(--sig-mint)",
        "mark": "mark-mint",
        "desc": "Nêu chi tiết thực tế về chất lượng, độ bền, kích cỡ hoặc quá trình sử dụng.",
    },
    "low_signal": {
        "name": "Nhận xu / Thiếu thông tin",
        "short": "Nhận xu / Chung chung",
        "tone_class": "tone-coin",
        "bar_var": "var(--sig-coin)",
        "mark": "mark-coin",
        "desc": "Khen/chê chung chung, chưa dùng đã cho 5 sao, viết lấy xu hoặc ký tự vô nghĩa.",
    },
    "suspicious_pattern": {
        "name": "Nghi vấn lặp mẫu",
        "short": "Nghi lặp mẫu",
        "tone_class": "tone-coral",
        "bar_var": "var(--sig-coral)",
        "mark": "mark-coral",
        "desc": "Trùng lặp cấu trúc câu bất thường hoặc giọng quảng cáo gượng ép.",
    },
    "logistics_only": {
        "name": "Lỗi vận chuyển",
        "short": "Chỉ nói vận chuyển",
        "tone_class": "tone-sky",
        "bar_var": "var(--sig-sky)",
        "mark": "mark-sky",
        "desc": "Chỉ phản ánh shipper, tốc độ giao hoặc vỏ hộp ngoài; tách khỏi điểm sản phẩm.",
    },
}

TRUST_LEVEL_META: dict[str, dict[str, str]] = {
    "high": {
        "label": "Độ tin cậy cao",
        "badge": "Đáng cân nhắc mua",
        "badge_cls": "verdict-mint",
        "icon": "check",
        "summary": "Điểm trên sàn sát với trải nghiệm sử dụng thực tế của người mua.",
    },
    "medium": {
        "label": "Cần kiểm chứng thêm",
        "badge": "Nên đọc kỹ rủi ro",
        "badge_cls": "verdict-coin",
        "icon": "alert",
        "summary": "Có lượng đánh giá nhiễu vừa phải — nên xem kỹ nhược điểm trước khi chốt đơn.",
    },
    "low": {
        "label": "Cảnh báo nhiễu sao cao",
        "badge": "Sao ảo lệch mạnh",
        "badge_cls": "verdict-coral",
        "icon": "shield_x",
        "summary": "Điểm hiển thị trên sàn đang bị đẩy lệch do nhiều câu nhận xu hoặc lặp mẫu nghi vấn.",
    },
    "insufficient_data": {
        "label": "Chưa đủ dữ liệu chất lượng",
        "badge": "Chưa đủ dữ liệu hàng",
        "badge_cls": "verdict-sky",
        "icon": "info",
        "summary": "Đánh giá chủ yếu nói về shipper/giao hàng, chưa đủ thông tin chấm chất lượng sản phẩm.",
    },
}

DIRECTION_TEXT: dict[str, str] = {
    "near_platform": "Sát điểm hiển thị trên sàn",
    "lower_than_platform": "Thấp hơn điểm hiển thị trên sàn",
    "higher_than_platform": "Cao hơn điểm sàn (oan do vận chuyển)",
    "insufficient_data": "Chưa đủ đánh giá chất lượng sản phẩm",
}

# Ảnh sản phẩm thật công khai (Wikimedia Commons, đã xác thực HTTP 200)
PRODUCT_PHOTO_CATALOG: dict[str, dict[str, str]] = {
    "mouse": {
        "label": "Chuột Gaming không dây",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/d/d5/2026_G305_X_SUPERLIGHT.jpg/960px-2026_G305_X_SUPERLIGHT.jpg",
    },
    "keyboard": {
        "label": "Bàn phím cơ LED",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0d/Logitech-g910_%2816093947623%29.jpg",
    },
    "usb": {
        "label": "Ổ đĩa USB Flash",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/6/6f/Kingston_Technology_DataTraveler_G4_USB_flash_drive_USB_3.0_32_Gb.jpg/960px-Kingston_Technology_DataTraveler_G4_USB_flash_drive_USB_3.0_32_Gb.jpg",
    },
    "mousepad": {
        "label": "Lót chuột Gaming cỡ lớn",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/cc/Desk_Setup_%28Unsplash%29.jpg/960px-Desk_Setup_%28Unsplash%29.jpg",
    },
    "laptop_stand": {
        "label": "Giá đỡ Laptop nhôm",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/88/Cozistyle_Stand_Sleeve.jpg/960px-Cozistyle_Stand_Sleeve.jpg",
    },
    "headphones": {
        "label": "Tai nghe Bluetooth chụp tai",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/1/18/Apple_AirPods_Max_3.jpg/960px-Apple_AirPods_Max_3.jpg",
    },
    "speaker": {
        "label": "Loa mini để bàn",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/8c/BOSE_SoundLink_mini.jpg/960px-BOSE_SoundLink_mini.jpg",
    },
    "cleaning_kit": {
        "label": "Bộ vệ sinh Laptop & Bàn phím",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a8/Keyboard_cleaner3.jpg/960px-Keyboard_cleaner3.jpg",
    },
    "cooling_fan": {
        "label": "Quạt tản nhiệt PC 12V",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/cf/Corsair_Logo_120mm_desktop_computer_case_fan_%2852504601012%29.jpg/960px-Corsair_Logo_120mm_desktop_computer_case_fan_%2852504601012%29.jpg",
    },
    "switch": {
        "label": "Switch bàn phím cơ",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/e/e4/Cherry_MX_Blue_Switches.jpg/960px-Cherry_MX_Blue_Switches.jpg",
    },
    "serum": {
        "label": "Serum dưỡng da",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/99/Optical_caustic_Cosmetic_oil_bottle_in_the_sun_mj.jpg/960px-Optical_caustic_Cosmetic_oil_bottle_in_the_sun_mj.jpg",
    },
    "charger": {
        "label": "Củ sạc nhanh & Phụ kiện",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ae/Phone_charger_2026.jpg/960px-Phone_charger_2026.jpg",
    },
    "tumbler": {
        "label": "Gia dụng & Bình giữ nhiệt",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3b/Thermos_%28PSF%29.png/960px-Thermos_%28PSF%29.png",
    },
    "handbag": {
        "label": "Thời trang & Túi xách",
        "url": "https://upload.wikimedia.org/wikipedia/commons/7/7d/1935-45_Prada_handbag%2C_tooled_and_gilded_leather_02.jpg",
    },
    "default": {
        "label": "Sản phẩm TMĐT",
        "url": "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/cc/Desk_Setup_%28Unsplash%29.jpg/960px-Desk_Setup_%28Unsplash%29.jpg",
    },
}

QUICK_PRESETS: dict[str, dict[str, str]] = {
    "seeding": {
        "title": "Bẫy sao ảo · 4.9★",
        "payload": json.dumps(
            {
                "product_name": "Tai nghe Bluetooth X100 Chống Ồn",
                "category": "phu_kien_dien_tu",
                "platform": "Shopee",
                "platform_rating": 4.9,
                "reviews": [
                    {"id": "r1", "rating": 5, "text": "Giao hàng nhanh, chưa dùng nhưng cho shop 5 sao lấy xu"},
                    {"id": "r2", "rating": 5, "text": "Hàng đóng gói rất đẹp, shop tư vấn nhiệt tình, xứng đáng 1000 sao"},
                    {"id": "r3", "rating": 5, "text": "Hàng đóng gói rất đẹp, shop tư vấn nhiệt tình, xứng đáng 1000 sao"},
                    {"id": "r4", "rating": 2, "text": "Pin dùng thực tế chỉ được khoảng 1.5 tiếng là tụt sạch, mic gọi ngoài đường bị rè."},
                    {"id": "r5", "rating": 1, "text": "Kết nối Bluetooth hay bị ngắt quãng khi đi xa điện thoại hơn 3 mét, nhựa vỏ hơi ọp ẹp."},
                    {"id": "r6", "rating": 5, "text": "Nhận hàng rồi để đây nhận xu nhé shop ơi."},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
    },
    "shipper": {
        "title": "Oan shipper · 3.4★",
        "payload": json.dumps(
            {
                "product_name": "Serum Vitamin C Dưỡng Sáng 30ml",
                "category": "my_pham",
                "platform": "Shopee",
                "platform_rating": 3.4,
                "reviews": [
                    {"id": "r1", "rating": 5, "text": "Chất serum thấm nhanh, không nhờn rít, dùng 2 tuần thấy da đều màu hơn rõ rệt."},
                    {"id": "r2", "rating": 5, "text": "Lọ thủy tinh tối màu cầm chắc tay, vòi nhỏ giọt kín, mùi cam nhẹ dễ chịu."},
                    {"id": "r3", "rating": 1, "text": "Shipper giao hàng trễ 4 ngày, gọi không thèm báo trước, thái độ rất khó chịu."},
                    {"id": "r4", "rating": 1, "text": "Đơn vị vận chuyển làm móp nát vỏ thùng carton bên ngoài, giao quá chậm."},
                    {"id": "r5", "rating": 5, "text": "Da nhạy cảm dùng không bị châm chích, sáng ngủ dậy thấy da ẩm mịn."},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
    },
    "refusal_link": {
        "title": "Chặn link sàn",
        "payload": "Hãy vào link https://shopee.vn/product/123456789/987654321 cào toàn bộ review và chấm điểm giúp mình",
    },
}


def _svg_icon(name: str, size: int = 16) -> str:
    """Bộ icon vector đồng nhất nét 1.85px (không dùng emoji thay thế icon)."""
    paths = {
        "check": '<circle cx="12" cy="12" r="9"/><path d="M8.5 12.2l2.3 2.4 4.8-5.1"/>',
        "alert": '<path d="M12 3.5L21 19.5H3L12 3.5Z"/><path d="M12 10v4.2"/><circle cx="12" cy="16.8" r="0.7" fill="currentColor" stroke="none"/>',
        "shield_x": '<path d="M12 3l7.5 2.8v6.1c0 4.9-3.2 8.3-7.5 9.6-4.3-1.3-7.5-4.7-7.5-9.6V5.8L12 3z"/><path d="M9.4 9.6l5.2 5.2M14.6 9.6l-5.2 5.2"/>',
        "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11.2v4.8"/><circle cx="12" cy="8" r="0.8" fill="currentColor" stroke="none"/>',
        "risk": '<path d="M12 3.5L21 19.5H3L12 3.5Z"/><path d="M12 9.5v4.5"/><circle cx="12" cy="16.8" r="0.7" fill="currentColor" stroke="none"/>',
        "chat": '<path d="M4.5 6.5h15a1.5 1.5 0 0 1 1.5 1.5v8a1.5 1.5 0 0 1-1.5 1.5H10l-4.5 3v-3H4.5A1.5 1.5 0 0 1 3 16V8a1.5 1.5 0 0 1 1.5-1.5z"/><path d="M8 11h8M8 14h5"/>',
        "shield_ok": '<path d="M12 3l7.5 2.8v6.1c0 4.9-3.2 8.3-7.5 9.6-4.3-1.3-7.5-4.7-7.5-9.6V5.8L12 3z"/><path d="M9 12.2l2.1 2.1 4.1-4.3"/>',
        "bag": '<path d="M6 8h12l-1 12H7L6 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>',
        "layers": '<path d="M12 4l8.5 4.5L12 13 3.5 8.5 12 4z"/><path d="M3.5 12.5L12 17l8.5-4.5"/><path d="M3.5 16.5L12 21l8.5-4.5"/>',
        "cpu": '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="0.8"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5V12l3.2 2"/>',
        "eye": '<path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
        "star": '<path d="M12 2.8l2.8 5.7 6.3.9-4.5 4.4 1.1 6.3L12 17.1 6.3 20.1l1.1-6.3-4.5-4.4 6.3-.9L12 2.8z" fill="currentColor" stroke="none"/>',
    }
    inner = paths.get(name, paths["info"])
    return (
        f'<svg class="rs-ic" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="1.85" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f"{inner}</svg>"
    )


def _render_stars_svg(rating: float | int | None, size: int = 12) -> str:
    """Render dãy 5 ngôi sao vàng vector gọn gàng chuẩn giao diện sàn TMĐT."""
    if not isinstance(rating, (int, float)):
        return ""
    filled = max(0, min(5, int(round(float(rating)))))
    parts = []
    for idx in range(5):
        cls = "rs-star-on" if idx < filled else "rs-star-off"
        parts.append(
            f'<svg class="{cls}" width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M12 2.8l2.8 5.7 6.3.9-4.5 4.4 1.1 6.3L12 17.1 6.3 20.1l1.1-6.3-4.5-4.4 6.3-.9L12 2.8z"/>'
            "</svg>"
        )
    return f'<span class="rs-stars" aria-label="{filled} trên 5 sao">{"".join(parts)}</span>'


def _natural_sort_key(path: str) -> list[Any]:
    """Sắp xếp tên file tự nhiên (sp_2 trước sp_10)."""
    base = os.path.basename(path)
    return [int(tok) if tok.isdigit() else tok.lower() for tok in re.split(r"(\d+)", base)]


def _pick_preview_reviews(reviews_raw: list[Any], limit: int = 3) -> list[dict[str, Any]]:
    """Chọn tối đa `limit` câu review tiêu biểu (pha lẫn sao cao & sao thấp) để xem trước ở trạng thái chờ."""
    valid: list[dict[str, Any]] = []
    for i, r in enumerate(reviews_raw or [], start=1):
        if not isinstance(r, dict):
            continue
        txt = str(r.get("text") or "").strip()
        if not txt:
            continue
        valid.append(
            {
                "id": str(r.get("id") or f"r{i}"),
                "author": str(r.get("author") or f"user_{i:02d}"),
                "rating": r.get("rating"),
                "text": txt,
            }
        )
    if len(valid) <= limit:
        return valid

    picked: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    high = next((r for r in valid if isinstance(r.get("rating"), (int, float)) and r["rating"] >= 4), None)
    low = next((r for r in valid if isinstance(r.get("rating"), (int, float)) and r["rating"] <= 2), None)
    for item in (high, low):
        if item and item["id"] not in used_ids:
            picked.append(item)
            used_ids.add(item["id"])
    for item in valid:
        if len(picked) >= limit:
            break
        if item["id"] not in used_ids:
            picked.append(item)
            used_ids.add(item["id"])
    return picked[:limit]


def _short_product_chip(name: str, max_len: int = 18) -> str:
    """Rút gọn tên sản phẩm gọn gàng cho nút chọn nhanh."""
    clean = re.sub(r"\s+", " ", (name or "").strip())
    if len(clean) <= max_len:
        return clean
    return clean[: max_len - 1].rstrip() + "…"


def load_sample_files(samples_dir: str = SAMPLES_DIR) -> list[dict[str, Any]]:
    """Quét động toàn bộ `data/samples/*.json`, không hardcode tên file và không crash khi rỗng."""
    if not os.path.isdir(samples_dir):
        return []

    items: list[dict[str, Any]] = []
    pattern = os.path.join(samples_dir, "*.json")
    for file_path in sorted(glob.glob(pattern), key=_natural_sort_key):
        try:
            with open(file_path, encoding="utf-8-sig") as f:
                raw_text = f.read()
            parsed = json.loads(raw_text)
        except Exception:
            continue
        if not isinstance(parsed, dict) or not isinstance(parsed.get("reviews"), list):
            continue

        product_id = str(parsed.get("product_id") or os.path.splitext(os.path.basename(file_path))[0])
        product_name = str(parsed.get("product_name") or product_id).strip()
        platform = str(parsed.get("platform") or "Shopee").strip()
        category = str(parsed.get("category") or "").strip()
        platform_rating = parsed.get("platform_rating")
        image_url = str(parsed.get("image_url") or "").strip()
        raw_reviews = parsed.get("reviews") or []
        review_count = len(raw_reviews)

        clean_reviews = [
            {
                "id": r.get("id", f"r{i}"),
                "author": r.get("author", f"user_{i:02d}"),
                "rating": r.get("rating"),
                "text": r.get("text", ""),
            }
            for i, r in enumerate(raw_reviews, start=1)
            if isinstance(r, dict)
        ]
        clean_payload = {
            "product_id": product_id,
            "product_name": product_name,
            "category": category,
            "platform": platform,
            "platform_rating": platform_rating,
            "reviews": clean_reviews,
        }
        items.append(
            {
                "product_id": product_id,
                "product_name": product_name,
                "platform": platform,
                "category": category,
                "platform_rating": platform_rating,
                "image_url": image_url,
                "review_count": review_count,
                "preview_reviews": _pick_preview_reviews(clean_reviews, limit=3),
                "file_name": os.path.basename(file_path),
                "payload_json": json.dumps(clean_payload, ensure_ascii=False, indent=2),
            }
        )
    return items


def detect_product_photo_key(product_name: str = "", category: str = "") -> str:
    """Tự động nhận diện loại sản phẩm từ tên và ngành hàng để chọn ảnh thật tương ứng."""
    combined = unicodedata.normalize("NFC", f"{product_name} {category}").lower()

    if any(k in combined for k in ("vệ sinh laptop", "dụng cụ vệ sinh", "bộ vệ sinh")):
        return "cleaning_kit"
    if any(k in combined for k in ("switch", "outemu", "cherry mx", "công tắc bàn phím")):
        return "switch"
    if any(k in combined for k in ("lót chuột", "pad chuột", "mousepad")):
        return "mousepad"
    if any(k in combined for k in ("bàn phím", "keyboard")):
        return "keyboard"
    if any(k in combined for k in ("chuột", "mouse", "g304", "g305")):
        return "mouse"
    if any(k in combined for k in ("giá đỡ laptop", "giá đỡ", "laptop stand")):
        return "laptop_stand"
    if any(k in combined for k in ("quạt tản nhiệt", "quạt làm mát", "cooling fan")):
        return "cooling_fan"
    if any(k in combined for k in ("usb", "ổ đĩa", "flash drive", "pendrive")):
        return "usb"
    if any(k in combined for k in ("loa ", "loa máy", "speaker", "soundlink")):
        return "speaker"
    if any(k in combined for k in ("tai nghe", "headphone", "earbud", "airpod", "thinkplus")):
        return "headphones"
    if any(k in combined for k in ("serum", "mỹ phẩm", "my_pham", "kem ", "nước hoa", "toner", "sữa rửa mặt", "chống nắng", "son ", "skincare")):
        return "serum"
    if any(k in combined for k in ("củ sạc", "sạc nhanh", "cáp sạc", "pin dự phòng", "adapter", "hub")):
        return "charger"
    if any(k in combined for k in ("gia dụng", "gia_dung", "bình giữ nhiệt", "máy xay", "ấm siêu tốc", "nồi", "đèn bàn", "quạt mini")):
        return "tumbler"
    if any(k in combined for k in ("thời trang", "thoi_trang", "túi", "balo", "áo ", "quần ", "giày", "dép", "váy", "ví ")):
        return "handbag"
    if any(k in combined for k in ("phu_kien_dien_tu", "phụ kiện")):
        return "charger"
    return "default"


def resolve_product_photo(
    photo_key: str,
    custom_image_url: str = "",
) -> tuple[str, str]:
    """Trả về `(image_url, category_label)` an toàn (chỉ chấp nhận URL http/https hợp lệ)."""
    meta = PRODUCT_PHOTO_CATALOG.get(photo_key, PRODUCT_PHOTO_CATALOG["default"])
    custom = (custom_image_url or "").strip()
    if custom.startswith(("https://", "http://")):
        return custom, meta["label"]
    return meta["url"], meta["label"]


def infer_meta_from_raw_input(raw_text: str) -> dict[str, Any]:
    """Trích nhanh siêu dữ liệu sản phẩm và review xem trước từ JSON hoặc văn bản dán tay."""
    text = (raw_text or "").strip()
    if text.startswith("{"):
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                reviews = obj.get("reviews") if isinstance(obj.get("reviews"), list) else []
                return {
                    "product_id": str(obj.get("product_id") or "Tùy chỉnh"),
                    "product_name": str(obj.get("product_name") or "Đánh giá dán trực tiếp").strip(),
                    "category": str(obj.get("category") or "").strip(),
                    "platform": str(obj.get("platform") or "Shopee").strip(),
                    "platform_rating": obj.get("platform_rating"),
                    "review_count": len(reviews),
                    "preview_reviews": _pick_preview_reviews(reviews, limit=3),
                    "image_url": str(obj.get("image_url") or "").strip(),
                }
        except Exception:
            pass

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    parsed_previews: list[dict[str, Any]] = []
    for idx, ln in enumerate(lines[:3], start=1):
        m = re.match(r"^\[?([1-5])\]?\s*(?:sao|★|\*)?[\s:\-–—]+(.+)$", ln, flags=re.IGNORECASE)
        if m:
            parsed_previews.append({"id": f"r{idx}", "author": f"user_{idx:02d}", "rating": int(m.group(1)), "text": m.group(2).strip()})
        else:
            parsed_previews.append({"id": f"r{idx}", "author": f"user_{idx:02d}", "rating": None, "text": ln})
    return {
        "product_id": "Văn bản tay",
        "product_name": lines[0][:80] if lines else "Chưa nhập đánh giá",
        "category": "",
        "platform": "Dán trực tiếp",
        "platform_rating": None,
        "review_count": len(lines),
        "preview_reviews": parsed_previews,
        "image_url": "",
    }


def highlight_quote_html(orig_text: str, quote: str, mark_class: str = "mark-coin") -> str:
    """Tô sáng nguyên văn `evidence_quote` bên trong `orig_text` (chống XSS, chuẩn hóa NFC)."""
    orig_nfc = unicodedata.normalize("NFC", orig_text or "")
    quote_nfc = unicodedata.normalize("NFC", quote or "").strip()
    valid_marks = ("mark-mint", "mark-coin", "mark-coral", "mark-sky")
    safe_cls = mark_class if mark_class in valid_marks else "mark-coin"
    if not orig_nfc:
        return f'<mark class="{safe_cls}">{html.escape(quote_nfc)}</mark>' if quote_nfc else ""
    if not quote_nfc:
        return html.escape(orig_nfc)

    tokens = quote_nfc.split()
    pattern = r"\s+".join(re.escape(tok) for tok in tokens)
    match = re.search(pattern, orig_nfc, flags=re.IGNORECASE)
    if not match:
        return html.escape(orig_nfc)

    before = html.escape(orig_nfc[: match.start()])
    matched = html.escape(orig_nfc[match.start() : match.end()])
    after = html.escape(orig_nfc[match.end() :])
    return f'{before}<mark class="{safe_cls}">{matched}</mark>{after}'


def compute_weight_breakdown(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    """Tính bảng minh bạch công thức WEIGHT_MAP (khớp 100% codebase/tools.py)."""
    rows: list[dict[str, Any]] = []
    total_weighted_sum = 0.0
    total_weight = 0.0
    total_reviews = 0

    for label, weight in WEIGHT_MAP.items():
        group = [
            r
            for r in (reviews or [])
            if isinstance(r, dict)
            and r.get("label") == label
            and isinstance(r.get("rating"), (int, float))
        ]
        count = len(group)
        total_reviews += count
        avg_rating = round(sum(float(r["rating"]) for r in group) / count, 2) if count else None
        group_weight = round(count * weight, 2)
        group_weighted_sum = round(sum(float(r["rating"]) * weight for r in group), 2)
        total_weight += count * weight
        total_weighted_sum += sum(float(r["rating"]) * weight for r in group)
        rows.append(
            {
                "label": label,
                "name": LABEL_META[label]["name"],
                "weight": weight,
                "count": count,
                "avg_rating": avg_rating,
                "group_weight": group_weight,
                "group_weighted_sum": group_weighted_sum,
            }
        )

    return {
        "rows": rows,
        "total_reviews": total_reviews,
        "total_weight": round(total_weight, 2),
        "total_weighted_sum": round(total_weighted_sum, 2),
        "computed_score": round(total_weighted_sum / total_weight, 1) if total_weight > 0 else None,
    }


def _safe_anchor_id(raw_id: str) -> str:
    """Chuẩn hóa mã review thành HTML anchor ID an toàn (`rev-r4`)."""
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", str(raw_id or ""))
    return f"rev-{cleaned}" if cleaned else "rev-item"


def build_animated_logo_svg(size: int = 46) -> str:
    """Logo khiên mua sắm ReviewShield đa lớp chuyển động (Cam san hô TMĐT, vàng xu, dấu tích bạc hà & ánh quét)."""
    return (
        f'<div class="rs-logo-stage" style="width:{size}px;height:{size}px;" aria-hidden="true">'
        f'<svg class="rs-logo-svg" width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">'
        "<defs>"
        '<clipPath id="rsShopShieldClip">'
        '<path d="M32 10L49 16.5V31.5C49 43 41.6 51.2 32 54.6C22.4 51.2 15 43 15 31.5V16.5L32 10Z"/>'
        "</clipPath>"
        '<linearGradient id="rsShopShieldGrad" x1="15" y1="10" x2="49" y2="54" gradientUnits="userSpaceOnUse">'
        '<stop offset="0%" stop-color="#F25C38"/>'
        '<stop offset="58%" stop-color="#DC3F22"/>'
        '<stop offset="100%" stop-color="#A82716"/>'
        "</linearGradient>"
        '<linearGradient id="rsShopSheen" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="#FFF5EE" stop-opacity="0"/>'
        '<stop offset="50%" stop-color="#FFF5EE" stop-opacity="0.46"/>'
        '<stop offset="100%" stop-color="#FFF5EE" stop-opacity="0"/>'
        "</linearGradient>"
        "</defs>"
        '<g class="rs-logo-outer-ring">'
        '<circle cx="32" cy="32" r="29.4" stroke="rgba(220, 63, 34, 0.28)" stroke-width="1.25" stroke-dasharray="4 5"/>'
        '<circle cx="32" cy="2.6" r="2.3" fill="#F25C38"/>'
        '<circle cx="61.4" cy="32" r="1.9" fill="#F59E0B"/>'
        '<circle cx="32" cy="61.4" r="1.9" fill="#0FA968"/>'
        '<circle cx="2.6" cy="32" r="1.7" fill="#1E88E5"/>'
        "</g>"
        '<g class="rs-logo-inner-ring">'
        '<circle cx="32" cy="32" r="24.4" stroke="rgba(245, 158, 11, 0.34)" stroke-width="1.05" stroke-dasharray="13 11"/>'
        '<circle cx="49.2" cy="14.8" r="1.9" fill="#FFC44D"/>'
        "</g>"
        '<circle class="rs-logo-pulse" cx="32" cy="32" r="20.6" stroke="#F25C38" stroke-width="1.35"/>'
        '<path class="rs-logo-body" d="M32 10L49 16.5V31.5C49 43 41.6 51.2 32 54.6C22.4 51.2 15 43 15 31.5V16.5L32 10Z" '
        'fill="url(#rsShopShieldGrad)" stroke="#FFF8F3" stroke-width="1.5" stroke-linejoin="round"/>'
        '<path d="M32 14L45.4 19.2V31.2C45.4 40.4 39.5 47.2 32 50.2C24.5 47.2 18.6 40.4 18.6 31.2V19.2L32 14Z" '
        'stroke="#FFD9C8" stroke-opacity="0.45" stroke-width="1" stroke-linejoin="round"/>'
        '<g clip-path="url(#rsShopShieldClip)">'
        '<rect class="rs-logo-sheen" x="-26" y="6" width="24" height="54" fill="url(#rsShopSheen)"/>'
        "</g>"
        '<path class="rs-logo-check" d="M24 32.4L29.6 38L41.4 25.8" '
        'stroke="#FFFDFB" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle class="rs-logo-dot" cx="42.4" cy="21.2" r="2.2" fill="#FFE07D"/>'
        "</svg>"
        "</div>"
    )


def _render_ambient_backdrop_html() -> str:
    """Nền đen nhung tĩnh lặng chỉ giữ 2 vầng sáng ấm dịu để tôn nổi sợi chỉ cuộn Lusion."""
    return (
        '<div class="rs-bg-stage" aria-hidden="true">'
        '<div class="rs-bg-orb rs-orb-sunset"></div>'
        '<div class="rs-bg-orb rs-orb-warm"></div>'
        "</div>"
    )


def _build_lusion_thread_and_intro_bridge_html(
    intro_nonce: int,
    is_replay: bool = False,
) -> str:
    """Cầu JS gọn (height=0) nạp runtime trực tiếp vào `window.parent` (sống bền qua mọi lần rerun Streamlit):
    1. Sợi chỉ lụa kéo dài theo con lăn kiểu Lusion.co — chạy hoàn toàn trong realm của trang chính,
       không bao giờ bị đóng băng khi bấm 'Soi đánh giá ngay' hay chuyển mẫu/tab.
    2. Màn Intro ~3.2s kể chuyện quét sao ảo (4.9★ → 2.6★) chung nền đen + sợi chỉ, kèm nút Bỏ qua (Esc).
    """
    runtime_ver = "rs-noir-thread-v3"
    cfg_js = json.dumps(
        {
            "nonce": int(intro_nonce),
            "isReplay": bool(is_replay),
            "ver": runtime_ver,
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    parent_runtime_src = r"""
(function() {
  const WIN = window;
  const DOC = document;
  const RUNTIME_VER = "rs-noir-thread-v3";
  WIN.__rsRuntimeVer = RUNTIME_VER;

  const reduceMotion = !!(WIN.matchMedia && WIN.matchMedia('(prefers-reduced-motion: reduce)').matches);
  const finePointer = !!(WIN.matchMedia && WIN.matchMedia('(hover: hover) and (pointer: fine)').matches);

  /* =========================================================================
     1. SỢI CHỈ LỤA KÉO DÀI THEO CON LĂN KIỂU LUSION.CO (PARENT-REALM RUNTIME)
     ========================================================================= */
  WIN.__rsEnsureLusionThread = function() {
    const CANVAS_ID = 'rs-lusion-thread-canvas';
    if (WIN.__rsLusionThread && WIN.__rsLusionThread.alive && WIN.__rsLusionThread.ver === RUNTIME_VER && DOC.getElementById(CANVAS_ID)) {
      return;
    }
    if (WIN.__rsLusionThread && typeof WIN.__rsLusionThread.destroy === 'function') {
      WIN.__rsLusionThread.destroy();
    }

    let canvas = DOC.getElementById(CANVAS_ID);
    if (!canvas) {
      canvas = DOC.createElement('canvas');
      canvas.id = CANVAS_ID;
      Object.assign(canvas.style, {
        position: 'fixed',
        inset: '0',
        width: '100vw',
        height: '100vh',
        zIndex: '1',
        pointerEvents: 'none',
        display: 'block',
      });
      DOC.body.appendChild(canvas);
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const st = {
      alive: true,
      ver: RUNTIME_VER,
      rafId: null,
      w: WIN.innerWidth || 1280,
      h: WIN.innerHeight || 800,
      dpr: Math.min(WIN.devicePixelRatio || 1, 2),
      targetProgress: 0.28,
      currentProgress: 0.28,
      virtualScroll: 0.0,
      mouseX: 0.5,
      mouseY: 0.35,
      smoothMouseX: 0.5,
      smoothMouseY: 0.35,
      t: 0,
      destroy: null,
    };

    function resize() {
      st.w = WIN.innerWidth || 1280;
      st.h = WIN.innerHeight || 800;
      st.dpr = Math.min(WIN.devicePixelRatio || 1, 2);
      canvas.width = Math.floor(st.w * st.dpr);
      canvas.height = Math.floor(st.h * st.dpr);
      ctx.setTransform(st.dpr, 0, 0, st.dpr, 0, 0);
    }

    function readScrollProgress() {
      const candidates = [
        DOC.querySelector('section[data-testid="stMain"]'),
        DOC.querySelector('[data-testid="stAppViewContainer"]'),
        DOC.querySelector('.main'),
        DOC.scrollingElement,
        DOC.documentElement,
        DOC.body,
      ];
      let bestRatio = null;
      let maxRange = 0;
      for (const el of candidates) {
        if (!el) continue;
        const range = (el.scrollHeight || 0) - (el.clientHeight || 0);
        if (range > maxRange && range > 50) {
          maxRange = range;
          bestRatio = Math.max(0, Math.min(1, (el.scrollTop || 0) / range));
        }
      }
      if (bestRatio === null) {
        const winMax = Math.max(0, (DOC.documentElement.scrollHeight || 0) - (WIN.innerHeight || 0));
        if (winMax > 50) {
          bestRatio = Math.max(0, Math.min(1, (WIN.scrollY || 0) / winMax));
        }
      }
      if (bestRatio !== null) {
        st.virtualScroll = bestRatio;
        st.targetProgress = 0.24 + bestRatio * 0.76;
      } else {
        st.targetProgress = 0.24 + st.virtualScroll * 0.76;
      }
    }

    function onWheel(ev) {
      const delta = (ev.deltaY || 0) * 0.00085;
      st.virtualScroll = Math.max(0, Math.min(1, st.virtualScroll + delta));
      readScrollProgress();
    }

    function onPointerMove(ev) {
      if (!finePointer) return;
      st.mouseX = Math.max(0, Math.min(1, ev.clientX / Math.max(1, st.w)));
      st.mouseY = Math.max(0, Math.min(1, ev.clientY / Math.max(1, st.h)));
    }

    function catmullRom(p0, p1, p2, p3, t) {
      const t2 = t * t;
      const t3 = t2 * t;
      return 0.5 * (
        (2 * p1) +
        (-p0 + p2) * t +
        (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
        (-p0 + 3 * p1 - 3 * p2 + p3) * t3
      );
    }

    function sampleCurve(u, time) {
      const w = st.w;
      const h = st.h;
      const mx = (st.smoothMouseX - 0.5) * 44;
      const my = (st.smoothMouseY - 0.5) * 28;
      const drift = reduceMotion ? 0 : Math.sin(time * 0.9) * 10;

      const pts = [
        { x: w * 0.06, y: -h * 0.06 },
        { x: w * 0.14, y: h * 0.04 },
        { x: w * 0.87 + mx * 0.5, y: h * 0.24 + my * 0.4 + drift },
        { x: w * 0.11 - mx * 0.6, y: h * 0.50 - my * 0.4 - drift * 0.8 },
        { x: w * 0.88 + mx * 0.5, y: h * 0.76 + my * 0.5 + drift * 0.7 },
        { x: w * 0.48 + mx * 0.2, y: h * 0.98 },
        { x: w * 0.52, y: h * 1.12 },
      ];

      const segCount = pts.length - 3;
      const scaled = Math.max(0, Math.min(segCount - 0.0001, u * segCount));
      const seg = Math.floor(scaled);
      const localT = scaled - seg;
      const p0 = pts[seg], p1 = pts[seg + 1], p2 = pts[seg + 2], p3 = pts[seg + 3];
      return {
        x: catmullRom(p0.x, p1.x, p2.x, p3.x, localT),
        y: catmullRom(p0.y, p1.y, p2.y, p3.y, localT),
      };
    }

    function drawFrame() {
      if (!st.alive) return;
      if (!DOC.getElementById(CANVAS_ID)) {
        st.destroy();
        return;
      }

      readScrollProgress();
      st.currentProgress += (st.targetProgress - st.currentProgress) * (reduceMotion ? 0.35 : 0.085);
      st.smoothMouseX += (st.mouseX - st.smoothMouseX) * 0.06;
      st.smoothMouseY += (st.mouseY - st.smoothMouseY) * 0.06;
      if (!reduceMotion) st.t += 0.016;

      ctx.clearRect(0, 0, st.w, st.h);

      const steps = 120;
      const maxStep = Math.max(8, Math.floor(steps * st.currentProgress));
      const mainPts = [];
      for (let i = 0; i <= maxStep; i++) {
        const u = i / steps;
        mainPts.push(sampleCurve(u, st.t));
      }

      if (mainPts.length > 2) {
        const gradMain = ctx.createLinearGradient(0, 0, st.w * 0.85, st.h);
        gradMain.addColorStop(0.0, 'rgba(255, 92, 53, 0.90)');
        gradMain.addColorStop(0.55, 'rgba(255, 148, 114, 0.78)');
        gradMain.addColorStop(1.0, 'rgba(255, 224, 210, 0.72)');

        const gradGlow = ctx.createLinearGradient(0, 0, st.w * 0.85, st.h);
        gradGlow.addColorStop(0.0, 'rgba(255, 92, 53, 0.16)');
        gradGlow.addColorStop(0.6, 'rgba(255, 148, 114, 0.11)');
        gradGlow.addColorStop(1.0, 'rgba(255, 224, 210, 0.08)');

        ctx.save();
        ctx.beginPath();
        ctx.moveTo(mainPts[0].x, mainPts[0].y);
        for (let i = 1; i < mainPts.length; i++) ctx.lineTo(mainPts[i].x, mainPts[i].y);
        ctx.strokeStyle = gradGlow;
        ctx.lineWidth = 22;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(mainPts[0].x, mainPts[0].y);
        for (let i = 1; i < mainPts.length; i++) ctx.lineTo(mainPts[i].x, mainPts[i].y);
        ctx.strokeStyle = gradMain;
        ctx.lineWidth = 4.2;
        ctx.stroke();

        ctx.beginPath();
        for (let i = 0; i < mainPts.length; i++) {
          const u = i / steps;
          const wave = Math.sin(u * 24 - st.t * 1.9) * (7.5 + u * 3.5);
          const waveY = Math.cos(u * 20 - st.t * 1.5) * 4.5;
          const px = mainPts[i].x + wave;
          const py = mainPts[i].y + waveY;
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.strokeStyle = 'rgba(255, 232, 220, 0.34)';
        ctx.lineWidth = 1.4;
        ctx.stroke();

        const tip = mainPts[mainPts.length - 1];
        const pulseR = reduceMotion ? 10 : 10 + Math.sin(st.t * 3.0) * 3.0;
        const tipGrad = ctx.createRadialGradient(tip.x, tip.y, 1, tip.x, tip.y, pulseR + 8);
        tipGrad.addColorStop(0, 'rgba(255, 255, 255, 0.96)');
        tipGrad.addColorStop(0.4, 'rgba(255, 118, 84, 0.65)');
        tipGrad.addColorStop(1, 'rgba(255, 92, 53, 0)');
        ctx.fillStyle = tipGrad;
        ctx.beginPath();
        ctx.arc(tip.x, tip.y, pulseR + 8, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(tip.x, tip.y, 3.6, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      st.rafId = WIN.requestAnimationFrame(drawFrame);
    }

    st.destroy = function() {
      st.alive = false;
      if (st.rafId) WIN.cancelAnimationFrame(st.rafId);
      WIN.removeEventListener('resize', resize);
      WIN.removeEventListener('wheel', onWheel);
      WIN.removeEventListener('scroll', readScrollProgress, true);
      DOC.removeEventListener('pointermove', onPointerMove);
    };

    WIN.__rsLusionThread = st;
    resize();
    WIN.addEventListener('resize', resize, { passive: true });
    WIN.addEventListener('wheel', onWheel, { passive: true });
    WIN.addEventListener('scroll', readScrollProgress, { passive: true, capture: true });
    DOC.addEventListener('pointermove', onPointerMove, { passive: true });
    st.rafId = WIN.requestAnimationFrame(drawFrame);
  };

  /* =========================================================================
     2. MÀN INTRO ~3.2s KỂ CHUYỆN QUÉT SAO ẢO (PARENT-REALM RUNTIME)
     ========================================================================= */
  WIN.__rsPlayStoryIntro = function(nonce, isReplay) {
    const lastPlayed = WIN.__rsPlayedIntroNonce || 0;
    if (nonce <= lastPlayed) return;
    WIN.__rsPlayedIntroNonce = nonce;

    if (reduceMotion && !isReplay) return;

    const STYLE_ID = 'rs-intro-style-dark';
    const oldLightStyle = DOC.getElementById('rs-intro-style');
    if (oldLightStyle) oldLightStyle.remove();
    if (!DOC.getElementById(STYLE_ID)) {
      const styleEl = DOC.createElement('style');
      styleEl.id = STYLE_ID;
      styleEl.textContent = `
        @keyframes rsIntroThreadDraw {
          from { stroke-dashoffset: 1800; }
          to { stroke-dashoffset: 0; }
        }
        @keyframes rsIntroSweep {
          0% { transform: translateX(-110%) skewX(-16deg); opacity: 0; }
          15% { opacity: 1; }
          85% { opacity: 1; }
          100% { transform: translateX(220%) skewX(-16deg); opacity: 0; }
        }
        @keyframes rsIntroCardIn {
          from { opacity: 0; transform: translateY(14px) scale(0.96); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes rsIntroChipIn {
          from { opacity: 0; transform: translateY(8px) scale(0.96); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes rsIntroProgress {
          from { transform: scaleX(0); }
          to { transform: scaleX(1); }
        }
        #rs-intro-overlay {
          position: fixed; inset: 0; z-index: 999999;
          display: flex; align-items: center; justify-content: center;
          padding: 24px;
          font-family: 'Be Vietnam Pro', system-ui, sans-serif;
          background:
            radial-gradient(54% 50% at 12% 14%, rgba(255, 92, 53, 0.14), transparent 64%),
            radial-gradient(48% 46% at 88% 86%, rgba(255, 170, 128, 0.08), transparent 64%),
            #09090B;
          transition: opacity 380ms cubic-bezier(0.23, 1, 0.32, 1), transform 380ms cubic-bezier(0.23, 1, 0.32, 1);
          overflow: hidden;
        }
        #rs-intro-overlay.rs-intro-exit {
          opacity: 0;
          transform: scale(1.025);
          pointer-events: none;
        }
        .rs-intro-svg-bg { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; }
        .rs-intro-thread-path {
          stroke-dasharray: 1800;
          stroke-dashoffset: 1800;
          animation: rsIntroThreadDraw 2.7s cubic-bezier(0.23, 1, 0.32, 1) forwards;
        }
        .rs-intro-skip {
          position: fixed; top: 22px; right: 24px; z-index: 5;
          display: inline-flex; align-items: center; gap: 7px;
          padding: 8px 16px; border-radius: 999px;
          background: rgba(24, 24, 28, 0.88);
          border: 1px solid rgba(255, 255, 255, 0.18);
          color: #FAFAFA; font-size: 13px; font-weight: 700; cursor: pointer;
          box-shadow: 0 10px 24px -10px rgba(0, 0, 0, 0.65);
          transition: transform 150ms cubic-bezier(0.23, 1, 0.32, 1), border-color 160ms cubic-bezier(0.23, 1, 0.32, 1);
        }
        .rs-intro-skip:active { transform: scale(0.97); }
        .rs-intro-skip:focus-visible { outline: 2px solid #FF5C35; outline-offset: 2px; }
        @media (hover: hover) and (pointer: fine) {
          .rs-intro-skip:hover { border-color: #FF5C35; }
        }
        .rs-intro-card {
          position: relative; z-index: 3;
          width: min(620px, 100%);
          background: rgba(18, 18, 21, 0.88);
          backdrop-filter: blur(24px);
          -webkit-backdrop-filter: blur(24px);
          border: 1px solid rgba(255, 255, 255, 0.11);
          border-radius: 24px;
          padding: 28px 30px 24px 30px;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 32px 70px -24px rgba(0, 0, 0, 0.82);
          animation: rsIntroCardIn 360ms cubic-bezier(0.23, 1, 0.32, 1) both;
          overflow: hidden;
        }
        .rs-intro-beam {
          position: absolute; top: 0; bottom: 0; left: 0; width: 42%;
          background: linear-gradient(90deg, transparent, rgba(255, 92, 53, 0.18), rgba(52, 211, 153, 0.18), transparent);
          pointer-events: none;
          opacity: 0;
        }
        .rs-intro-beam.scan-on { animation: rsIntroSweep 1.25s cubic-bezier(0.23, 1, 0.32, 1) forwards; }
        .rs-intro-brand { display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 18px; }
        .rs-intro-brand-name {
          font-family: 'Plus Jakarta Sans', 'Be Vietnam Pro', sans-serif;
          font-size: 24px; font-weight: 800; letter-spacing: -0.03em; color: #FAFAFA;
        }
        .rs-intro-brand-sub { font-size: 12.5px; color: #93939E; font-weight: 500; }
        .rs-intro-stage {
          background: #101013;
          border: 1px solid rgba(255, 255, 255, 0.09);
          border-radius: 18px; padding: 20px 22px; color: #FAFAFA;
          display: grid; grid-template-columns: 1fr auto; gap: 14px; align-items: center;
          margin-bottom: 16px;
        }
        .rs-intro-score-lbl { font-size: 12px; color: #93939E; font-weight: 600; }
        .rs-intro-score-val {
          font-family: 'Plus Jakarta Sans', 'Be Vietnam Pro', sans-serif;
          font-variant-numeric: tabular-nums;
          font-size: 46px; font-weight: 800; letter-spacing: -0.035em; line-height: 1.04;
          color: #FAFAFA; margin: 4px 0;
          transition: color 260ms cubic-bezier(0.23, 1, 0.32, 1);
        }
        .rs-intro-score-val.is-real { color: #FF6B4A; }
        .rs-intro-verdict {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 6px 13px; border-radius: 999px;
          background: rgba(255, 255, 255, 0.07); color: #D4D4D8;
          border: 1px solid rgba(255, 255, 255, 0.14);
          font-size: 12.5px; font-weight: 700;
          transition: background-color 260ms cubic-bezier(0.23, 1, 0.32, 1), color 260ms cubic-bezier(0.23, 1, 0.32, 1), border-color 260ms cubic-bezier(0.23, 1, 0.32, 1);
        }
        .rs-intro-verdict.locked {
          background: rgba(52, 211, 153, 0.14); color: #34D399;
          border-color: rgba(52, 211, 153, 0.38);
        }
        .rs-intro-chips { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; margin-bottom: 16px; }
        @media (max-width: 560px) {
          .rs-intro-chips { grid-template-columns: 1fr; }
          .rs-intro-stage { grid-template-columns: 1fr; }
        }
        .rs-intro-chip {
          background: #17171B; border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 12px; padding: 10px 11px;
          animation: rsIntroChipIn 300ms cubic-bezier(0.23, 1, 0.32, 1) both;
          transition: opacity 280ms cubic-bezier(0.23, 1, 0.32, 1), transform 280ms cubic-bezier(0.23, 1, 0.32, 1), border-color 260ms cubic-bezier(0.23, 1, 0.32, 1);
        }
        .rs-intro-chip:nth-child(2) { animation-delay: 90ms; }
        .rs-intro-chip:nth-child(3) { animation-delay: 180ms; }
        .rs-intro-chip.filtered { opacity: 0.36; transform: scale(0.96); border-color: rgba(255, 92, 53, 0.28); }
        .rs-intro-chip-tag { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 999px; margin-bottom: 5px; }
        .tag-coin { background: rgba(234, 179, 8, 0.14); color: #EAB308; }
        .tag-coral { background: rgba(255, 107, 74, 0.15); color: #FF6B4A; }
        .tag-sky { background: rgba(122, 162, 196, 0.15); color: #7AA2C4; }
        .rs-intro-chip-txt { font-size: 12px; color: #D4D4D8; line-height: 1.38; }
        .rs-intro-chip.filtered .rs-intro-chip-txt { text-decoration: line-through; }
        .rs-intro-bar { height: 4px; border-radius: 999px; background: rgba(255, 255, 255, 0.08); overflow: hidden; }
        .rs-intro-bar-fill {
          height: 100%; width: 100%;
          background: linear-gradient(90deg, #FF5C35 0%, #FFAE8A 100%);
          transform-origin: left center;
          animation: rsIntroProgress 3.15s linear forwards;
        }
      `;
      DOC.head.appendChild(styleEl);
    }

    const old = DOC.getElementById('rs-intro-overlay');
    if (old) old.remove();

    const overlay = DOC.createElement('div');
    overlay.id = 'rs-intro-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-label', 'Giới thiệu ReviewShield');
    overlay.innerHTML = `
      <svg class="rs-intro-svg-bg" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" fill="none">
        <defs>
          <linearGradient id="rsIntroGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#FF5C35" stop-opacity="0.86"/>
            <stop offset="60%" stop-color="#FF9E7D" stop-opacity="0.70"/>
            <stop offset="100%" stop-color="#FFE4D6" stop-opacity="0.58"/>
          </linearGradient>
        </defs>
        <path class="rs-intro-thread-path" d="M-40 120 C 260 40, 420 340, 760 220 C 1060 110, 1220 440, 1500 320" stroke="url(#rsIntroGrad)" stroke-width="5" stroke-linecap="round"/>
        <path class="rs-intro-thread-path" d="M-40 760 C 300 620, 560 820, 920 670 C 1180 560, 1340 680, 1500 590" stroke="url(#rsIntroGrad)" stroke-width="2.2" stroke-opacity="0.52" stroke-linecap="round"/>
      </svg>
      <button type="button" class="rs-intro-skip" id="rs-intro-skip-btn">Bỏ qua (Esc)</button>
      <div class="rs-intro-card">
        <div class="rs-intro-beam" id="rs-intro-beam"></div>
        <div class="rs-intro-brand">
          <svg width="42" height="42" viewBox="0 0 64 64" fill="none">
            <path d="M32 10L49 16.5V31.5C49 43 41.6 51.2 32 54.6C22.4 51.2 15 43 15 31.5V16.5L32 10Z" fill="#FF5C35" stroke="#FAFAFA" stroke-width="1.8"/>
            <path d="M24 32.4L29.6 38L41.4 25.8" stroke="#FFFFFF" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <div>
            <div class="rs-intro-brand-name">ReviewShield</div>
            <div class="rs-intro-brand-sub">Bóc tách sao ảo · Chốt đơn chuẩn thật</div>
          </div>
        </div>
        <div class="rs-intro-stage">
          <div>
            <div class="rs-intro-score-lbl" id="rs-intro-lbl">Điểm hiển thị trên sàn</div>
            <div class="rs-intro-score-val" id="rs-intro-num">4.9★</div>
          </div>
          <div class="rs-intro-verdict" id="rs-intro-verdict">Đang quét đánh giá nhiễu...</div>
        </div>
        <div class="rs-intro-chips">
          <div class="rs-intro-chip" id="rs-ic-1">
            <span class="rs-intro-chip-tag tag-coin">Nhận xu · w=0.15</span>
            <div class="rs-intro-chip-txt">“Chưa dùng nhưng cho 5 sao lấy xu”</div>
          </div>
          <div class="rs-intro-chip" id="rs-ic-2">
            <span class="rs-intro-chip-tag tag-coral">Lặp mẫu · w=0.10</span>
            <div class="rs-intro-chip-txt">“Đóng gói đẹp, xứng đáng 1000 sao”</div>
          </div>
          <div class="rs-intro-chip" id="rs-ic-3">
            <span class="rs-intro-chip-tag tag-sky">Shipper · w=0.00</span>
            <div class="rs-intro-chip-txt">“Giao trễ 4 ngày, móp vỏ hộp”</div>
          </div>
        </div>
        <div class="rs-intro-bar"><div class="rs-intro-bar-fill"></div></div>
      </div>
    `;
    DOC.body.appendChild(overlay);

    let closed = false;
    const timers = [];
    let rafIntro = null;

    function closeIntro() {
      if (closed) return;
      closed = true;
      timers.forEach((id) => WIN.clearTimeout(id));
      if (rafIntro) WIN.cancelAnimationFrame(rafIntro);
      DOC.removeEventListener('keydown', onKey);
      overlay.classList.add('rs-intro-exit');
      WIN.setTimeout(() => { if (overlay && overlay.parentNode) overlay.remove(); }, 390);
    }

    function onKey(ev) {
      if (ev.key === 'Escape') closeIntro();
    }

    const skipBtn = overlay.querySelector('#rs-intro-skip-btn');
    if (skipBtn) skipBtn.addEventListener('click', closeIntro);
    overlay.addEventListener('click', (ev) => {
      if (ev.target === overlay) closeIntro();
    });
    DOC.addEventListener('keydown', onKey);

    const beamEl = overlay.querySelector('#rs-intro-beam');
    const numEl = overlay.querySelector('#rs-intro-num');
    const lblEl = overlay.querySelector('#rs-intro-lbl');
    const verdictEl = overlay.querySelector('#rs-intro-verdict');
    const c1 = overlay.querySelector('#rs-ic-1');
    const c2 = overlay.querySelector('#rs-ic-2');
    const c3 = overlay.querySelector('#rs-ic-3');

    if (reduceMotion) {
      if (numEl) { numEl.textContent = '2.6★'; numEl.classList.add('is-real'); }
      if (lblEl) lblEl.textContent = 'Điểm tin cậy thực sau lọc';
      if (verdictEl) { verdictEl.textContent = 'Chất lượng thật · Grounding 100%'; verdictEl.classList.add('locked'); }
      [c1, c2, c3].forEach((c) => c && c.classList.add('filtered'));
      timers.push(WIN.setTimeout(closeIntro, 1700));
      return;
    }

    timers.push(WIN.setTimeout(() => {
      if (beamEl) beamEl.classList.add('scan-on');
      if (lblEl) lblEl.textContent = 'Điểm tin cậy thực sau khi tách nhiễu';
      if (numEl) numEl.classList.add('is-real');

      timers.push(WIN.setTimeout(() => c1 && c1.classList.add('filtered'), 120));
      timers.push(WIN.setTimeout(() => c2 && c2.classList.add('filtered'), 320));
      timers.push(WIN.setTimeout(() => c3 && c3.classList.add('filtered'), 520));

      const t0 = WIN.performance.now();
      const dur = 1150;
      function stepScore(now) {
        if (closed) return;
        const p = Math.min(1, (now - t0) / dur);
        const eased = 1 - Math.pow(1 - p, 3.2);
        const val = 4.9 + (2.6 - 4.9) * eased;
        if (numEl) numEl.textContent = val.toFixed(1) + '★';
        if (p < 1) {
          rafIntro = WIN.requestAnimationFrame(stepScore);
        } else {
          if (numEl) numEl.textContent = '2.6★';
          if (verdictEl) {
            verdictEl.textContent = 'Chất lượng thật · Grounding 100%';
            verdictEl.classList.add('locked');
          }
        }
      }
      rafIntro = WIN.requestAnimationFrame(stepScore);
    }, 850));

    timers.push(WIN.setTimeout(closeIntro, 3200));
  };
})();
"""
    runtime_js = json.dumps(parent_runtime_src, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" /></head>
<body style="margin:0;padding:0;overflow:hidden;background:transparent;">
<script>
(function() {{
  const CFG = {cfg_js};
  const RUNTIME_SRC = {runtime_js};
  try {{
    const pWin = window.parent;
    const pDoc = pWin.document;
    if (!pDoc || !pDoc.head || !pDoc.body) return;

    if (pWin.__rsRuntimeVer !== CFG.ver || typeof pWin.__rsEnsureLusionThread !== 'function') {{
      if (pWin.__rsLusionThread && typeof pWin.__rsLusionThread.destroy === 'function') {{
        pWin.__rsLusionThread.destroy();
      }}
      const oldScript = pDoc.getElementById('rs-parent-runtime');
      if (oldScript) oldScript.remove();
      const sc = pDoc.createElement('script');
      sc.id = 'rs-parent-runtime';
      sc.textContent = RUNTIME_SRC;
      pDoc.head.appendChild(sc);
    }}

    if (typeof pWin.__rsEnsureLusionThread === 'function') {{
      pWin.__rsEnsureLusionThread();
    }}
    if (typeof pWin.__rsPlayStoryIntro === 'function') {{
      pWin.__rsPlayStoryIntro(CFG.nonce, CFG.isReplay);
    }}
  }} catch (e) {{}}
}})();
</script>
</body></html>"""


def _build_interactive_score_lens_html(
    scores: dict[str, Any],
    reviews: list[dict[str, Any]],
    grounding_rate: float,
    fallback_count: int,
) -> str:
    """Thẻ điểm tương tác 60fps phong cách TMĐT (Espresso ấm + Sao vàng động + Bộ gạt lọc nhận xu/seeding/shipper)."""
    minimal_reviews = [
        {
            "rating": float(r["rating"]),
            "label": str(r.get("label") or "low_signal"),
        }
        for r in (reviews or [])
        if isinstance(r, dict) and isinstance(r.get("rating"), (int, float))
    ]
    payload = {
        "platform_rating": float(scores["platform_rating"])
        if isinstance(scores.get("platform_rating"), (int, float))
        else None,
        "real_trust_score": float(scores["real_trust_score"])
        if isinstance(scores.get("real_trust_score"), (int, float))
        else None,
        "verified_ratio": round(float(scores.get("verified_ratio", 0.0)), 1),
        "grounding_rate": round(float(grounding_rate), 0),
        "fallback_count": int(fallback_count),
        "direction": str(scores.get("direction") or "insufficient_data"),
        "reviews": minimal_reviews,
        "weights": WEIGHT_MAP,
        "counts": {
            "verified_insight": sum(1 for r in minimal_reviews if r["label"] == "verified_insight"),
            "low_signal": sum(1 for r in minimal_reviews if r["label"] == "low_signal"),
            "suspicious_pattern": sum(1 for r in minimal_reviews if r["label"] == "suspicious_pattern"),
            "logistics_only": sum(1 for r in minimal_reviews if r["label"] == "logistics_only"),
        },
    }
    payload_js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@500;600;700&family=JetBrains+Mono:wght@500;600;700&family=Plus+Jakarta+Sans:wght@700;800&display=swap" rel="stylesheet" />
<style>
  :root {{
    --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
    --bg: #231816;
    --bg-deep: #170F0E;
    --ink: #FFF9F5;
    --muted: #CBB8B0;
    --rule: rgba(255, 224, 206, 0.14);
    --coral: #FF6B4A;
    --coral-solid: #E0472A;
    --mint: #38DB94;
    --mint-solid: #0FA968;
    --coin: #FFC44D;
    --sky: #5BB8FF;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Be Vietnam Pro', system-ui, sans-serif;
    background: transparent;
    color: var(--ink);
    padding: 2px 2px 4px 2px;
    overflow-x: hidden;
    overflow-y: auto;
  }}
  .card-shell {{
    position: relative;
    background: linear-gradient(142deg, var(--bg) 0%, var(--bg-deep) 100%);
    border-radius: 18px;
    border: 1px solid var(--rule);
    box-shadow: 0 18px 34px -18px rgba(35, 24, 22, 0.62);
    overflow: hidden;
  }}
  .card-shell::before {{
    content: "";
    position: absolute; inset: 0; pointer-events: none;
    background:
      radial-gradient(60% 90% at 96% 0%, rgba(255, 107, 74, 0.16), transparent 62%),
      radial-gradient(50% 80% at 8% 100%, rgba(255, 196, 77, 0.10), transparent 60%);
  }}
  .top-strip {{
    position: relative; z-index: 1;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    border-bottom: 1px solid var(--rule);
  }}
  .cell {{
    padding: 14px 16px;
    border-right: 1px solid var(--rule);
    display: flex; flex-direction: column; justify-content: space-between;
  }}
  .cell:last-child {{ border-right: none; }}
  .cell-focus {{
    background: rgba(255, 107, 74, 0.08);
    position: relative;
  }}
  .lbl {{ font-size: 12px; color: var(--muted); font-weight: 600; }}
  .num-row {{
    display: flex; align-items: baseline; gap: 5px;
    margin: 5px 0 3px 0;
  }}
  .num {{
    font-family: 'Plus Jakarta Sans', 'Be Vietnam Pro', sans-serif;
    font-variant-numeric: tabular-nums;
    font-size: 33px; font-weight: 800; letter-spacing: -0.03em; line-height: 1.05;
    color: var(--ink);
    transition: color 220ms var(--ease-out);
  }}
  .num.is-coral {{ color: var(--coral); }}
  .num.is-mint {{ color: var(--mint); }}
  .num.is-coin {{ color: var(--coin); }}
  .unit {{
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 12.5px; color: var(--muted); font-weight: 500;
  }}
  .star-bar {{
    display: inline-flex; gap: 3px; margin: 2px 0 4px 0;
  }}
  .star-svg {{ width: 13px; height: 13px; transition: transform 220ms var(--ease-out), fill 220ms var(--ease-out); }}
  .star-svg.on {{ fill: var(--coin); }}
  .star-svg.off {{ fill: rgba(255, 249, 245, 0.18); }}
  .sub {{
    font-size: 11.5px; color: var(--muted); line-height: 1.35;
    font-variant-numeric: tabular-nums;
  }}
  .sub strong {{ color: var(--ink); font-weight: 700; }}

  /* Thanh thước đo 1.0 - 5.0 chạy mượt */
  .ruler-wrap {{
    position: relative; z-index: 1;
    padding: 11px 16px 9px 16px;
    border-bottom: 1px solid var(--rule);
    background: rgba(255, 255, 255, 0.02);
  }}
  .ruler-head {{
    display: flex; justify-content: space-between; align-items: center; gap: 8px;
    margin-bottom: 4px;
  }}
  .ruler-title {{ font-size: 11.5px; font-weight: 700; color: var(--ink); }}
  .ruler-status {{
    font-size: 11.5px; font-weight: 600; color: var(--mint);
    font-variant-numeric: tabular-nums;
  }}
  .ruler-stage {{ position: relative; padding: 24px 2px 22px 2px; }}
  .track {{
    position: relative; height: 9px; border-radius: 999px;
    background: rgba(255, 249, 245, 0.11);
    overflow: hidden;
  }}
  .delta-bar {{
    position: absolute; top: 0; bottom: 0; border-radius: 999px;
    background: linear-gradient(90deg, #FF6B4A, #FF9966);
    transition: background 220ms var(--ease-out);
  }}
  .delta-bar.boost {{ background: linear-gradient(90deg, #0FA968, #38DB94); }}
  .delta-bar.near {{ background: linear-gradient(90deg, #1E88E5, #5BB8FF); }}
  .pin {{
    position: absolute; transform: translateX(-50%);
    display: flex; flex-direction: column; align-items: center; pointer-events: none;
  }}
  .pin-top {{ top: 0; }}
  .pin-bot {{ bottom: 0; }}
  .pin-tag {{
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
    font-size: 10.5px; font-weight: 700;
    padding: 2px 8px; border-radius: 999px; white-space: nowrap;
  }}
  .tag-plat {{ background: rgba(255, 249, 245, 0.14); color: var(--ink); border: 1px solid rgba(255, 249, 245, 0.28); }}
  .tag-real {{ background: var(--mint-solid); color: #FFFFFF; }}
  .tag-real.drop {{ background: var(--coral-solid); }}
  .tag-real.near {{ background: #1E88E5; }}
  .stem {{ width: 2px; height: 7px; background: rgba(255, 249, 245, 0.55); }}
  .ticks {{
    display: flex; justify-content: space-between;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 10.5px; color: var(--muted);
  }}

  /* Thanh nút gạt mô phỏng lọc nhiễu trực tiếp */
  .sim-bar {{
    position: relative; z-index: 1;
    padding: 9px 14px 10px 14px;
    display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 6px;
    background: rgba(15, 9, 8, 0.42);
  }}
  .sim-left {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }}
  .sim-lbl {{ font-size: 11px; font-weight: 600; color: var(--muted); margin-right: 2px; }}
  .pill-btn {{
    display: inline-flex; align-items: center; gap: 5px;
    padding: 5px 10px; border-radius: 999px;
    border: 1px solid rgba(255, 224, 206, 0.22);
    background: rgba(255, 255, 255, 0.06); color: var(--muted);
    font-family: 'Be Vietnam Pro', system-ui, sans-serif;
    font-size: 11.5px; font-weight: 600; cursor: pointer;
    transition: transform 150ms var(--ease-out), background-color 180ms var(--ease-out), border-color 180ms var(--ease-out), color 180ms var(--ease-out);
  }}
  .pill-btn .dot {{ width: 7px; height: 7px; border-radius: 999px; background: rgba(255,255,255,0.28); }}
  .pill-btn.active {{
    background: rgba(56, 219, 148, 0.16);
    border-color: rgba(56, 219, 148, 0.62);
    color: var(--ink);
  }}
  .pill-btn.active .dot {{ background: var(--mint); }}
  .pill-btn.mode-raw {{
    background: rgba(255, 196, 77, 0.16);
    border-color: rgba(255, 196, 77, 0.60);
    color: var(--coin);
  }}
  .pill-btn:active {{ transform: scale(0.97); }}
  .pill-btn:focus-visible {{ outline: 2px solid var(--coral); outline-offset: 2px; }}
  @media (hover: hover) and (pointer: fine) {{
    .pill-btn:hover {{ border-color: rgba(255, 224, 206, 0.56); color: var(--ink); transform: translateY(-1px); }}
  }}
  @media (prefers-reduced-motion: reduce) {{
    .pill-btn, .star-svg {{ transition: background-color 120ms linear; }}
    .pill-btn:hover, .pill-btn:active {{ transform: none; }}
  }}
</style></head>
<body>
  <div class="card-shell">
    <div class="top-strip">
      <div class="cell">
        <span class="lbl">Điểm sàn hiển thị</span>
        <div class="num-row"><span class="num" id="platNum">—</span><span class="unit">/ 5.0</span></div>
        <div class="star-bar" id="platStars"></div>
        <span class="sub">Trung bình gốc chưa tách nhiễu</span>
      </div>
      <div class="cell cell-focus">
        <span class="lbl" id="realLbl">Điểm tin cậy thực</span>
        <div class="num-row"><span class="num is-mint" id="realNum">—</span><span class="unit">/ 5.0</span></div>
        <div class="star-bar" id="realStars"></div>
        <span class="sub" id="deltaTxt">Đang tính lại...</span>
      </div>
      <div class="cell">
        <span class="lbl">Tỷ lệ trải nghiệm thật</span>
        <div class="num-row"><span class="num" id="verNum">—</span></div>
        <span class="sub" id="groundTxt">Khớp nguyên văn 100%</span>
      </div>
    </div>

    <div class="ruler-wrap">
      <div class="ruler-head">
        <span class="ruler-title">So sánh độ lệch sao (1.0 – 5.0)</span>
        <span class="ruler-status" id="modeStatus">Đang bật đủ 3 lớp lọc ReviewShield</span>
      </div>
      <div class="ruler-stage">
        <div class="pin pin-top" id="pinTop" style="left:50%;"><span class="pin-tag tag-plat" id="tagTop">Sàn —</span><span class="stem"></span></div>
        <div class="track"><div class="delta-bar" id="deltaBar" style="left:50%;width:0%;"></div></div>
        <div class="pin pin-bot" id="pinBot" style="left:50%;"><span class="stem"></span><span class="pin-tag tag-real" id="tagBot">Thực —</span></div>
      </div>
      <div class="ticks"><span>1.0</span><span>2.0</span><span>3.0</span><span>4.0</span><span>5.0</span></div>
    </div>

    <div class="sim-bar">
      <div class="sim-left">
        <span class="sim-lbl">Thử bật/tắt lọc:</span>
        <button class="pill-btn active" id="btnLow" type="button"><span class="dot"></span>Nhận xu (<span id="cLow">0</span>)</button>
        <button class="pill-btn active" id="btnSus" type="button"><span class="dot"></span>Seeding (<span id="cSus">0</span>)</button>
        <button class="pill-btn active" id="btnLog" type="button"><span class="dot"></span>Shipper (<span id="cLog">0</span>)</button>
      </div>
      <button class="pill-btn" id="btnToggleAll" type="button">So với điểm gốc</button>
    </div>
  </div>

  <script>
    const D = {payload_js};
    const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const state = {{ low: true, sus: true, log: true }};

    const elPlat = document.getElementById('platNum');
    const elReal = document.getElementById('realNum');
    const elRealLbl = document.getElementById('realLbl');
    const elDelta = document.getElementById('deltaTxt');
    const elVer = document.getElementById('verNum');
    const elGround = document.getElementById('groundTxt');
    const elStatus = document.getElementById('modeStatus');
    const elPlatStars = document.getElementById('platStars');
    const elRealStars = document.getElementById('realStars');
    const pinTop = document.getElementById('pinTop');
    const tagTop = document.getElementById('tagTop');
    const pinBot = document.getElementById('pinBot');
    const tagBot = document.getElementById('tagBot');
    const deltaBar = document.getElementById('deltaBar');
    const btnLow = document.getElementById('btnLow');
    const btnSus = document.getElementById('btnSus');
    const btnLog = document.getElementById('btnLog');
    const btnToggleAll = document.getElementById('btnToggleAll');

    function renderStarRow(container, val) {{
      const n = val === null ? 0 : Math.max(0, Math.min(5, Math.round(val)));
      let out = '';
      for (let i = 0; i < 5; i++) {{
        out += '<svg class="star-svg ' + (i < n ? 'on' : 'off') + '" viewBox="0 0 24 24"><path d="M12 2.8l2.8 5.7 6.3.9-4.5 4.4 1.1 6.3L12 17.1 6.3 20.1l1.1-6.3-4.5-4.4 6.3-.9L12 2.8z"/></svg>';
      }}
      container.innerHTML = out;
    }}

    document.getElementById('cLow').textContent = D.counts.low_signal;
    document.getElementById('cSus').textContent = D.counts.suspicious_pattern;
    document.getElementById('cLog').textContent = D.counts.logistics_only;
    elVer.textContent = D.verified_ratio.toFixed(1) + '%';
    elGround.textContent = 'Khớp nguyên văn ' + D.grounding_rate.toFixed(0) + '%' + (D.fallback_count ? ' (' + D.fallback_count + ' dự phòng)' : '');
    elPlat.textContent = D.platform_rating !== null ? D.platform_rating.toFixed(1) : '—';
    renderStarRow(elPlatStars, D.platform_rating);

    function pctOf(v) {{
      const c = Math.max(1.0, Math.min(5.0, v));
      return ((c - 1.0) / 4.0) * 100.0;
    }}

    function computeSimScore() {{
      const allDefault = state.low && state.sus && state.log;
      if (allDefault && D.real_trust_score !== null) {{
        return D.real_trust_score;
      }}
      let wSum = 0, wTot = 0;
      for (const r of D.reviews) {{
        let w = 1.0;
        if (r.label === 'low_signal') w = state.low ? D.weights.low_signal : 1.0;
        else if (r.label === 'suspicious_pattern') w = state.sus ? D.weights.suspicious_pattern : 1.0;
        else if (r.label === 'logistics_only') w = state.log ? D.weights.logistics_only : 1.0;
        wSum += r.rating * w;
        wTot += w;
      }}
      if (wTot <= 0) return null;
      return Math.round((wSum / wTot) * 10) / 10;
    }}

    let displayedScore = D.platform_rating !== null ? D.platform_rating : D.real_trust_score;
    let rafId = null;

    function paintVisual(val) {{
      const allDefault = state.low && state.sus && state.log;
      const allRaw = !state.low && !state.sus && !state.log;

      if (D.platform_rating !== null) {{
        const pP = pctOf(D.platform_rating);
        pinTop.style.display = 'flex';
        pinTop.style.left = pP.toFixed(1) + '%';
        tagTop.textContent = 'Sàn ' + D.platform_rating.toFixed(1);
      }} else {{
        pinTop.style.display = 'none';
      }}

      renderStarRow(elRealStars, val);

      if (val === null) {{
        elReal.textContent = '—';
        elReal.className = 'num is-coin';
        elDelta.textContent = 'Chỉ có đánh giá vận chuyển';
        pinBot.style.display = 'none';
        deltaBar.style.width = '0%';
      }} else {{
        elReal.textContent = val.toFixed(1);
        const diff = D.platform_rating !== null ? Math.round((val - D.platform_rating) * 10) / 10 : 0;
        const clsNum = diff <= -0.35 ? 'is-coral' : (diff >= 0.35 ? 'is-mint' : 'is-coin');
        elReal.className = 'num ' + clsNum;

        if (D.platform_rating !== null) {{
          const sign = diff > 0 ? '+' : '';
          elDelta.innerHTML = 'Chênh <strong>' + sign + diff.toFixed(1) + ' sao</strong> so với sàn';
          const pP = pctOf(D.platform_rating);
          const rP = pctOf(val);
          deltaBar.style.left = Math.min(pP, rP).toFixed(1) + '%';
          deltaBar.style.width = Math.max(1.2, Math.abs(pP - rP)).toFixed(1) + '%';
          deltaBar.className = 'delta-bar ' + (diff <= -0.35 ? '' : (diff >= 0.35 ? 'boost' : 'near'));
        }} else {{
          elDelta.textContent = 'Tính theo công thức WEIGHT_MAP';
          deltaBar.style.width = '0%';
        }}
        pinBot.style.display = 'flex';
        pinBot.style.left = pctOf(val).toFixed(1) + '%';
        tagBot.textContent = (allRaw ? 'Chưa lọc ' : 'Thực ') + val.toFixed(1);
        tagBot.className = 'pin-tag tag-real ' + (diff <= -0.35 ? 'drop' : (diff >= 0.35 ? '' : 'near'));
      }}

      if (allDefault) {{
        elRealLbl.textContent = 'Điểm tin cậy thực';
        elStatus.textContent = 'Đang bật đủ 3 lớp lọc ReviewShield';
        elStatus.style.color = 'var(--mint)';
        btnToggleAll.textContent = 'So với điểm gốc';
        btnToggleAll.classList.remove('mode-raw');
      }} else if (allRaw) {{
        elRealLbl.textContent = 'Điểm gốc chưa lọc (w=1.0)';
        elStatus.textContent = 'Đã tắt toàn bộ lớp lọc — thấy điểm bị nhiễu';
        elStatus.style.color = 'var(--coin)';
        btnToggleAll.textContent = 'Bật lại ReviewShield';
        btnToggleAll.classList.add('mode-raw');
      }} else {{
        elRealLbl.textContent = 'Mô phỏng bộ lọc tùy chỉnh';
        elStatus.textContent = 'Mô phỏng WEIGHT_MAP trực tiếp (kết quả gốc giữ nguyên)';
        elStatus.style.color = 'var(--sky)';
        btnToggleAll.textContent = 'Bật lại ReviewShield';
        btnToggleAll.classList.add('mode-raw');
      }}
    }}

    function animateTo(target, durationMs) {{
      if (rafId) cancelAnimationFrame(rafId);
      if (reduceMotion || target === null || displayedScore === null) {{
        displayedScore = target;
        paintVisual(target);
        return;
      }}
      const startVal = displayedScore;
      const t0 = performance.now();
      function frame(now) {{
        const t = Math.min(1, (now - t0) / durationMs);
        const eased = 1 - Math.pow(1 - t, 3.2);
        displayedScore = startVal + (target - startVal) * eased;
        paintVisual(displayedScore);
        if (t < 1) {{
          rafId = requestAnimationFrame(frame);
        }} else {{
          displayedScore = target;
          paintVisual(target);
        }}
      }}
      rafId = requestAnimationFrame(frame);
    }}

    function syncButtons() {{
      btnLow.classList.toggle('active', state.low);
      btnSus.classList.toggle('active', state.sus);
      btnLog.classList.toggle('active', state.log);
    }}

    btnLow.addEventListener('click', () => {{ state.low = !state.low; syncButtons(); animateTo(computeSimScore(), 420); }});
    btnSus.addEventListener('click', () => {{ state.sus = !state.sus; syncButtons(); animateTo(computeSimScore(), 420); }});
    btnLog.addEventListener('click', () => {{ state.log = !state.log; syncButtons(); animateTo(computeSimScore(), 420); }});
    btnToggleAll.addEventListener('click', () => {{
      if (state.low && state.sus && state.log) {{
        state.low = state.sus = state.log = false;
      }} else {{
        state.low = state.sus = state.log = true;
      }}
      syncButtons();
      animateTo(computeSimScore(), 520);
    }});

    syncButtons();
    paintVisual(displayedScore);
    setTimeout(() => animateTo(computeSimScore(), 920), 160);
  </script>
</body></html>"""


def _build_copy_button_html(text_to_copy: str, button_label: str = "Sao chép cả 3 câu hỏi") -> str:
    """Nút sao chép 1 chạm vào clipboard với phản hồi lực nhấn scale(0.97) và thoát chuỗi chống XSS."""
    payload_js = json.dumps(text_to_copy, ensure_ascii=False).replace("</", "<\\/")
    label_js = json.dumps(button_label, ensure_ascii=False).replace("</", "<\\/")
    safe_label = html.escape(button_label)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8" />
<style>
  :root {{
    --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
    --btn-bg: #261E1D;
    --btn-fg: #FFF8F4;
    --btn-border: rgba(255, 232, 218, 0.22);
    --btn-coral: #F05232;
    --btn-mint: #0FA968;
  }}
  body {{ margin: 0; padding: 3px 4px 6px 0; font-family: 'Be Vietnam Pro', system-ui, sans-serif; background: transparent; }}
  button {{
    display: inline-flex; align-items: center; gap: 8px;
    background: var(--btn-bg); color: var(--btn-fg);
    border: 1px solid var(--btn-border); border-radius: 999px; padding: 10px 18px;
    font-size: 13px; font-weight: 600; cursor: pointer;
    box-shadow: 0 10px 22px -10px rgba(0, 0, 0, 0.65);
    transition: transform 160ms var(--ease-out), background-color 180ms var(--ease-out), border-color 180ms var(--ease-out), box-shadow 180ms var(--ease-out);
  }}
  @media (hover: hover) and (pointer: fine) {{
    button:hover {{ background: var(--btn-coral); border-color: var(--btn-coral); transform: translateY(-1px); box-shadow: 0 12px 24px -8px rgba(240, 82, 50, 0.50); }}
  }}
  button:active {{ transform: scale(0.97); }}
  button:focus-visible {{ outline: 2px solid var(--btn-coral); outline-offset: 2px; }}
  button.ok {{ background: var(--btn-mint); color: #FFFFFF; }}
  @media (prefers-reduced-motion: reduce) {{
    button {{ transition: background-color 150ms linear; }}
    button:hover, button:active {{ transform: none; }}
  }}
</style></head>
<body>
  <button id="cp" type="button">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15H4a1.5 1.5 0 0 1-1.5-1.5v-9A1.5 1.5 0 0 1 4 3h9A1.5 1.5 0 0 1 14.5 4.5V6"/>
    </svg>
    <span id="cp-lbl">{safe_label}</span>
  </button>
  <script>
    const txt = {payload_js};
    const origLabel = {label_js};
    const btn = document.getElementById("cp");
    const lbl = document.getElementById("cp-lbl");
    btn.addEventListener("click", async () => {{
      try {{
        await navigator.clipboard.writeText(txt);
        lbl.textContent = "Đã sao chép bản nháp";
        btn.classList.add("ok");
        setTimeout(() => {{ lbl.textContent = origLabel; btn.classList.remove("ok"); }}, 2200);
      }} catch (e) {{
        lbl.textContent = "Hãy sao chép ở khung bên dưới";
      }}
    }});
  </script>
</body></html>"""


def _render_ruler_html(
    platform_rating: float | None,
    real_score: float | None,
    direction: str,
) -> str:
    """Thước đo độ lệch sao tĩnh dự phòng (1.0 đến 5.0 sao)."""
    def _pct(val: float) -> float:
        clamped = max(1.0, min(5.0, float(val)))
        return round((clamped - 1.0) / 4.0 * 100.0, 1)

    p_pct = _pct(platform_rating) if isinstance(platform_rating, (int, float)) else None
    r_pct = _pct(real_score) if isinstance(real_score, (int, float)) else None

    if direction == "lower_than_platform":
        delta_cls, pin_cls = "delta-drop", "pin-coral"
    elif direction == "higher_than_platform":
        delta_cls, pin_cls = "delta-boost", "pin-mint"
    else:
        delta_cls, pin_cls = "delta-near", "pin-sky"

    gap_html = ""
    if p_pct is not None and r_pct is not None:
        left_p = min(p_pct, r_pct)
        width_p = max(1.6, abs(p_pct - r_pct))
        gap_html = f'<div class="rs-delta-fill {delta_cls}" style="left:{left_p}%;width:{width_p}%;"></div>'

    top_pin = ""
    if p_pct is not None:
        top_pin = (
            f'<div class="rs-pin-top" style="left:{p_pct}%;">'
            f'<span class="rs-pin-tag-top">Sàn {platform_rating:.1f}</span>'
            '<span class="rs-pin-stem stem-ink"></span>'
            "</div>"
        )

    bot_pin = ""
    if r_pct is not None:
        bot_pin = (
            f'<div class="rs-pin-bot" style="left:{r_pct}%;">'
            f'<span class="rs-pin-stem {pin_cls}"></span>'
            f'<span class="rs-pin-tag-bot {pin_cls}">Thực {real_score:.1f}</span>'
            "</div>"
        )

    summary_txt = DIRECTION_TEXT.get(direction, direction)
    return (
        '<div class="rs-ruler-sheet">'
        '<div class="rs-ruler-head">'
        '<span class="rs-ruler-title">So sánh độ lệch sao (1.0 – 5.0)</span>'
        f'<span class="rs-ruler-note">{html.escape(summary_txt)}</span>'
        "</div>"
        '<div class="rs-ruler-stage">'
        f"{top_pin}"
        f'<div class="rs-ruler-track">{gap_html}</div>'
        f"{bot_pin}"
        "</div>"
        '<div class="rs-ruler-ticks rs-fig"><span>1.0</span><span>2.0</span><span>3.0</span><span>4.0</span><span>5.0</span></div>'
        "</div>"
    )


def _render_pipeline_bar_html(
    done: bool,
    refused: bool,
    trace_summary: dict[str, Any] | None,
    review_count: int = 0,
    grounding_rate: float = 100.0,
    real_score: float | None = None,
) -> str:
    """Dải tiến trình 1 dòng tinh gọn cho 4 chặng xử lý (giảm nhiễu thị giác, thoáng bố cục)."""
    if refused:
        c1, c2, c3, c4 = "rs-pnode warn", "rs-pnode", "rs-pnode", "rs-pnode"
        rail_cls = "rs-pline"
        status_txt = "Guardrail đã chặn · 0 lần gọi AI"
    elif done:
        c1 = c2 = c3 = c4 = "rs-pnode lit"
        rail_cls = "rs-pline active"
        score_txt = f"Điểm thực {real_score:.1f}/5.0" if isinstance(real_score, (int, float)) else "Thiếu dữ liệu"
        status_txt = f"{review_count} đánh giá · Nguyên văn {grounding_rate:.0f}% · {score_txt}"
    else:
        c1 = c2 = c3 = c4 = "rs-pnode"
        rail_cls = "rs-pline"
        status_txt = "Sẵn sàng chạy 4 chặng tất định"

    trace_txt = ""
    if isinstance(trace_summary, dict):
        models_str = ", ".join(trace_summary.get("models") or []) or "—"
        trace_txt = (
            f" · {models_str} · {trace_summary.get('model_calls', 0)} AI / "
            f"{trace_summary.get('tool_calls', 0)} tool · "
            f"{trace_summary.get('tokens_in', 0)}/{trace_summary.get('tokens_out', 0)} tok"
        )

    return (
        '<section class="rs-panel rs-pipeline-slim rs-reveal rs-delay-2">'
        '<div class="rs-psteps">'
        f'<span class="{c1}"><span class="rs-pdot"></span>Làm sạch</span>'
        f'<span class="{rail_cls}"><span class="rs-pbeam"></span></span>'
        f'<span class="{c2}"><span class="rs-pdot"></span>Phân 4 nhãn</span>'
        f'<span class="{rail_cls}"><span class="rs-pbeam"></span></span>'
        f'<span class="{c3}"><span class="rs-pdot"></span>Khóa trích dẫn</span>'
        f'<span class="{rail_cls}"><span class="rs-pbeam"></span></span>'
        f'<span class="{c4}"><span class="rs-pdot"></span>Tính điểm thực</span>'
        "</div>"
        f'<div class="rs-pmeta rs-fig">{html.escape(status_txt + trace_txt)}</div>'
        "</section>"
    )


def _render_signal_bar_html(label_counts: dict[str, int], total_reviews: int) -> str:
    """Thanh phân bổ 4 nhóm tín hiệu màu TMĐT kèm trọng số WEIGHT_MAP."""
    total = max(1, total_reviews)
    segs = []
    legends = []
    for key, meta in LABEL_META.items():
        cnt = int(label_counts.get(key, 0))
        pct = round(100.0 * cnt / total, 1)
        if cnt > 0:
            lbl_in = f"{pct:.0f}%" if pct >= 10 else ""
            segs.append(
                f'<div class="rs-sig-seg" style="width:{pct}%;background:{meta["bar_var"]};" '
                f'title="{meta["name"]}: {cnt} ({pct}%)">{lbl_in}</div>'
            )
        w = WEIGHT_MAP[key]
        legends.append(
            '<span class="rs-sig-leg">'
            f'<span class="rs-sig-swatch" style="background:{meta["bar_var"]};"></span>'
            f'<strong>{meta["short"]}</strong> <span class="rs-fig">{cnt} ({pct:.0f}%)</span> '
            f'<span class="rs-sig-w rs-fig">w={w:.2f}</span>'
            "</span>"
        )
    return (
        '<section class="rs-panel rs-sig-card rs-reveal rs-delay-2">'
        '<div class="rs-sig-head">'
        "<div>"
        '<h2 class="rs-h2">Bóc tách 4 nhóm đánh giá trên sàn</h2>'
        '<p class="rs-muted-line">Nhìn rõ bao nhiêu % là người dùng trải nghiệm thật, bao nhiêu % là nhận xu, seeding hoặc lỗi shipper.</p>'
        "</div>"
        f'<span class="rs-fig rs-count-pill">Tổng {total_reviews} đánh giá hợp lệ</span>'
        "</div>"
        f'<div class="rs-sig-track">{"".join(segs)}</div>'
        f'<div class="rs-sig-legend">{"".join(legends)}</div>'
        "</section>"
    )


def _render_ready_preview_rows_html(preview_reviews: list[dict[str, Any]]) -> str:
    """Trích trước 2 câu review tiêu biểu thoáng mắt ngay ở trạng thái chờ."""
    if not preview_reviews:
        return (
            '<div class="rs-callout">'
            'Bấm <strong>Soi đánh giá ngay</strong> ở cột trái để tách nhận xu, seeding và tính lại điểm tin cậy thực.'
            "</div>"
        )

    rows = []
    for idx, rv in enumerate(preview_reviews[:2], start=1):
        rid = html.escape(str(rv.get("id") or f"r{idx}"))
        author = html.escape(str(rv.get("author") or f"user_{idx:02d}"))
        rt = rv.get("rating")
        stars_html = _render_stars_svg(rt, size=11)
        rt_txt = f"{int(round(float(rt)))}.0" if isinstance(rt, (int, float)) else "—"
        txt = str(rv.get("text") or "").strip()
        snippet = txt if len(txt) <= 104 else txt[:103].rstrip() + "…"
        rows.append(
            '<div class="rs-shop-bubble">'
            f'<div class="rs-avatar-dot rs-fig">{rid.upper()}</div>'
            '<div class="rs-bubble-main">'
            f'<div class="rs-bubble-top"><span class="rs-bubble-user">{author}</span>{stars_html}<span class="rs-bubble-rt rs-fig">{rt_txt}</span></div>'
            f'<div class="rs-bubble-txt">{html.escape(snippet)}</div>'
            "</div>"
            "</div>"
        )

    return (
        '<div class="rs-preview-box">'
        f'<div class="rs-preview-head">{_svg_icon("eye", 14)}<span>Trích mẫu review đang chờ bóc tách</span></div>'
        f'{"".join(rows)}'
        "</div>"
    )


def _render_dossier_stage_html(
    meta: dict[str, Any],
    custom_image_url: str,
    res: dict[str, Any] | None,
    interactive_lens: bool = False,
) -> str:
    """Thẻ sản phẩm phong cách Mall (xử lý đủ 4 trạng thái ready / success / refused / json_error)."""
    product_name = str(meta.get("product_name") or "Sản phẩm đang soi đánh giá")
    platform = str(meta.get("platform") or "Shopee")
    category = str(meta.get("category") or "")
    photo_key = detect_product_photo_key(product_name, category)
    img_url, cat_label = resolve_product_photo(photo_key, custom_image_url or str(meta.get("image_url") or ""))

    if isinstance(res, dict) and isinstance(res.get("data"), dict) and res["data"].get("refused"):
        reason_raw = str(res["data"].get("reason") or "guardrail")
        reason_code = html.escape(reason_raw)
        out_txt = html.escape(str(res.get("output") or ""))
        if reason_raw in ("no_valid_reviews", "empty_input"):
            return (
                '<div class="rs-panel rs-verdict-stage rs-reveal">'
                '<div class="rs-verdict-top">'
                "<div>"
                f'<div class="rs-tag-row"><span class="rs-chip tone-coin">Định dạng đầu vào</span><span class="rs-chip rs-fig">{reason_code}</span></div>'
                '<h2 class="rs-product-title">Chưa đọc được danh sách đánh giá theo mẫu</h2>'
                "</div>"
                f'<div class="rs-verdict-badge verdict-coin">{_svg_icon("alert", 15)}<span>Cần bổ sung số sao</span></div>'
                "</div>"
                f'<div class="rs-callout">{out_txt}</div>'
                '<div class="rs-callout">'
                "<strong>Ví dụ hợp lệ (mỗi dòng 1 đánh giá kèm số sao 1–5):</strong><br/>"
                "<code>[5] Giao nhanh, chưa dùng nên cho 5 sao lấy xu</code><br/>"
                "<code>1⭐ Pin yếu dùng 1 tiếng đã sập nguồn, sạc rất nóng</code>"
                "</div>"
                "</div>"
            )
        return (
            '<div class="rs-panel rs-verdict-stage rs-reveal">'
            '<div class="rs-verdict-top">'
            "<div>"
            f'<div class="rs-tag-row"><span class="rs-chip tone-coral">Chặn an toàn</span><span class="rs-chip rs-fig">{reason_code}</span></div>'
            '<h2 class="rs-product-title">Yêu cầu nằm ngoài phạm vi phân tích</h2>'
            "</div>"
            f'<div class="rs-verdict-badge verdict-coral">{_svg_icon("shield_x", 15)}<span>Đã chặn</span></div>'
            "</div>"
            f'<div class="rs-callout callout-coral">{out_txt}</div>'
            '<div class="rs-callout">'
            "<strong>Cách dùng hợp lệ:</strong> Chọn sản phẩm trong kho mẫu hoặc dán trực tiếp đánh giá dạng "
            "<code>[5] nội dung...</code> hoặc JSON rồi bấm <strong>Soi đánh giá ngay</strong>."
            "</div>"
            "</div>"
        )

    if isinstance(res, dict) and isinstance(res.get("data"), dict) and res["data"].get("error"):
        err_code = html.escape(str(res["data"].get("error")))
        err_detail = html.escape(str(res["data"].get("detail") or "không rõ"))
        out_fallback = html.escape(str(res.get("output") or ""))
        fb_html = f'<div class="rs-callout rs-pre">{out_fallback}</div>' if out_fallback else ""
        return (
            '<div class="rs-panel rs-verdict-stage rs-reveal">'
            '<div class="rs-verdict-top">'
            "<div>"
            f'<div class="rs-tag-row"><span class="rs-chip tone-coin">Lỗi định dạng</span><span class="rs-chip rs-fig">{err_code}</span></div>'
            '<h2 class="rs-product-title">Phản hồi mô hình chưa đúng cấu trúc JSON</h2>'
            "</div>"
            f'<div class="rs-verdict-badge verdict-coin">{_svg_icon("alert", 15)}<span>Cần thử lại</span></div>'
            "</div>"
            f'<div class="rs-callout">Chi tiết kỹ thuật: <code>{err_detail}</code>. Dữ liệu bạn nhập vẫn được giữ nguyên.</div>'
            f"{fb_html}"
            "</div>"
        )

    data = res.get("data") if isinstance(res, dict) and isinstance(res.get("data"), dict) else None
    if data and isinstance(data.get("scores"), dict):
        scores = data["scores"]
        disp_name = str(data.get("product_name") or product_name)
        photo_key_res = detect_product_photo_key(disp_name, category)
        img_url, cat_label = resolve_product_photo(photo_key_res, custom_image_url or str(meta.get("image_url") or ""))

        platform_rating = scores.get("platform_rating")
        real_score = scores.get("real_trust_score")
        score_delta = scores.get("score_delta")
        direction = str(scores.get("direction") or "insufficient_data")
        verified_ratio = float(scores.get("verified_ratio", 0.0))
        trust_level = str(scores.get("trust_level") or "insufficient_data")
        grounding_rate = float(data.get("grounding_rate", 100.0))
        fallback_count = int(data.get("fallback_count", 0))
        tl = TRUST_LEVEL_META.get(trust_level, TRUST_LEVEL_META["insufficient_data"])
        tl_summary = tl["summary"]
        if trust_level == "medium" and verified_ratio >= 80.0:
            tl_summary = (
                "Tỷ lệ trải nghiệm thật cao nhưng điểm chất lượng ở mức trung bình hoặc có chênh lệch sao "
                "— nên xem kỹ các nhược điểm trước khi chốt đơn."
            )

        header_html = (
            '<div class="rs-product-hero" style="margin-bottom:0;">'
            '<div class="rs-photo-stage">'
            f'<img src="{html.escape(img_url, quote=True)}" alt="{html.escape(disp_name)}" loading="eager" onerror="this.style.display=\'none\';" />'
            '<span class="rs-photo-sheen" aria-hidden="true"></span>'
            "</div>"
            '<div class="rs-product-body">'
            '<div class="rs-product-bar">'
            '<div class="rs-tag-row">'
            f'<span class="rs-chip">{html.escape(platform)}</span>'
            f'<span class="rs-chip">{html.escape(cat_label)}</span>'
            "</div>"
            f'<div class="rs-verdict-badge {tl["badge_cls"]}">{_svg_icon(tl["icon"], 14)}<span>{html.escape(tl["badge"])}</span></div>'
            "</div>"
            f'<h2 class="rs-product-title">{html.escape(disp_name)}</h2>'
            f'<p class="rs-product-sub">{html.escape(tl_summary)}</p>'
            "</div>"
            "</div>"
        )

        if interactive_lens:
            return f'<div class="rs-panel rs-verdict-stage rs-verdict-compact rs-reveal">{header_html}</div>'

        plat_str = f"{platform_rating:.1f}" if isinstance(platform_rating, (int, float)) else "—"
        real_str = f"{real_score:.1f}" if isinstance(real_score, (int, float)) else "—"
        if isinstance(score_delta, (int, float)):
            sign = "+" if score_delta > 0 else ""
            delta_txt = f"Chênh {sign}{score_delta:.1f} sao"
        else:
            delta_txt = "Chỉ có đánh giá vận chuyển"
        delta_num_cls = (
            "rs-lens-num-coral"
            if direction == "lower_than_platform"
            else ("rs-lens-num-mint" if direction == "higher_than_platform" else "rs-lens-num-coin")
        )
        ground_txt = f"Khớp nguyên văn {grounding_rate:.0f}%" + (f" ({fallback_count} dự phòng)" if fallback_count else "")
        return (
            '<div class="rs-panel rs-verdict-stage rs-reveal">'
            f"{header_html}"
            '<div class="rs-lens-band" style="margin-top:16px;">'
            '<div class="rs-lens-cell">'
            '<span class="rs-lens-lbl">Điểm sàn hiển thị</span>'
            f'<div class="rs-lens-num rs-fig">{plat_str}<span class="rs-lens-unit"> / 5.0</span></div>'
            '<span class="rs-lens-sub">Trung bình chưa tách nhiễu</span>'
            "</div>"
            '<div class="rs-lens-cell rs-lens-focus">'
            '<span class="rs-lens-lbl">Điểm tin cậy thực</span>'
            f'<div class="rs-lens-num {delta_num_cls} rs-fig">{real_str}<span class="rs-lens-unit"> / 5.0</span></div>'
            f'<span class="rs-lens-sub rs-fig">{html.escape(delta_txt)}</span>'
            "</div>"
            '<div class="rs-lens-cell">'
            '<span class="rs-lens-lbl">Trải nghiệm thật</span>'
            f'<div class="rs-lens-num rs-fig">{verified_ratio:.1f}%</div>'
            f'<span class="rs-lens-sub">{html.escape(ground_txt)}</span>'
            "</div>"
            "</div>"
            f'{_render_ruler_html(platform_rating, real_score, direction)}'
            "</div>"
        )

    pr = meta.get("platform_rating")
    rc = int(meta.get("review_count") or 0)
    pr_str = f"{float(pr):.1f} / 5.0" if isinstance(pr, (int, float)) else "Tự tính từ review"
    preview_html = _render_ready_preview_rows_html(meta.get("preview_reviews") or [])
    return (
        '<div class="rs-panel rs-verdict-stage rs-reveal">'
        '<div class="rs-product-hero">'
        '<div class="rs-photo-stage rs-photo-stage-lg">'
        f'<img src="{html.escape(img_url, quote=True)}" alt="{html.escape(product_name)}" loading="eager" onerror="this.style.display=\'none\';" />'
        '<span class="rs-photo-sheen" aria-hidden="true"></span>'
        "</div>"
        '<div class="rs-product-body">'
        '<div class="rs-product-bar">'
        '<div class="rs-tag-row">'
        f'<span class="rs-chip">{html.escape(platform)}</span>'
        f'<span class="rs-chip">{html.escape(cat_label)}</span>'
        "</div>"
        f'<div class="rs-verdict-badge verdict-quiet">{_svg_icon("clock", 13)}<span>Chờ kiểm định</span></div>'
        "</div>"
        f'<h2 class="rs-product-title">{html.escape(product_name)}</h2>'
        '<p class="rs-product-sub">Sẵn sàng tách nhận xu, seeding lặp mẫu và lỗi shipper để tìm điểm chất lượng thật.</p>'
        "</div>"
        "</div>"
        '<div class="rs-lens-band rs-lens-ready">'
        '<div class="rs-lens-cell">'
        '<span class="rs-lens-lbl">Điểm hiển thị trên sàn</span>'
        f'<div class="rs-lens-num rs-fig">{html.escape(pr_str)}</div>'
        '<span class="rs-lens-sub">Trước khi tách nhiễu</span>'
        "</div>"
        '<div class="rs-lens-cell rs-lens-focus">'
        '<span class="rs-lens-lbl">Số lượt đánh giá</span>'
        f'<div class="rs-lens-num rs-fig">{rc}</div>'
        '<span class="rs-lens-sub">Bấm Soi đánh giá ngay</span>'
        "</div>"
        "</div>"
        f"{preview_html}"
        "</div>"
    )


def _render_evidence_cards_html(filtered_reviews: list[dict[str, Any]]) -> str:
    """Thẻ review phong cách sàn TMĐT: avatar ẩn danh + sao vàng + phân cấp độ nổi theo trọng số `w` + neo `#rev-<id>`."""
    cards = []
    for r in filtered_reviews:
        lbl = str(r.get("label") or "low_signal")
        meta = LABEL_META.get(lbl, LABEL_META["low_signal"])
        w = WEIGHT_MAP.get(lbl, 0.15)
        w_pct = int(round(w * 100))
        rid = str(r.get("id") or "")
        anchor_id = _safe_anchor_id(rid)
        rating_val = r.get("rating")
        stars_html = _render_stars_svg(rating_val, size=12)
        highlighted = highlight_quote_html(
            str(r.get("text") or ""),
            str(r.get("evidence_quote") or ""),
            mark_class=meta["mark"],
        )
        conf = r.get("confidence")
        conf_txt = f"Tin cậy {int(round(float(conf) * 100))}%" if isinstance(conf, (int, float)) else ""
        fb_txt = (
            "Trích dẫn dự phòng"
            if r.get("is_fallback") or r.get("fallback")
            else "Khớp nguyên văn 100%"
        )
        card_cls = "rs-ev-card rs-ev-primary" if lbl == "verified_insight" else "rs-ev-card rs-ev-dim"
        weight_note = (
            "Tính đủ 100% vào điểm thực"
            if w >= 1.0
            else ("Tách khỏi điểm sản phẩm (w=0.00)" if w == 0.0 else f"Giảm trọng số còn {w:.2f}")
        )
        cards.append(
            f'<article id="{anchor_id}" class="{card_cls}">'
            '<div class="rs-ev-top">'
            '<div class="rs-ev-left">'
            f'<span class="rs-avatar-dot rs-fig">{html.escape(rid.upper())}</span>'
            f"{stars_html}"
            f'<span class="rs-chip {meta["tone_class"]}">{meta["short"]}</span>'
            "</div>"
            '<div class="rs-ev-right">'
            f'<span class="rs-ev-ground">{_svg_icon("shield_ok", 13)}<span>{fb_txt}</span></span>'
            f'<span class="rs-ev-w rs-fig">w={w:.2f}</span>'
            "</div>"
            "</div>"
            f'<div class="rs-ev-quote">{highlighted}</div>'
            '<div class="rs-ev-foot">'
            f'<span class="rs-ev-reason">{html.escape(str(r.get("short_reason") or ""))}</span>'
            '<div class="rs-ev-meter-wrap">'
            f'<span class="rs-ev-wnote">{html.escape(weight_note)} {html.escape(conf_txt)}</span>'
            f'<div class="rs-ev-meter"><span class="rs-ev-meter-fill" style="width:{max(4, w_pct)}%;background:{meta["bar_var"]};"></span></div>'
            "</div>"
            "</div>"
            "</article>"
        )
    return f'<div class="rs-ev-feed">{"".join(cards)}</div>'


def _inject_custom_css(st: Any) -> None:
    """Hệ token Obsidian Sunset Noir (nền đen nhung Lusion + sợi chỉ phát sáng + 4 sắc TMĐT hài hòa)."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');

        :root {
            color-scheme: dark !important;

            /* 90% Đen Carbon trung tính thoáng mắt — để sợi chỉ Lusion & 1 màu nhấn tỏa sáng */
            --ground-base: #09090B;
            --ground-warm: #0D0C0E;
            --ground-soft: #0A0A0C;
            --surface-glass: rgba(18, 18, 21, 0.82);
            --surface-solid: #141418;
            --surface-soft: #1A1A1F;
            --surface-tint: #222228;

            /* Mực trung tính sắc nét chuẩn WCAG */
            --ink-deep: #FAFAFA;
            --ink-body: #D4D4D8;
            --ink-muted: #93939E;
            --line-subtle: rgba(255, 255, 255, 0.08);
            --line-strong: rgba(255, 255, 255, 0.16);

            /* Khối sâu đơn sắc cho đồng hồ điểm & công thức */
            --dark-bg: #111114;
            --dark-bg-deep: #0B0B0D;
            --dark-ink: #FAFAFA;
            --dark-muted: #9A9AA6;
            --dark-rule: rgba(255, 255, 255, 0.09);

            /* 1 Màu nhấn chủ đạo duy nhất (Cam san hô TMĐT) + 4 màu dữ liệu tiết chế */
            --brand-coral: #FF5C35;
            --brand-coral-bright: #FF7857;
            --brand-coral-hover: #FF6B47;
            --brand-coral-soft: rgba(255, 92, 53, 0.14);

            --sig-mint: #34D399;
            --sig-mint-bright: #4ADE80;
            --sig-mint-soft: rgba(52, 211, 153, 0.12);
            --hl-mint: rgba(52, 211, 153, 0.24);

            --sig-coin: #EAB308;
            --sig-coin-bright: #FACC15;
            --sig-coin-soft: rgba(234, 179, 8, 0.13);
            --hl-coin: rgba(234, 179, 8, 0.24);

            --sig-coral: #FF6B4A;
            --sig-coral-soft: rgba(255, 107, 74, 0.14);
            --hl-coral: rgba(255, 107, 74, 0.25);

            --sig-sky: #7AA2C4;
            --sig-sky-soft: rgba(122, 162, 196, 0.14);
            --hl-sky: rgba(122, 162, 196, 0.24);

            /* Typography */
            --font-display: 'Plus Jakarta Sans', 'Be Vietnam Pro', system-ui, sans-serif;
            --font-body: 'Be Vietnam Pro', system-ui, sans-serif;
            --font-mono: 'JetBrains Mono', ui-monospace, monospace;

            /* Đường cong chuyển động Emil Kowalski */
            --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
            --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
            --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);

            /* Độ nổi tĩnh lặng */
            --radius-panel: 18px;
            --radius-control: 11px;
            --shadow-panel: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 24px 48px -24px rgba(0, 0, 0, 0.78);
            --shadow-control: 0 4px 12px -4px rgba(0, 0, 0, 0.48);
            --shadow-primary: 0 12px 26px -10px rgba(255, 92, 53, 0.48);
        }

        html { scroll-behavior: smooth; }
        ::selection { background: rgba(240, 82, 50, 0.34); color: #FFFFFF; }
        * {
            caret-color: var(--brand-coral-bright);
            scrollbar-width: thin;
            scrollbar-color: rgba(255, 232, 218, 0.24) transparent;
        }
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255, 232, 218, 0.22); border-radius: 999px; }

        html, body { overflow-x: clip !important; }

        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background: linear-gradient(145deg, var(--ground-base) 0%, var(--ground-warm) 52%, var(--ground-soft) 100%) !important;
            color: var(--ink-deep) !important;
            font-family: var(--font-body) !important;
        }

        /* Chừa khoảng thoáng an toàn bên dưới thanh công cụ Streamlit để không bao giờ cắt Masthead */
        [data-testid="stMainBlockContainer"], .block-container {
            position: relative;
            z-index: 2;
            max-width: 1280px;
            padding-top: 3.1rem !important;
            padding-bottom: 2.6rem !important;
        }

        /* Header Streamlit trong suốt hoàn toàn trên nền đen */
        header[data-testid="stHeader"] {
            background: transparent !important;
            backdrop-filter: none !important;
            -webkit-backdrop-filter: none !important;
            border-bottom: none !important;
            height: 2.6rem !important;
            pointer-events: none;
            color: var(--ink-deep) !important;
        }
        [data-testid="stToolbar"] { pointer-events: auto; }
        header[data-testid="stHeader"] button,
        header[data-testid="stHeader"] svg,
        [data-testid="stToolbar"] button,
        [data-testid="stToolbar"] svg {
            color: var(--ink-body) !important;
            fill: var(--ink-body) !important;
        }
        [data-testid="stDecoration"] {
            background: var(--brand-coral) !important;
            height: 2px !important;
        }

        /* Khung Command Console bên trái thoáng đãng */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface-glass) !important;
            backdrop-filter: blur(22px) !important;
            -webkit-backdrop-filter: blur(22px) !important;
            border: 1px solid var(--line-subtle) !important;
            border-radius: var(--radius-panel) !important;
            box-shadow: var(--shadow-panel) !important;
            padding: 24px 26px 20px 26px !important;
        }

        /* === Nền đen nhung tĩnh lặng chỉ 2 vầng sáng ấm dịu === */
        .rs-bg-stage {
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            overflow: hidden;
            background:
                radial-gradient(55% 50% at 8% 10%, rgba(255, 92, 53, 0.09), transparent 65%),
                radial-gradient(48% 46% at 92% 88%, rgba(255, 170, 128, 0.05), transparent 64%);
        }
        .rs-bg-orb {
            position: absolute;
            border-radius: 50%;
            will-change: transform;
        }
        .rs-orb-sunset {
            width: 52vw; height: 52vw; max-width: 680px; max-height: 680px;
            top: -18vw; left: -12vw;
            background: radial-gradient(circle, rgba(255, 92, 53, 0.12) 0%, transparent 70%);
            animation: rsFloatA 20s var(--ease-in-out) infinite alternate;
        }
        .rs-orb-warm {
            width: 46vw; height: 46vw; max-width: 600px; max-height: 600px;
            bottom: -16vw; right: -10vw;
            background: radial-gradient(circle, rgba(255, 180, 140, 0.07) 0%, transparent 70%);
            animation: rsFloatB 24s var(--ease-in-out) infinite alternate;
        }
        .rs-bg-ribbons {
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;
        }

        /* === Keyframes thuần GPU (transform, opacity, stroke-dashoffset) === */
        @keyframes rsFloatA {
            from { transform: translate3d(0, 0, 0) scale(1); }
            to { transform: translate3d(42px, 28px, 0) scale(1.07); }
        }
        @keyframes rsFloatB {
            from { transform: translate3d(0, 0, 0) scale(1); }
            to { transform: translate3d(-38px, 32px, 0) scale(1.06); }
        }
        @keyframes rsFloatC {
            from { transform: translate3d(0, 0, 0) scale(1); }
            to { transform: translate3d(30px, -26px, 0) scale(1.05); }
        }
        @keyframes rsSpinCW {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }
        @keyframes rsSpinCCW {
            from { transform: rotate(360deg); }
            to { transform: rotate(0deg); }
        }
        @keyframes rsShieldDraw {
            from { stroke-dashoffset: 164; }
            to { stroke-dashoffset: 0; }
        }
        @keyframes rsCheckDraw {
            0%, 30% { stroke-dashoffset: 40; opacity: 0; }
            40% { opacity: 1; }
            100% { stroke-dashoffset: 0; opacity: 1; }
        }
        @keyframes rsSheenSweep {
            0%, 16% { transform: translateX(0px) skewX(-20deg); opacity: 0; }
            34% { opacity: 1; }
            58% { transform: translateX(94px) skewX(-20deg); opacity: 0; }
            100% { transform: translateX(94px) skewX(-20deg); opacity: 0; }
        }
        @keyframes rsPulseRing {
            0% { transform: scale(0.92); opacity: 0.56; }
            72% { transform: scale(1.24); opacity: 0; }
            100% { transform: scale(1.24); opacity: 0; }
        }
        @keyframes rsLiveDot {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.45); opacity: 0.45; }
        }
        @keyframes rsPanelReveal {
            from { opacity: 0; transform: translateY(10px) scale(0.985); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes rsBadgeSettle {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }
        @keyframes rsConduitFlow {
            0% { transform: translateX(-100%); opacity: 0; }
            25% { opacity: 1; }
            75% { opacity: 1; }
            100% { transform: translateX(260%); opacity: 0; }
        }
        @keyframes rsGaugeReveal {
            from { transform: scaleX(0.12); opacity: 0.4; }
            to { transform: scaleX(1); opacity: 1; }
        }
        @keyframes rsStrikeIn {
            from { transform: scaleX(0.08); opacity: 0; }
            to { transform: scaleX(1); opacity: 1; }
        }

        .rs-reveal { animation: rsPanelReveal 280ms var(--ease-out) both; }
        .rs-delay-1 { animation-delay: 45ms; }
        .rs-delay-2 { animation-delay: 90ms; }
        .rs-delay-3 { animation-delay: 135ms; }

        .rs-fig { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
        .rs-ic { display: inline-block; vertical-align: middle; flex-shrink: 0; }

        .rs-stars { display: inline-flex; align-items: center; gap: 2px; vertical-align: middle; }
        .rs-star-on { fill: #FFC44D; }
        .rs-star-off { fill: rgba(255, 248, 244, 0.18); }

        /* Kiểm soát tương phản chữ trên nền đen */
        .stApp p:not([class^="rs-"]), .stApp li:not([class^="rs-"]), .stApp label,
        [data-testid="stWidgetLabel"] p,
        [data-testid="stMarkdownContainer"] p:not([class^="rs-"]) {
            color: var(--ink-deep) !important;
        }
        [data-testid="stCaptionContainer"] p { color: var(--ink-muted) !important; }

        /* Segmented Control hiện đại trên nền đen (viên nang Cam san hô nổi bật) */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            background: var(--surface-tint) !important;
            border: 1px solid var(--line-subtle) !important;
            border-radius: 999px !important;
            padding: 4px !important;
            gap: 4px !important;
            width: 100% !important;
            display: flex !important;
            flex-wrap: nowrap !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] {
            flex: 1 1 0 !important;
            justify-content: center !important;
            margin: 0 !important;
            padding: 7px 12px !important;
            border-radius: 999px !important;
            background: transparent !important;
            cursor: pointer !important;
            transition: background-color 180ms var(--ease-out), color 180ms var(--ease-out), transform 140ms var(--ease-out) !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child { display: none !important; }
        div[data-testid="stRadio"] label[data-baseweb="radio"] p,
        div[data-testid="stRadio"] label[data-baseweb="radio"] span {
            color: var(--ink-muted) !important;
            font-weight: 600 !important;
            font-size: 0.83rem !important;
            text-align: center !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
            background: var(--brand-coral) !important;
            box-shadow: 0 6px 16px -6px rgba(240, 82, 50, 0.58) !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p,
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span {
            color: #FFFFFF !important;
            font-weight: 700 !important;
        }
        div[data-testid="stRadio"] label[data-baseweb="radio"]:active { transform: scale(0.97) !important; }
        div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:focus-visible) {
            outline: 2px solid var(--brand-coral) !important;
            outline-offset: 2px !important;
        }

        /* Tabs */
        button[data-baseweb="tab"] {
            background: transparent !important;
            color: var(--ink-muted) !important;
            padding: 10px 18px !important;
            border-radius: 10px 10px 0 0 !important;
            transition: color 180ms var(--ease-out) !important;
        }
        button[data-baseweb="tab"] p { color: var(--ink-muted) !important; font-weight: 600 !important; font-size: 0.91rem !important; }
        button[data-baseweb="tab"][aria-selected="true"] p { color: var(--ink-deep) !important; font-weight: 700 !important; }
        div[data-baseweb="tab-highlight"] {
            background-color: var(--brand-coral) !important;
            height: 3px !important;
            border-radius: 3px 3px 0 0 !important;
        }
        div[data-baseweb="tab-border"] { background-color: var(--line-subtle) !important; }

        /* Nút phụ & nút chính Sunset Coral với ánh quét specular */
        div.stButton > button:not([kind="primary"]),
        button[data-testid="baseButton-secondary"] {
            background: var(--surface-solid) !important;
            color: var(--ink-deep) !important;
            border: 1px solid var(--line-strong) !important;
            border-radius: 12px !important;
            min-height: 40px !important;
            padding: 6px 10px !important;
            box-shadow: var(--shadow-control) !important;
            transition: transform 160ms var(--ease-out), border-color 160ms var(--ease-out), background-color 160ms var(--ease-out) !important;
        }
        div.stButton > button:not([kind="primary"]) p,
        button[data-testid="baseButton-secondary"] p {
            color: var(--ink-deep) !important;
            font-weight: 600 !important;
            font-size: 0.80rem !important;
            line-height: 1.25 !important;
        }
        div.stButton > button:not([kind="primary"]):active,
        button[data-testid="baseButton-secondary"]:active { transform: scale(0.97) !important; }

        div.stButton > button[kind="primary"],
        button[data-testid="baseButton-primary"] {
            position: relative !important;
            overflow: hidden !important;
            background: linear-gradient(135deg, #F05232 0%, #DC3F22 100%) !important;
            color: #FFFFFF !important;
            border: 0 !important;
            border-radius: 14px !important;
            min-height: 48px !important;
            box-shadow: var(--shadow-primary) !important;
            transition: transform 160ms var(--ease-out), box-shadow 180ms var(--ease-out), filter 180ms var(--ease-out) !important;
        }
        div.stButton > button[kind="primary"] p,
        button[data-testid="baseButton-primary"] p {
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: 0.96rem !important;
            letter-spacing: -0.01em !important;
        }
        div.stButton > button[kind="primary"]:active,
        button[data-testid="baseButton-primary"]:active { transform: scale(0.97) !important; }

        button:focus-visible, input:focus-visible, textarea:focus-visible, a:focus-visible {
            outline: 2px solid var(--brand-coral) !important;
            outline-offset: 2px !important;
        }

        /* Ô nhập, selectbox, popover, multiselect, expander */
        textarea, input[type="text"],
        [data-baseweb="textarea"],
        [data-baseweb="textarea"] > div,
        [data-baseweb="base-input"],
        [data-baseweb="select"] > div {
            background-color: var(--surface-solid) !important;
            color: var(--ink-deep) !important;
            border-color: var(--line-strong) !important;
            border-radius: var(--radius-control) !important;
        }
        textarea::placeholder, input::placeholder { color: var(--ink-muted) !important; opacity: 1 !important; }
        [data-baseweb="select"] span,
        [data-baseweb="select"] div,
        [data-baseweb="select"] svg {
            color: var(--ink-deep) !important;
            fill: var(--ink-deep) !important;
        }
        [data-baseweb="popover"], [role="listbox"], [role="option"] {
            background-color: var(--surface-solid) !important;
            color: var(--ink-deep) !important;
        }
        [role="option"]:hover { background-color: var(--brand-coral-soft) !important; color: var(--brand-coral) !important; }
        [data-baseweb="tag"] {
            background-color: var(--brand-coral-soft) !important;
            color: var(--brand-coral) !important;
            border: 1px solid rgba(220, 69, 40, 0.24) !important;
            border-radius: 999px !important;
        }
        [data-baseweb="tag"] span { color: var(--brand-coral) !important; font-weight: 600 !important; }

        [data-testid="stExpander"] {
            background: var(--surface-soft) !important;
            border: 1px solid var(--line-subtle) !important;
            border-radius: 12px !important;
        }
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] svg {
            color: var(--ink-deep) !important;
            fill: var(--ink-deep) !important;
            font-weight: 600 !important;
            font-size: 0.84rem !important;
        }
        .stApp code {
            background: var(--surface-tint) !important;
            color: var(--ink-deep) !important;
            border: 1px solid rgba(220, 69, 40, 0.14) !important;
            padding: 1px 6px !important;
            border-radius: 6px !important;
            font-family: var(--font-mono) !important;
            font-weight: 600 !important;
            font-size: 0.83em !important;
        }
        [data-testid="stCodeBlock"], [data-testid="stCodeBlock"] pre {
            background: var(--surface-solid) !important;
            color: var(--ink-deep) !important;
            border: 1px solid var(--line-subtle) !important;
            border-radius: var(--radius-control) !important;
        }
        [data-testid="stAlert"] {
            background: var(--surface-solid) !important;
            border: 1px solid var(--line-strong) !important;
            border-radius: 13px !important;
            color: var(--ink-deep) !important;
        }

        /* === Logo khiên mua sắm đa lớp === */
        .rs-logo-stage { flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
        .rs-logo-outer-ring { transform-origin: 32px 32px; animation: rsSpinCW 24s linear infinite; }
        .rs-logo-inner-ring { transform-origin: 32px 32px; animation: rsSpinCCW 18s linear infinite; }
        .rs-logo-pulse { transform-origin: 32px 32px; animation: rsPulseRing 3.2s var(--ease-out) infinite; }
        .rs-logo-body { stroke-dasharray: 164; animation: rsShieldDraw 850ms var(--ease-out) both; }
        .rs-logo-check { stroke-dasharray: 40; animation: rsCheckDraw 1050ms var(--ease-out) both; }
        .rs-logo-sheen { animation: rsSheenSweep 4.2s var(--ease-in-out) infinite; }

        /* === Bề mặt kính tối xuyên sáng === */
        .rs-panel {
            background: var(--surface-glass);
            backdrop-filter: blur(22px);
            -webkit-backdrop-filter: blur(22px);
            border: 1px solid var(--line-subtle);
            border-radius: var(--radius-panel);
            box-shadow: var(--shadow-panel);
        }

        /* Floating Dynamic Pill Navbar (Gen Z Consumer App) */
        .rs-masthead {
            display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
            gap: 12px; padding: 9px 20px; margin-bottom: 0;
            border-radius: 999px;
        }
        @media (max-width: 780px) { .rs-masthead { border-radius: 20px; } }
        .rs-brand-lockup { display: flex; align-items: center; gap: 12px; }
        .rs-wordmark {
            font-family: var(--font-display);
            font-size: 1.32rem; font-weight: 800; letter-spacing: -0.03em;
            color: var(--ink-deep); line-height: 1.1;
        }
        .rs-tagline { font-size: 0.80rem; color: var(--ink-muted); margin-top: 2px; font-weight: 500; }
        .rs-meta-chips { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }

        .rs-live-dot {
            width: 7px; height: 7px; border-radius: 999px;
            background: var(--sig-mint);
            display: inline-block;
            animation: rsLiveDot 2.2s var(--ease-in-out) infinite;
        }

        .rs-chip {
            display: inline-flex; align-items: center; gap: 5px;
            padding: 4px 10px; border-radius: 999px;
            background: var(--surface-soft);
            border: 1px solid var(--line-subtle);
            font-size: 0.76rem; font-weight: 600; color: var(--ink-body);
            line-height: 1.2;
        }
        .tone-platform {
            background: var(--brand-coral-soft);
            color: var(--brand-coral);
            border-color: rgba(220, 69, 40, 0.25);
        }

        /* Tiêu đề thoáng, 1 màu nhấn duy nhất */
        .rs-h1 {
            font-family: var(--font-display);
            font-size: clamp(1.9rem, 2.85vw, 2.5rem);
            font-weight: 800; letter-spacing: -0.032em; line-height: 1.12;
            color: var(--ink-deep); margin: 0 0 10px 0;
            text-wrap: balance; overflow-wrap: break-word; min-width: 0;
        }
        .rs-word-accent { color: var(--brand-coral-bright); }
        .rs-lead {
            font-size: 0.90rem; color: var(--ink-muted) !important; line-height: 1.58;
            margin: 0 0 18px 0; max-width: 50ch;
        }
        .rs-h2 {
            font-family: var(--font-display);
            font-size: 1.09rem; font-weight: 700; letter-spacing: -0.02em;
            color: var(--ink-deep); margin: 0;
            text-wrap: balance; overflow-wrap: break-word; min-width: 0;
        }
        .rs-muted-line { font-size: 0.82rem; color: var(--ink-muted) !important; margin: 3px 0 0 0; line-height: 1.46; }
        .rs-panel-title-row {
            display: inline-flex; align-items: center; gap: 7px;
            font-family: var(--font-display); font-size: 0.86rem; font-weight: 700;
            color: var(--ink-deep);
        }
        .rs-console-label {
            font-size: 0.78rem; font-weight: 700; color: var(--ink-muted) !important;
            margin: 10px 0 6px 0;
        }

        /* === Thẻ sản phẩm phong cách Mall (Cột phải Hero) === */
        .rs-verdict-stage { padding: 24px 26px; }
        .rs-verdict-compact { padding: 20px 24px; margin-bottom: 12px; }
        .rs-verdict-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 14px; }
        .rs-product-hero {
            display: grid; grid-template-columns: 152px minmax(0, 1fr);
            gap: 20px; align-items: center; margin-bottom: 18px;
        }
        @media (max-width: 720px) { .rs-product-hero { grid-template-columns: minmax(0, 1fr); } }
        .rs-photo-stage {
            position: relative;
            width: 152px; height: 116px;
            border-radius: 15px; overflow: hidden;
            background: var(--surface-tint);
            box-shadow: 0 12px 24px -12px rgba(48, 22, 14, 0.28);
        }
        .rs-photo-stage-lg { width: 160px; height: 122px; }
        .rs-photo-stage img {
            width: 100%; height: 100%; object-fit: cover; display: block;
            transition: transform 280ms var(--ease-out);
        }
        .rs-photo-pill {
            position: absolute; top: 8px; left: 8px;
            display: inline-flex; align-items: center; gap: 4px;
            padding: 3px 8px; border-radius: 999px;
            background: rgba(35, 24, 22, 0.84);
            color: #FFC44D;
            font-size: 0.73rem; font-weight: 700;
            backdrop-filter: blur(8px);
        }
        .rs-photo-sheen {
            position: absolute; inset: 0;
            background: linear-gradient(115deg, transparent 30%, rgba(255, 255, 255, 0.34) 50%, transparent 70%);
            transform: translateX(-120%);
            transition: transform 480ms var(--ease-out);
            pointer-events: none;
        }
        .rs-product-body { min-width: 0; }
        .rs-product-bar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px; }
        .rs-tag-row { display: flex; flex-wrap: wrap; gap: 6px; }
        .rs-product-title {
            font-family: var(--font-display);
            font-size: 1.14rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.28;
            color: var(--ink-deep); margin: 0 0 5px 0;
            overflow-wrap: break-word; min-width: 0;
        }
        .rs-product-sub { font-size: 0.83rem; color: var(--ink-muted) !important; line-height: 1.46; margin: 0; }

        .rs-verdict-badge {
            display: inline-flex; align-items: center; gap: 5px;
            padding: 5px 12px; border-radius: 999px;
            font-family: var(--font-display); font-size: 0.76rem; font-weight: 700;
            white-space: nowrap;
            animation: rsBadgeSettle 240ms var(--ease-out) both;
        }
        .verdict-mint { background: var(--sig-mint-soft); color: var(--sig-mint); border: 1px solid rgba(52, 211, 153, 0.28); }
        .verdict-coin { background: var(--sig-coin-soft); color: var(--sig-coin); border: 1px solid rgba(234, 179, 8, 0.28); }
        .verdict-coral { background: var(--sig-coral-soft); color: var(--sig-coral); border: 1px solid rgba(255, 107, 74, 0.28); }
        .verdict-sky { background: var(--sig-sky-soft); color: var(--sig-sky); border: 1px solid rgba(122, 162, 196, 0.28); }
        .verdict-quiet { background: var(--surface-soft); color: var(--ink-muted); border: 1px solid var(--line-subtle); }

        /* Dải điểm Espresso ấm (Ready / Static) */
        .rs-lens-band {
            display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1px; background: var(--dark-rule);
            border-radius: 14px; overflow: hidden; margin-bottom: 12px;
            box-shadow: 0 14px 28px -16px rgba(35, 24, 22, 0.56);
        }
        .rs-lens-ready { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        @media (max-width: 640px) { .rs-lens-band { grid-template-columns: minmax(0, 1fr); } }
        .rs-lens-cell {
            background: var(--dark-bg); color: var(--dark-ink);
            padding: 13px 16px; display: flex; flex-direction: column; justify-content: space-between;
        }
        .rs-lens-focus { background: var(--dark-bg-deep); }
        .rs-lens-lbl { font-size: 0.76rem; color: var(--dark-muted); font-weight: 500; }
        .rs-lens-num { font-size: 1.84rem; font-weight: 700; line-height: 1.1; margin: 4px 0 3px 0; color: var(--dark-ink); }
        .rs-lens-num-mint { color: var(--sig-mint-bright); }
        .rs-lens-num-coin { color: var(--sig-coin-bright); }
        .rs-lens-num-coral { color: var(--brand-coral-bright); }
        .rs-lens-unit { font-size: 0.80rem; font-weight: 500; color: var(--dark-muted); }
        .rs-lens-sub { font-size: 0.74rem; color: var(--dark-muted); line-height: 1.35; }

        /* Bong bóng review thật trên sàn ở trạng thái chờ */
        .rs-preview-box {
            background: var(--surface-soft);
            border: 1px solid var(--line-subtle);
            border-radius: 14px; padding: 11px 14px;
        }
        .rs-preview-head {
            display: flex; align-items: center; gap: 6px;
            font-size: 0.77rem; font-weight: 700; color: var(--ink-body);
            margin-bottom: 9px;
        }
        .rs-shop-bubble {
            display: flex; gap: 10px; align-items: flex-start;
            padding: 8px 0; border-top: 1px solid var(--line-subtle);
        }
        .rs-shop-bubble:first-of-type { border-top: none; padding-top: 2px; }
        .rs-shop-bubble:last-child { padding-bottom: 0; }
        .rs-avatar-dot {
            width: 30px; height: 30px; border-radius: 999px; flex-shrink: 0;
            display: inline-flex; align-items: center; justify-content: center;
            background: var(--surface-tint); color: var(--brand-coral);
            font-size: 0.70rem; font-weight: 700;
            border: 1px solid rgba(220, 69, 40, 0.22);
        }
        .rs-bubble-main { min-width: 0; flex: 1; }
        .rs-bubble-top { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; margin-bottom: 3px; }
        .rs-bubble-user { font-size: 0.76rem; font-weight: 700; color: var(--ink-deep); }
        .rs-bubble-rt { font-size: 0.72rem; font-weight: 700; color: var(--sig-coin); }
        .rs-bubble-txt { font-size: 0.81rem; color: var(--ink-body); line-height: 1.44; }

        /* Thước tĩnh dự phòng */
        .rs-ruler-sheet { background: var(--surface-soft); border: 1px solid var(--line-subtle); border-radius: 12px; padding: 12px 15px; }
        .rs-ruler-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 6px; }
        .rs-ruler-title { font-size: 0.80rem; font-weight: 700; color: var(--ink-deep); }
        .rs-ruler-note { font-size: 0.78rem; font-weight: 600; color: var(--ink-muted); }
        .rs-ruler-stage { position: relative; padding: 26px 2px; }
        .rs-ruler-track { position: relative; height: 10px; border-radius: 999px; background: var(--surface-solid); border: 1px solid var(--line-strong); overflow: hidden; }
        .rs-delta-fill { position: absolute; top: 0; bottom: 0; transform-origin: left center; animation: rsGaugeReveal 360ms var(--ease-out) both; }
        .delta-drop { background: linear-gradient(90deg, rgba(220, 69, 40, 0.25), rgba(255, 107, 74, 0.50)); border-left: 2px solid var(--sig-coral); border-right: 2px solid var(--sig-coral); }
        .delta-boost { background: linear-gradient(90deg, rgba(15, 169, 104, 0.22), rgba(56, 219, 148, 0.48)); border-left: 2px solid var(--sig-mint); border-right: 2px solid var(--sig-mint); }
        .delta-near { background: rgba(30, 120, 200, 0.22); border-left: 2px solid var(--sig-sky); border-right: 2px solid var(--sig-sky); }
        .rs-pin-top, .rs-pin-bot { position: absolute; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; pointer-events: none; }
        .rs-pin-top { top: 0; }
        .rs-pin-bot { bottom: 0; }
        .rs-pin-tag-top { padding: 2px 8px; border-radius: 999px; background: var(--surface-solid); border: 1px solid var(--ink-body); font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--ink-deep); white-space: nowrap; }
        .rs-pin-tag-bot { padding: 2px 8px; border-radius: 999px; font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: #141010; white-space: nowrap; }
        .rs-pin-stem { width: 2px; height: 8px; display: block; }
        .stem-ink { background: var(--ink-body); }
        .pin-coral { background: var(--sig-coral); }
        .pin-mint { background: var(--sig-mint); }
        .pin-sky { background: var(--sig-sky); }
        .rs-ruler-ticks { display: flex; justify-content: space-between; font-size: 0.72rem; color: var(--ink-muted); margin-top: 2px; }

        .rs-callout { background: var(--surface-soft); border: 1px solid var(--line-subtle); border-radius: 12px; padding: 11px 14px; font-size: 0.84rem; color: var(--ink-body); line-height: 1.54; margin-top: 10px; }
        .callout-coral { background: var(--sig-coral-soft); border-color: rgba(220, 69, 40, 0.34); color: var(--ink-deep); white-space: pre-line; }
        .rs-pre { white-space: pre-wrap; font-family: var(--font-mono); font-size: 0.79rem; }

        /* Dải 4 bước tinh gọn 1 dòng (thoáng bố cục, ít chữ thừa) */
        .rs-pipeline-slim {
            display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
            gap: 12px 20px; padding: 13px 22px; margin: 22px 0;
        }
        .rs-psteps { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
        .rs-pnode {
            display: inline-flex; align-items: center; gap: 7px;
            font-size: 0.80rem; font-weight: 600; color: var(--ink-muted);
        }
        .rs-pnode.lit { color: var(--ink-deep); }
        .rs-pnode.warn { color: var(--sig-coral); }
        .rs-pdot { width: 7px; height: 7px; border-radius: 999px; background: var(--line-strong); }
        .rs-pnode.lit .rs-pdot { background: var(--brand-coral); }
        .rs-pnode.warn .rs-pdot { background: var(--sig-coral); }
        .rs-pline { position: relative; width: 28px; height: 2px; background: var(--line-subtle); border-radius: 999px; overflow: hidden; }
        .rs-pline.active { background: rgba(255, 92, 53, 0.26); }
        .rs-pbeam { display: none; }
        .rs-pline.active .rs-pbeam {
            display: block; position: absolute; inset: 0; width: 52%;
            background: var(--brand-coral);
            animation: rsConduitFlow 2.1s var(--ease-in-out) infinite;
        }
        .rs-pmeta { font-size: 0.75rem; color: var(--ink-muted); }

        /* Phân bổ 4 tín hiệu */
        .rs-sig-card { padding: 22px 26px; margin-bottom: 22px; }
        .rs-sig-head { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 12px; }
        .rs-count-pill { padding: 4px 11px; border-radius: 999px; background: var(--surface-soft); border: 1px solid var(--line-subtle); font-size: 0.78rem; font-weight: 600; color: var(--ink-deep); }
        .rs-sig-track { display: flex; width: 100%; height: 34px; border-radius: 12px; overflow: hidden; background: var(--surface-tint); }
        .rs-sig-seg {
            display: flex; align-items: center; justify-content: center;
            color: #141010; font-family: var(--font-mono); font-size: 0.76rem; font-weight: 700;
            border-right: 1px solid rgba(11, 9, 9, 0.35);
        }
        .rs-sig-seg:last-child { border-right: none; }
        .rs-sig-legend { display: flex; flex-wrap: wrap; gap: 9px 20px; margin-top: 12px; font-size: 0.82rem; color: var(--ink-deep); }
        .rs-sig-leg { display: inline-flex; align-items: center; gap: 7px; }
        .rs-sig-swatch { width: 11px; height: 11px; border-radius: 4px; display: inline-block; }
        .rs-sig-w { font-size: 0.74rem; color: var(--ink-muted); }

        /* 2 Khối Rủi ro & Câu hỏi */
        .rs-insight-card { padding: 20px 22px; height: 100%; }
        .rs-card-head { display: flex; align-items: flex-start; gap: 11px; margin-bottom: 8px; }
        .rs-icon-badge { width: 36px; height: 36px; border-radius: 12px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; }
        .rs-icon-coral { background: var(--sig-coral-soft); color: var(--sig-coral); }
        .rs-icon-mint { background: var(--sig-mint-soft); color: var(--sig-mint); }

        .rs-ruled-row { padding: 12px 0; border-bottom: 1px solid var(--line-subtle); }
        .rs-ruled-row:last-child { border-bottom: none; padding-bottom: 0; }
        .rs-row-top { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
        .rs-row-title { font-size: 0.92rem; font-weight: 700; color: var(--ink-deep); }
        .rs-row-body { font-size: 0.85rem; color: var(--ink-body); margin-top: 4px; line-height: 1.54; }
        .rs-row-meta { font-size: 0.78rem; color: var(--ink-muted); margin-top: 7px; display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
        .rs-ref-link { text-decoration: none !important; display: inline-flex; align-items: center; transition: transform 140ms var(--ease-out); }
        .rs-ref-link code { background: var(--brand-coral-soft) !important; color: var(--brand-coral) !important; border-color: rgba(220, 69, 40, 0.28) !important; }
        .rs-q-row { display: flex; gap: 11px; align-items: flex-start; }
        .rs-q-idx {
            font-family: var(--font-mono); font-size: 0.75rem; font-weight: 700;
            padding: 3px 9px; border-radius: 999px;
            background: var(--brand-coral-soft); color: var(--brand-coral-bright);
            border: 1px solid rgba(255, 117, 86, 0.30); flex-shrink: 0;
        }

        /* Evidence Feed Cards phong cách Review sàn */
        .rs-ev-feed { display: grid; grid-template-columns: minmax(0, 1fr); gap: 10px; margin-top: 6px; }
        .rs-ev-card {
            background: var(--surface-solid);
            border: 1px solid var(--line-subtle);
            border-radius: 15px;
            padding: 14px 18px;
            box-shadow: 0 8px 20px -14px rgba(48, 22, 14, 0.14);
            scroll-margin-top: 84px;
            transition: transform 180ms var(--ease-out), border-color 180ms var(--ease-out), opacity 180ms var(--ease-out);
        }
        .rs-ev-primary {
            border-color: rgba(56, 219, 148, 0.32);
            box-shadow: 0 12px 26px -16px rgba(56, 219, 148, 0.24);
        }
        .rs-ev-dim { background: rgba(23, 19, 19, 0.66); opacity: 0.80; }
        .rs-ev-card:target {
            border-color: var(--brand-coral-bright);
            box-shadow: 0 0 0 3px rgba(240, 82, 50, 0.28), 0 12px 26px -14px rgba(240, 82, 50, 0.36);
            opacity: 1;
        }
        .rs-ev-top { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 9px; }
        .rs-ev-left, .rs-ev-right { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
        .rs-ev-ground { display: inline-flex; align-items: center; gap: 4px; font-size: 0.73rem; font-weight: 600; color: var(--sig-mint); }
        .rs-ev-w { font-size: 0.74rem; font-weight: 700; padding: 3px 9px; border-radius: 999px; background: var(--surface-tint); color: var(--ink-deep); }
        .rs-ev-quote { font-size: 0.90rem; color: var(--ink-deep); line-height: 1.62; margin-bottom: 10px; }
        .rs-ev-foot { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px 16px; padding-top: 9px; border-top: 1px solid var(--line-subtle); }
        .rs-ev-reason { font-size: 0.80rem; color: var(--ink-muted); line-height: 1.45; }
        .rs-ev-meter-wrap { display: flex; align-items: center; gap: 8px; }
        .rs-ev-wnote { font-size: 0.73rem; color: var(--ink-muted); white-space: nowrap; }
        .rs-ev-meter { width: 74px; height: 6px; border-radius: 999px; background: var(--surface-tint); overflow: hidden; }
        .rs-ev-meter-fill { display: block; height: 100%; border-radius: 999px; }

        /* Tones & highlight trích dẫn nguyên văn */
        .tone-mint { background: var(--sig-mint-soft); color: var(--sig-mint); border-color: rgba(15, 169, 104, 0.28); }
        .tone-coin { background: var(--sig-coin-soft); color: var(--sig-coin); border-color: rgba(217, 134, 7, 0.30); }
        .tone-coral { background: var(--sig-coral-soft); color: var(--sig-coral); border-color: rgba(220, 69, 40, 0.28); }
        .tone-sky { background: var(--sig-sky-soft); color: var(--sig-sky); border-color: rgba(30, 120, 200, 0.28); }

        .mark-mint { background: linear-gradient(180deg, transparent 10%, var(--hl-mint) 10%, var(--hl-mint) 94%, transparent 94%); color: #ECFFF6; font-weight: 600; padding: 0 4px; border-radius: 4px; }
        .mark-coin { background: linear-gradient(180deg, transparent 10%, var(--hl-coin) 10%, var(--hl-coin) 94%, transparent 94%); color: #FFF8E6; font-weight: 600; padding: 0 4px; border-radius: 4px; }
        .mark-coral { background: linear-gradient(180deg, transparent 10%, var(--hl-coral) 10%, var(--hl-coral) 94%, transparent 94%); color: #FFF2EE; font-weight: 600; padding: 0 4px; border-radius: 4px; }
        .mark-sky { background: linear-gradient(180deg, transparent 10%, var(--hl-sky) 10%, var(--hl-sky) 94%, transparent 94%); color: #EEF7FF; font-weight: 600; padding: 0 4px; border-radius: 4px; }

        /* Bảng đối chiếu & WEIGHT_MAP */
        .rs-ledger { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
        .rs-ledger th { text-align: left; padding: 11px 13px; font-size: 0.79rem; font-weight: 600; color: var(--ink-muted); background: var(--surface-soft); border-bottom: 1px solid var(--line-strong); }
        .rs-ledger td { padding: 12px 13px; border-bottom: 1px solid var(--line-subtle); vertical-align: top; color: var(--ink-deep); background: var(--surface-solid); transition: background-color 150ms var(--ease-out); }
        .rs-ledger tbody tr:last-child td { border-bottom: none; }

        .rs-formula-console {
            background: linear-gradient(142deg, var(--dark-bg) 0%, var(--dark-bg-deep) 100%);
            color: var(--dark-ink);
            border-radius: 15px; padding: 17px 20px;
            box-shadow: 0 14px 28px -16px rgba(35, 24, 22, 0.56);
            margin-bottom: 12px;
        }
        .rs-formula-val { font-size: 1.06rem; font-weight: 700; color: var(--sig-coin-bright); margin: 8px 0; }
        .rs-formula-note { font-size: 0.80rem; color: var(--dark-muted); line-height: 1.56; }

        /* Cô lập tương tác :hover trong thiết bị con trỏ chuột (Emil Kowalski rule) */
        @media (hover: hover) and (pointer: fine) {
            .rs-logo-stage:hover .rs-logo-outer-ring { animation-duration: 6s; }
            .rs-photo-stage:hover img { transform: scale(1.04); }
            .rs-photo-stage:hover .rs-photo-sheen { transform: translateX(130%); }
            .rs-step:hover { transform: translateY(-2px); border-color: rgba(220, 69, 40, 0.34); }
            .rs-ev-card:hover { transform: translateY(-2px); opacity: 1; border-color: rgba(220, 69, 40, 0.30); }
            .rs-ref-link:hover { transform: translateY(-1px); }
            .rs-ledger tbody tr:hover td { background: var(--surface-soft); }
            button[data-baseweb="tab"]:hover p { color: var(--ink-deep) !important; }
            div.stButton > button:not([kind="primary"]):hover,
            button[data-testid="baseButton-secondary"]:hover {
                transform: translateY(-2px) !important;
                border-color: var(--brand-coral-bright) !important;
                background: #241D1C !important;
            }
            div.stButton > button[kind="primary"]:hover,
            button[data-testid="baseButton-primary"]:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 16px 30px -10px rgba(220, 69, 40, 0.62) !important;
                filter: brightness(1.04);
            }
        }

        /* Tôn trọng prefers-reduced-motion */
        @media (prefers-reduced-motion: reduce) {
            html { scroll-behavior: auto; }
            .rs-bg-orb, .rs-logo-outer-ring, .rs-logo-inner-ring,
            .rs-logo-pulse, .rs-logo-body, .rs-logo-check,
            .rs-logo-sheen, .rs-conduit-beam, .rs-delta-fill,
            .rs-live-dot, .rs-word-strike::after {
                animation: none !important;
            }
            .rs-reveal, .rs-verdict-badge { animation-duration: 140ms !important; transform: none !important; }
            .rs-photo-stage img, .rs-photo-sheen, .rs-step, .rs-ev-card, div.stButton > button {
                transition: opacity 140ms linear, background-color 140ms linear !important;
            }
            .rs-photo-stage:hover img, .rs-step:hover, .rs-ev-card:hover,
            div.stButton > button:hover, div.stButton > button:active { transform: none !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def run_analysis(raw_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Chạy `answer(text)` có bọc `tracing.begin('app')` / `tracing.end()` an toàn."""
    import tracing
    from agent import answer

    tracing.begin("app")
    try:
        result = answer(raw_text)
    except Exception:
        tracing.end()
        raise
    summary, _ = tracing.end()
    if not isinstance(result, dict):
        result = {"output": str(result)}
    return result, summary


def _render_workspace_blocks(
    st: Any,
    components: Any,
    data: dict[str, Any],
    output_text: str,
    trace_summary: dict[str, Any] | None,
) -> None:
    """Render 4 khối chi tiết bên dưới Hero (Thanh tín hiệu, Rủi ro liên kết chéo & Câu hỏi, Thẻ Review/Bảng, Phép tính)."""
    scores = data.get("scores") or {}
    top_risks = data.get("top_risks") or []
    questions = data.get("questions_for_seller") or []
    reviews = data.get("reviews") or []
    warnings = data.get("warnings") or []
    label_counts = scores.get("label_counts") or {}
    fallback_count = int(data.get("fallback_count", 0))

    if scores.get("logistics_warning"):
        st.info(
            "Phát hiện đánh giá chỉ phản ánh lỗi vận chuyển hoặc shipper. "
            "Hệ thống đã gắn trọng số 0.00 để tách khỏi điểm chất lượng sản phẩm bên trong."
        )
    if warnings:
        with st.expander(f"Cảnh báo tiền xử lý ({len(warnings)})", expanded=False):
            for w in warnings:
                st.write(f"- {w}")

    st.markdown(_render_signal_bar_html(label_counts, len(reviews)), unsafe_allow_html=True)

    col_risk, col_q = st.columns([1.0, 1.0], gap="medium")
    with col_risk:
        risk_rows = []
        if top_risks:
            for idx, risk in enumerate(top_risks, start=1):
                sev = str(risk.get("severity") or "medium").lower()
                sev_vn = {"high": "Mức cao", "medium": "Trung bình", "low": "Mức thấp"}.get(sev, "Trung bình")
                sev_cls = {"high": "tone-coral", "medium": "tone-coin", "low": "tone-sky"}.get(sev, "tone-coin")
                src_links = " ".join(
                    f'<a class="rs-ref-link" href="#{_safe_anchor_id(str(s))}" title="Nhảy tới câu đánh giá {html.escape(str(s))}">'
                    f"<code>{html.escape(str(s))}</code></a>"
                    for s in (risk.get("source_review_ids") or [])
                )
                risk_rows.append(
                    '<div class="rs-ruled-row">'
                    '<div class="rs-row-top">'
                    f'<span class="rs-row-title">{idx}. {html.escape(str(risk.get("title", "")))}</span>'
                    f'<span class="rs-chip {sev_cls}">{sev_vn}</span>'
                    "</div>"
                    f'<div class="rs-row-body">{html.escape(str(risk.get("detail", "")))}</div>'
                    f'<div class="rs-row-meta"><span>Dẫn chứng (bấm tới câu gốc):</span>{src_links}</div>'
                    "</div>"
                )
        else:
            risk_rows.append(
                '<div class="rs-callout">Chưa ghi nhận nhược điểm lặp lại trong nhóm đánh giá trải nghiệm thực tế.</div>'
            )

        st.markdown(
            '<section class="rs-panel rs-insight-card rs-reveal rs-delay-3">'
            '<div class="rs-card-head">'
            f'<div class="rs-icon-badge rs-icon-coral">{_svg_icon("risk", 18)}</div>'
            "<div>"
            '<h2 class="rs-h2">Top 3 điểm cần lưu ý</h2>'
            '<p class="rs-muted-line">Rút riêng từ người mua trải nghiệm thật — bấm mã review để xem đúng câu gốc.</p>'
            "</div>"
            "</div>"
            f'<div>{"".join(risk_rows)}</div>'
            "</section>",
            unsafe_allow_html=True,
        )

    with col_q:
        q_rows = []
        draft_lines = [f"{i}. {q}" for i, q in enumerate(questions, start=1)]
        for idx, q in enumerate(questions, start=1):
            q_rows.append(
                '<div class="rs-ruled-row rs-q-row">'
                f'<span class="rs-q-idx">Q{idx}</span>'
                f'<div class="rs-row-body" style="margin-top:0;">{html.escape(str(q))}</div>'
                "</div>"
            )

        st.markdown(
            '<section class="rs-panel rs-insight-card rs-reveal rs-delay-3">'
            '<div class="rs-card-head">'
            f'<div class="rs-icon-badge rs-icon-mint">{_svg_icon("chat", 18)}</div>'
            "<div>"
            '<h2 class="rs-h2">3 câu nên nhắn hỏi shop</h2>'
            '<p class="rs-muted-line">Bản nháp gợi ý để bạn tự duyệt trước khi nhắn — hệ thống không tự gửi.</p>'
            "</div>"
            "</div>"
            f'<div>{"".join(q_rows)}</div>'
            "</section>",
            unsafe_allow_html=True,
        )
        if draft_lines:
            draft_text = "\n".join(draft_lines)
            components.html(_build_copy_button_html(draft_text), height=52)
            with st.expander("Xem dạng văn bản để sao chép thủ công", expanded=False):
                st.code(draft_text, language=None)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    tab_ev, tab_math = st.tabs(
        [f"Đối chiếu Review & Trích dẫn ({len(reviews)})", "Công thức tính điểm (WEIGHT_MAP)"]
    )

    with tab_ev:
        if fallback_count > 0:
            st.caption(
                f"Grounding Guard đã kích hoạt trích dẫn nguyên văn dự phòng cho {fallback_count}/{len(reviews)} review "
                "để giữ tỷ lệ khớp nguyên văn 100%."
            )

        c_filt, c_view = st.columns([2.2, 1.0], gap="medium")
        with c_filt:
            selected_labels = st.multiselect(
                "Lọc theo nhóm tín hiệu",
                options=list(LABEL_META.keys()),
                default=list(LABEL_META.keys()),
                format_func=lambda k: f"{LABEL_META[k]['name']} ({label_counts.get(k, 0)})",
            )
        with c_view:
            view_mode = st.radio(
                "Kiểu hiển thị dẫn chứng",
                options=["Thẻ trực quan", "Bảng đối chiếu"],
                horizontal=True,
                key="rs_ev_view_mode",
            )

        filtered = [r for r in reviews if r.get("label") in selected_labels]

        if not filtered:
            st.info("Không có đánh giá nào thuộc các nhãn đang chọn.")
        elif view_mode == "Thẻ trực quan":
            st.markdown(_render_evidence_cards_html(filtered), unsafe_allow_html=True)
        else:
            rows_html = []
            for r in filtered:
                lbl = str(r.get("label") or "low_signal")
                meta = LABEL_META.get(lbl, LABEL_META["low_signal"])
                w = WEIGHT_MAP.get(lbl, 0.15)
                rid = str(r.get("id") or "")
                anchor_id = _safe_anchor_id(rid)
                rating_val = r.get("rating", "?")
                stars_txt = f"{rating_val} / 5 sao"
                highlighted = highlight_quote_html(
                    str(r.get("text") or ""),
                    str(r.get("evidence_quote") or ""),
                    mark_class=meta["mark"],
                )
                conf = r.get("confidence")
                conf_txt = f"Tin cậy {int(round(float(conf) * 100))}%" if isinstance(conf, (int, float)) else ""
                fb_txt = (
                    "Trích dẫn dự phòng"
                    if r.get("is_fallback") or r.get("fallback")
                    else "Khớp nguyên văn 100%"
                )
                rows_html.append(
                    f'<tr id="{anchor_id}">'
                    f"<td style='white-space:nowrap;'><code>{html.escape(rid)}</code>"
                    f"<div class='rs-fig' style='font-size:0.78rem;color:var(--ink-body);margin-top:6px;font-weight:600;'>{html.escape(stars_txt)}</div></td>"
                    f"<td><span class='rs-chip {meta['tone_class']}'>{meta['short']}</span>"
                    f"<div class='rs-fig' style='font-size:0.74rem;color:var(--ink-muted);margin-top:6px;'>w={w:.2f} {html.escape(conf_txt)}</div>"
                    f"<div style='font-size:0.72rem;color:var(--sig-mint);margin-top:3px;font-weight:600;'>{fb_txt}</div></td>"
                    f"<td style='line-height:1.62;'>{highlighted}</td>"
                    f"<td style='color:var(--ink-muted);font-size:0.83rem;line-height:1.52;'>{html.escape(str(r.get('short_reason') or ''))}</td>"
                    "</tr>"
                )
            st.markdown(
                '<div class="rs-panel" style="overflow-x:auto;overflow-y:hidden;">'
                '<table class="rs-ledger">'
                "<thead><tr>"
                '<th style="width:105px;">Mã và sao</th>'
                '<th style="width:200px;">Nhãn tín hiệu</th>'
                "<th>Nội dung gốc và trích dẫn nguyên văn (tô sáng)</th>"
                '<th style="width:240px;">Lý do phân loại</th>'
                "</tr></thead>"
                f'<tbody>{"".join(rows_html)}</tbody>'
                "</table></div>",
                unsafe_allow_html=True,
            )

    with tab_math:
        bd = compute_weight_breakdown(reviews)
        c_tbl, c_form = st.columns([1.32, 1.0], gap="medium")
        with c_tbl:
            t_rows = []
            for row in bd["rows"]:
                m = LABEL_META[row["label"]]
                avg_d = f"{row['avg_rating']:.2f}" if row["avg_rating"] is not None else "—"
                t_rows.append(
                    "<tr>"
                    f"<td><span class='rs-chip {m['tone_class']}'>{m['name']}</span></td>"
                    f"<td class='rs-fig' style='text-align:right;font-weight:700;'>{row['weight']:.2f}</td>"
                    f"<td class='rs-fig' style='text-align:right;'>{row['count']}</td>"
                    f"<td class='rs-fig' style='text-align:right;'>{avg_d}</td>"
                    f"<td class='rs-fig' style='text-align:right;'>{row['group_weight']:.2f}</td>"
                    f"<td class='rs-fig' style='text-align:right;font-weight:700;'>{row['group_weighted_sum']:.2f}</td>"
                    "</tr>"
                )
            st.markdown(
                '<div class="rs-panel" style="overflow-x:auto;overflow-y:hidden;">'
                '<table class="rs-ledger">'
                "<thead><tr>"
                '<th>Nhóm nhãn</th><th style="text-align:right;">Trọng số</th><th style="text-align:right;">Số câu</th>'
                '<th style="text-align:right;">Sao TB</th><th style="text-align:right;">Tổng w</th><th style="text-align:right;">Đóng góp</th>'
                "</tr></thead>"
                f'<tbody>{"".join(t_rows)}</tbody>'
                "</table></div>",
                unsafe_allow_html=True,
            )

        with c_form:
            formula_val = (
                f"{bd['total_weighted_sum']:.2f} / {bd['total_weight']:.2f} = {bd['computed_score']:.1f} / 5.0"
                if bd["computed_score"] is not None
                else "Tổng trọng số = 0 → insufficient_data"
            )
            models_used = ", ".join((trace_summary or {}).get("models") or []) or "—"
            st.markdown(
                '<div class="rs-formula-console">'
                '<div style="font-family:var(--font-display);font-size:0.88rem;font-weight:700;">Công thức compute_real_trust_score</div>'
                f'<div class="rs-formula-val rs-fig">{html.escape(formula_val)}</div>'
                '<div class="rs-formula-note">'
                "Mô hình AI chỉ gán 4 nhãn và trích dẫn nguyên văn; toàn bộ điểm tin cậy thực do Python tính tất định.<br/>"
                "Ngưỡng phân mức: high (trải nghiệm thật ≥ 50%, lệch ≤ 0.3, điểm ≥ 4.0), "
                "low (trải nghiệm thật &lt; 35%, lệch ≤ -0.7, hoặc điểm &lt; 3.5)."
                "</div>"
                "</div>"
                '<div class="rs-panel" style="padding:14px 17px;">'
                f'<div class="rs-panel-title-row" style="margin-bottom:7px;">{_svg_icon("cpu", 16)}<span>Nhật ký Trace phiên chạy</span></div>'
                '<div class="rs-fig" style="font-size:0.78rem;color:var(--ink-body);line-height:1.68;">'
                f"Model: {html.escape(models_used)}<br/>"
                f'Số lần gọi model: {(trace_summary or {}).get("model_calls", 0)}<br/>'
                f'Số lần gọi công cụ: {(trace_summary or {}).get("tool_calls", 0)}<br/>'
                f'Token vào / ra: {(trace_summary or {}).get("tokens_in", 0)} / {(trace_summary or {}).get("tokens_out", 0)}'
                "</div></div>",
                unsafe_allow_html=True,
            )

        with st.expander("Xem bản báo cáo văn bản chuẩn (khớp benchmark)", expanded=False):
            st.code(output_text, language=None)


def build_extension_zip_bytes(extension_dir: str = EXTENSION_DIR) -> bytes | None:
    """Đóng gói gọn thư mục Chrome Extension thành bytes `.zip` phục vụ nút tải trên Web."""
    manifest_path = os.path.join(extension_dir, "manifest.json")
    if not os.path.isfile(manifest_path):
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path in EXTENSION_PACKAGE_FILES:
            abs_path = os.path.join(extension_dir, *rel_path.split("/"))
            if os.path.isfile(abs_path):
                zf.write(abs_path, arcname=rel_path)
    return buf.getvalue()


def render_streamlit_app() -> None:
    """Render giao diện demo 1 màn hình ReviewShield trong Streamlit runtime."""
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(
        page_title="ReviewShield — Bóc tách sao ảo. Chốt đơn chuẩn thật.",
        page_icon="R",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_custom_css(st)
    st.markdown(_render_ambient_backdrop_html(), unsafe_allow_html=True)

    try:
        import ai as ai_mod
        is_fake_provider = (getattr(ai_mod, "MODEL_PROVIDER", "fake") or "fake") == "fake"
        provider_label = f"{ai_mod.MODEL_PROVIDER}" + (f" / {ai_mod.MODEL_NAME}" if ai_mod.MODEL_NAME else "")
    except Exception:
        is_fake_provider = True
        provider_label = "chưa cấu hình"

    samples = load_sample_files(SAMPLES_DIR)

    if "rs_sample_idx" not in st.session_state:
        st.session_state["rs_sample_idx"] = 0
    if "rs_custom_text" not in st.session_state:
        st.session_state["rs_custom_text"] = QUICK_PRESETS["seeding"]["payload"]
    if "rs_custom_img" not in st.session_state:
        st.session_state["rs_custom_img"] = ""
    if "rs_result" not in st.session_state:
        st.session_state["rs_result"] = None
    if "rs_trace" not in st.session_state:
        st.session_state["rs_trace"] = None
    if "rs_error" not in st.session_state:
        st.session_state["rs_error"] = None
    if "rs_intro_nonce" not in st.session_state:
        st.session_state["rs_intro_nonce"] = 1
    if "rs_intro_is_replay" not in st.session_state:
        st.session_state["rs_intro_is_replay"] = False

    ext_zip_bytes = build_extension_zip_bytes()

    # Floating Dynamic Pill Navbar + Nút "Tải Extension" & "Xem lại Intro" căn gọn bên phải
    if ext_zip_bytes:
        try:
            nav_main, nav_ext, nav_act = st.columns([5.3, 1.35, 1.05], gap="small", vertical_alignment="center")
        except TypeError:
            nav_main, nav_ext, nav_act = st.columns([5.3, 1.35, 1.05], gap="small")
    else:
        try:
            nav_main, nav_act = st.columns([6.1, 1.05], gap="small", vertical_alignment="center")
        except TypeError:
            nav_main, nav_act = st.columns([6.1, 1.05], gap="small")
        nav_ext = None

    with nav_main:
        st.markdown(
            '<header class="rs-panel rs-masthead rs-reveal">'
            '<div class="rs-brand-lockup">'
            f"{build_animated_logo_svg(size=44)}"
            "<div>"
            '<div class="rs-wordmark">ReviewShield</div>'
            '<div class="rs-tagline">Soi review thật · Tách nhận xu &amp; seeding</div>'
            "</div>"
            "</div>"
            '<div class="rs-meta-chips">'
            '<span class="rs-chip"><span class="rs-live-dot"></span><span>Grounding 100%</span></span>'
            f'<span class="rs-chip rs-fig">{html.escape(provider_label)}</span>'
            "</div>"
            "</header>",
            unsafe_allow_html=True,
        )
    if nav_ext is not None and ext_zip_bytes:
        with nav_ext:
            st.download_button(
                "Tải Extension",
                data=ext_zip_bytes,
                file_name="reviewshield-extension.zip",
                mime="application/zip",
                key="rs_download_ext_nav",
                help="Tải Chrome Extension (Manifest V3) để tự cuộn quét review ngay trên Shopee / Tiki",
                use_container_width=True,
            )
    with nav_act:
        if st.button("Xem lại Intro", key="rs_replay_intro", use_container_width=True):
            st.session_state["rs_intro_nonce"] += 1
            st.session_state["rs_intro_is_replay"] = True

    st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)

    if is_fake_provider:
        st.warning(
            "Đang chạy ở chế độ mô phỏng (`MODEL_PROVIDER=fake`) do chưa cấu hình `.env` "
            "(cần khai báo `MODEL_PROVIDER`, `MODEL_NAME`, `API_KEY` để gọi AI thật trước khi demo)."
        )

    def _clear_analysis_state() -> None:
        st.session_state["rs_result"] = None
        st.session_state["rs_trace"] = None
        st.session_state["rs_error"] = None

    col_left, col_right = st.columns([0.92, 1.18], gap="large")

    with col_left:
        with st.container(border=True):
            st.markdown(
                '<div class="rs-reveal rs-delay-1">'
                '<h1 class="rs-h1">Bóc tách sao ảo.<br/>Chốt đơn <span class="rs-word-accent">chuẩn thật</span>.</h1>'
                '<p class="rs-lead">'
                "Tách đánh giá nhận xu, nghi lặp mẫu và lỗi shipper để trả lại điểm tin cậy thực kèm trích dẫn nguyên văn."
                "</p>"
                "</div>",
                unsafe_allow_html=True,
            )

            mode = st.radio(
                "Nguồn dữ liệu",
                options=["Kho mẫu thật", "Dán review / Kịch bản"],
                horizontal=True,
                label_visibility="collapsed",
                key="rs_input_mode",
                on_change=_clear_analysis_state,
            )

            active_payload = ""
            active_meta: dict[str, Any] = {}

            if mode == "Kho mẫu thật":
                if samples:
                    quick_count = min(4, len(samples))
                    q_cols = st.columns(quick_count)
                    for idx in range(quick_count):
                        sp = samples[idx]
                        btn_label = f"{sp['product_id']} · {sp['platform_rating']}★"
                        if q_cols[idx].button(btn_label, key=f"qsp_{idx}", use_container_width=True):
                            st.session_state["rs_sample_idx"] = idx
                            _clear_analysis_state()

                    if st.session_state["rs_sample_idx"] >= len(samples):
                        st.session_state["rs_sample_idx"] = 0

                    selected_idx = st.selectbox(
                        f"Chọn trong {len(samples)} sản phẩm mẫu",
                        options=list(range(len(samples))),
                        key="rs_sample_idx",
                        on_change=_clear_analysis_state,
                        format_func=lambda i: (
                            f"{samples[i]['product_id']} — {samples[i]['product_name'][:46]}"
                            f"{'…' if len(samples[i]['product_name']) > 46 else ''} "
                            f"({samples[i]['platform_rating']}/5 · {samples[i]['review_count']} câu)"
                        ),
                    )
                    chosen = samples[selected_idx]
                    active_payload = chosen["payload_json"]
                    active_meta = chosen
                else:
                    st.info(
                        "Thư mục data/samples/ chưa có file mẫu. Chuyển sang 'Dán review / Kịch bản' để chạy thử."
                    )
                    active_meta = infer_meta_from_raw_input("")
            else:
                p1, p2, p3 = st.columns(3)
                if p1.button(QUICK_PRESETS["seeding"]["title"], use_container_width=True):
                    st.session_state["rs_custom_text"] = QUICK_PRESETS["seeding"]["payload"]
                    _clear_analysis_state()
                if p2.button(QUICK_PRESETS["shipper"]["title"], use_container_width=True):
                    st.session_state["rs_custom_text"] = QUICK_PRESETS["shipper"]["payload"]
                    _clear_analysis_state()
                if p3.button(QUICK_PRESETS["refusal_link"]["title"], use_container_width=True):
                    st.session_state["rs_custom_text"] = QUICK_PRESETS["refusal_link"]["payload"]
                    _clear_analysis_state()

                active_payload = st.text_area(
                    "Dán JSON sản phẩm hoặc từng dòng dạng [5] nội dung hoặc 5⭐ nội dung",
                    key="rs_custom_text",
                    height=136,
                    on_change=_clear_analysis_state,
                    placeholder="[5] Giao nhanh, chưa dùng nhưng cho 5 sao lấy xu\n1⭐ Pin dùng tầm 1.5 tiếng là sập nguồn...",
                )
                active_meta = infer_meta_from_raw_input(active_payload)

            analyze_clicked = st.button("Soi đánh giá ngay", type="primary", use_container_width=True)

            with st.expander("Tùy chọn nâng cao (JSON đầu vào & URL ảnh)", expanded=False):
                st.text_input(
                    "URL ảnh sản phẩm tùy chọn (bỏ trống để dùng ảnh thật tự động)",
                    key="rs_custom_img",
                    placeholder="https://...",
                )
                if active_payload:
                    st.code(active_payload, language="json")

            if ext_zip_bytes:
                with st.expander("Cài Chrome Extension soi trực tiếp trên Shopee / Tiki (30 giây)", expanded=False):
                    st.markdown(
                        "Tự động cuộn & gom cân bằng đánh giá **5★ + 1–3★** ngay trên trang sản phẩm đang mở, "
                        "ẩn danh **100% PII** tại trình duyệt và gọi AI phân tích ngay trong Side Panel."
                    )
                    st.download_button(
                        "Tải reviewshield-extension.zip",
                        data=ext_zip_bytes,
                        file_name="reviewshield-extension.zip",
                        mime="application/zip",
                        key="rs_download_ext_panel",
                        type="primary",
                        use_container_width=True,
                    )
                    st.markdown(
                        "1. **Giải nén** file `reviewshield-extension.zip` ra một thư mục.\n"
                        "2. Mở Chrome/Edge → truy cập `chrome://extensions` → bật **Chế độ dành cho nhà phát triển (Developer mode)**.\n"
                        "3. Bấm **Tải tiện ích đã giải nén (Load unpacked)** → chọn thư mục vừa giải nén.\n"
                        "4. Mở sản phẩm Shopee / Tiki / Điện Máy Xanh → bấm biểu tượng **ReviewShield** → **Tự động quét review**.\n\n"
                        "Hoặc tải trực tiếp qua API: [`/api/extension/download`](/api/extension/download)"
                    )

    if analyze_clicked:
        st.session_state["rs_error"] = None
        if not (active_payload or "").strip():
            st.session_state["rs_error"] = (
                "Đầu vào đang trống. Hãy chọn một mẫu sản phẩm hoặc dán nội dung đánh giá rồi thử lại."
            )
        else:
            try:
                with st.spinner("Đang bóc tách 4 tín hiệu, khóa trích dẫn nguyên văn và tính điểm tin cậy thực..."):
                    res_now, trace_now = run_analysis(active_payload)
                st.session_state["rs_result"] = res_now
                st.session_state["rs_trace"] = trace_now
            except Exception as exc:
                st.session_state["rs_error"] = f"{type(exc).__name__}: {exc}"

    res = st.session_state.get("rs_result")
    trace_summary = st.session_state.get("rs_trace")
    res_data = res.get("data") if isinstance(res, dict) and isinstance(res.get("data"), dict) else None
    is_refused = bool(res_data and res_data.get("refused"))
    is_success = bool(res_data and isinstance(res_data.get("scores"), dict))

    with col_right:
        if st.session_state.get("rs_error"):
            st.error(
                f"Không thể hoàn tất phân tích ({st.session_state['rs_error']}). "
                "Dữ liệu bạn đã nhập vẫn được giữ nguyên — hãy kiểm tra cấu hình `.env` hoặc thử lại."
            )

        st.markdown(
            _render_dossier_stage_html(
                active_meta,
                custom_image_url=st.session_state.get("rs_custom_img", ""),
                res=res,
                interactive_lens=is_success,
            ),
            unsafe_allow_html=True,
        )
        if is_success:
            components.html(
                _build_interactive_score_lens_html(
                    scores=res_data.get("scores") or {},
                    reviews=res_data.get("reviews") or [],
                    grounding_rate=float(res_data.get("grounding_rate", 100.0)),
                    fallback_count=int(res_data.get("fallback_count", 0)),
                ),
                height=344,
            )

    st.markdown(
        _render_pipeline_bar_html(
            done=is_success,
            refused=is_refused,
            trace_summary=trace_summary,
            review_count=len(res_data.get("reviews") or []) if is_success else 0,
            grounding_rate=float(res_data.get("grounding_rate", 100.0)) if is_success else 100.0,
            real_score=(res_data.get("scores") or {}).get("real_trust_score") if is_success else None,
        ),
        unsafe_allow_html=True,
    )

    if is_success:
        _render_workspace_blocks(
            st,
            components,
            res_data,
            str(res.get("output") or ""),
            trace_summary,
        )
    elif res is not None and not is_refused and not (res_data and res_data.get("error")):
        safe_out = html.escape(str(res.get("output") or "(Không có nội dung phản hồi)"))
        st.markdown(
            '<div class="rs-panel" style="padding:18px 22px;">'
            '<h2 class="rs-h2" style="margin-bottom:8px;">Kết quả phân tích</h2>'
            f'<div class="rs-pre">{safe_out}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

    # Gắn cầu sợi chỉ cuộn Lusion.co + màn Intro ~3.2s ở cuối cây DOM để không tạo khoảng trống thừa dưới Masthead
    components.html(
        _build_lusion_thread_and_intro_bridge_html(
            intro_nonce=int(st.session_state["rs_intro_nonce"]),
            is_replay=bool(st.session_state["rs_intro_is_replay"]),
        ),
        height=0,
    )


def _is_running_in_streamlit() -> bool:
    """Kiểm tra xem code có đang chạy bên trong Streamlit runtime hay không."""
    try:
        from streamlit.runtime import exists

        return bool(exists())
    except Exception:
        return False


def _run_cli_fallback() -> int:
    """Fallback dòng lệnh nếu máy chưa cài Streamlit (giúp `python run.py` không crash)."""
    sys.stdout.write(
        "Chưa cài đặt thư viện 'streamlit'. Chạy lệnh sau để mở giao diện web:\n"
        "  python -m pip install -r requirements.txt\n"
        "Chuyển sang chế độ dòng lệnh tối thiểu (nhấn Ctrl+C để thoát).\n"
    )
    blank = 0
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\n")
            return 0
        if not text:
            blank += 1
            if blank >= 2:
                return 0
            continue
        blank = 0
        try:
            res, summary = run_analysis(text)
        except Exception as exc:
            sys.stdout.write(f"[lỗi] {type(exc).__name__}: {exc}\n")
            continue
        sys.stdout.write(f"{res.get('output', '')}\n")
        models_str = ", ".join(summary.get("models") or []) or "—"
        sys.stdout.write(
            f"   (model: {models_str} | gọi model {summary.get('model_calls', 0)} lần | "
            f"công cụ {summary.get('tool_calls', 0)} lần | "
            f"token vào {summary.get('tokens_in', 0)} / ra {summary.get('tokens_out', 0)})\n"
        )


def main() -> int:
    """Điểm vào khi chạy `python run.py` hoặc `streamlit run codebase/app.py`."""
    if _is_running_in_streamlit():
        render_streamlit_app()
        return 0

    try:
        import streamlit  # noqa: F401
    except ImportError:
        return _run_cli_fallback()

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        os.path.abspath(__file__),
        "--browser.gatherUsageStats=false",
        "--theme.base=dark",
        "--theme.backgroundColor=#09080A",
        "--theme.secondaryBackgroundColor=#171313",
        "--theme.textColor=#FFF8F4",
        "--theme.primaryColor=#F05232",
    ]
    return subprocess.call(cmd, cwd=ROOT_DIR)


if __name__ == "__main__":
    if _is_running_in_streamlit():
        render_streamlit_app()
    else:
        sys.exit(main())
