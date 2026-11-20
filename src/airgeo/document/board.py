"""Bản vẽ: hình đang giảng, tỉ lệ, đơn vị và lịch sử Undo. Nét vẽ luôn được nhận dạng; nét không ra hình bị bỏ.
Mỗi lúc 1 hình: vẽ hình mới thì thay hình cũ (Undo lấy lại).

Mọi thay đổi đi qua các hàm ở đây; trước mỗi thao tác lưu 1 bản sao (shapes + scale) để Undo.
Hình là dict: id, kind, pts, raw = [(x, y, t)] của nét gốc, locked (đã sửa số đo);
hình tròn thêm center, radius.
"""
import copy
from collections import deque

from airgeo.geometry.construct import fit
from airgeo.geometry.hit import contains, distance_to_shape, overlaps
from airgeo.geometry.measure import measure
from airgeo.geometry.recognize import recognize
from airgeo.geometry.rotate import rotate_points, straighten
from airgeo.geometry.shapes import tidy
from airgeo.geometry.units import UNITS


def make_shape(raw):
    """raw: [(x, y, t)] của nét -> hình đã nhận dạng, nắn (gần vuông / đều / cân...) và làm thẳng trục.
    Không ra hình thì kind = "free"."""
    shape = recognize(raw)
    shape["raw"] = raw
    return straighten(tidy(shape))


def describe_result(shape):
    info = shape.get("info", {})
    return shape["kind"] + "".join(f" {k}={v}" for k, v in info.items())


class Board:
    def __init__(self, history_limit=50):
        self.shapes = []
        self.scale = None      # số px ứng với 1 cm; None = chưa đặt (số đo hiện px)
        self.unit = "cm"
        self.last_info = ""    # lý do nhận dạng của nét cuối, hiển thị lên HUD
        self._history = deque(maxlen=history_limit)
        self._next_id = 1

    def begin(self):
        """Lưu bản sao trước 1 thao tác. Gọi đúng 1 lần cho mỗi thao tác. Trả về bản sao (để undo(only=...))."""
        self._history.append((copy.deepcopy(self.shapes), self.scale))
        return self._history[-1]

    def undo(self, only=None):
        """Gỡ bước cuối. only: chỉ gỡ nếu bước cuối đúng là bản sao này (đã bị U / Xóa hết gỡ mất thì thôi).
        Trả về False nếu không có gì để gỡ."""
        if not self._history or (only is not None and self._history[-1] is not only):
            return False
        self.shapes, self.scale = self._history.pop()
        return True

    def get(self, sid):
        return next((s for s in self.shapes if s["id"] == sid), None)

    def add_stroke(self, raw):
        """Nét đã nhận dạng thay hình cũ (1 bước Undo, tỉ lệ về chưa đặt vì hình mới chưa có số đo).
        Nét không ra hình: không thêm, không lưu Undo, trả về hình kind "free" (không có id)."""
        shape = make_shape(raw)
        self.last_info = describe_result(shape)
        if shape["kind"] == "free":
            return shape
        self.begin()
        shape["id"], shape["locked"] = self._next_id, False
        self._next_id += 1
        self.shapes, self.scale = [shape], None
        return shape

    def fit(self, sid, box):
        """Phóng / thu hình cho vừa box và ra giữa; tỉ lệ nhân theo nên số đo (cm) giữ nguyên. Không tự lưu Undo
        (đi cùng bước vẽ / sửa số đo)."""
        s = self.get(sid)
        if s is None:
            return
        new, k = fit(s, box)
        self.shapes = [new if x["id"] == sid else x for x in self.shapes]
        if self.scale is not None:
            self.scale *= k

    def collides(self, shape, ignore_id=None):
        """Hình đầu tiên bị shape đè lên (bỏ qua hình ignore_id – chính nó khi kéo / sửa), None nếu không đè."""
        return next((s for s in self.shapes if s["id"] != ignore_id and overlaps(shape, s)), None)

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
        s["raw"] = [(x + dx, y + dy, t) for x, y, t in s["raw"]]
        if "center" in s:
            cx, cy = s["center"]
            s["center"] = (cx + dx, cy + dy)

    def rotate(self, sid, deg, about):
        """Xoay hình quanh about (độ, chiều kim đồng hồ trên ảnh). Như translate: không tự lưu Undo."""
        s = self.get(sid)
        if s is None:
            return
        s["pts"] = rotate_points(s["pts"], deg, about)
        s["raw"] = rotate_points(s["raw"], deg, about)
        if "center" in s:
            s["center"] = rotate_points([s["center"]], deg, about)[0]

    def apply_edit(self, sid, shape, scale):
        """Thay hình bằng hình dựng lại theo số đo và đặt tỉ lệ, cùng 1 bước Undo."""
        self.begin()
        self.scale = scale
        self.shapes = [shape if s["id"] == sid else s for s in self.shapes]

    def cycle_unit(self):
        self.unit = UNITS[(UNITS.index(self.unit) + 1) % len(UNITS)]

    def shape_at(self, pos, radius):
        """Ưu tiên hình vẽ sau cùng (nằm trên) có nét cách pos không quá radius px; không trúng nét
        thì lấy hình kín nhỏ nhất chứa pos (hình lồng nhau: bấm giữa hình nhỏ cầm hình nhỏ)."""
        for s in reversed(self.shapes):
            if distance_to_shape(pos, s) <= radius:
                return s
        inside = [s for s in self.shapes if contains(pos, s)]
        return min(inside, key=lambda s: measure(s)["area"], default=None)
