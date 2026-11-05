"""Vẽ bảng nhập số đo + bàn phím số trên không (logic ở interaction/edit_panel.py)."""
import cv2

from airgeo.ui.render import draw_button, text

TITLES = {"line": "Doan thang", "triangle": "Tam giac", "rect": "Chu nhat", "circle": "Hinh tron"}
HINT_COLOR = (150, 150, 150)
ERROR_COLOR = (0, 0, 255)


def draw_edit_panel(img, panel, unit, cursor):
    """cursor: vị trí con trỏ để viền phím đang trỏ vào, None nếu không thấy tay."""
    x0, y0, x1, y1 = panel.rect
    roi = img[y0:y1, x0:x1]
    roi[:] = (roi * 0.25).astype(roi.dtype)
    cv2.rectangle(img, (x0, y0), (x1, y1), (200, 200, 200), 1)
    hover = panel.hit(cursor) if cursor is not None else None
    text(img, f"{TITLES[panel.kind]}  (don vi: {unit})", panel.title_pos, 0.6)
    draw_button(img, panel.reset_rect, "Dat lai ti le", on=panel.reset_scale,
                hover=hover == ("reset", None), scale=0.5)
    for f, r in zip(panel.fields, panel.field_rects):
        draw_button(img, r, "", on=f == panel.focus, hover=hover == ("field", f))
        v = panel.values[f]
        text(img, f"{f}: {v or panel.hints[f]}", (int(r[0]) + 8, int(r[3]) - 17), 0.6,
             (255, 255, 255) if v else HINT_COLOR)
    for ch, r in panel.key_rects.items():
        draw_button(img, r, ch, hover=hover == ("key", ch), scale=0.8)
    draw_button(img, panel.ok_rect, "OK", hover=hover == ("ok", None))
    draw_button(img, panel.cancel_rect, "Huy", hover=hover == ("cancel", None))
    if panel.error:
        text(img, "Loi: " + panel.error, panel.error_pos, 0.55, ERROR_COLOR)
