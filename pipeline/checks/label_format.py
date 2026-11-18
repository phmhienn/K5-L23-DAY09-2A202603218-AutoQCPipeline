"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    limits = cfg["label_format"]
    issues = []
    for label_path in ds.label_files():
        stem = label_path.stem
        image_size = ds.image_size(stem)
        boxes_by_class = {}

        for line_no, text in ds.read_label_lines(stem) or []:
            try:
                class_id, cx, cy, w, h = parse_yolo_line(text)
            except (ValueError, OverflowError) as exc:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, str(exc), line=line_no))
                continue

            if not 0 <= class_id < len(ds.classes):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem,
                                    f"ID lớp không hợp lệ: {class_id}", line=line_no))
                continue
            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem,
                                    "Chiều rộng hoặc chiều cao không dương", line=line_no))
                continue

            left, right = cx - w / 2, cx + w / 2
            top, bottom = cy - h / 2, cy + h / 2
            overflow = max(0.0, -left, right - 1, -top, bottom - 1)
            if overflow > limits["overflow_tol"]:
                issues.append(Issue("label_format", ERROR, "BOX_OUT_OF_IMAGE", stem,
                                    f"Box tràn mép ảnh {overflow:.6g}", line=line_no,
                                    extra={"overflow": overflow}))

            box = (cx, cy, w, h)
            previous_boxes = boxes_by_class.setdefault(class_id, [])
            if any(iou_xywh(box, previous) > limits["dup_box_iou"] for previous in previous_boxes):
                issues.append(Issue("label_format", ERROR, "DUP_BOX", stem,
                                    "Box trùng với một dòng trước cùng lớp", line=line_no))
            previous_boxes.append(box)

            if image_size is not None:
                image_width, image_height = image_size
                short_side_px = min(w * image_width, h * image_height)
                if short_side_px < limits["min_box_px"]:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem,
                                        f"Cạnh ngắn chỉ {short_side_px:.2f} px", line=line_no))
            if w * h > limits["max_box_frac"]:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem,
                                    f"Box chiếm {w * h:.1%} diện tích ảnh", line=line_no))

    return issues
