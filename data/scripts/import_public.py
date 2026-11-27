#!/usr/bin/env python3
"""Chọn tất định và nhập review công khai từ JSONL ngoài repo, chỉ dùng stdlib.

Nhóm ứng viên là tín hiệu từ khóa, không phải nhãn chuẩn hay chiều điểm đã chấm.
Tỷ lệ không dấu = số chữ cái ASCII / tổng chữ cái (không tính số, dấu câu).
Các chỉ số dùng 12 review không rỗng đầu tiên; không lọc sao hay PII để xếp nhóm.
Khi xuất, bỏ review nghi PII và lấy review kế tiếp theo row_order.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

try:
    from .common import RAW_DIR, pii_hits
    from .make_samples import markdown_cells, parse_raw
except ImportError:
    from common import RAW_DIR, pii_hits
    from make_samples import markdown_cells, parse_raw

SOURCES = {"dienmayxanh": "Điện Máy Xanh", "thegioididong": "Thế Giới Di Động"}
QUOTAS = {"higher": 4, "near": 6, "lower": 4, "kho": 2}  # 16 sp: bộ dữ liệu chỉ có 4 ứng viên higher
LOGISTICS = re.compile(
    r"giao|ship|vận chuyển|lắp|lap dat|nhân viên|nv |kỹ thuật|ky thuat|hẹn|trễ|tre hen|chậm|cham", re.I,
)
FAULT = re.compile(r"hỏng|hư|lỗi|loi|rò|ro ri|kêu|ồn|nóng|chập|không chạy|ko chạy|bể|vỡ|nứt", re.I)
# Chỉ phần xưng hô không phân biệt hoa thường; tên phải viết hoa chữ cái đầu.
UPPER = "A-ZÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬĐÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴ"
NAME_WORD = rf"[{UPPER}][^\W\d_]*"
PERSON = re.compile(
    rf"\b(?P<title>(?i:nhân viên|kỹ thuật|kĩ thuật|bên lắp|anh|chị|chi|em|bạn|cô|chú|bác|nv|kt))"
    rf"\s+(?P<name>{NAME_WORD}(?:\s+{NAME_WORD}){{0,2}})\b",
)


@dataclass
class Candidate:
    """Sản phẩm có metadata nhất quán và ít nhất 12 review không rỗng."""
    source: str
    product_id: str
    product: str
    category: str
    reviews: list[dict[str, Any]]
    platform_rating: float
    low: int
    logistics: int
    logistics_only: int
    faults: int
    mean_length: float
    unaccented: float

    @property
    def key(self) -> tuple[str, str]:
        """Khóa sản phẩm theo đúng nguồn và ID gốc."""
        return self.source, self.product_id

    def fits(self, group: str) -> bool:
        """Kiểm điều kiện nhóm trên 12 review đầu, không suy nhãn V/L/S/G."""
        if group == "higher":
            return self.logistics_only >= 2
        if group == "near":
            return self.low <= 2 and self.mean_length >= 60
        if group == "lower":
            return self.platform_rating >= 4.0 and self.faults >= 3
        return group == "kho"

    def fit_key(self, group: str) -> tuple[float, ...]:
        """Điểm phù hợp giảm dần, các khóa cuối dùng ID và nguồn tăng dần."""
        if group == "higher":
            return (-self.logistics_only, self.faults, -self.mean_length)
        if group == "near":
            return (self.low, -self.mean_length)
        if group == "lower":
            return (-self.faults, -self.platform_rating, -self.mean_length)
        return (-self.unaccented,)


def clean_text(text: str) -> str:
    """Chuẩn hóa Unicode và gộp mọi khoảng trắng, không sửa chính tả."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def load_candidates(path: Path) -> list[Candidate]:
    """Đọc, kiểm schema, gom ID thật; loại metadata thiếu để tránh trộn sản phẩm."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    missing: Counter[str] = Counter()
    total = 0
    with path.open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            required = {"text", "product", "rating", "source", "category", "product_id", "row_order"}
            if not isinstance(row, dict) or not required <= row.keys():
                raise ValueError(f"dòng {line_number}: thiếu trường JSONL")
            if row["source"] not in SOURCES:
                raise ValueError(f"dòng {line_number}: source không hỗ trợ")
            if type(row["rating"]) is not int or not 1 <= row["rating"] <= 5:
                raise ValueError(f"dòng {line_number}: rating phải là số nguyên 1–5")
            if type(row["row_order"]) is not int or row["row_order"] < 0:
                raise ValueError(f"dòng {line_number}: row_order phải là số nguyên không âm")
            if not isinstance(row["text"], str):
                raise ValueError(f"dòng {line_number}: text phải là chuỗi")
            total += 1
            if not isinstance(row["product_id"], str) or not row["product_id"].strip():
                missing[row["source"]] += 1
                continue
            if not all(isinstance(row[k], str) and row[k].strip() for k in ("category", "product")):
                missing[row["source"]] += 1
            elif not re.fullmatch(r"[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*", row["category"]):
                raise ValueError(f"dòng {line_number}: category không chuẩn hóa được thành snake_case")
            grouped[row["source"], row["product_id"]].append(row)
    candidates = []
    for (source, product_id), rows in sorted(grouped.items()):
        # Không bỏ riêng dòng thiếu metadata rồi tính trung bình trên phần còn lại.
        if any(not all(isinstance(r[k], str) and r[k].strip() for k in ("category", "product")) for r in rows):
            continue
        rows.sort(key=lambda row: row["row_order"])
        if len({r["row_order"] for r in rows}) != len(rows):
            raise ValueError(f"{source}/{product_id}: row_order trùng; không xác định thứ tự")
        if len({(r["product"], r["category"]) for r in rows}) != 1:
            raise ValueError(f"{source}/{product_id}: metadata không nhất quán")
        first = [r for r in rows if clean_text(r["text"])][:12]
        if len(first) < 12:
            continue
        texts = [clean_text(r["text"]) for r in first]
        low = [clean_text(r["text"]) for r in first if r["rating"] <= 2]
        letters = [c for text in texts for c in text if c.isalpha()]
        candidates.append(Candidate(
            source, product_id, rows[0]["product"], rows[0]["category"], rows,
            round(sum(r["rating"] for r in rows) / len(rows), 1), len(low),
            sum(bool(LOGISTICS.search(t)) for t in low),
            sum(bool(LOGISTICS.search(t)) and not FAULT.search(t) for t in low),
            sum(bool(FAULT.search(t)) for t in low), sum(map(len, texts)) / 12,
            sum(c.isascii() for c in letters) / len(letters) if letters else 0.0,
        ))
    print(f"Đọc {total} review; {len(grouped)} sản phẩm đủ metadata; {len(candidates)} ứng viên >=12 review không rỗng.")
    for source, count in sorted(missing.items()):
        print(f"CẢNH BÁO: loại {count} dòng {source} thiếu product_id/category/product; không gom các ID rỗng.")
    print("Số ứng viên theo nhóm (có thể trùng): " + ", ".join(
        f"{group}={sum(c.fits(group) for c in candidates)}" for group in QUOTAS
    ))
    return candidates


def cell(value: object) -> str:
    """Escape dấu pipe và gộp khoảng trắng trong ô Markdown."""
    return clean_text(str(value)).replace("|", r"\|")


def print_candidates(candidates: list[Candidate]) -> None:
    """In toàn bộ ứng viên cùng thống kê của 12 review đầu."""
    print("Tỷ lệ không dấu = chữ cái ASCII / tổng chữ cái; L-only = giao/lắp không kèm từ khóa lỗi.")
    print("| source | product_id | product | category | 1–2★ | giao/lắp | L-only | lỗi | dài TB | không dấu | tổng review | platform_rating |")
    print("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for c in candidates:
        print("| " + " | ".join(map(cell, (
            c.source, c.product_id, c.product, c.category, c.low, c.logistics,
            c.logistics_only, c.faults, f"{c.mean_length:.1f}", f"{100*c.unaccented:.1f}%",
            len(c.reviews), f"{c.platform_rating:.1f}",
        ))) + " |")


def select_candidates(candidates: list[Candidate]) -> list[tuple[str, Candidate]]:
    """Chọn đủ quota: nhóm hiếm trước, ưu tiên category mới, nguồn ít, độ phù hợp.

    Tối đa 2/category. Backtracking tìm bộ đủ quota nếu lựa chọn tham lam bị kẹt.
    Kho xếp tỷ lệ không dấu trước, rồi độ đa dạng, nguồn và ID. Không nới tiêu chí.
    """
    pools = {g: [c for c in candidates if c.fits(g)] for g in QUOTAS}
    shortages = [f"{g}: cần {n}, chỉ có {len(pools[g])}" for g, n in QUOTAS.items() if len(pools[g]) < n]
    if shortages:
        raise ValueError("Không đủ bộ theo tiêu chí: " + "; ".join(shortages) + ". Không ghi file nào.")
    order = sorted(QUOTAS, key=lambda g: (len(pools[g]) / QUOTAS[g], list(QUOTAS).index(g)))
    used: set[tuple[str, str]] = set()
    categories: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    chosen: list[tuple[str, Candidate]] = []

    def search(index: int, remaining: int, group_used: set[tuple[str, str]]) -> bool:
        """Duyệt thứ tự ưu tiên cố định và loại hoán vị trùng trong cùng nhóm."""
        if index == len(order):
            return True
        group = order[index]
        if not remaining:
            return search(index + 1, QUOTAS[order[index + 1]] if index + 1 < len(order) else 0, set())
        available = [c for c in pools[group] if c.key not in used and c.key not in group_used and categories[c.category] < 2]
        if len(available) < remaining:
            return False
        def priority(c: Candidate) -> tuple[Any, ...]:
            diversity = (categories[c.category], sources[c.source])
            fit = c.fit_key(group)
            return (*fit, *diversity, c.product_id, c.source) if group == "kho" else (*diversity, *fit, c.product_id, c.source)
        rejected = set(group_used)
        for c in sorted(available, key=priority):
            chosen.append((group, c))
            used.add(c.key)
            categories[c.category] += 1
            sources[c.source] += 1
            if search(index, remaining - 1, rejected):
                return True
            chosen.pop()
            used.remove(c.key)
            categories[c.category] -= 1
            sources[c.source] -= 1
            rejected.add(c.key)
        return False

    if not search(0, QUOTAS[order[0]], set()):
        raise ValueError("Không thể thỏa quota và tối đa 2/category; không ghi file nào.")
    return sorted(chosen, key=lambda item: (list(QUOTAS).index(item[0]), item[1].fit_key(item[0]), item[1].product_id, item[1].source))


def print_selection(selected: list[tuple[str, Candidate]]) -> None:
    """In ánh xạ sp_XX cố định và nhóm ứng viên."""
    print("| sp_XX | nhóm | category | source | product_id | product | platform_rating |")
    print("|---|---|---|---|---|---|---:|")
    for index, (group, c) in enumerate(selected, 1):
        print("| " + " | ".join(map(cell, (f"sp_{index:02d}", group, c.category, c.source, c.product_id, c.product, f"{c.platform_rating:.1f}"))) + " |")


def extract_reviews(c: Candidate) -> list[tuple[dict[str, Any], str, str, list[tuple[int, int, str]]]]:
    """Lấy 12 review hợp lệ đầu; chỉ thêm tối đa 2 ít sao nếu 12 dòng không có."""
    eligible = []
    for row in c.reviews:
        text = clean_text(row["text"])
        if not text:
            continue
        hits = pii_hits(text)
        if hits:
            print(f"Bỏ {c.source}/{c.product_id} row_order={row['row_order']}: {', '.join(hits)} (không in PII).")
            continue
        replacements: list[tuple[int, int, str]] = []
        def replace(match: re.Match[str]) -> str:
            """Ghi vị trí thay tên, không lặp lại danh tính gốc trong log."""
            replacements.append((match.start('name'), match.end('name'), match.group('title')))
            return match.group('title') + " [tên]"
        eligible.append((row, PERSON.sub(replace, text), "", replacements))
    if len(eligible) < 12:
        raise ValueError(f"{c.source}/{c.product_id}: chỉ {len(eligible)} review sau loại PII, cần 12")
    result = eligible[:12]
    if not any(row["rating"] <= 2 for row, *_ in result):
        result += [(r, t, "x", edits) for r, t, _, edits in eligible[12:] if r["rating"] <= 2][:2]
    return result


def empty_template(path: Path) -> bool:
    """Chỉ cho ghi đè bảng review xác nhận trống hoàn toàn, ngoại trừ số thứ tự."""
    in_reviews = False
    found = False
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if "|" not in raw:
            in_reviews = False
            continue
        cells = markdown_cells(raw)
        if cells == ["#", "Sao", "Lọc thêm", "V", "L", "S", "G", "Nội dung review (nguyên văn)"]:
            found = in_reviews = True
            continue
        if not in_reviews or all(re.fullmatch(r":?-{3,}:?", s) for s in cells):
            continue
        if len(cells) != 8 or not cells[0].isdigit() or any(cells[1:]):
            return False
    return found


def write_selection(selected: list[tuple[str, Candidate]], raw_dir: Path) -> None:
    """Chuẩn bị đủ bộ, chặn file đã điền, ghi bảng ngoài repo và nhật ký chọn."""
    prepared = []
    for index, (group, c) in enumerate(selected, 1):
        target = raw_dir / f"sp_{index:02d}.md"
        if not 1 <= index <= 18:
            raise ValueError("Chỉ được ghi sp_01–sp_18")
        if target.is_symlink() or target.with_suffix('.txt').exists() or (target.exists() and not empty_template(target)):
            raise ValueError(f"Không ghi đè {target.name}: đã có nội dung hoặc không phải mẫu trống. Không ghi file nào.")
        rows = extract_reviews(c)
        for value in (c.product, c.category):
            if pii_hits(value):
                raise ValueError(f"{c.source}/{c.product_id}: metadata nghi PII")
        lines = [
            f"# Sản phẩm sp_{index:02d} (bộ công khai p-storm/vietnamese-electronics-product-reviews, nhóm: {group})", "",
            f"Nguồn: {c.source} product_id={c.product_id}; platform_rating = trung bình {len(c.reviews)} review trong bộ dữ liệu", "",
            "Xem hướng dẫn và ví dụ ở sp00.md. Gõ x vào đúng 1 ô V/L/S/G cho mỗi review.", "",
            "### Thông tin sản phẩm", "", "| Mục | Điền vào đây |", "|---|---|",
            f"| Tên sản phẩm | {cell(c.product)} |",
            f"| Sàn (Shopee / Tiki / TikTok Shop / Lazada) | {SOURCES[c.source]} |",
            f"| Ngành hàng | {c.category.replace('-', '_')} |",
            f"| Điểm sao trên sàn | {c.platform_rating:.1f} |",
            f"| Loại câu (thuong / kho) | {'kho' if group == 'kho' else 'thuong'} |", "",
            "### Review", "", "| # | Sao | Lọc thêm | V | L | S | G | Nội dung review (nguyên văn) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for number, (row, text, picked, _) in enumerate(rows, 1):
            lines.append(f"| {number} | {row['rating']} | {picked} |  |  |  |  | {cell(text)} |")
        prepared.append((target, "\n".join(lines) + "\n", rows, group, c))
    log_target = raw_dir / "public" / "selection_log.md"
    if log_target.is_symlink():
        raise ValueError("selection_log.md không được là symlink")
    # Kiểm toàn bộ bảng trước khi ghi bất kỳ file thật nào.
    with TemporaryDirectory(prefix="reviewshield-validate-") as temporary:
        for target, content, *_ in prepared:
            check_path = Path(temporary) / target.name
            check_path.write_text(content, encoding="utf-8")
            product, _, errors, _ = parse_raw(check_path)
            if errors or product is None:
                raise ValueError(f"Bảng dự kiến không đọc được: {target.name}: {errors}")
    log = ["# Nhật ký chọn bộ dữ liệu công khai", "", "Chọn tất định; nhóm ứng viên không phải nhãn chuẩn. V/L/S/G để trống.",
           "12 review không rỗng đầu theo row_order = natural; khi xuất bỏ PII và lấy dòng kế tiếp.",
           "platform_rating là trung bình toàn bộ review sản phẩm trong bộ dữ liệu, không phải điểm hiển thị trên web.", "",
           "| sp_XX | source | product_id | product | nhóm ứng viên | số review lấy | platform_rating | số review toàn bộ |",
           "|---|---|---|---|---|---:|---:|---:|"]
    count = 0
    edit_log = ["", "## Các vị trí ẩn danh", ""]
    raw_dir.mkdir(parents=True, exist_ok=True)
    for target, content, rows, group, c in prepared:
        # Kiểm lại ngay trước khi ghi để không đè file vừa được người khác điền.
        if target.exists() and not empty_template(target):
            raise ValueError(f"{target.name} vừa thay đổi; dừng ghi")
        target.write_text(content, encoding="utf-8")
        log.append("| " + " | ".join(map(cell, (target.stem, c.source, c.product_id, c.product, group, len(rows), f"{c.platform_rating:.1f}", len(c.reviews)))) + " |")
        for number, (row, _, _, edits) in enumerate(rows, 1):
            for start, end, title in edits:
                message = f"{target.stem}/r{number} row_order={row['row_order']} ký tự [{start}:{end}]: {title} [tên]"
                print("ẨN DANH: " + message)
                edit_log.append("- ẨN DANH: " + message)
                count += 1
    log.extend(edit_log)
    log.append(f"\nTổng số chỗ thay [tên]: {count}.")
    log_target.parent.mkdir(parents=True, exist_ok=True)
    log_target.write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"Đã ghi {len(prepared)} bảng và {log_target}; tổng số chỗ thay [tên]: {count}.")


def main(argv: list[str] | None = None) -> int:
    """Mặc định chỉ hướng dẫn; select/write thất bại rõ ràng nếu không đủ quota."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RAW_DIR / "public" / "reviews.jsonl")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--candidates", action="store_true", help="In bảng chỉ số ứng viên")
    modes.add_argument("--select", action="store_true", help="Chọn đủ 4 higher / 6 near / 4 lower / 2 kho (16 sp)")
    modes.add_argument("--write", action="store_true", help="Chọn và ghi sp_01–sp_18 ngoài repo; không ghi đè dữ liệu đã điền")
    args = parser.parse_args(argv)
    if not any((args.candidates, args.select, args.write)):
        parser.print_help()
        return 0
    try:
        candidates = load_candidates(args.input)
        if args.candidates:
            print_candidates(candidates)
        else:
            selected = select_candidates(candidates)
            print_selection(selected)
            if args.write:
                write_selection(selected, RAW_DIR)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
