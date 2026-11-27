"""Hằng số, tính điểm và kiểm dữ liệu dùng chung cho công cụ offline."""

from __future__ import annotations

import csv
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT.parent / "raw_reviews"
SAMPLES_DIR = REPO_ROOT / "data" / "samples"
LABELS_CSV = REPO_ROOT / "eval" / "labels.csv"
BENCH_CSV = REPO_ROOT / "eval" / "benchmark.csv"
EXTRA_CSV = REPO_ROOT / "eval" / "extra_cases.csv"

WEIGHT_MAP = {
    "verified_insight": 1.00,
    "low_signal": 0.15,
    "suspicious_pattern": 0.10,
    "logistics_only": 0.00,
}
LABELS = list(WEIGHT_MAP)
LABEL_ALIASES = dict(zip("vlsg", LABELS)) | {label: label for label in LABELS}
LABEL_ALIASES.update({key.upper(): value for key, value in LABEL_ALIASES.copy().items()})
PLATFORMS = {"Shopee", "Tiki", "TikTok Shop", "Lazada", "Điện Máy Xanh", "Thế Giới Di Động"}
DIRECTIONS = {
    "near_platform", "lower_than_platform", "higher_than_platform", "insufficient_data",
}
LABEL_FIELDS = ["product_id", "review_id", "rating", "label", "picked", "type"]
BENCH_FIELDS = ["id", "input", "expected", "pass_criterion", "type", "source"]

# Giữ regex và cách bỏ email trước khi dò URL/@handle từ tools_tuong/check_samples.py.
PHONE = re.compile(r"(?<!\d)(?:\+?84|0)[\s.\-]?\d(?:[\s.\-]?\d){8,9}(?!\d)")
EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
URL = re.compile(r"https?://|www\.|\b[\w\-]+\.(?:com|vn|net)\b", re.I)
LONG_DIGITS = re.compile(r"\d{9,}")
AT_HANDLE = re.compile(r"(?<![\w])@[A-Za-z0-9_.]{3,}")


def pii_hits(text: str) -> list[str]:
    """Trả các loại PII nghi vấn; không đưa giá trị nhạy cảm vào thông báo."""
    no_email = EMAIL.sub(" ", text)
    checks = (
        ("SĐT", PHONE, text), ("email", EMAIL, text),
        ("link/tên miền", URL, no_email),
        ("dãy ≥9 chữ số (mã đơn/SĐT?)", LONG_DIGITS, text),
        ("@tên tài khoản", AT_HANDLE, no_email),
    )
    return [name for name, regex, source in checks if regex.search(source)]


def norm_text(s: str) -> str:
    """Chuẩn hóa NFC, chữ thường và khoảng trắng để so khớp trích dẫn."""
    return " ".join(unicodedata.normalize("NFC", s).lower().split())


def compute_score(
    reviews: list[dict[str, Any]], platform_rating: float | None = None,
) -> dict[str, Any]:
    """Tính điểm tất định từ rating/nhãn chuẩn; danh sách rỗng là thiếu dữ liệu."""
    counts = dict.fromkeys(LABELS, 0)
    for review in reviews:
        rating, label = review["rating"], review["label"]
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            raise ValueError("rating phải là số nguyên 1–5")
        if label not in WEIGHT_MAP:
            raise ValueError(f"nhãn không hợp lệ: {label!r}")
        counts[label] += 1
    if platform_rating is None:
        platform_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else None
    elif isinstance(platform_rating, bool) or not isinstance(platform_rating, (int, float)) or not 1 <= platform_rating <= 5:
        raise ValueError("platform_rating phải là số trong [1.0, 5.0]")
    total_weight = math.fsum(WEIGHT_MAP[r["label"]] for r in reviews)
    weighted_sum = math.fsum(r["rating"] * WEIGHT_MAP[r["label"]] for r in reviews)
    ratio = round(100 * counts["verified_insight"] / len(reviews), 1) if reviews else 0.0
    real = round(weighted_sum / total_weight, 1) if total_weight else None
    delta = round(real - platform_rating, 1) if real is not None else None
    if delta is None:
        direction = trust = "insufficient_data"
    else:
        direction = "near_platform" if abs(delta) <= 0.3 else (
            "lower_than_platform" if delta < -0.3 else "higher_than_platform"
        )
        if ratio >= 50 and abs(delta) <= 0.3 and real >= 4:
            trust = "high"
        elif ratio < 35 or delta <= -0.7 or real < 3.5:
            trust = "low"
        else:
            trust = "medium"
    return {
        "platform_rating": platform_rating, "real_trust_score": real,
        "score_delta": delta, "direction": direction, "verified_ratio": ratio,
        "trust_level": trust, "label_counts": counts,
        "logistics_warning": counts["logistics_only"] > 0 or total_weight == 0,
    }


def read_csv_rows(path: Path, fields: list[str]) -> list[dict[str, str]]:
    """Đọc CSV UTF-8 có/không BOM và kiểm đủ cột, số ô từng dòng."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != fields:
            raise ValueError(f"{path}: cột CSV phải đúng thứ tự {','.join(fields)}")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"{path}: dòng {reader.line_num} sai số ô")
            rows.append(row)
        return rows


def read_labels(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    """Đọc nhãn chuẩn; chấp nhận nhãn trống đang chờ gán, cấm khóa trùng."""
    result = {}
    for line, row in enumerate(read_csv_rows(path, LABEL_FIELDS), 2):
        prefix = f"{path}: dòng {line}"
        if not re.fullmatch(r"sp_\d{2}", row["product_id"]) or not re.fullmatch(r"r[1-9]\d*", row["review_id"]):
            raise ValueError(f"{prefix}: product_id/review_id sai định dạng")
        if row["rating"] not in {"1", "2", "3", "4", "5"}:
            raise ValueError(f"{prefix}: rating phải là số nguyên 1–5")
        if row["label"] not in ["", *LABELS]:
            raise ValueError(f"{prefix}: nhãn không hợp lệ")
        if row["picked"] not in {"natural", "added"} or row["type"] not in {"thuong", "kho"}:
            raise ValueError(f"{prefix}: picked/type không hợp lệ")
        key = (row["product_id"], row["review_id"])
        if key in result:
            raise ValueError(f"{prefix}: khóa nhãn trùng {key}")
        result[key] = row
    return result


def scored_reviews(
    product: dict[str, Any], labels: dict[tuple[str, str], dict[str, str]],
) -> tuple[list[dict[str, Any]], set[str]]:
    """Đối chiếu từng review với CSV; trả review đã gán nhãn và tập type."""
    scored, types = [], set()
    for review in product["reviews"]:
        key = (product["product_id"], review["id"])
        if key not in labels:
            raise ValueError(f"thiếu dòng label cho {key[0]}/{key[1]}")
        row = labels[key]
        if int(row["rating"]) != review["rating"]:
            raise ValueError(f"rating trong labels.csv lệch ở {key[0]}/{key[1]}")
        types.add(row["type"])
        if row["label"]:
            scored.append({"rating": review["rating"], "label": row["label"]})
    if len(types) > 1:
        raise ValueError(f"{product['product_id']}: type không thống nhất trong labels.csv")
    return scored, types
