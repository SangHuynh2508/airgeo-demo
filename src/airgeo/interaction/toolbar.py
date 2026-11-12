"""Thanh nút trên không ở mép trên màn hình: đưa con trỏ vào nút rồi chụm để bấm.

Chỉ bấm lúc BẮT ĐẦU chụm (sự kiện down), nên giữ chụm không bấm lặp.
"Xoa het" phải bấm 2 lần trong confirm_window giây để tránh xóa nhầm.
Giao diện chính là tư thế tay (gesture/pose.py); thanh này là dự phòng + cho biết trạng thái.
2 cụm: công cụ (Vẽ, Chọn, Xóa) bên trái | lệnh bên phải.
"""
BUTTONS = ["draw", "select", "erase", "undo", "unit", "smart", "clear"]
GAP, SPLIT = 10, 40     # khe giữa các nút / thêm giữa 2 cụm


class Toolbar:
    def __init__(self, width, config):
        self.height = config.toolbar_height
        self.confirm_window = config.confirm_window
        n = len(BUTTONS)
        w = (width - GAP * (n + 1) - SPLIT) / n   # chia đều chiều rộng: luôn vừa khung hình
        x = [GAP + i * (w + GAP) + SPLIT * (i >= 3) for i in range(n)]
        self.rects = {b: (x[i], 5, x[i] + w, self.height - 5) for i, b in enumerate(BUTTONS)}
        self._armed_until = float("-inf")

    def contains(self, pos):
        return pos[1] < self.height

    def hit(self, pos):
        for b, (x0, y0, x1, y1) in self.rects.items():
            if x0 <= pos[0] <= x1 and y0 <= pos[1] <= y1:
                return b
        return None

    def press(self, pos, t):
        """Gọi khi bắt đầu chụm trong thanh nút. Trả về hành động cần làm, hoặc None."""
        b = self.hit(pos)
        if b == "clear" and not self.clear_armed(t):
            self._armed_until = t + self.confirm_window   # lần 1: nút đổi chữ thành "Chac chua?"
            return None
        self._armed_until = float("-inf")
        return b

    def clear_armed(self, t):
        return t <= self._armed_until
