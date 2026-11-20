"""Vẽ thanh nút trên không (logic ở interaction/toolbar.py)."""
from airgeo.ui.render import _label_chip, draw_button, fit_size
from airgeo.ui.text import text_size

LABELS = {"draw": "Vẽ", "select": "Chọn", "erase": "Xóa", "undo": "Hoàn tác", "clear": "Xóa hết"}
CHIP_SIZE = 26          # cỡ chữ viên công cụ khi dải nút ẩn


def draw_toolbar(img, ctl, t, cursor):
    """cursor: vị trí con trỏ (để viền nút đang trỏ vào), None nếu không thấy tay.
    Dải ẩn: chỉ 1 viên góc dưới trái cho biết công cụ + đơn vị (góc trên trái là vùng xóa khi kéo hình)."""
    tb = ctl.toolbar
    if not tb.visible:
        s = f"{LABELS[ctl.tool]}  ·  {ctl.board.unit}"
        _label_chip(img, [s], (24, img.shape[0] - text_size([s], CHIP_SIZE, True)[1] - 18), CHIP_SIZE, bold=True)
        return
    roi = img[0:tb.height, :]
    roi[:] = (roi * 0.35).astype(roi.dtype)
    hover = tb.hit(cursor) if cursor is not None else None
    armed = tb.clear_armed(t)
    labels = {**LABELS, "unit": f"Đơn vị: {ctl.board.unit}", "clear": "Chắc chưa?" if armed else LABELS["clear"]}
    x0, _, x1, _ = tb.rects["draw"]
    size = fit_size(list(labels.values()), x1 - x0, 22)      # cùng 1 cỡ chữ cho cả dải (khung hẹp thì nhỏ lại)
    for b, rect in tb.rects.items():
        on = b == ctl.tool or (b == "clear" and armed)
        draw_button(img, rect, labels[b], on=on, hover=b == hover, scale=size / 36)
