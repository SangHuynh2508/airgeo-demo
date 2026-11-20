"""Tiện ích dùng chung cho test."""


def place_line(ctl, y, x0=100, x1=300):
    """Đặt đoạn thẳng ngang thẳng vào bảng (1 bước Undo như khi vẽ). Không vẽ qua công cụ Vẽ vì vẽ thì hình mới
    thay hình cũ và được phóng to ra giữa."""
    b = ctl.board
    b.begin()
    s = {"kind": "line", "pts": [(x0, y), (x1, y)], "raw": [(x0, y, 0.0), (x1, y, 0.0)], "id": b._next_id,
         "locked": False}
    b._next_id += 1
    b.shapes.append(s)
    return s
