# Hồ Sơ Đánh Giá Hệ Thống (Eval Profile) — ReviewShield

## 1. Bộ dữ liệu kiểm thử (`eval/benchmark.csv`)
* **Quy mô:** 25–30 tình huống kiểm thử thật (mỗi dòng là một cụm 6–15 review sản phẩm công khai từ sàn TMĐT đã ẩn danh người mua).
* **Phân bổ 4 nhóm kịch bản:**
  1. `genuine_high` (7 cases): Sản phẩm chất lượng tốt thật, đa số review mô tả chi tiết trải nghiệm.
  2. `seeding_heavy` (8 cases): Điểm sàn 4.8–5.0 nhưng hơn 50% là review nhận xu hoặc lặp mẫu câu quảng cáo.
  3. `logistics_bias` (5 cases): Sản phẩm ổn nhưng bị đánh 1–2 sao do shipper/vận chuyển.
  4. `hidden_defects` (5–10 cases): Điểm sàn cao nhưng review 1–3 sao gần đây lặp lại cùng 1–2 lỗi nghiêm trọng.

## 2. Quy trình dựng & gán nhãn `eval/benchmark.csv`
1. Thu thập công khai từ 4–5 ngành hàng phổ biến (Phụ kiện điện tử, Thời trang, Gia dụng, Mỹ phẩm, Đồ ăn vặt).
2. Ẩn danh toàn bộ thông tin tài khoản người mua thành `user_01`, `user_02`.
3. Gán nhãn chuẩn theo đúng quy tắc phân định ranh giới tại `docs/AI_PROMPT_AND_SCORING.md`.
4. Kiểm tra chéo giữa 2 thành viên đối với các review nằm ở ranh giới giữa `low_signal` và `verified_insight`.

## 3. Metric & Cách chấm (Khớp `eval/metric_spec.yaml`)
* `label_accuracy` (`code`, ngưỡng `>= 85%`)
* `direction_match` (`code`, ngưỡng `>= 85%`)
* `citation_grounding` (`code`, ngưỡng `== 100%`)
* `actionable_quality` (`nguoi`, ngưỡng `>= 80%`)

## 4. Lệnh chạy chuẩn theo khung repo
```bash
python run.py eval --try          # Chạy thử nhanh vài câu
python run.py eval                # Chạy toàn bộ eval/benchmark.csv -> tạo eval/run-N.csv
python run.py score eval/run-1.csv # Tổng hợp điểm sau khi điền cột pass/ghi_chu
```

## 5. Kết quả tổng hợp
* `[Cập nhật sau khi chạy python run.py eval và dán bảng từ eval/report.md]`
