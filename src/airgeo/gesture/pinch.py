"""Phát hiện chụm/nhả giữa ngón cái (4) và ngón trỏ (8).

Tỉ lệ = khoảng cách(4, 8) / kích thước bàn tay (landmark 0 -> 9), nên không phụ thuộc
tay ở xa hay gần camera (ý tưởng chuẩn hóa theo palmSize lấy từ AI-Virtual-Painter, MIT).

Tính cả 2 cách, chọn bằng `mode` (phím P trong app):
  - "2d": trên ảnh (pixel). Sai khi 2 ngón tách nhau theo chiều sâu (ngón cái nằm sau ngón trỏ).
  - "3d": trên tọa độ 3D (world landmarks, mét). Chiều sâu z chỉ là ước lượng từ 1 camera,
          sai nặng khi bàn tay nghiêng ngang / ngón trỏ chĩa vào camera.

Dùng 2 ngưỡng (hysteresis): đang nhả thì phải xuống dưới `on_ratio` mới bật chụm,
đang chụm thì phải vượt `off_ratio` mới nhả. Ngoài ra khi đang chụm mà mất tay hoặc tỉ lệ
vượt ngưỡng nhả, chưa nhả ngay mà "giữ" (holding) tối đa `grace` giây: MediaPipe hay đặt
sai điểm vài frame (tỉ lệ nhảy 0.2 <-> 0.6), nếu cắt ngay thì nét bị đứt.
"""
import math


class PinchDetector:
    def __init__(self, on_ratio=0.20, off_ratio=0.35, grace=0.2, mode="2d"):
        assert on_ratio < off_ratio, "ngưỡng bật chụm phải nhỏ hơn ngưỡng nhả"
        self.on_ratio = on_ratio
        self.off_ratio = off_ratio
        self.grace = grace
        self.mode = mode
        self.pinched = False
        self.holding = False  # đang chụm nhưng frame này không tin được -> không thêm điểm
        self.ratio = self.ratio2d = self.ratio3d = None  # hiển thị lên HUD để tự hiệu chỉnh
        self.since = None     # thời điểm bắt đầu chuỗi frame "không tin được"

    def shift(self, delta):
        """Dịch cả 2 ngưỡng (giữ nguyên khoảng hysteresis) – phím , và . trong app."""
        if self.on_ratio + delta > 0.05:
            self.on_ratio += delta
            self.off_ratio += delta

    def toggle_mode(self):
        self.mode = "3d" if self.mode == "2d" else "2d"

    def update(self, hand, t):
        if hand is None:
            self.ratio = self.ratio2d = self.ratio3d = None
        else:
            p = hand["pts"]
            self.ratio2d = math.dist(p[4], p[8]) / max(math.dist(p[0], p[9]), 1e-6)
            self.ratio3d = math.dist(hand["w4"], hand["w8"]) / max(math.dist(hand["w0"], hand["w9"]), 1e-6)
            self.ratio = self.ratio2d if self.mode == "2d" else self.ratio3d

        if not self.pinched:
            self.holding = False
            if self.ratio is not None and self.ratio < self.on_ratio:
                self.pinched = True
            return self.pinched

        if self.ratio is not None and self.ratio <= self.off_ratio:
            self.since, self.holding = None, False
            return True
        # Mất tay hoặc tỉ lệ vượt ngưỡng nhả: chờ thêm `grace` giây rồi mới nhả
        if self.since is None:
            self.since = t
        if t - self.since <= self.grace:
            self.holding = True
            return True
        self.pinched, self.holding, self.since = False, False, None
        return False


def draw_point(hand):
    """Điểm vẽ = trung điểm ngón cái (4) và ngón trỏ (8), không phải riêng đầu ngón trỏ.
    Khi khép/mở ngón, đầu ngón trỏ đi xuống/lên một quãng sau khi đã vượt ngưỡng chụm -> đoạn thừa
    ở đầu và cuối nét. Hai ngón đi về phía nhau nên trung điểm gần như đứng yên."""
    (x4, y4), (x8, y8) = hand["p4"], hand["p8"]
    return (x4 + x8) / 2, (y4 + y8) / 2
