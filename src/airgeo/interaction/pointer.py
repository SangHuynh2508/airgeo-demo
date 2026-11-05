"""Biến trạng thái chụm từng frame thành sự kiện con trỏ: hover / down / move / up.

Chụm = nhấn chuột, rê khi chụm = kéo, nhả = thả. Frame "giữ nét" (mất tay / tỉ lệ nhảy vọt, xem
gesture/pinch.py) không có điểm tin được nên không sinh sự kiện.
"""
from dataclasses import dataclass


@dataclass
class PointerEvent:
    kind: str                       # "hover" | "down" | "move" | "up"
    pos: tuple[float, float]        # điểm đã lọc
    t: float


class PointerTracker:
    def __init__(self):
        self.down = False
        self.last = None            # vị trí hợp lệ cuối cùng

    def update(self, res, t):
        events = []
        if res.pinched:
            if res.fpt is not None:  # "down" chờ tới frame đầu tiên có điểm
                events.append(PointerEvent("move" if self.down else "down", res.fpt, t))
                self.down, self.last = True, res.fpt
        else:
            if self.down:
                events.append(PointerEvent("up", self.last, t))
                self.down = False
            if res.fpt is not None:
                events.append(PointerEvent("hover", res.fpt, t))
                self.last = res.fpt
        return events
