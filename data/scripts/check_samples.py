#!/usr/bin/env python3
"""Kiểm data/samples/*.json của ReviewShield (việc của Thành viên 3). Chỉ đọc, không sửa file.

Dùng:
    python3 data/scripts/check_samples.py     # kiểm data/samples
    python3 check_samples.py <thư_mục>        # kiểm một thư mục khác
    python3 check_samples.py <file.json> ...  # kiểm vài file

Mã thoát: 0 = không có LỖI (có thể còn CẢNH BÁO), 1 = có lỗi.
Quy ước lấy từ docs/member/README.md §2.1, AGENTS.md §4, member-3-data-evidence-eval.md.
"""
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

try:
    from .common import (DIRECTIONS, LABELS_CSV, PLATFORMS, SAMPLES_DIR,
                         compute_score, pii_hits, read_labels, scored_reviews)
except ImportError:
    from common import (DIRECTIONS, LABELS_CSV, PLATFORMS, SAMPLES_DIR,
                        compute_score, pii_hits, read_labels, scored_reviews)

DEFAULT_DIR = str(SAMPLES_DIR)

TOP_KEYS = {"product_id", "product_name", "category", "platform", "platform_rating",
            "expected_direction", "reviews"}
REVIEW_KEYS = {"id", "author", "rating", "text"}
# Mục tiêu theo repo (member/README.md §4, member-3): chỉ để báo tiến độ, không phải lỗi.
TARGET_TOTAL = (25, 30)
TARGET_PLATFORM = {"Shopee": (10, 12), "Tiki": (8, 10), "TikTok Shop + Lazada": (5, 8)}
REVIEWS_PER_PRODUCT = (6, 15)

def check_file(path: str | Path, errors: list[str], warns: list[str]) -> dict[str, Any] | None:
    """Kiểm một file; trả về dict đã parse (hoặc None nếu không đọc được)."""
    name = os.path.basename(path)

    def err(msg: str) -> None:
        """Ghi một lỗi của sản phẩm."""
        errors.append("%s: %s" % (name, msg))

    def warn(msg: str) -> None:
        """Ghi một cảnh báo của sản phẩm."""
        warns.append("%s: %s" % (name, msg))

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as e:
        err("không đọc được file: %s" % e)
        return None
    except UnicodeDecodeError:
        err("không phải UTF-8")
        return None
    except ValueError as e:
        err("JSON lỗi cú pháp: %s" % e)
        return None
    if not isinstance(data, dict):
        err("gốc của file phải là một object { ... }")
        return None

    missing = TOP_KEYS - set(data)
    extra = set(data) - TOP_KEYS
    if missing:
        err("thiếu trường: %s" % ", ".join(sorted(missing)))
    if extra:
        warn("trường lạ ở mức sản phẩm: %s (khung không dùng)" % ", ".join(sorted(extra)))

    m = re.fullmatch(r"(sp_\d{2})\.json", name)
    if not m:
        err("tên file phải dạng sp_01.json … sp_30.json")
    elif data.get("product_id") != m.group(1):
        err("product_id %r không khớp tên file (%s)" % (data.get("product_id"), m.group(1)))

    for k in ("product_name", "category"):
        if k in data and not (isinstance(data[k], str) and data[k].strip()):
            err("%s phải là chuỗi không rỗng" % k)
    if "platform" in data and (not isinstance(data["platform"], str) or data["platform"] not in PLATFORMS):
        err("platform %r không hợp lệ, dùng: %s" % (data["platform"], ", ".join(sorted(PLATFORMS))))
    pr = data.get("platform_rating")
    if "platform_rating" in data and (isinstance(pr, bool) or not isinstance(pr, (int, float)) or not 1.0 <= pr <= 5.0):
        err("platform_rating phải là số trong [1.0, 5.0], đang là %r" % (pr,))
    if "expected_direction" in data and (not isinstance(data["expected_direction"], str) or data["expected_direction"] not in DIRECTIONS):
        err("expected_direction %r không hợp lệ, dùng: %s" % (data["expected_direction"], ", ".join(sorted(DIRECTIONS))))

    reviews = data.get("reviews")
    if not isinstance(reviews, list):
        if "reviews" in data:
            err("reviews phải là danh sách")
        return data
    lo, hi = REVIEWS_PER_PRODUCT
    if not lo <= len(reviews) <= hi:
        warn("có %d review, repo yêu cầu %d–%d" % (len(reviews), lo, hi))

    authors, texts = [], []
    for i, r in enumerate(reviews, start=1):
        tag = "review #%d" % i
        if not isinstance(r, dict):
            err("%s không phải object" % tag)
            continue
        miss = REVIEW_KEYS - set(r)
        if miss:
            err("%s thiếu trường: %s" % (tag, ", ".join(sorted(miss))))
        ex = set(r) - REVIEW_KEYS
        if ex:
            # Nhãn chuẩn mà nằm ở đây sẽ bị đưa nguyên vào prompt của AI => lộ đáp án.
            err("%s có trường lạ %s — KHÔNG đưa nhãn chuẩn / ghi chú vào samples (app gửi nguyên file cho AI)"
                % (tag, ", ".join(sorted(ex))))
        if r.get("id") != "r%d" % i:
            err("%s: id phải là r%d (liên tiếp), đang là %r" % (tag, i, r.get("id")))
        a = r.get("author")
        if not (isinstance(a, str) and re.fullmatch(r"user_\d{2,}", a)):
            err("%s: author phải dạng user_01, user_02…, đang là %r" % (tag, a))
        else:
            authors.append(a)
        rt = r.get("rating")
        if isinstance(rt, bool) or not isinstance(rt, int) or not 1 <= rt <= 5:
            err("%s: rating phải là số nguyên 1–5, đang là %r" % (tag, rt))
        t = r.get("text")
        if not (isinstance(t, str) and t.strip()):
            err("%s: text rỗng hoặc không phải chuỗi" % tag)
            continue
        texts.append(t)
        if unicodedata.normalize("NFC", t) != t:
            warn("%s: text ở dạng Unicode tổ hợp (NFD), nên chuẩn hoá NFC để so khớp trích dẫn không lệch" % tag)
        if t != t.strip() or "  " in t or "\n" in t:
            warn("%s: có khoảng trắng thừa / xuống dòng (khung sẽ chuẩn hoá, kiểm lại nếu cố ý)" % tag)
        for kind in pii_hits(t):
            err("%s: nghi lộ PII — %s" % (tag, kind))

    dup_authors = sorted({a for a in authors if authors.count(a) > 1})
    if dup_authors:
        warn("author trùng: %s (mỗi review nên một user_XX riêng)" % ", ".join(dup_authors))
    stars = {r["rating"] for r in reviews if isinstance(r, dict) and isinstance(r.get("rating"), int)}
    absent = [s for s in range(1, 6) if s not in stars]
    if absent and len(reviews) >= 5:
        warn("chưa có review %s sao (repo yêu cầu trải đều 1–5 sao)" % ", ".join(map(str, absent)))
    return data


def main(argv: list[str] | None = None) -> int:
    """Kiểm mẫu, đối chiếu CSV nhãn nếu có, rồi báo lỗi và tiến độ."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", help="Thư mục hoặc file JSON cần kiểm")
    parser.add_argument("--labels", type=Path, default=LABELS_CSV, help="CSV nhãn để kiểm chéo")
    args = parser.parse_args(argv)
    targets = args.targets or [DEFAULT_DIR]
    files = []
    for t in targets:
        if os.path.isdir(t):
            files += [os.path.join(t, f) for f in sorted(os.listdir(t)) if f.endswith(".json")]
        elif os.path.isfile(t):
            files.append(t)
        elif not args.targets:  # thư mục mặc định chưa được tạo
            print("Chưa có thư mục data/samples (%s)." % os.path.normpath(t))
            print("Tiến độ: 0/%d–%d sản phẩm. Tạo thư mục rồi thêm sp_01.json …" % TARGET_TOTAL)
            return 0
        else:
            print("Không tìm thấy: %s" % t)
            return 2
    if not files:
        print("Chưa có file .json nào trong %s" % (targets[0],))
        print("Tiến độ: 0/%d–%d sản phẩm." % TARGET_TOTAL)
        return 0

    files = list(dict.fromkeys(files))
    errors: list[str] = []
    warns: list[str] = []
    products: list[dict[str, Any]] = []
    good: list[dict[str, Any]] = []
    labels = None
    if args.labels.exists():
        try:
            labels = read_labels(args.labels)
        except (ValueError, OSError, UnicodeError, csv.Error) as exc:
            errors.append(str(exc))
    elif args.labels != LABELS_CSV:
        errors.append(f"Không tìm thấy CSV nhãn: {args.labels}")
    else:
        warns.append("Chưa có eval/labels.csv; chưa kiểm chéo nhãn/direction.")
    for p in files:
        before = len(errors)
        d = check_file(p, errors, warns)
        if d:
            products.append(d)
            if len(errors) == before and labels is not None:
                try:
                    scored, _ = scored_reviews(d, labels)
                    known_ids = {r["id"] for r in d["reviews"]}
                    extra_ids = sorted(rid for pid, rid in labels if pid == d["product_id"] and rid not in known_ids)
                    if extra_ids:
                        raise ValueError(f"CSV nhãn có review thừa: {', '.join(extra_ids)}")
                    direction = compute_score(scored, d["platform_rating"])["direction"]
                    if d["expected_direction"] != direction:
                        errors.append(f"{os.path.basename(p)}: expected_direction={d['expected_direction']} lệch compute_score={direction}")
                    if len(scored) != len(d["reviews"]):
                        warns.append(f"{os.path.basename(p)}: còn nhãn trống; direction chỉ tính trên nhãn đã gán, chưa đưa vào benchmark")
                except ValueError as exc:
                    errors.append(f"{os.path.basename(p)}: {exc}")
            if len(errors) == before:
                good.append(d)

    # Trùng nội dung giữa các sản phẩm (dán nhầm một sản phẩm hai lần)
    names = Counter(p["product_name"] for p in products if isinstance(p.get("product_name"), str) and p["product_name"])
    for n, c in names.items():
        if c > 1:
            warns.append("product_name trùng ở %d file: %r" % (c, n))

    print("Đã kiểm %d file." % len(files))
    if errors:
        print("\nLỖI (%d):" % len(errors))
        for e in errors:
            print("  ✗ " + e)
    if warns:
        print("\nCẢNH BÁO (%d):" % len(warns))
        for w in warns:
            print("  ! " + w)

    # Tiến độ so với mục tiêu của repo
    plat = Counter(p.get("platform") for p in good)
    plat["TikTok Shop + Lazada"] = plat.pop("TikTok Shop", 0) + plat.pop("Lazada", 0)
    print("\nTiến độ (chỉ tính file không lỗi): %d sản phẩm, mục tiêu %d–%d" % ((len(good),) + TARGET_TOTAL))
    for k, (lo, hi) in TARGET_PLATFORM.items():
        print("  %-22s %2d  (mục tiêu %d–%d)" % (k, plat.get(k, 0), lo, hi))
    print("  expected_direction   : " + ", ".join("%s %d" % kv for kv in sorted(Counter(
        p.get("expected_direction") for p in good).items(), key=lambda kv: str(kv[0]))))
    print("  category             : " + ", ".join("%s %d" % kv for kv in sorted(Counter(
        p.get("category") for p in good).items(), key=lambda kv: str(kv[0]))))
    print("  tổng số review       : %d" % sum(len(p.get("reviews", [])) for p in good if isinstance(p.get("reviews"), list)))

    print("\nLưu ý: script chỉ bắt PII dạng SĐT/email/link/mã dài. Vẫn phải đọc lướt tay để loại tên người, "
          "địa chỉ, tên shop kèm tên riêng.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
