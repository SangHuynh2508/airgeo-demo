"""Logic mỗi frame của bảng vẽ: chụm -> lọc -> nét -> nhận dạng hình.

Không dùng camera hay cửa sổ, nên test được bằng bàn tay giả (tests/conftest.py)
và sau này chạy lại được trên dữ liệu CSV đã ghi (giai đoạn 2).
"""
from dataclasses import dataclass

from airgeo.config import Config
from airgeo.filters import MovingAverage, NoFilter, OneEuro
from airgeo.geometry.recognize import recognize
from airgeo.gesture.pinch import PinchDetector, draw_point


@dataclass
class FrameResult:
    raw: tuple[float, float] | None   # điểm vẽ thô (trung điểm 4–8); None nếu không thấy tay / frame bị bỏ qua
    fpt: tuple[float, float] | None   # điểm đã lọc
    pinched: bool
    holding: bool                     # đang chụm nhưng frame không tin được (xem gesture/pinch.py)


def make_shape(raw, smart):
    """raw: [(x, y, t)] của nét. Giữ lại raw để nhận dạng lại khi bật/tắt Smart Shape."""
    shape = recognize(raw) if smart else {"kind": "free", "pts": [(x, y) for x, y, _ in raw]}
    shape["raw"] = raw
    return shape


def describe_result(shape):
    info = shape.get("info", {})
    return shape["kind"] + "".join(f" {k}={v}" for k, v in info.items())


class DrawingSession:
    def __init__(self, config: Config):
        self.pinch = PinchDetector(config.pinch_on, config.pinch_off, config.pinch_grace, config.pinch_mode)
        self.moving_avg = MovingAverage(config.ma_window)
        self.one_euro = OneEuro(config.one_euro_mincutoff, config.one_euro_beta, config.one_euro_dcutoff)
        self.filters = {"none": NoFilter(), "moving_avg": self.moving_avg, "one_euro": self.one_euro}
        self.flt = self.one_euro
        self.strokes = []    # các nét đã xong: dict hình (geometry/recognize.py) + "raw" = [(x, y, t)]
        self.cur = None      # nét đang vẽ: [(x_filt, y_filt, t)]
        self.smart = False
        self.last_info = ""  # lý do nhận dạng của nét cuối, hiển thị lên HUD

    def step(self, hand, t) -> FrameResult:
        pinched = self.pinch.update(hand, t)
        raw = fpt = None
        if hand and not self.pinch.holding:
            raw = draw_point(hand)
            fpt = self.flt.filter(*raw, t)
        elif not hand and not pinched:
            self.flt.reset()  # tránh điểm lọc bị "kéo" từ vị trí cũ khi tay xuất hiện lại

        # Chụm thì nối điểm đã lọc thành nét, nhả thì kết thúc nét.
        # Frame "holding" bị bỏ qua: không đưa vào bộ lọc, không thêm điểm.
        if pinched:
            if self.cur is None:
                self.cur = []
            if fpt:
                self.cur.append((fpt[0], fpt[1], t))
        elif self.cur is not None:
            if len(self.cur) >= 2:
                self.strokes.append(make_shape(self.cur, self.smart))
                self.last_info = describe_result(self.strokes[-1])
            self.cur = None
        return FrameResult(raw, fpt, pinched, self.pinch.holding)

    def select_filter(self, name):
        self.flt = self.filters[name]
        self.flt.reset()

    def toggle_smart(self):
        # Nhận dạng lại cả các nét đã vẽ, để bật/tắt thấy khác biệt ngay
        self.smart = not self.smart
        self.strokes = [make_shape(s["raw"], self.smart) for s in self.strokes]

    def undo(self):
        if self.strokes:
            self.strokes.pop()

    def clear(self):
        self.strokes.clear()

    def csv_row(self, hand, t, res: FrameResult):
        """Một dòng CSV cho frame này. Tọa độ thô luôn là landmark 4 và 8 (chưa lọc)."""
        def fmt(v):
            return None if v is None else f"{v:.2f}"
        p4 = hand["p4"] if hand else (None, None)
        p8 = hand["p8"] if hand else (None, None)
        fpt = res.fpt or (None, None)
        return dict(t=f"{t:.6f}", x8_raw=fmt(p8[0]), y8_raw=fmt(p8[1]), x4_raw=fmt(p4[0]), y4_raw=fmt(p4[1]),
                    pinch=int(res.pinched), filter_name=self.flt.name,
                    x_filt=fmt(fpt[0]), y_filt=fmt(fpt[1]), mode="smart" if self.smart else "free")
