"""Vẽ thanh nút trên không (logic ở interaction/toolbar.py)."""
from airgeo.ui.render import draw_button, fit_size

LABELS = {"draw": "Vẽ", "select": "Chọn", "erase": "Xóa", "undo": "Hoàn tác", "clear": "Xóa hết", "smart": "Smart"}


def draw_toolbar(img, ctl, t, cursor):
    """cursor: vị trí con trỏ (để viền nút đang trỏ vào), None nếu không thấy tay."""
    tb = ctl.toolbar
    roi = img[0:tb.height, :]
    roi[:] = (roi * 0.35).astype(roi.dtype)
    hover = tb.hit(cursor) if cursor is not None else None
    armed = tb.clear_armed(t)
    labels = {**LABELS, "unit": f"Đơn vị: {ctl.board.unit}", "clear": "Chắc chưa?" if armed else LABELS["clear"]}
    x0, _, x1, _ = tb.rects["draw"]
    size = fit_size(list(labels.values()), x1 - x0, 22)      # cùng 1 cỡ chữ cho cả dải (khung hẹp thì nhỏ lại)
    for b, rect in tb.rects.items():
        on = b == ctl.tool or (b == "smart" and ctl.board.smart) or (b == "clear" and armed)
        draw_button(img, rect, labels[b], on=on, hover=b == hover, scale=size / 36)
