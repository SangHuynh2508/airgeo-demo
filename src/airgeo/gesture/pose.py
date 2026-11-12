"""Tư thế tay để ra lệnh (không cần bấm nút): giữ yên một tư thế đủ lâu thì chạy lệnh.

Chỉ xét 4 ngón trỏ, giữa, áp út, út (ngón cái hay bị che / nhận sai). Ngón duỗi = đầu ngón xa cổ tay hơn khớp
giữa ngón (_extended), nên tay xoay hướng nào cũng nhận được.
  three (trỏ + giữa + áp út) -> Vẽ;  palm (xòe 4 ngón) -> Chọn, giữ tiếp -> menu tròn;
  rock (trỏ + út)           -> Xóa;  fist (nắm tay)    -> Undo (giữ lâu hơn: tay thả lỏng hay khép hờ;
  sau khi vẽ / bấm phải xòe tay ra rồi mới nắm lại – xem Controller.on_pose).
Trỏ 1 ngón / 2 ngón là tư thế làm việc (di con trỏ, áp 2 ngón bấm) nên không phải lệnh.
"""
from airgeo.gesture.pinch import _extended

POSES = {(1, 1, 1, 0): "three", (1, 1, 1, 1): "palm", (1, 0, 0, 1): "rock", (0, 0, 0, 0): "fist"}
POSE_ACTIONS = {"three": [(0.5, "draw")], "palm": [(0.5, "select"), (1.5, "menu")],
                "rock": [(0.5, "erase")], "fist": [(0.8, "undo")]}


def fingers(pts):
    """(trỏ, giữa, áp út, út) – ngón nào đang duỗi."""
    return tuple(int(_extended(pts, tip, tip - 2)) for tip in (8, 12, 16, 20))


def classify(pts):
    return POSES.get(fingers(pts))


class PoseTrigger:
    """Đếm thời gian giữ tư thế. Mỗi mốc (giây, lệnh) bắn đúng 1 lần cho mỗi lần giữ; đổi tư thế thì đếm lại.
    Mất tư thế <= grace giây (MediaPipe nhận sai vài frame) vẫn tính là đang giữ."""

    def __init__(self, stages=POSE_ACTIONS, grace=0.15):
        self.stages, self.grace = stages, grace
        self.reset()

    def reset(self):
        self.pose, self.start, self.seen, self.fired = None, 0.0, 0.0, 0

    def consume(self):
        """Bỏ các mốc còn lại của lần giữ này (đã dùng tư thế cho việc khác)."""
        self.fired = len(self.stages.get(self.pose, []))

    def update(self, pose, t):
        if pose is None:
            if self.pose is not None and t - self.seen > self.grace:
                self.reset()
            return None
        if pose != self.pose:
            self.pose, self.start, self.fired = pose, t, 0
        self.seen = t
        stages = self.stages.get(pose, [])
        if self.fired < len(stages) and t - self.start >= stages[self.fired][0] - 1e-6:
            self.fired += 1
            return stages[self.fired - 1][1]
        return None

    @property
    def progress(self):
        """(lệnh sắp chạy, tỉ lệ 0..1 thời gian đã giữ) để vẽ vòng tiến độ; None nếu không giữ gì."""
        stages = self.stages.get(self.pose, [])
        if self.fired >= len(stages):
            return None
        hold, action = stages[self.fired]
        return action, min(1.0, (self.seen - self.start) / hold)
