"""Gợi ý chấm các metric bằng code; không điền pass hoặc sửa lượt chạy."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data" / "scripts"))
sys.path.insert(0, str(ROOT / "eval"))
from common import DIRECTIONS, LABELS, norm_text, read_csv_rows
from run_eval import OUT_COLS, load_yaml

SUGGEST_COLS = ["id", "type", "direction_ok", "label_correct", "label_total",
                "quotes_ok", "quotes_total", "code_pass_suggest", "note"]
HUMAN_NOTE = "CHƯA xét actionable_quality — người chấm quyết định"
REVIEW_LINE = re.compile(
    r"\[\s*([^|\]\s]+)\s*\|\s*[1-5]\s*★?\s*\|\s*([^|\]]+?)\s*\]"
)
DIRECTION_LINE = re.compile(
    r"\bdirection\b\s*\)?\s*[:=]\s*([a-z_]+)\b", re.IGNORECASE
)


def parse_expected(text: str) -> tuple[str, dict[str, str]]:
    """Đọc direction và nhãn kỳ vọng, từ chối khóa trùng hoặc giá trị lạ."""
    fields: dict[str, str] = {}
    for part in text.split(";"):
        if not part.strip():
            continue
        match = re.fullmatch(r"\s*(direction|r[1-9]\d*)\s*=\s*([a-z_]+)\s*", part)
        if not match or match[1] in fields:
            raise ValueError("expected sai định dạng hoặc lặp khóa")
        fields[match[1]] = match[2]
    direction = fields.pop("direction", "")
    if direction not in DIRECTIONS or not fields or any(v not in LABELS for v in fields.values()):
        raise ValueError("expected thiếu direction/nhãn review hợp lệ")
    return direction, fields


def extract_quote(tail: str) -> str:
    """Lấy ngoặc kép đầu/cuối trước phần lý do; giữ dấu bên trong trích dẫn."""
    # Chỉ nhận dấu phân cách khi phía trước đã có cặp ngoặc kép đóng.
    boundaries = [m.start() for m in re.finditer(r"\s+[—-]", tail)]
    fallback = ""
    for end in [*boundaries, len(tail)]:
        prefix = tail[:end].strip()
        if len(prefix) >= 2 and (prefix[0], prefix[-1]) in {('"', '"'), ('“', '”')} and not fallback:
            fallback = prefix[1:-1]
        straight = prefix.startswith('"') and prefix.endswith('"') and prefix.count('"') % 2 == 0
        curly = prefix.startswith('“') and prefix.endswith('”') and prefix.count('“') == prefix.count('”')
        if len(prefix) >= 2 and (straight or curly):
            return prefix[1:-1]
    return fallback


def parse_output(text: str) -> tuple[list[str], list[tuple[str, str, str]]]:
    """Tách dòng direction và các dòng phân loại, kể cả dòng thiếu trích dẫn."""
    directions: list[str] = []
    reviews: list[tuple[str, str, str]] = []
    for line in unicodedata.normalize("NFC", text).splitlines():
        directions.extend(m[1].lower() for m in DIRECTION_LINE.finditer(line))
        match = REVIEW_LINE.search(line)
        if match:
            reviews.append((match[1], match[2].strip(), extract_quote(line[match.end():])))
    return directions, reviews


def original_reviews(text: str) -> dict[str, str]:
    """Đọc review gốc theo id từ JSON input; không lấy bằng chứng từ id khác."""
    product = json.loads(text)
    if not isinstance(product, dict) or not isinstance(product.get("reviews"), list):
        raise ValueError("input không có danh sách reviews")
    originals: dict[str, str] = {}
    for review in product["reviews"]:
        if not isinstance(review, dict) or not isinstance(review.get("id"), str) or not isinstance(review.get("text"), str):
            raise ValueError("review gốc thiếu id/text hợp lệ")
        if review["id"] in originals:
            raise ValueError("input có id review trùng")
        originals[review["id"]] = review["text"]
    return originals


def grade_row(row: dict[str, str]) -> dict[str, Any]:
    """Tính metric cho một câu; giữ câu lỗi kỹ thuật ở mẫu số sản phẩm."""
    result: dict[str, Any] = dict.fromkeys(SUGGEST_COLS, "")
    result.update(id=row["id"], type=row["type"], product=False,
                  label_correct=0, label_total=0, quotes_ok=0, quotes_total=0)
    technical_error = bool(row["error"].strip())
    is_product = row["type"].strip() != "tu_choi" and bool(re.search(r"\bdirection\s*=", row["expected"]))
    if not is_product:
        note = "lỗi kỹ thuật, không chấm đạt" if technical_error else "cần người chấm"
        if "điểm tin cậy thực" in norm_text(row["output"]):
            note += "; có bảng điểm — kiểm có bịa không"
        result.update(code_pass_suggest=False if technical_error else "", note=note)
        return result
    result.update(product=True, direction_ok=False, code_pass_suggest=False)
    try:
        expected_direction, expected_labels = parse_expected(row["expected"])
        result["label_total"] = len(expected_labels)
        directions, displayed = parse_output(row["output"])
        result["quotes_total"] = len(displayed)
        originals = original_reviews(row["input"])
        counts = Counter(rid for rid, _, _ in displayed)
        predicted = {rid: label for rid, label, _ in displayed if counts[rid] == 1}
        result["direction_ok"] = directions == [expected_direction]
        result["label_correct"] = sum(predicted.get(rid) == label for rid, label in expected_labels.items())
        result["quotes_ok"] = sum(
            bool(norm_text(quote)) and rid in originals and norm_text(quote) in norm_text(originals[rid])
            for rid, _, quote in displayed
        )
        result["code_pass_suggest"] = (
            result["direction_ok"] and result["label_correct"] / result["label_total"] >= 0.85
            and result["quotes_total"] > 0 and result["quotes_ok"] == result["quotes_total"]
        )
        notes = [HUMAN_NOTE]
        if any(count > 1 for count in counts.values()):
            notes.append("id lặp trong output tính sai nhãn")
        if not displayed:
            notes.append("không có trích dẫn để tính grounding; không gợi ý đạt")
        result["note"] = "; ".join(notes)
    except (ValueError, TypeError, KeyError) as exc:
        result.update(direction_ok=False, label_correct=0, quotes_ok=0,
                      code_pass_suggest=False, note=f"cần người chấm: {exc}; {HUMAN_NOTE}")
    if technical_error:
        result.update(direction_ok=False, label_correct=0, quotes_ok=0, code_pass_suggest=False,
                      note=f"lỗi kỹ thuật, không chấm đạt; {HUMAN_NOTE}")
    return result


def metric_thresholds() -> dict[str, tuple[str, float]]:
    """Đọc ngưỡng phần trăm từ YAML bằng bộ đọc thư viện chuẩn của khung."""
    spec = load_yaml(str(ROOT / "eval" / "metric_spec.yaml"))
    wanted = {"label_accuracy", "direction_match", "citation_grounding"}
    thresholds: dict[str, tuple[str, float]] = {}
    for metric in spec["metrics"]:
        if metric["name"] not in wanted:
            continue
        match = re.fullmatch(r"\s*(>=|==)\s*(\d+(?:\.\d+)?)\s*%\s*", metric["threshold"])
        if not match or metric["name"] in thresholds:
            raise ValueError("Ngưỡng metric không hợp lệ hoặc trùng")
        thresholds[metric["name"]] = (match[1], float(match[2]))
    if thresholds.keys() != wanted:
        raise ValueError("Thiếu ngưỡng label_accuracy/direction_match/citation_grounding")
    return thresholds


def render_summary(rows: list[dict[str, str]], results: list[dict[str, Any]]) -> str:
    """In bảng từng câu, đoạn output cần đọc và ba metric cộng dồn."""
    thresholds = metric_thresholds()
    lines = ["Chỉ gợi ý, không điền pass. " + HUMAN_NOTE + ".", "",
             "| id | type | direction_ok | label x/y | grounding x/y | gợi ý |",
             "|---|---|---|---|---|---|"]
    for res in results:
        direction = str(res["direction_ok"]) if res["product"] else "—"
        label = f"{res['label_correct']}/{res['label_total']}" if res["product"] else "—"
        grounding = f"{res['quotes_ok']}/{res['quotes_total']}" if res["product"] else "—"
        suggestion = (f"code_pass={res['code_pass_suggest']}; " if res["product"] else "") + res["note"]
        cells = [res["id"], res["type"], direction, label, grounding, suggestion]
        lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    for row, res in zip(rows, results):
        if not res["product"]:
            lines.extend(["", f"{res['id']} — 300 ký tự đầu output:", row["output"][:300]])
    products = [res for res in results if res["product"]]
    metrics = [
        ("label_accuracy", sum(r["label_correct"] for r in products), sum(r["label_total"] for r in products)),
        ("direction_match", sum(bool(r["direction_ok"]) for r in products), len(products)),
        ("citation_grounding", sum(r["quotes_ok"] for r in products), sum(r["quotes_total"] for r in products)),
    ]
    lines.extend(["", "Metric tổng trên các câu sản phẩm (kể cả câu lỗi kỹ thuật; tử số câu lỗi = 0):"])
    for name, correct, total in metrics:
        operator, target = thresholds[name]
        if total:
            percent = 100 * correct / total
            passed = percent >= target if operator == ">=" else percent == target
            status = f"{percent:.1f}% — {'đạt' if passed else 'không đạt'} ngưỡng {operator} {target:g}%"
        else:
            status = f"không có mẫu để tính; ngưỡng {operator} {target:g}%"
        lines.append(f"- {name} = {correct}/{total}: {status}")
    lines.extend(["", HUMAN_NOTE + "."])
    return "\n".join(lines) + "\n"


def validate_destination(source: Path, target: Path) -> None:
    """Chặn ghi lượt chạy, kể cả đường dẫn tương đương, symlink và hardlink."""
    resolved = target.resolve()
    if re.fullmatch(r"run-.*\.csv", target.name, re.IGNORECASE) or re.fullmatch(r"run-.*\.csv", resolved.name, re.IGNORECASE):
        raise ValueError("Không ghi file có tên run-*.csv; hãy chọn CSV gợi ý riêng")
    if resolved == source.resolve() or (target.exists() and os.path.samefile(source, target)):
        raise ValueError("Không được ghi đè file lượt chạy đầu vào")
    if target.exists():
        for run in (ROOT / "eval").glob("run-*.csv"):
            if os.path.samefile(target, run):
                raise ValueError("File đích là liên kết tới eval/run-*.csv; không ghi")


def main(argv: list[str] | None = None) -> int:
    """Đọc lượt chạy UTF-8-sig; chỉ ghi CSV gợi ý khi có --out."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_csv", type=Path, help="File lượt chạy cần hỗ trợ chấm")
    parser.add_argument("--out", type=Path, help="CSV gợi ý riêng, không phải run-*.csv")
    args = parser.parse_args(argv)
    try:
        if args.out:
            validate_destination(args.run_csv, args.out)
        rows = read_csv_rows(args.run_csv, OUT_COLS)
        results = [grade_row(row) for row in rows]
        report = render_summary(rows, results)
        if args.out:
            with args.out.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=SUGGEST_COLS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(results)
        print(report, end="")
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
