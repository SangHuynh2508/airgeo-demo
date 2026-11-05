"""Bộ lọc đơn giản để so sánh: không lọc và trung bình trượt (Moving Average)."""
from collections import deque


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
