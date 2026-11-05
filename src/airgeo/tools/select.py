"""Công cụ Chọn: chụm vào hình để chọn; chụm rồi kéo quá drag_threshold px thì hình đi theo tay.

Cả lần kéo là 1 bước Undo (begin() 1 lần lúc bắt đầu kéo). Rung tay nhỏ hơn ngưỡng chỉ là chọn.
"""
import math


class SelectTool:
    def __init__(self, config):
        self.hit_radius = config.hit_radius
        self.drag_threshold = config.drag_threshold
        self.selected = None        # id hình đang chọn
        self._grab = None           # điểm bắt đầu chụm trên hình (None = lần chụm này không kéo gì)
        self._last = None
        self._dragging = False

    def on_event(self, ev, ctl):
        board = ctl.board
        if ev.kind == "down":
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
