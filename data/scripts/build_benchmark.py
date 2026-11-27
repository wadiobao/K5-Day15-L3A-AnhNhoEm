"""Sinh benchmark từ mẫu/nhãn và ca bổ sung, giữ ID và khóa nội dung cũ."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from .check_samples import check_file
    from .common import (BENCH_CSV, BENCH_FIELDS, EXTRA_CSV, LABELS_CSV, SAMPLES_DIR,
                         compute_score, read_csv_rows, read_labels, scored_reviews)
except ImportError:
    from check_samples import check_file
    from common import (BENCH_CSV, BENCH_FIELDS, EXTRA_CSV, LABELS_CSV, SAMPLES_DIR,
                        compute_score, read_csv_rows, read_labels, scored_reviews)

PASS_CRITERION = (
    "Đạt khi: (1) output ghi đúng direction như expected; "
    "(2) >=85% nhãn review [rX | sao | nhãn] khớp expected; "
    "(3) mọi evidence_quote là chuỗi con nguyên văn của review gốc "
    "(không phân biệt hoa/thường, khoảng trắng); "
    "(4) người chấm xác nhận Top rủi ro và 3 câu hỏi kiểm chứng sát phàn nàn thật (actionable_quality)."
)
LOCKED_FIELDS = ("input", "expected", "pass_criterion", "type")


def source_key(source: str) -> str | None:
    """Lấy khóa ổn định extra/key hoặc product_id từ source của câu cũ."""
    extra = re.search(r"\bextra\s+([A-Za-z0-9_-]+)\b", source)
    if extra:
        return extra.group(1)
    product = re.search(r"\bsp_\d{2}\b", source)
    return product.group(0) if product else None


def collect_cases(samples: Path, labels_path: Path, extras: Path) -> list[tuple[str, dict[str, str]]]:
    """Tạo các câu có đủ nhãn; không dùng expected_direction lưu sẵn làm đáp án."""
    cases = []
    labels = read_labels(labels_path) if labels_path.exists() else {}
    if not labels_path.exists():
        print(f"CẢNH BÁO: chưa có {labels_path}; chưa thể thêm câu từ samples.")
    for path in sorted(samples.glob("*.json")):
        errors: list[str] = []
        warnings: list[str] = []
        product = check_file(path, errors, warnings)
        if errors:
            raise ValueError("\n".join(errors))
        for warning in warnings:
            print(f"CẢNH BÁO: {warning}")
        if product is None:
            raise ValueError(f"Không đọc được sản phẩm: {path}")
        pid, reviews = product["product_id"], product["reviews"]
        if not reviews or any(not labels.get((pid, r["id"]), {}).get("label") for r in reviews):
            print(f"CẢNH BÁO: bỏ qua nguồn {pid} vì chưa đủ nhãn; câu cũ nếu có vẫn được giữ.")
            continue
        scored, types = scored_reviews(product, labels)
        review_ids = {r["id"] for r in reviews}
        if any(rid not in review_ids for product_id, rid in labels if product_id == pid):
            raise ValueError(f"{pid}: labels.csv có review thừa so với samples")
        direction = compute_score(scored, product["platform_rating"])["direction"]
        payload = {key: product[key] for key in ("product_name", "platform", "platform_rating")}
        payload["reviews"] = [{key: review[key] for key in ("id", "rating", "text")} for review in reviews]
        expected = "; ".join([f"direction={direction}"] + [
            f"{r['id']}={labels[(pid, r['id'])]['label']}" for r in reviews
        ])
        cases.append((pid, {
            "input": json.dumps(payload, ensure_ascii=False), "expected": expected,
            "pass_criterion": PASS_CRITERION, "type": next(iter(types)),
            "source": f"data_that: {product['platform']} {pid}",
        }))
    for row in read_csv_rows(extras, ["key", *BENCH_FIELDS[1:]]):
        key = row.pop("key")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
            raise ValueError(f"{extras}: khóa extra không hợp lệ: {key!r}")
        if not row["source"].startswith("tu_viet:") or source_key(row["source"]) != key:
            raise ValueError(f"{extras}: source phải là tu_viet: extra {key}")
        if row["type"] not in {"thuong", "kho", "tu_choi"} or any(not value.strip() for value in row.values()):
            raise ValueError(f"{extras}: {key} có ô trống hoặc type sai")
        cases.append((key, row))
    keys = [key for key, _ in cases]
    if len(keys) != len(set(keys)):
        raise ValueError("Khóa câu thử bị trùng giữa samples/extra; không ghi benchmark.")
    return cases


def merge_cases(
    old_rows: list[dict[str, str]], cases: list[tuple[str, dict[str, str]]], force: bool,
) -> list[dict[str, str]]:
    """Giữ mọi câu cũ trừ dòng ví dụ; chặn thay đổi trường khóa trừ --force."""
    old_by_key, kept, ids = {}, [], set()
    numbers = [int(m.group(1)) for row in old_rows if (m := re.fullmatch(r"RS(\d+)", row["id"]))]
    next_id = max(numbers, default=0) + 1
    dropped = []
    for row in old_rows:
        if any("(ví dụ" in value.lower() for value in row.values()):
            dropped.append(row["id"])
            continue
        if not row["id"].strip() or row["id"] in ids:
            raise ValueError(f"benchmark cũ có ID rỗng/trùng: {row['id']!r}")
        ids.add(row["id"])
        key = source_key(row["source"])
        if key is not None:
            if key in old_by_key:
                raise ValueError(f"benchmark cũ có khóa nguồn trùng: {key}")
            old_by_key[key] = row
        kept.append(row)
    if dropped:
        print(f"Đã bỏ {len(dropped)} dòng mẫu có '(ví dụ': {', '.join(dropped)}")
    fresh = dict(cases)
    differences = []
    for key, row in cases:
        if key in old_by_key:
            old = old_by_key[key]
            for field in LOCKED_FIELDS:
                if row[field] != old[field]:
                    differences.append(f"{old['id']} ({key}): {field}: cũ={old[field]!r}; mới={row[field]!r}")
    if differences:
        print("KHÓA CP2: phát hiện thay đổi câu đã có:")
        for difference in differences:
            print(f"  - {difference}")
        if not force:
            raise ValueError("Đã chặn thay đổi; không ghi file. Chỉ dùng --force khi có chủ ý và được phép theo quy định dự án.")
    if force:
        print("!!! CẢNH BÁO LỚN: AGENTS.md cấm sửa expected sau CP2 19:30 27/11 !!!")
    result = []
    for row in kept:
        key = source_key(row["source"])
        if key in fresh:
            result.append({"id": row["id"], **fresh.pop(key)})
        else:
            print(f"CẢNH BÁO: {row['id']} không còn nguồn tương ứng; giữ nguyên toàn bộ câu cũ.")
            result.append(row)
    for key, _ in cases:
        if key in fresh:
            result.append({"id": f"RS{next_id:02d}", **fresh.pop(key)})
            next_id += 1
    return result


def main(argv: list[str] | None = None) -> int:
    """Sinh CSV sau khi kiểm xong; mã 1 khi bị chặn hoặc dữ liệu sai."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=BENCH_CSV, help="CSV benchmark đầu ra")
    parser.add_argument("--samples", type=Path, default=SAMPLES_DIR, help="Thư mục mẫu đầu vào")
    parser.add_argument("--labels", type=Path, default=LABELS_CSV, help="CSV nhãn đầu vào")
    parser.add_argument("--extra", type=Path, default=EXTRA_CSV, help="CSV câu bổ sung")
    parser.add_argument("--force", action="store_true", help="Cho phép ghi đè nội dung cũ, kèm cảnh báo CP2")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ báo cáo, không ghi file")
    args = parser.parse_args(argv)
    try:
        old = read_csv_rows(args.out, BENCH_FIELDS) if args.out.exists() else []
        cases = collect_cases(args.samples, args.labels, args.extra)
        rows = merge_cases(old, cases, args.force)
        if not args.dry_run:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=BENCH_FIELDS, quoting=csv.QUOTE_MINIMAL)
                writer.writeheader()
                writer.writerows(rows)
    except (ValueError, OSError, UnicodeError, csv.Error) as exc:
        print(f"LỖI: {exc}")
        return 1
    by_type = Counter(row["type"] for row in rows)
    sources = Counter(re.split(r"[:\s]", row["source"].strip(), maxsplit=1)[0] for row in rows)
    n = len(rows)
    print(f"{'DỰ KIẾN' if args.dry_run else 'Đã ghi'} {n} câu: {args.out}")
    print("Theo type: " + ", ".join(f"{key}={value}" for key, value in sorted(by_type.items())))
    print("Theo source code: " + ", ".join(f"{key}={value}" for key, value in sorted(sources.items())))
    print(f"Tỉ lệ data_that: {sources['data_that']}/{n} ({100 * sources['data_that'] / n if n else 0:.1f}%)")
    if args.dry_run:
        print("Chạy thử: không ghi file nào.")
    print("Nhắc: chạy python3 run.py check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
