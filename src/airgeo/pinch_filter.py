"""Chụm + lọc mỗi frame: từ bàn tay (MediaPipe) ra điểm con trỏ đã lọc và trạng thái chụm.

Cử chỉ theo ngữ cảnh (`want`, do Controller.gesture_for quyết định theo chỗ con trỏ):
vẽ bằng chụm ngón cái + trỏ, còn thanh nút / bảng nhập / Chọn / Xóa bấm bằng áp 2 ngón trỏ + giữa.
Đang bấm dở thì giữ cử chỉ đó tới khi nhả. Con trỏ lúc rê luôn là đầu ngón trỏ; lúc chụm để vẽ
thì là trung điểm ngón cái – trỏ (xem gesture/pinch.py: draw_point).

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
        g, m = config.pinch_grace, config.pinch_mode
        self.detectors = {"pinch": PinchDetector(config.pinch_on, config.pinch_off, g, m, "pinch"),
                          "two_finger": PinchDetector(config.two_finger_on, config.two_finger_off, g, m, "two_finger")}
        self.active = "pinch"
        self._blocked = False   # cử chỉ mới đã "bấm" sẵn lúc đổi sang -> phải nhả ra rồi bấm lại
        self._source = "p8"     # điểm con trỏ đang lấy từ đâu: "p8" | "mid"
        self.moving_avg = MovingAverage(config.ma_window)
        self.one_euro = OneEuro(config.one_euro_mincutoff, config.one_euro_beta, config.one_euro_dcutoff)
        self.filters = {"none": NoFilter(), "moving_avg": self.moving_avg, "one_euro": self.one_euro}
        self.flt = self.one_euro

    @property
    def pinch(self):
        """Detector của cử chỉ đang dùng (HUD, phím , . chỉnh ngưỡng của nó)."""
        return self.detectors[self.active]

    def step(self, hand, t, want="pinch") -> FrameResult:
        for d in self.detectors.values():   # cả 2 cập nhật mỗi frame để hysteresis / grace luôn đúng
            d.update(hand, t)
        if not self.pinch.pinched and want != self.active:
            self.active = want
            self._blocked = self.pinch.pinched
        det = self.pinch
        if self._blocked and (not det.pinched or det.holding):
            self._blocked = False           # đã thấy 2 ngón tách ra
        pinched = det.pinched and not self._blocked
        holding = det.holding and not self._blocked
        raw = fpt = None
        if hand and not holding:
            source = "mid" if pinched and self.active == "pinch" else "p8"
            if source != self._source:      # điểm con trỏ đổi chỗ: nhảy thẳng, không để bộ lọc kéo vệt
                self._source = source
                self.flt.reset()
            raw = draw_point(hand) if source == "mid" else hand["p8"]
            fpt = self.flt.filter(*raw, t)
        elif not hand and not pinched:
            self.flt.reset()  # tránh điểm lọc bị "kéo" từ vị trí cũ khi tay xuất hiện lại
        return FrameResult(raw, fpt, pinched, holding)

    def toggle_mode(self):
        """Phím P: đo 2D/3D cho cả 2 cử chỉ."""
        for d in self.detectors.values():
            d.toggle_mode()

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
