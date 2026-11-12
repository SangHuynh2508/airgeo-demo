"""Công cụ Chọn: chụm vào hình để chọn; chụm rồi kéo quá drag_threshold px thì hình đi theo tay.
Chụm vào nhãn cạnh (AB, BC, dai, r...) của hình đang chọn thì mở bảng nhập số đo.
Cột nút "Tinh:" ở mép phải: bấm nút nào thì mới hiện số đo đó (cạnh, góc, chu vi...) của hình đang chọn;
đổi / bỏ chọn hình thì tắt hết.

Tay cầm xoay (chấm ở góc trên phải khung bao hình đang chọn, trừ hình tròn): áp 2 ngón vào rồi kéo vòng quanh
hình thì hình xoay quanh tâm; cạnh gần trục lệch <= SNAP_DEG thì hít thẳng ngang / dọc.

Cả lần kéo / xoay là 1 bước Undo (begin() 1 lần lúc bắt đầu). Rung tay nhỏ hơn ngưỡng chỉ là chọn.
"""
import math

from airgeo.geometry.construct import label_anchors
from airgeo.geometry.rotate import center, rotate_points, snap_delta

MEASURES = {"line": ["sides"], "triangle": ["sides", "angles", "perimeter", "area"],
            "rect": ["sides", "angles", "perimeter", "area"], "circle": ["radius", "perimeter", "area"]}
MENU_W, MENU_H, MENU_GAP = 150, 44, 8
HANDLE_OFFSET, SNAP_DEG = 32, 8


class SelectTool:
    def __init__(self, config, width=1280):
        self.hit_radius = config.hit_radius
        self.label_radius = config.label_radius
        self.drag_threshold = config.drag_threshold
        self.menu_x = width - MENU_W - 10
        self.menu_y = config.toolbar_height + 40          # chừa chỗ chữ "Tinh:"
        self.top = config.toolbar_height
        self.rotation = None        # đang xoay: {"pivot", "a0", "pts0", "kind", "applied", "pos"}
        self.selected = None        # id hình đang chọn
        self.show = set()           # số đo đang hiện của hình đang chọn
        self._grab = None           # điểm bắt đầu chụm trên hình (None = lần chụm này không kéo gì)
        self._last = None
        self._dragging = False
        self._snap = None           # bản sao Undo của lần kéo hiện tại
        self._clear_at = None       # điểm chạm vào chỗ trống: nhả tại đây thì bỏ chọn
        self.blocked = False        # hình đang kéo đè lên hình khác (tô đỏ; nhả lúc này thì bật về)

    def menu(self, shape):
        """[(số đo, (x0, y0, x1, y1))] – các nút trong cột "Tinh:" cho loại hình này."""
        return [(k, (self.menu_x, self.menu_y + i * (MENU_H + MENU_GAP),
                     self.menu_x + MENU_W, self.menu_y + i * (MENU_H + MENU_GAP) + MENU_H))
                for i, k in enumerate(MEASURES.get(shape["kind"], []))]

    def handle(self, shape):
        """Vị trí tay cầm xoay: góc khung bao gần nhất còn nằm trong vùng vẽ (ưu tiên trên phải, xa nhãn cạnh và
        cột Tính); hình tròn không xoay."""
        if shape is None or shape["kind"] == "circle":
            return None
        xs, ys = [p[0] for p in shape["pts"]], [p[1] for p in shape["pts"]]
        d = HANDLE_OFFSET
        corners = [(max(xs) + d, min(ys) - d), (min(xs) - d, min(ys) - d), (max(xs) + d, max(ys) + d),
                   (min(xs) - d, max(ys) + d)]
        ok = [c for c in corners if c[1] >= self.top + 20 and 20 <= c[0] <= self.menu_x - 20]
        return (ok or corners[2:])[0]

    def _label_at(self, board, pos):
        shape = board.get(self.selected) if self.selected else None
        if shape is None:
            return None, None
        for f, p in label_anchors(shape).items():
            if math.dist(pos, p) <= self.label_radius:
                return shape, f
        return shape, None

    def _menu_at(self, board, pos):
        shape = board.get(self.selected) if self.selected else None
        for k, (x0, y0, x1, y1) in self.menu(shape) if shape else []:
            if x0 <= pos[0] <= x1 and y0 <= pos[1] <= y1:
                return k
        return None

    def on_event(self, ev, ctl):
        board = ctl.board
        if ev.kind == "down":
            measure = self._menu_at(board, ev.pos)
            if measure:
                self.show ^= {measure}
                self._grab = None
                return
            h = self.handle(board.get(self.selected)) if self.selected else None
            if h and math.dist(ev.pos, h) <= self.label_radius:
                shape = board.get(self.selected)
                p = center(shape)
                self.rotation = {"pivot": p, "a0": math.atan2(ev.pos[1] - p[1], ev.pos[0] - p[0]), "pos": ev.pos,
                                 "pts0": list(shape["pts"]), "kind": shape["kind"], "applied": 0.0}
                self._grab, self._dragging = ev.pos, False
                return
            shape, field = self._label_at(board, ev.pos)
            if field:
                ctl.panel.open(shape, field, board)
                self._grab = None
                return
            shape = board.shape_at(ev.pos, self.hit_radius)
            self._dragging = False
            if shape is None:
                # Chỗ trống: chỉ bỏ chọn khi chạm rồi nhả tại chỗ. Lúc di tay tới cột "Tinh:", 2 ngón hay
                # vô tình áp sát -> "bấm" giữa đường; tay đang di chuyển thì không tính là bỏ chọn.
                self._grab, self._clear_at = None, ev.pos
                return
            if shape["id"] != self.selected:
                self.show = set()   # số đo chỉ tính khi được yêu cầu, cho từng lần chọn
            self.selected = shape["id"]
            self._grab = ev.pos
        elif ev.kind == "move" and self._clear_at is not None:
            if math.dist(ev.pos, self._clear_at) > self.drag_threshold:
                self._clear_at = None
        elif ev.kind == "move" and self._grab is not None:
            if not self._dragging:
                if math.dist(ev.pos, self._grab) <= self.drag_threshold:
                    return
                self._dragging, self._last = True, self._grab
                self._snap = board.begin()
            if self.rotation:
                self._rotate(board, ev.pos)
            else:
                board.translate(self.selected, ev.pos[0] - self._last[0], ev.pos[1] - self._last[1])
            self._last = ev.pos
            shape = board.get(self.selected)       # None nếu U gỡ mất hình giữa lúc kéo
            self.blocked = shape is not None and board.collides(shape, self.selected) is not None
        elif ev.kind == "up":
            if self._clear_at is not None:
                self.selected, self.show = None, set()
            if self.blocked:
                board.undo(self._snap)   # gỡ đúng lần kéo này: hình về chỗ cũ, không để lại bước Undo
                ctl.notify("Không thả được: đè lên hình khác", ev.t)
            self._grab, self._dragging, self._clear_at, self.blocked = None, False, None, False
            self.rotation = None

    def _rotate(self, board, pos):
        r = self.rotation
        p = r["pivot"]
        delta = math.degrees(math.atan2(pos[1] - p[1], pos[0] - p[0]) - r["a0"])
        delta = (delta + 180) % 360 - 180
        target = delta + snap_delta({"kind": r["kind"], "pts": rotate_points(r["pts0"], delta, p)}, SNAP_DEG)
        board.rotate(self.selected, target - r["applied"], p)
        r["applied"], r["pos"] = target, pos

    def end(self, ctl):
        if self.blocked:
            ctl.board.undo(self._snap)   # đổi công cụ giữa lúc kéo đè: cũng bật về
        self.selected, self._grab, self._dragging, self._clear_at, self.blocked = None, None, False, None, False
        self.show, self.rotation = set(), None
