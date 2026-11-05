"""Chụm + lọc mỗi frame: từ bàn tay (MediaPipe) ra điểm con trỏ đã lọc và trạng thái chụm.

Không dùng camera hay cửa sổ nên test được bằng bàn tay giả (tests/conftest.py).
Tách từ session.py của giai đoạn 1; phần nét/hình chuyển sang tools/draw.py + document/board.py.
"""
from dataclasses import dataclass

from airgeo.config import Config
from airgeo.filters import MovingAverage, NoFilter, OneEuro
from airgeo.gesture.pinch import PinchDetector, draw_point


@dataclass
class FrameResult:
    raw: tuple[float, float] | None   # điểm vẽ thô (trung điểm 4–8); None nếu không thấy tay / frame bị bỏ qua
    fpt: tuple[float, float] | None   # điểm đã lọc = con trỏ
    pinched: bool
    holding: bool                     # đang chụm nhưng frame không tin được (xem gesture/pinch.py)


class PinchFilter:
    def __init__(self, config: Config):
        self.pinch = PinchDetector(config.pinch_on, config.pinch_off, config.pinch_grace, config.pinch_mode)
        self.moving_avg = MovingAverage(config.ma_window)
        self.one_euro = OneEuro(config.one_euro_mincutoff, config.one_euro_beta, config.one_euro_dcutoff)
        self.filters = {"none": NoFilter(), "moving_avg": self.moving_avg, "one_euro": self.one_euro}
        self.flt = self.one_euro

    def step(self, hand, t) -> FrameResult:
        pinched = self.pinch.update(hand, t)
        raw = fpt = None
        if hand and not self.pinch.holding:
            raw = draw_point(hand)
            fpt = self.flt.filter(*raw, t)
        elif not hand and not pinched:
            self.flt.reset()  # tránh điểm lọc bị "kéo" từ vị trí cũ khi tay xuất hiện lại
        return FrameResult(raw, fpt, pinched, self.pinch.holding)

    def select_filter(self, name):
        self.flt = self.filters[name]
        self.flt.reset()

    def csv_row(self, hand, t, res: FrameResult, smart):
        """Một dòng CSV cho frame này. Tọa độ thô luôn là landmark 4 và 8 (chưa lọc)."""
        def fmt(v):
            return None if v is None else f"{v:.2f}"
        p4 = hand["p4"] if hand else (None, None)
        p8 = hand["p8"] if hand else (None, None)
        fpt = res.fpt or (None, None)
        return dict(t=f"{t:.6f}", x8_raw=fmt(p8[0]), y8_raw=fmt(p8[1]), x4_raw=fmt(p4[0]), y4_raw=fmt(p4[1]),
                    pinch=int(res.pinched), filter_name=self.flt.name,
                    x_filt=fmt(fpt[0]), y_filt=fmt(fpt[1]), mode="smart" if smart else "free")
