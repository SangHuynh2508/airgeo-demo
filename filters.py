"""Các bộ lọc làm mượt tọa độ 2D, cùng một interface:

    filter(x, y, t) -> (x_hat, y_hat)   # t: giây, lấy từ time.perf_counter()
    reset()                              # gọi khi mất tay / bắt đầu lại
    name, describe()                     # dùng cho HUD và CSV

Muốn thay bằng bản tự cài đặt: viết class mới có đúng các phương thức trên.
"""
from collections import deque

# Package chính thức của tác giả 1€ Filter (BSD-3): https://github.com/casiez/OneEuroFilter
from OneEuroFilter import OneEuroFilter as _OneEuro1D


class NoFilter:
    name = "none"

    def filter(self, x, y, t):
        return x, y

    def reset(self):
        pass

    def describe(self):
        return "khong loc"


class MovingAverage:
    name = "moving_avg"

    def __init__(self, n=5):
        self.n = n
        self.buf = deque(maxlen=n)

    def set_n(self, n):
        self.n = max(1, n)
        self.buf = deque(self.buf, maxlen=self.n)

    def filter(self, x, y, t):
        self.buf.append((x, y))
        k = len(self.buf)
        return sum(p[0] for p in self.buf) / k, sum(p[1] for p in self.buf) / k

    def reset(self):
        self.buf.clear()

    def describe(self):
        return f"n={self.n}"


class OneEuro:
    """Lọc riêng x và y bằng 2 bộ 1€, truyền timestamp thật (tần số tự cập nhật theo t)."""
    name = "one_euro"

    def __init__(self, mincutoff=1.0, beta=0.007, dcutoff=1.0, freq=30.0):
        # freq chỉ là ước lượng ban đầu; package tự tính lại từ timestamp ở các frame sau
        self.mincutoff, self.beta, self.dcutoff, self.freq = mincutoff, beta, dcutoff, freq
        self.reset()

    def reset(self):
        # Package không có reset(), nên tạo lại 2 bộ lọc
        self.fx = _OneEuro1D(self.freq, self.mincutoff, self.beta, self.dcutoff)
        self.fy = _OneEuro1D(self.freq, self.mincutoff, self.beta, self.dcutoff)

    def set_params(self, mincutoff=None, beta=None):
        if mincutoff is not None:
            self.mincutoff = mincutoff
            self.fx.setMinCutoff(mincutoff)
            self.fy.setMinCutoff(mincutoff)
        if beta is not None:
            self.beta = beta
            self.fx.setBeta(beta)
            self.fy.setBeta(beta)

    def filter(self, x, y, t):
        return self.fx(x, t), self.fy(y, t)

    def describe(self):
        return f"mincutoff={self.mincutoff:.3f} beta={self.beta:.4f}"


if __name__ == "__main__":
    import random
    import statistics

    # Tay "đứng yên" ở (100, 100) có nhiễu ±3 px, 30 Hz: bộ lọc phải giảm độ rung
    random.seed(0)
    samples = [(100 + random.gauss(0, 3), 100 + random.gauss(0, 3), i / 30) for i in range(300)]
    std = {}
    for f in (NoFilter(), MovingAverage(5), OneEuro()):
        std[f.name] = statistics.pstdev([f.filter(*s)[0] for s in samples][30:])
        print(f"{f.name:10s} std_x = {std[f.name]:.2f} px")
    assert std["one_euro"] < std["none"] / 2
    print("filters OK")
