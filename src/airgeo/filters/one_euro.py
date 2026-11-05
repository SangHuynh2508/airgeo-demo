"""1€ Filter: bọc package chính thức của tác giả (BSD-3): https://github.com/casiez/OneEuroFilter

Casiez, Roussel & Vogel (CHI 2012). Giai đoạn 3 sẽ có bản tự cài (one_euro_own.py) cùng interface.
"""
from OneEuroFilter import OneEuroFilter as _OneEuro1D


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
