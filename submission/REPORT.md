# Báo cáo Day 09 — <Phạm Trọng Hiện>, <2A202603218>

## 1. Kết luận trước

**Hold — bộ dữ liệu chưa được phát hành.** Với ngưỡng đã chốt (`phash_dist = 16`, `second_opinion.conf = 0.6`), pipeline nhận **224 ảnh** và xuất bản nháp gồm **193 ảnh**. Sau khi duyệt 80 ảnh, không còn lỗi bắt buộc, nhưng **34/193 ảnh (17,62%)** vẫn có cảnh báo chưa duyệt, vượt ngưỡng **10%**.

## 2. Lỗi và phân việc

Bảng dưới đây dùng số liệu của lần chạy trước khi điều chỉnh ngưỡng (`phash_dist = 2`, `second_opinion.conf = 0.25`), khi pipeline giữ **205/224 ảnh**.

| Mã lỗi                 |         Số ảnh/dòng | Ai sửa | Vì sao                                         |
| ---------------------- | ------------------: | ------ | ---------------------------------------------- |
| `CORRUPT_IMAGE`        |               2 ảnh | Máy    | Loại ảnh không đọc được.                       |
| `BAD_SIZE`             |               3 ảnh | Máy    | Loại ảnh có cạnh ngắn dưới ngưỡng.             |
| `DUP_IMAGE_EXACT`      |               8 ảnh | Máy    | Loại bản trùng từng byte.                      |
| `DUP_IMAGE_NEAR`       |               2 ảnh | Máy    | Loại ảnh bị nhận diện là gần trùng.            |
| `LEAK_TEST`            |               4 ảnh | Máy    | Loại ảnh bị báo trùng với kho test/validation. |
| `BAD_FORMAT`           |      3 dòng / 3 ảnh | Máy    | Xóa dòng sai định dạng.                        |
| `BAD_CLASS_ID`         |      6 dòng / 6 ảnh | Máy    | Xóa dòng có ID ngoài danh sách lớp.            |
| `BOX_ZERO`             |      4 dòng / 4 ảnh | Máy    | Xóa box có cạnh không dương.                   |
| `DUP_BOX`              |      7 dòng / 7 ảnh | Máy    | Xóa box lặp cùng lớp.                          |
| `BOX_OUT_OF_IMAGE`     |      8 dòng / 8 ảnh | Máy    | Cắt box về trong ảnh.                          |
| `BAD_CLASS_NAME`       |       2 cờ / 1 file | Máy    | Chuẩn hóa danh sách tên lớp trong `data.yaml`. |
| `MISSING_LABEL_FILE`   |               6 ảnh | Người  | Gán nhãn cho ảnh chưa có file nhãn.            |
| `EMPTY_LABEL`          |              12 ảnh | Người  | Phân biệt ảnh nền và ảnh bị bỏ sót nhãn.       |
| `BOX_TINY`             |        6 cờ / 4 ảnh | Người  | Xem box nhỏ có đúng vật thể không.             |
| `BOX_HUGE`             |        3 cờ / 3 ảnh | Người  | Xem box lớn có ôm đúng vật thể không.          |
| `CLASS_RARE`           | 4 cờ cấp bộ dữ liệu | Người  | Đánh giá phân bố lớp ở cấp bộ dữ liệu.         |
| `POSSIBLE_MISSING`     |     152 cờ / 86 ảnh | Người  | Xác nhận có vật thể bị bỏ sót.                 |
| `POSSIBLE_WRONG_CLASS` |      22 cờ / 21 ảnh | Người  | Xác nhận lớp đúng khi nhãn và model bất đồng.  |
| `POSSIBLE_LOOSE_BOX`   |      45 cờ / 37 ảnh | Người  | Xem lại độ khít của box.                       |
| `POSSIBLE_FALSE_POS`   |      25 cờ / 24 ảnh | Người  | Xác nhận box có khoanh đúng một vật thể.       |

Hàng đợi xếp ảnh theo điểm giảm dần, dựa trên trọng số cảnh báo, độ tin cậy của model và điểm cộng cho nhãn đã sửa hoặc còn thiếu.
Người xem được **187/243 cờ ngữ nghĩa**

## 3. Calibration (2 ngưỡng)

| Tham số                 | Khởi đầu | Đã chọn | Precision / Recall (trước → sau)                                                                                           | Lý do (đánh đổi)                                                                                                                  |
| ----------------------- | -------: | ------: | -------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `duplicates.phash_dist` |        2 |      16 | Gần trùng: `1.00 / 0.50 → 1.00 / 0.83`. Trùng byte: giữ `1.00 / 1.00`.                                                     | Bắt được 5/6 ca gần trùng trên tập calibration, tăng từ 3/6.                                                                      |
| `second_opinion.conf`   |     0.25 |     0.6 | Thiếu box: `0.50 / 1.00 → 0.57 / 1.00`.<br>Sai lớp: `0.56 / 0.83 → 0.62 / 0.83`.<br>Box lệch: `0.29 / 0.40 → 0.20 / 0.20`. | Ưu tiên cảnh báo thiếu box và sai lớp: precision tăng, recall giữ nguyên. Đổi lại, số ca box lệch bắt được giảm từ 2/5 xuống 1/5. |

Ở ngưỡng `16`, precision cho ảnh gần trùng đạt `1.00` trên tập calibration, nhưng `01_intake.csv` cho thấy `img_0011` (chơi tennis) bị loại vì bị báo gần trùng với `img_0008` (trượt tuyết). Hai ảnh khác nhau dù khoảng cách pHash đúng bằng `16`.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được

**Thử cửa chặn.** Với `--budget 0` duyệt **0/193 ảnh**. `work/rep_nb/07_error_list_v3.csv` còn **6 lỗi `MISSING_LABEL_FILE`**. Pipeline trả **Rework**, mã thoát **20**. `work/rep_nb/08_summary.json` ghi `exported: null` và không có manifest trong `work/exp_nb/clean_v1/`.

**Hai điểm mù đo trên tập calibration:**

- **Ảnh gần trùng.** Với `phash_dist = 16`, pipeline chỉ nhận ra **5/6 ca** gần trùng đã chèn và bỏ sót **1 ca** (recall `0.83`).
- **Box lỏng hoặc lệch.** Với `second_opinion.conf = 0.6`, pipeline chỉ gắn đúng cờ `POSSIBLE_LOOSE_BOX` ở **1/5 ca** đã chèn và bỏ sót **4 ca** (recall `0.20`).

## 5. Train: raw vs clean (tùy chọn, chấm riêng)

Hai biến thể dùng cùng model `yolo26n.pt`, 20 epoch, seed `0` và `1`, batch 16, kích thước ảnh 640 và cùng tập test 100 ảnh. Bảng ghi trung bình ± độ lệch chuẩn mẫu của hai seed.

| Biến thể | Ảnh trước lọc Ultralytics |             mAP50 |        mAP50–95 |     Precision |        Recall |
| -------- | ------------------------: | ----------------: | --------------: | ------------: | ------------: |
| `raw`    |                       224 | 0.72575 ± 0.00021 | 0.5117 ± 0.0038 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| `clean`  |                       193 | 0.72940 ± 0.00240 | 0.4996 ± 0.0003 | 0.794 ± 0.028 | 0.619 ± 0.005 |

**Kết quả.** `clean` tăng mAP50 **0.00365** (+0,365 điểm phần trăm), cùng bậc với độ lệch chuẩn của chênh lệch theo cặp seed (`0.00219`). mAP50–95 giảm **0.0121**. Với hai seed, chưa đủ bằng chứng để kết luận `clean` cải thiện mô hình một cách ổn định.

- **Rò rỉ có thể làm điểm `raw` cao hơn.** Báo cáo intake gắn 11 ảnh `raw` với tập test, trong đó đã xác nhận cặp `img_0049` và `test_033` là hai bản của cùng cảnh. Để đo ảnh hưởng, train lại `raw` sau khi chỉ bỏ các cặp rò rỉ đã xác nhận, giữ cùng cấu hình, seed và tập đánh giá.
- **Sửa nhãn `bus` có thể giúp lớp này.** AP50 trung bình của `bus` tăng từ `0.6949` lên `0.7153`, còn tổng số box `bus` trên bốn ảnh được duyệt tăng từ 1 lên 6. Có thể kiểm bằng cách giữ nguyên tập ảnh `clean`, thử khôi phục riêng nhãn cũ trên bốn ảnh rồi so AP50 của `bus` qua nhiều seed.

Chi tiết theo seed và theo lớp nằm trong [ANALYSIS.md](results/ANALYSIS.md).

## 6. Quyết định và ghi chú AI

**Quyết định cuối: Hold.** Bản nháp còn **34/193 ảnh (17,62%)** có cảnh báo chưa duyệt và **0 lỗi bắt buộc**.

- **Prompt chính.** Hãy viết `label_format`, `gate`, `autofix` và `second_opinion` theo yêu cầu và test có sẵn của lab. Hỗ trợ điều chỉnh chính tả, lời văn
- **Cách kiểm.** Chạy `pytest` được **79 test đạt**, đối chiếu các lỗi chèn trên tập calibration và thử `--budget 0` để xác nhận gate trả **Rework** khi còn lỗi bắt buộc.
- **Một lần cần sửa.** AI viết sai các số liệu, tự bịa các số liệu mà không yêu cầu
