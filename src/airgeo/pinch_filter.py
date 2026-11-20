"""Chụm + lọc mỗi frame: từ bàn tay (MediaPipe) ra điểm con trỏ đã lọc và trạng thái chụm.

Cử chỉ theo ngữ cảnh (`want`, do Controller.gesture_for quyết định theo chỗ con trỏ):
vẽ bằng chụm ngón cái + trỏ, còn thanh nút / bảng nhập / Chọn / Xóa bấm bằng áp 2 ngón trỏ + giữa.
Đang bấm dở thì giữ cử chỉ đó tới khi nhả. Con trỏ lúc rê luôn là đầu ngón trỏ; lúc chụm để vẽ
thì là trung điểm ngón cái – trỏ (xem gesture/pinch.py: draw_point).

Ổn định điểm bấm ("hiệu ứng Heisenberg": chính động tác khép ngón kéo lệch con trỏ, Bowman 2001):
lúc nhận ra bấm, điểm bấm lấy chính điểm bấm (trung điểm 4-8 khi chụm) của `press_rewind` giây trước – chỉ gỡ
phần cả bàn tay trôi, không gỡ quãng đầu ngón trỏ đi xuống khi khép (sẽ làm con trỏ treo xa tay); suốt lần bấm con
trỏ = điểm nguồn + độ lệch cố định (đi theo tay, không nhảy); nhả ra thì độ lệch giảm dần về 0 trong DECAY giây.
Phím S tắt / bật (so sánh trong bài đo bấm mục tiêu).

Không dùng camera hay cửa sổ nên test được bằng bàn tay giả (tests/conftest.py).
Tách từ session.py của giai đoạn 1; phần nét/hình chuyển sang tools/draw.py + document/board.py.
"""
import math
from collections import deque
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


DECAY = 0.15        # giây để con trỏ trượt từ điểm bấm về lại đầu ngón sau khi nhả


class PinchFilter:
    def __init__(self, config: Config):
        g, m, c = config.pinch_grace, config.pinch_mode, config.release_confirm
        self.detectors = {"pinch": PinchDetector(config.pinch_on, config.pinch_off, g, m, "pinch", c),
                          "two_finger": PinchDetector(config.two_finger_on, config.two_finger_off, g, m,
                                                      "two_finger", c)}
        self.active = "pinch"
        self._blocked = False   # cử chỉ mới đã "bấm" sẵn lúc đổi sang -> phải nhả ra rồi bấm lại
        self._source = "p8"     # điểm con trỏ đang lấy từ đâu: "p8" | "mid"
        self.stabilize = True   # ổn định điểm bấm (phím S)
        self.rewind, self.rewind_max = config.press_rewind, config.press_rewind_max_px
        self._hist = deque()    # (t, điểm bấm thô của cử chỉ đang dùng) lúc rê, ~0.5 s gần nhất
        self._pressing = False  # đã có điểm của lần bấm hiện tại
        self._offset = (0.0, 0.0)
        self._released = None   # (t nhả, độ lệch lúc nhả) – độ lệch đang giảm dần
        self._last_in = None    # điểm cuối cùng đưa vào bộ lọc
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
        if (self._blocked or not self.pinch.pinched) and want != self.active:
            self.active = want              # đang bị chặn (chưa bấm gì) thì cũng đổi được
            self._blocked = self.pinch.pinched
            self._hist.clear()              # điểm bấm cũ là của cử chỉ kia (trung điểm 4-8 / đầu ngón trỏ)
        det = self.pinch
        if self._blocked and not det.pinched:
            self._blocked = False           # đã thấy 2 ngón tách ra (mất tay 1 frame = "giữ", chưa phải tách)
        pinched = det.pinched and not self._blocked
        holding = det.holding and not self._blocked
        raw = fpt = None
        if hand and not holding:
            source = "mid" if pinched and self.active == "pinch" else "p8"
            raw = draw_point(hand) if source == "mid" else hand["p8"]
            if not self.stabilize:
                if source != self._source:  # điểm con trỏ đổi chỗ: nhảy thẳng, không để bộ lọc kéo vệt
                    self.flt.reset()
                self._offset = (0.0, 0.0)
            elif pinched and not self._pressing:
                aim = self._aim(t)          # điểm bấm trước lúc ngón khép
                if aim is not None:
                    ox, oy = aim[0] - raw[0], aim[1] - raw[1]
                    k = min(1.0, self.rewind_max / max(math.hypot(ox, oy), 1e-9))   # chỉ gỡ trôi, không gỡ cú quét tay
                    self._offset = (ox * k, oy * k)
                    self.flt.reset()        # bộ lọc bắt đầu đúng tại điểm bấm
                self._released = None
                self._hist.clear()          # lần bấm sau chỉ lùi theo các điểm rê sau lần này
            elif not pinched and self._pressing and self._last_in is not None:
                # vừa nhả: giữ con trỏ tại chỗ rồi trượt dần về đầu ngón
                self._released = (t, (self._last_in[0] - raw[0], self._last_in[1] - raw[1]))
            if not pinched and self._released:
                t0, (ox, oy) = self._released
                k = max(0.0, 1 - (t - t0) / DECAY)
                self._offset = (ox * k, oy * k)
                if k == 0:
                    self._released = None
            self._source, self._pressing = source, pinched
            self._last_in = (raw[0] + self._offset[0], raw[1] + self._offset[1])
            fpt = self.flt.filter(*self._last_in, t)
            if not pinched:
                self._hist.append((t, draw_point(hand) if self.active == "pinch" else hand["p8"]))
                while self._hist and t - self._hist[0][0] > 0.5:
                    self._hist.popleft()
        elif not hand and not pinched:
            self.flt.reset()  # tránh điểm lọc bị "kéo" từ vị trí cũ khi tay xuất hiện lại
            self._hist.clear()
            self._pressing, self._offset, self._released, self._last_in = False, (0.0, 0.0), None, None
        return FrameResult(raw, fpt, pinched, holding)

    def _aim(self, t):
        """Điểm bấm lúc t - rewind (lấy điểm mới nhất không muộn hơn); lịch sử ngắn hơn thì lấy điểm cũ nhất."""
        if not self._hist:
            return None
        before = [p for tt, p in self._hist if tt <= t - self.rewind]
        return before[-1] if before else self._hist[0][1]

    def toggle_mode(self):
        """Phím P: đo 2D/3D cho cả 2 cử chỉ."""
        for d in self.detectors.values():
            d.toggle_mode()

    def select_filter(self, name):
        self.flt = self.filters[name]
        self.flt.reset()

    def csv_row(self, hand, t, res: FrameResult):
        """Một dòng CSV cho frame này. Tọa độ thô luôn là landmark 4 và 8 (chưa lọc)."""
        def fmt(v):
            return None if v is None else f"{v:.2f}"
        p4 = hand["p4"] if hand else (None, None)
        p8 = hand["p8"] if hand else (None, None)
        fpt = res.fpt or (None, None)
        return dict(t=f"{t:.6f}", x8_raw=fmt(p8[0]), y8_raw=fmt(p8[1]), x4_raw=fmt(p4[0]), y4_raw=fmt(p4[1]),
                    pinch=int(res.pinched), filter_name=self.flt.name,
                    x_filt=fmt(fpt[0]), y_filt=fmt(fpt[1]), mode="smart")
