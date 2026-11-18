"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, parse_yolo_line


DROP_LINES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMAGES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _clip_box(line):
    class_id, cx, cy, w, h = parse_yolo_line(line)
    left, right = max(0.0, cx - w / 2), min(1.0, cx + w / 2)
    top, bottom = max(0.0, cy - h / 2), min(1.0, cy + h / 2)
    if right <= left or bottom <= top:
        return ""
    return f"{class_id} {(left + right) / 2} {(top + bottom) / 2} {right - left} {bottom - top}"


def fix(ds, issues, cfg):
    fixes = []
    remove_stems, needs_label = set(), set()
    line_codes = defaultdict(dict)
    rename_classes = False

    for issue in issues:
        if issue.severity != ERROR:
            continue
        code, stem = issue.code, issue.image
        if code in REMOVE_IMAGES or code.startswith("DUP_IMAGE_"):
            remove_stems.add(stem)
        elif code == "MISSING_LABEL_FILE":
            needs_label.add(stem)
        elif code == "BAD_CLASS_NAME":
            rename_classes = True
        elif issue.line is not None and (code in DROP_LINES or code == "BOX_OUT_OF_IMAGE"):
            line_codes[stem].setdefault(issue.line, set()).add(code)

    for path in ds.image_files():
        stem = path.stem
        if stem in remove_stems:
            path.unlink()
            ds.label_path(stem).unlink(missing_ok=True)
            fixes.append(dict(image=stem, line=None, action="remove_image", before=path.name, after=""))
        elif stem in needs_label and not ds.label_path(stem).exists():
            fixes.append(dict(image=stem, line=None, action="needs_label",
                              before="(không có file)", after="chuyển người gán"))

    for path in ds.label_files():
        stem = path.stem
        if stem not in line_codes or stem in remove_stems:
            continue
        kept = []
        changed = False
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True), 1):
            codes = line_codes[stem].get(line_no)
            if not codes:
                kept.append(line)
                continue
            before = line.rstrip("\r\n")
            after = "" if codes & DROP_LINES else _clip_box(before)
            action = "clip_box" if after else "drop_line"
            if after:
                kept.append(after + "\n")
            fixes.append(dict(image=stem, line=line_no, action=action, before=before, after=after))
            changed = True
        if changed:
            path.write_text("".join(kept), encoding="utf-8")

    if rename_classes:
        path = ds.yaml_path
        data = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
        names = dict(enumerate(cfg["classes"]))
        if ds.yaml_names() != names:
            before = data.get("names")
            data["names"] = names
            path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
            fixes.append(dict(image="data.yaml", line=None, action="rename_classes",
                              before=str(before), after=str(names)))

    return fixes
