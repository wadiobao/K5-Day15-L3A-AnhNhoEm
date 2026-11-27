"""Chuyển file review thô thành mẫu ẩn danh và CSV nhãn, không gọi AI."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from .common import (LABEL_ALIASES, LABEL_FIELDS, LABELS_CSV, PLATFORMS,
                         RAW_DIR, SAMPLES_DIR, compute_score, pii_hits)
except ImportError:
    from common import (LABEL_ALIASES, LABEL_FIELDS, LABELS_CSV, PLATFORMS,
                        RAW_DIR, SAMPLES_DIR, compute_score, pii_hits)

HEADERS = {"product_name", "platform", "category", "platform_rating", "type"}
MARKDOWN_HEADERS = {
    "tên sản phẩm": "product_name", "sàn": "platform", "ngành hàng": "category",
    "điểm sao": "platform_rating", "loại câu": "type",
}
def platform_key(value: str) -> str:
    """Bỏ dấu, chuẩn hóa hoa/thường và khoảng trắng của tên sàn."""
    folded = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return " ".join("".join(char for char in folded if not unicodedata.combining(char)).split())


PLATFORM_ALIASES = {platform_key(platform): platform for platform in PLATFORMS} | {
    "tiktok": "TikTok Shop", "dienmayxanh": "Điện Máy Xanh",
    "thegioididong": "Thế Giới Di Động", "tgdd": "Thế Giới Di Động",
}


def markdown_cells(raw: str) -> list[str]:
    """Tách ô tại pipe không escape, bỏ viền bảng và giữ pipe đã escape trong ô."""
    cells, current = [], []
    backslashes = 0
    line = raw.strip()
    trailing_border = False
    for char in line:
        trailing_border = char == "|" and backslashes % 2 == 0
        if char == "|":
            if backslashes % 2:
                current.pop()
                current.append("|")
            else:
                cells.append("".join(current).strip())
                current = []
        else:
            current.append(char)
        backslashes = backslashes + 1 if char == "\\" else 0
    cells.append("".join(current).strip())
    if cells and line.startswith("|"):
        cells.pop(0)
    if cells and trailing_border:
        cells.pop()
    return cells


def read_markdown(
    path: Path, lines: list[str], error: Callable[[int, str], None], warnings: list[str],
) -> tuple[dict[str, str], dict[str, int], list[tuple[int, str, str, str, str]], int]:
    """Đọc hai bảng Markdown; giữ số dòng gốc, sao/nhãn chờ kiểm chung với TXT."""
    headers: dict[str, str] = {}
    header_lines: dict[str, int] = {}
    rows: list[tuple[int, str, str, str, str]] = []
    table = ""
    columns: list[str] = []
    review_line = len(lines) + 1
    for line_number, raw in enumerate(lines, 1):
        if "|" not in raw:
            table = ""
            continue
        cells = markdown_cells(raw)
        if not cells or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        names = [" ".join(unicodedata.normalize("NFC", cell).casefold().split()) for cell in cells]
        if names[0] == "mục":
            table = "info"
            continue
        if {"sao", "v", "l", "s", "g"} <= set(names):
            table, columns, review_line = "reviews", names, line_number
            required = ["sao", "v", "l", "s", "g"]
            if any(names.count(name) != 1 for name in required) or names[-1] in required:
                error(line_number, "bảng review phải có mỗi cột Sao/V/L/S/G đúng một lần và nội dung ở cuối")
                table = ""
            continue
        if table == "info":
            key = next((value for prefix, value in MARKDOWN_HEADERS.items() if names[0].startswith(prefix)), None)
            if key is None:
                continue
            value = unicodedata.normalize("NFC", cells[1]) if len(cells) == 2 else ""
            if key in header_lines:
                error(line_number, f"header lạ, trùng hoặc rỗng: {key!r}")
                continue
            header_lines[key] = line_number
            if not value:
                continue
            for kind in pii_hits(value):
                error(line_number, f"header {key}: nghi PII — {kind}")
            if key == "platform":
                value = PLATFORM_ALIASES.get(platform_key(value), value)
            elif key == "platform_rating":
                value = value.replace(",", ".")
            headers[key], header_lines[key] = value, line_number
        elif table == "reviews":
            if len(cells) > len(columns):
                cells = cells[:len(columns) - 1] + ["|".join(cells[len(columns) - 1:])]
                warnings.append(f"{path.name}: dòng {line_number}: thừa ô do dấu | chưa escape; đã ghép vào nội dung")
            if len(cells) != len(columns):
                error(line_number, "dòng review sai số ô so với tiêu đề bảng")
                continue
            values = dict(zip(columns, cells))
            star, text = values["sao"], cells[-1]
            if not star and not text:
                continue
            checked = [name for name in "vlsg" if values[name]]
            if len(checked) > 1:
                error(line_number, "chỉ được tích một nhãn V/L/S/G")
            alias = checked[0] if len(checked) == 1 else "?"
            picked = "added" if any(value for name, value in values.items() if name.startswith("lọc")) else "natural"
            rows.append((line_number, star, alias, text, picked))
    if review_line == len(lines) + 1:
        error(review_line, "thiếu bảng review có cột Sao/V/L/S/G và nội dung ở cuối")
    return headers, header_lines, rows, review_line


def parse_raw(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[str], list[str]]:
    """Đọc sản phẩm; None không lỗi là bảng trống, các lỗi khác giữ số dòng gốc."""
    errors: list[str] = []
    warnings: list[str] = []
    headers: dict[str, str] = {}
    header_lines: dict[str, int] = {}
    reviews, labels = [], []
    separated = False
    review_rows: list[tuple[int, str, str, str, str]] = []

    def error(line: int, message: str) -> None:
        """Gắn tên file và số dòng vào lỗi."""
        errors.append(f"{path.name}: dòng {line}: {message}")

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not re.fullmatch(r"sp_\d{2}", path.stem):
        error(1, "tên file phải có dạng sp_XX.txt hoặc sp_XX.md")
    separator_line = len(lines) + 1
    is_markdown = path.suffix == ".md"
    if is_markdown:
        headers, header_lines, review_rows, separator_line = read_markdown(path, lines, error, warnings)
        if separator_line <= len(lines) and not review_rows and not errors:
            return None, [], [], [f"{path.name}: chưa điền bảng review"]
        separated = True
    raw_lines = [] if is_markdown else lines
    for line_number, raw in enumerate(raw_lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not separated:
            if line == "---":
                separated, separator_line = True, line_number
                continue
            if ":" not in line:
                error(line_number, "header phải có dạng key: value (hoặc thiếu dòng ---)")
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            value = unicodedata.normalize("NFC", value)
            if key not in HEADERS or key in headers or not value:
                error(line_number, f"header lạ, trùng hoặc rỗng: {key!r}")
                continue
            if key == "platform":
                value = PLATFORM_ALIASES.get(platform_key(value), value)
            headers[key], header_lines[key] = value, line_number
            for kind in pii_hits(value):
                error(line_number, f"header {key}: nghi PII — {kind}")
            continue
        parts = raw.split("|", 2)
        if len(parts) != 3:
            error(line_number, "review phải có dạng <sao> | <nhãn> | <nguyên văn>")
            continue
        star, alias, text = (part.strip() for part in parts)
        review_rows.append((line_number, star, alias, text, "added" if star.startswith("+") else "natural"))
    for line_number, star, alias, text, picked in review_rows:
        text = unicodedata.normalize("NFC", text)
        valid = True
        match = re.fullmatch(r"([1-5])(?:\s*(?:★|sao))?" if is_markdown else r"\+?([1-5])", star, re.I)
        if not match:
            error(line_number, "rating phải là 1–5 (vd 5, 5★, 5 sao)" if is_markdown else
                  "rating phải là 1–5, có thể có tiền tố +")
            valid = False
        label = "" if alias == "?" else LABEL_ALIASES.get(alias.lower())
        if label is None:
            error(line_number, f"nhãn lạ: {alias!r}; dùng V/L/S/G, tên đầy đủ hoặc ?")
            valid = False
        if not text:
            error(line_number, "text rỗng")
            valid = False
        for kind in pii_hits(text):
            error(line_number, f"nghi PII — {kind}")
            valid = False
        if not valid:
            continue
        index = len(reviews) + 1
        rating = int(match.group(1))
        reviews.append({"id": f"r{index}", "author": f"user_{index:02d}", "rating": rating, "text": text})
        labels.append({"product_id": path.stem, "review_id": f"r{index}", "rating": rating,
                       "label": label, "picked": picked,
                       "type": headers.get("type", "")})
    if not separated:
        error(separator_line, "thiếu dòng phân cách ---")
    for key in sorted(HEADERS - headers.keys()):
        error(header_lines.get(key, separator_line), f"thiếu header {key}")
    if "platform" in headers and headers["platform"] not in PLATFORMS:
        error(header_lines["platform"], "platform phải thuộc: " + ", ".join(sorted(PLATFORMS)))
    if "type" in headers and headers["type"] not in {"thuong", "kho"}:
        error(header_lines["type"], "type phải là thuong hoặc kho")
    if "category" in headers and not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", headers["category"]):
        error(header_lines["category"], "category phải là snake_case không dấu")
    try:
        platform_rating = float(headers.get("platform_rating", ""))
        if not 1 <= platform_rating <= 5:
            raise ValueError
    except ValueError:
        platform_rating = None
        error(header_lines.get("platform_rating", separator_line), "platform_rating phải là số trong [1.0, 5.0]")
    if not reviews:
        error(separator_line, "không có review hợp lệ")
    if errors:
        return None, [], errors, warnings
    if not 6 <= len(reviews) <= 15:
        warnings.append(f"{path.name}: có {len(reviews)} review, khuyến nghị 6–15")
    absent = sorted(set(range(1, 6)) - {r["rating"] for r in reviews})
    if absent:
        warnings.append(f"{path.name}: thiếu mức sao {', '.join(map(str, absent))}")
    scored = [{"rating": row["rating"], "label": row["label"]} for row in labels if row["label"]]
    if len(scored) != len(reviews):
        warnings.append(f"{path.name}: còn {len(reviews) - len(scored)} nhãn ?; expected_direction tạm tính trên nhãn đã gán")
    product = {"product_id": path.stem, **{key: headers[key] for key in ("product_name", "category", "platform")},
               "platform_rating": platform_rating,
               "expected_direction": compute_score(scored, platform_rating)["direction"], "reviews": reviews}
    return product, labels, errors, warnings


def main(argv: list[str] | None = None) -> int:
    """Chạy chuyển đổi; mã 1 nếu bất kỳ sản phẩm nào lỗi, mã 0 nếu hợp lệ."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=RAW_DIR, help="Thư mục review thô")
    parser.add_argument("--out-samples", type=Path, default=SAMPLES_DIR, help="Thư mục mẫu JSON")
    parser.add_argument("--out-labels", type=Path, default=LABELS_CSV, help="CSV nhãn chuẩn")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ báo cáo, không ghi file")
    args = parser.parse_args(argv)
    if not args.raw.is_dir():
        print(f"LỖI: không tìm thấy thư mục thô {args.raw}")
        return 1
    paths_by_id: dict[str, list[Path]] = {}
    for path in sorted(args.raw.iterdir()):
        if not path.is_file() or path.suffix not in {".txt", ".md"}:
            continue
        if not re.fullmatch(r"sp_\d{2}", path.stem) or "MAU" in path.name.upper():
            print(f"Bỏ qua {path.name} (không phải file dữ liệu)")
            continue
        paths_by_id.setdefault(path.stem, []).append(path)
    if not paths_by_id:
        print("Chưa có file thô để xử lý; không ghi file nào.")
        return 0
    all_labels, products = [], []
    failed = 0
    for product_id, paths in paths_by_id.items():
        if len(paths) > 1:
            failed += 1
            print(f"LỖI: {product_id}: trùng mã sản phẩm ở {', '.join(path.name for path in paths)}; không ghi sản phẩm này.")
            continue
        path = paths[0]
        try:
            product, rows, errors, warnings = parse_raw(path)
        except (OSError, UnicodeError) as exc:
            product, rows, errors, warnings = None, [], [f"{path.name}: không đọc được UTF-8: {exc}"], []
        for message in errors:
            print(f"LỖI: {message}")
        if product is None and not errors:
            print(f"Bỏ qua {path.name}: chưa điền bảng review; không ghi JSON, không đưa vào labels.csv.")
            continue
        for message in warnings:
            print(f"CẢNH BÁO: {message}")
        if product is None:
            failed += 1
            print(f"Bỏ qua {path.name}; không ghi JSON, không đưa vào labels.csv. JSON cũ (nếu có) được giữ nguyên.")
        else:
            products.append(product)
            all_labels.extend(rows)
    if not args.dry_run:
        args.out_samples.mkdir(parents=True, exist_ok=True)
        args.out_labels.parent.mkdir(parents=True, exist_ok=True)
        for product in products:
            target = args.out_samples / f"{product['product_id']}.json"
            target.write_text(json.dumps(product, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        with args.out_labels.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=LABEL_FIELDS)
            writer.writeheader()
            writer.writerows(all_labels)
    print(f"{'DỰ KIẾN' if args.dry_run else 'Đã xử lý'}: {len(products)} sản phẩm hợp lệ, {failed} sản phẩm lỗi, {len(all_labels)} dòng nhãn.")
    if args.dry_run:
        print("Chạy thử: không ghi file nào.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
