"""Thanh nút trên không ở mép trên màn hình: đưa con trỏ vào nút rồi chụm để bấm.

Chỉ bấm lúc BẮT ĐẦU chụm (sự kiện down), nên giữ chụm không bấm lặp.
"Xoa het" phải bấm 2 lần trong confirm_window giây để tránh xóa nhầm.
"""
BUTTONS = ["draw", "select", "erase", "undo", "clear", "unit", "smart"]
GAP = 10


class Toolbar:
    def __init__(self, width, config):
        self.height = config.toolbar_height
        self.confirm_window = config.confirm_window
        n = len(BUTTONS)
        w = (width - GAP * (n + 1)) / n          # chia đều chiều rộng: luôn vừa khung hình
        self.rects = {b: (GAP + i * (w + GAP), 5, GAP + i * (w + GAP) + w, self.height - 5)
                      for i, b in enumerate(BUTTONS)}
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
