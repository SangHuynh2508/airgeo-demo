"""Tiện ích dùng chung cho test."""


def tri_path(y=300, x0=100, x1=260, n=5):
    """Nét tam giác kín (đáy ngang ở y, đỉnh cao 140 px) như khi vẽ tay: n điểm mỗi cạnh, 3n + 1 điểm."""
    c = [(x0, y), (x1, y), ((x0 + x1) / 2, y - 140)]
    return [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
            for a, b in zip(c, c[1:] + c[:1]) for k in range(n)] + [c[0]]


def place_tri(ctl, y, x0=100, x1=300):
    """Đặt tam giác đáy ngang (x0..x1, y), đỉnh cao 80 px vào bảng (1 bước Undo như khi vẽ). Không vẽ qua công cụ
    Vẽ vì vẽ thì hình mới thay hình cũ và được phóng to ra giữa."""
    b = ctl.board
    b.begin()
    s = {"kind": "triangle", "pts": [(x0, y), (x1, y), ((x0 + x1) / 2, y - 80)], "id": b._next_id}
    b._next_id += 1
    b.shapes.append(s)
    return s
