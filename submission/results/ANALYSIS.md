# Phân tích thí nghiệm raw và clean

Hai biến thể dùng `yolo26n.pt`, 20 epoch, kích thước ảnh 640, batch 16 và seed 0, 1. Cả hai được đánh giá trên cùng 100 ảnh test. Số liệu lấy từ bốn file `*_seed*.json`.

## 1. Chênh lệch mAP50 và độ nhiễu giữa các seed

| Biến thể | Seed 0 | Seed 1 | mAP50 trung bình ± độ lệch chuẩn mẫu |
| -------- | -----: | -----: | -----------------------------------: |
| `raw`    | 0.7256 | 0.7259 |                    0.72575 ± 0.00021 |
| `clean`  | 0.7277 | 0.7311 |                    0.72940 ± 0.00240 |

Chênh `clean − raw` là **+0.00365**, tương đương **+0,365 điểm phần trăm**. Hai chênh lệch theo cặp seed là `+0.0021` và `+0.0052`, với độ lệch chuẩn mẫu `0.00219`. Hai lượt đều tăng mAP50, trong khi mAP50–95 trung bình giảm từ `0.5117` xuống `0.4996`.

## 2. Số ảnh raw thực sự vào train

Hai file `raw_seed*.json` ghi **224 ảnh**, vì `scripts/train_compare.py` đếm file trong thư mục ảnh trước lọc. Khi quét lại bản sao của lô `raw` bằng `verify_image_label` của Ultralytics **8.4.215**, bộ kiểm tra giữ **213/224 ảnh** và bỏ **11 ảnh**.

## 3. Rò rỉ giữa raw và tập test

`../reports/01_intake.csv` có **11 ảnh raw bị gắn `LEAK_TEST`** với ảnh trong `data/test`. Đây là các cặp nghi trùng theo pHash. Đã xem trực tiếp cặp `img_0049.jpg` và `test_033.jpg`: cùng cảnh và bố cục, khác kích thước.

**Chưa định lượng được mức thổi phồng**

## 4. Lớp nào được lợi nhất?

| Lớp      | AP50 trung bình raw | AP50 trung bình clean | Chênh clean − raw |
| -------- | ------------------: | --------------------: | ----------------: |
| `car`    |             0.73750 |               0.75300 |          +0.01550 |
| `person` |             0.82205 |               0.82770 |          +0.00565 |
| `truck`  |             0.64845 |               0.62145 |          −0.02700 |
| `bus`    |             0.69490 |               0.71530 |      **+0.02040** |

`bus` tăng nhiều nhất về AP50 trung bình. Trong `../reports/02_error_list_v1.csv`, `img_0020` bị nghi sai lớp thành loại khác thay vì `bus`, còn `img_0065`, `img_0066` và `img_0151` bị nghi thiếu box `bus`. Cả bốn ảnh được duyệt. Khi đối chiếu nhãn `raw` với bản xuất, tổng số box `bus` trên bốn ảnh tăng từ **1 lên 6**. Đây là một lý do khả dĩ cho mức tăng AP50.

## 5. Clean còn vấn đề gì?

`clean` là bản đã qua AutoQC và duyệt một phần. Các cờ còn lại cần người xác nhận, và calibration cũng cho thấy công cụ có thể bỏ sót lỗi. Muốn có mốc tham chiếu gần với giới hạn của dữ liệu sạch, cần duyệt đầy đủ nhãn trên cùng tập 193 ảnh rồi train lại với cùng điều kiện.
