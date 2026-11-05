"""Vẽ thanh nút trên không (logic ở interaction/toolbar.py)."""
from airgeo.ui.render import draw_button

LABELS = {"draw": "Ve", "select": "Chon", "erase": "Xoa", "undo": "Undo", "clear": "Xoa het", "smart": "Smart"}


def draw_toolbar(img, ctl, t, cursor):
    """cursor: vị trí con trỏ (để viền nút đang trỏ vào), None nếu không thấy tay."""
    tb = ctl.toolbar
    roi = img[0:tb.height, :]
    roi[:] = (roi * 0.35).astype(roi.dtype)
    hover = tb.hit(cursor) if cursor is not None else None
    armed = tb.clear_armed(t)
    for b, rect in tb.rects.items():
        if b == "clear" and armed:
            label = "Chac chua?"
        elif b == "unit":
            label = f"Don vi: {ctl.board.unit}"
        else:
            label = LABELS[b]
        on = b == ctl.tool or (b == "smart" and ctl.board.smart) or (b == "clear" and armed)
        draw_button(img, rect, label, on=on, hover=b == hover)
