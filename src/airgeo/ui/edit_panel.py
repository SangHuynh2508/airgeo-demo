"""Vẽ bảng nhập số đo: ô các cạnh, ô viết số trên không, nút (logic ở interaction/edit_panel.py)."""
import cv2
import numpy as np

from airgeo.ui.render import BUTTON_EDGE, BUTTON_HOVER, FIELD_LABELS, draw_button, ip
from airgeo.ui.text import put_text, text_size

TITLES = {"line": "Đoạn thẳng", "triangle": "Tam giác", "rect": "Hình chữ nhật", "circle": "Hình tròn"}
BUTTON_LABELS = {"dot": "Dấu chấm", "back": "← Xóa 1 số", "clear": "Xóa ô", "ok": "OK", "cancel": "Hủy"}
INK = (255, 255, 255)
GUIDE = (90, 90, 90)
DIGIT_COLOR = (0, 220, 255)
ERROR_COLOR = (90, 90, 255)


def _stroke(img, pts):
    if len(pts) >= 2:
        cv2.polylines(img, [np.array([ip(p) for p in pts], np.int32)], False, INK, 4, cv2.LINE_AA)
    elif pts:
        cv2.circle(img, ip(pts[0]), 3, INK, -1, cv2.LINE_AA)


def draw_edit_panel(img, panel, unit, cursor):
    """cursor: vị trí con trỏ để viền ô / nút đang trỏ vào, None nếu không thấy tay."""
    x0, y0, x1, y1 = panel.rect
    roi = img[y0:y1, x0:x1]
    roi[:] = (roi * 0.2).astype(roi.dtype)
    cv2.rectangle(img, (x0, y0), (x1, y1), BUTTON_EDGE, 1)
    writing = cursor is not None and panel.in_pad(cursor)
    hover = panel.hit(cursor) if cursor is not None and not writing else None
    put_text(img, [f"{TITLES[panel.kind]}: nhập số đo ({unit})"], panel.title_pos, 22, bold=True)
    for f, r in zip(panel.fields, panel.field_rects):
        v = panel.values[f]
        label = f"{FIELD_LABELS.get(f, f)} = {v} {unit}" if v else f"{FIELD_LABELS.get(f, f)} = …"
        draw_button(img, r, label, on=f == panel.focus, hover=hover == ("field", f), scale=26 / 36)

    # ô viết: nền tối hơn, dòng kẻ chân chữ, chữ số nhận được hiện vàng phía trên từng chữ
    px0, py0, px1, py1 = panel.pad_rect
    pad = img[py0:py1, px0:px1]
    pad[:] = (pad * 0.5).astype(pad.dtype)
    cv2.rectangle(img, (px0, py0), (px1, py1), BUTTON_HOVER if writing else BUTTON_EDGE, 3 if writing else 1)
    base_y = py0 + int((py1 - py0) * 0.85)
    cv2.line(img, (px0 + 12, base_y), (px1 - 12, base_y), GUIDE, 1, cv2.LINE_AA)
    if not panel.reader.groups and panel.cur is None:
        hint = "Chụm ngón cái + trỏ, viết số vào đây (hoặc gõ bàn phím)"
        w, h = text_size([hint], 20)
        put_text(img, [hint], ((px0 + px1 - w) // 2, (py0 + py1 - h) // 2), 20, (150, 150, 150))
    for g in panel.reader.groups:
        for s in g["strokes"]:
            _stroke(img, s)
        put_text(img, [g["ch"]], (int(g["x0"]), py0 + 4), 22, DIGIT_COLOR, bold=True)
    if panel.cur:
        _stroke(img, panel.cur)

    for b, r in panel.button_rects.items():
        draw_button(img, r, BUTTON_LABELS[b], hover=hover == ("button", b), scale=22 / 36, primary=b == "ok")
    if panel.error:
        put_text(img, [panel.error], panel.error_pos, 20, ERROR_COLOR, bold=True)
