"""Công cụ Chọn: chụm vào hình để chọn; chụm rồi kéo quá drag_threshold px thì hình đi theo tay.
Chụm vào nhãn cạnh (AB, BC, dai, r...) của hình đang chọn thì mở bảng nhập số đo.
Cột nút "Tinh:" ở mép phải: bấm nút nào thì mới hiện số đo đó (cạnh, góc, chu vi...) của hình đang chọn;
đổi / bỏ chọn hình thì tắt hết.

Cả lần kéo là 1 bước Undo (begin() 1 lần lúc bắt đầu kéo). Rung tay nhỏ hơn ngưỡng chỉ là chọn.
"""
import math

from airgeo.geometry.construct import label_anchors

MEASURES = {"line": ["sides"], "triangle": ["sides", "angles", "perimeter", "area"],
            "rect": ["sides", "angles", "perimeter", "area"], "circle": ["radius", "perimeter", "area"]}
MENU_W, MENU_H, MENU_GAP = 150, 44, 8


class SelectTool:
    def __init__(self, config, width=1280):
        self.hit_radius = config.hit_radius
        self.label_radius = config.label_radius
        self.drag_threshold = config.drag_threshold
        self.menu_x = width - MENU_W - 10
        self.menu_y = config.toolbar_height + 40          # chừa chỗ chữ "Tinh:"
        self.selected = None        # id hình đang chọn
        self.show = set()           # số đo đang hiện của hình đang chọn
        self._grab = None           # điểm bắt đầu chụm trên hình (None = lần chụm này không kéo gì)
        self._last = None
        self._dragging = False
        self._clear_at = None       # điểm chạm vào chỗ trống: nhả tại đây thì bỏ chọn

    def menu(self, shape):
        """[(số đo, (x0, y0, x1, y1))] – các nút trong cột "Tinh:" cho loại hình này."""
        return [(k, (self.menu_x, self.menu_y + i * (MENU_H + MENU_GAP),
                     self.menu_x + MENU_W, self.menu_y + i * (MENU_H + MENU_GAP) + MENU_H))
                for i, k in enumerate(MEASURES.get(shape["kind"], []))]

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
                board.begin()
            board.translate(self.selected, ev.pos[0] - self._last[0], ev.pos[1] - self._last[1])
            self._last = ev.pos
        elif ev.kind == "up":
            if self._clear_at is not None:
                self.selected, self.show = None, set()
            self._grab, self._dragging, self._clear_at = None, False, None

    def end(self, ctl):
        self.selected, self._grab, self._dragging, self._clear_at = None, None, False, None
        self.show = set()
