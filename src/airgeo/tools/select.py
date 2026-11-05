"""Công cụ Chọn: chụm vào hình để chọn; chụm rồi kéo quá drag_threshold px thì hình đi theo tay.
Chụm vào nhãn cạnh (AB, BC, dai, r...) của hình đang chọn thì mở bảng nhập số đo.

Cả lần kéo là 1 bước Undo (begin() 1 lần lúc bắt đầu kéo). Rung tay nhỏ hơn ngưỡng chỉ là chọn.
"""
import math

from airgeo.geometry.construct import label_anchors


class SelectTool:
    def __init__(self, config):
        self.hit_radius = config.hit_radius
        self.label_radius = config.label_radius
        self.drag_threshold = config.drag_threshold
        self.selected = None        # id hình đang chọn
        self._grab = None           # điểm bắt đầu chụm trên hình (None = lần chụm này không kéo gì)
        self._last = None
        self._dragging = False

    def _label_at(self, board, pos):
        shape = board.get(self.selected) if self.selected else None
        if shape is None:
            return None, None
        for f, p in label_anchors(shape).items():
            if math.dist(pos, p) <= self.label_radius:
                return shape, f
        return shape, None

    def on_event(self, ev, ctl):
        board = ctl.board
        if ev.kind == "down":
            shape, field = self._label_at(board, ev.pos)
            if field:
                ctl.panel.open(shape, field, board)
                self._grab = None
                return
            shape = board.shape_at(ev.pos, self.hit_radius)
            self.selected = shape["id"] if shape else None
            self._grab = ev.pos if shape else None
            self._dragging = False
        elif ev.kind == "move" and self._grab is not None:
            if not self._dragging:
                if math.dist(ev.pos, self._grab) <= self.drag_threshold:
                    return
                self._dragging, self._last = True, self._grab
                board.begin()
            board.translate(self.selected, ev.pos[0] - self._last[0], ev.pos[1] - self._last[1])
            self._last = ev.pos
        elif ev.kind == "up":
            self._grab, self._dragging = None, False

    def end(self, ctl):
        self.selected, self._grab, self._dragging = None, None, False
