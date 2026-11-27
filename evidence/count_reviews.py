"""Đếm A–D từ mẫu/nhãn chuẩn, xuất Markdown để kiểm tay và dán báo cáo."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data" / "scripts"))
from common import LABELS_CSV, SAMPLES_DIR, compute_score, read_labels, scored_reviews

D_PATTERN = re.compile(
    r"(chưa dùng|chưa sử dụng|chưa xài|chưa dung|chua dung|chua su dung|lấy xu|nhận xu|lay xu|nhan xu)",
    re.IGNORECASE,
)


def load_data(samples: Path, labels_path: Path) -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[str]
]:
    """Ghép review/nhãn; trả sản phẩm, review và cảnh báo thiếu nhãn."""
    if not samples.is_dir():
        raise ValueError(f"Không tìm thấy thư mục mẫu: {samples}")
    labels = read_labels(labels_path)
    products: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for path in sorted(samples.glob("*.json")):
        product = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(product, dict) or not re.fullmatch(r"sp_\d{2}", str(product.get("product_id", ""))):
            raise ValueError(f"{path}: product_id không hợp lệ")
        pid = product["product_id"]
        if pid in seen or not isinstance(product.get("reviews"), list):
            raise ValueError(f"{path}: sản phẩm trùng hoặc reviews không phải danh sách")
        seen.add(pid)
        ids: set[str] = set()
        for review in product["reviews"]:
            if not isinstance(review, dict) or not re.fullmatch(r"r[1-9]\d*", str(review.get("id", ""))):
                raise ValueError(f"{path}: review id không hợp lệ")
            rid = review["id"]
            if rid in ids or not isinstance(review.get("text"), str):
                raise ValueError(f"{pid}/{rid}: id trùng hoặc text không phải chuỗi")
            ids.add(rid)
            rating = review.get("rating")
            if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
                raise ValueError(f"{pid}/{rid}: rating phải là số nguyên 1–5")
        scored, _ = scored_reviews(product, labels)
        complete = len(scored) == len(product["reviews"])
        direction = None
        if complete:
            direction = compute_score(scored, product["platform_rating"])["direction"]
        else:
            warnings.append(
                f"CẢNH BÁO: {pid} thiếu {len(product['reviews']) - len(scored)} nhãn; "
                "bỏ toàn bộ sản phẩm khỏi A/B/C, vẫn tính D."
            )
        products.append({"product_id": pid, "complete": complete, "direction": direction})
        for review in product["reviews"]:
            row = labels[(pid, review["id"])]
            reviews.append({**review, "product_id": pid, "label": row["label"],
                            "picked": row["picked"], "complete": complete})
    products.sort(key=lambda p: p["product_id"])
    reviews.sort(key=lambda r: (r["product_id"], int(r["id"][1:])))
    return products, reviews, warnings


def render_report(
    products: list[dict[str, Any]], reviews: list[dict[str, Any]], warnings: list[str],
) -> str:
    """Tính tử/mẫu số đúng tập lọc và chọn tối đa tám ví dụ tất định."""
    eligible = [r for r in reviews if r["complete"]]
    a_base = [r for r in eligible if r["rating"] == 5 and r["picked"] == "natural"]
    a_hits = [r for r in a_base if r["label"] in {"low_signal", "suspicious_pattern"}]
    b_all = [r for r in eligible if r["rating"] <= 2]
    b_natural = [r for r in b_all if r["picked"] == "natural"]
    b_hits = [r for r in b_all if r["label"] == "logistics_only"]
    b_natural_hits = [r for r in b_hits if r["picked"] == "natural"]
    c_base = [p for p in products if p["complete"]]
    c_hits = {p["product_id"] for p in c_base if p["direction"] == "lower_than_platform"}
    insufficient = sum(p["direction"] == "insufficient_data" for p in c_base)
    d_base = [r for r in reviews if r["rating"] == 5]
    d_hits = [r for r in d_base if D_PATTERN.search(unicodedata.normalize("NFC", r["text"]))]
    natural = sum(r["picked"] == "natural" for r in reviews)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    lines = [
        f"Chạy lúc {stamp}, trên {len(products)} sản phẩm, {len(reviews)} review "
        f"(natural {natural}, added {len(reviews) - natural})",
        "", *warnings, "", "| Đếm gì | x / N | % | Ghi chú |", "|---|---|---|---|",
    ]
    metrics = [
        ("A", len(a_hits), len(a_base), "Review 5★ natural; low_signal hoặc suspicious_pattern"),
        ("B-natural", len(b_natural_hits), len(b_natural), "Review 1–2★ natural; logistics_only"),
        ("B-natural+added", len(b_hits), len(b_all), "Review 1–2★ gồm added; không phải tỷ lệ tự nhiên"),
        ("C", len(c_hits), len(c_base), "Sản phẩm đủ nhãn; tính cả added; "
         f"insufficient_data: {insufficient} sản phẩm (vẫn trong mẫu số)"),
        ("D", len(d_hits), len(d_base), "Review 5★ natural+added; khớp regex NFC, không cần nhãn"),
    ]
    for name, count, total, note in metrics:
        percent = f"{100 * count / total:.1f}%" if total else "không có mẫu để tính"
        lines.append(f"| {name} | {count} / {total} | {percent} | {note} |")
    lines.extend(["", "A và D không chứng minh review giả.", "", "### Ví dụ nguyên văn", ""])
    examples: list[dict[str, Any]] = []
    used: set[tuple[str, str]] = set()
    for candidates, limit in (
        (a_hits, 2), (b_hits, 2), (d_hits, 2),
        ([r for r in reviews if r["product_id"] in c_hits], 8),
    ):
        taken = 0
        for review in candidates:
            key = (review["product_id"], review["id"])
            if key in used:
                continue
            if taken >= limit or len(examples) >= 8:
                break
            used.add(key)
            examples.append(review)
            taken += 1
    for r in examples:
        lines.append(f"- {r['product_id']}/{r['id']} · {r['rating']}★ · {r['picked']} · "
                     f"{r['label'] or '(chưa gán nhãn)'} · \"{r['text']}\"")
    if not examples:
        lines.append("Không có review phù hợp để minh họa A/B/D/C.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Đọc dữ liệu và in báo cáo; chỉ ghi file khi có --md."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, default=SAMPLES_DIR, help="Thư mục mẫu JSON")
    parser.add_argument("--labels", type=Path, default=LABELS_CSV, help="CSV nhãn chuẩn")
    parser.add_argument("--md", type=Path, help="Ghi thêm báo cáo Markdown vào file riêng")
    args = parser.parse_args(argv)
    try:
        if args.md and args.md.resolve() == Path(__file__).with_name("data-mining.md").resolve():
            raise ValueError("Không ghi trực tiếp data-mining.md; hãy chọn file báo cáo riêng")
        report = render_report(*load_data(args.samples, args.labels))
        if args.md:
            args.md.write_text(report, encoding="utf-8")
        print(report, end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
