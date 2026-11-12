"""Menu tròn cho lệnh ít dùng (Đơn vị, Smart, Xóa hết): giữ xòe tay lâu thì mở quanh bàn tay, áp 2 ngón vào mục
để chọn. Bấm ra ngoài / mục Đóng / quá TIMEOUT giây thì đóng. "Xóa hết" bấm 2 lần mới xóa."""
import math

ITEMS = ["unit", "smart", "clear", "close"]      # trên, phải, dưới, trái
RADIUS, ITEM_R, TIMEOUT = 120, 48, 6.0


class RadialMenu:
    def __init__(self, width, height, top=0, confirm_window=2.0):
        self.width, self.height, self.top = width, height, top
        self.confirm_window = confirm_window
        self.center = None
        self.opened = 0.0
        self._armed_until = float("-inf")

    @property
    def is_open(self):
        return self.center is not None

    def open(self, center, t):
        m = RADIUS + ITEM_R        # kẹp tâm để mọi mục nằm trong khung (dưới dải trạng thái)
        self.center = (min(max(center[0], m), self.width - m), min(max(center[1], self.top + m), self.height - m))
        self.opened, self._armed_until = t, float("-inf")

    def close(self):
        self.center = None

    def positions(self):
        cx, cy = self.center
        return [(a, (cx + RADIUS * math.cos(math.radians(-90 + 90 * i)), cy + RADIUS * math.sin(math.radians(-90 + 90 * i))))
                for i, a in enumerate(ITEMS)]

    def hit(self, pos):
        return next((a for a, p in self.positions() if math.dist(pos, p) <= ITEM_R), None)

    def clear_armed(self, t):
        return t <= self._armed_until

    def press(self, pos, t):
        """Trả về lệnh cần chạy (menu đóng lại), hoặc None."""
        a = self.hit(pos)
        if a == "clear" and not self.clear_armed(t):
            self._armed_until, self.opened = t + self.confirm_window, t   # lần 1: đổi chữ "Chắc chưa?"
            return None
        self.close()
        return None if a in (None, "close") else a

    def expired(self, t):
        return self.is_open and t - self.opened > TIMEOUT
