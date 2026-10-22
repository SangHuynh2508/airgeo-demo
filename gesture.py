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


if __name__ == "__main__":
    def hand(r):
        # Lòng bàn tay dài 100 px / 0.1 m; ngón trỏ cách ngón cái r lần lòng bàn tay
        return {"pts": [(0, 0)] * 4 + [(0, 0)] + [(0, 0)] * 3 + [(r * 100, 0), (0, 100)] + [(0, 0)] * 11,
                "w0": (0, 0, 0), "w9": (0, 0.1, 0), "w4": (0, 0, 0), "w8": (0, 0, r * 0.1)}

    d = PinchDetector(0.30, 0.45, grace=0.2)
    # 0.38 nằm giữa 2 ngưỡng: lúc chưa chụm thì không bật, lúc đang chụm thì không nhả
    assert [d.update(hand(r), i * 0.033) for i, r in enumerate((0.6, 0.38, 0.2, 0.38, 0.44))] == \
        [False, False, True, True, True]
    # Tỉ lệ nhảy lên 0.6 trong 0.1 s rồi về lại: vẫn chụm, các frame đó "holding"
    assert d.update(hand(0.6), 1.0) is True and d.holding
    assert d.update(None, 1.1) is True and d.holding
    assert d.update(hand(0.2), 1.15) is True and not d.holding
    # Mở tay thật (> 0.2 s) thì nhả
    d.update(hand(0.6), 2.0)
    assert d.update(hand(0.6), 2.25) is False
    d.shift(-0.05)
    assert abs(d.on_ratio - 0.25) < 1e-9 and abs(d.off_ratio - 0.40) < 1e-9
    # Chế độ 3d dùng khoảng cách theo chiều sâu
    d3 = PinchDetector(mode="3d")
    d3.update(hand(0.5), 0)
    assert abs(d3.ratio3d - 0.5) < 1e-9 and d3.ratio == d3.ratio3d
    print("gesture OK")
