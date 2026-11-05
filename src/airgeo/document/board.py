"""Bản vẽ: danh sách hình, tỉ lệ, đơn vị, chế độ Smart Shape và lịch sử Undo.

Mọi thay đổi đi qua các hàm ở đây; trước mỗi thao tác lưu 1 bản sao (shapes + scale) để Undo.
Hình là dict: id, kind, pts, raw = [(x, y, t)] của nét gốc, locked (đã sửa số đo);
hình tròn thêm center, radius.
"""
import copy
from collections import deque

from airgeo.geometry.hit import distance_to_shape
from airgeo.geometry.recognize import recognize
from airgeo.geometry.units import UNITS


def make_shape(raw, smart):
    """raw: [(x, y, t)] của nét. Giữ lại raw để nhận dạng lại khi bật/tắt Smart Shape."""
    shape = recognize(raw) if smart else {"kind": "free", "pts": [(x, y) for x, y, _ in raw]}
    shape["raw"] = raw
    return shape


def describe_result(shape):
    info = shape.get("info", {})
    return shape["kind"] + "".join(f" {k}={v}" for k, v in info.items())


class Board:
    def __init__(self, history_limit=50):
        self.shapes = []
        self.scale = None      # số px ứng với 1 cm; None = chưa đặt (số đo hiện px)
        self.unit = "cm"
        self.smart = False
        self.last_info = ""    # lý do nhận dạng của nét cuối, hiển thị lên HUD
        self._history = deque(maxlen=history_limit)
        self._next_id = 1

    def begin(self):
        """Lưu bản sao trước 1 thao tác. Gọi đúng 1 lần cho mỗi thao tác."""
        self._history.append((copy.deepcopy(self.shapes), self.scale, self.smart))

    def undo(self):
        if not self._history:
            return
        self.shapes, self.scale, smart_then = self._history.pop()
        if smart_then != self.smart:
            # Smart đã bật/tắt sau thao tác đó (bật/tắt Smart không nằm trong lịch sử):
            # nhận dạng lại để khớp chế độ hiện tại
            self.set_smart(self.smart)

    def get(self, sid):
        return next((s for s in self.shapes if s["id"] == sid), None)

    def add_stroke(self, raw):
        self.begin()
        shape = make_shape(raw, self.smart)
        shape["id"], shape["locked"] = self._next_id, False
        self._next_id += 1
        self.shapes.append(shape)
        self.last_info = describe_result(shape)
        return shape

    def remove(self, sid):
        if self.get(sid) is not None:
            self.begin()
            self.shapes = [s for s in self.shapes if s["id"] != sid]

    def clear(self):
        if self.shapes:
            self.begin()
            self.shapes = []

    def translate(self, sid, dx, dy):
        """Không tự lưu Undo: công cụ Chọn gọi begin() 1 lần khi bắt đầu kéo (cả lần kéo = 1 bước)."""
        s = self.get(sid)
        if s is None:
            return
        s["pts"] = [(x + dx, y + dy) for x, y in s["pts"]]
        s["raw"] = [(x + dx, y + dy, t) for x, y, t in s["raw"]]   # để bật/tắt Smart vẫn đúng vị trí
        if "center" in s:
            cx, cy = s["center"]
            s["center"] = (cx + dx, cy + dy)

    def apply_edit(self, sid, shape, scale):
        """Thay hình bằng hình dựng lại theo số đo và đặt tỉ lệ, cùng 1 bước Undo."""
        self.begin()
        self.scale = scale
        self.shapes = [shape if s["id"] == sid else s for s in self.shapes]

    def set_smart(self, on):
        self.smart = on
        self.shapes = [s if s["locked"] else self._rerecognized(s) for s in self.shapes]

    def _rerecognized(self, s):
        new = make_shape(s["raw"], self.smart)
        new["id"], new["locked"] = s["id"], False
        return new

    def cycle_unit(self):
        self.unit = UNITS[(UNITS.index(self.unit) + 1) % len(UNITS)]

    def shape_at(self, pos, radius):
        """Hình vẽ sau cùng (nằm trên) có nét cách pos không quá radius px."""
        for s in reversed(self.shapes):
            if distance_to_shape(pos, s) <= radius:
                return s
        return None
