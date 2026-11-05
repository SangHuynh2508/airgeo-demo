"""Phát hiện "bấm"/nhả bằng cử chỉ tay. Hai cử chỉ (phím K trong app):
  - "pinch": chụm ngón cái (4) và ngón trỏ (8). Tay nằm ngang thì ngón trỏ ở trên điểm chụm,
             nên khi với lên mép trên khung camera ngón trỏ ra khỏi hình trước.
  - "two_finger": áp ngón giữa (12) sát ngón trỏ (8), cả 2 ngón duỗi. Con trỏ là đầu ngón trỏ =
             điểm cao nhất của bàn tay, với tới thanh nút ở mép trên mà tay vẫn trong khung.
             Nắm tay (2 đầu ngón cũng sát nhau) không tính là bấm.

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


PAIRS = {"pinch": (4, 8), "two_finger": (8, 12)}


def _extended(p, tip, pip):
    """Ngón duỗi: đầu ngón xa cổ tay (0) hơn khớp giữa ngón – không phụ thuộc tay xoay hướng nào."""
    return math.dist(p[tip], p[0]) > math.dist(p[pip], p[0])


class PinchDetector:
    def __init__(self, on_ratio=0.20, off_ratio=0.35, grace=0.2, mode="2d", gesture="pinch",
                 two_finger=(0.25, 0.40)):
        assert on_ratio < off_ratio and two_finger[0] < two_finger[1], "ngưỡng bật phải nhỏ hơn ngưỡng nhả"
        self.limits = {"pinch": [on_ratio, off_ratio], "two_finger": list(two_finger)}  # mỗi cử chỉ 1 cặp ngưỡng
        self.grace = grace
        self.mode = mode
        self.gesture = gesture
        self.pinched = False
        self.holding = False  # đang chụm nhưng frame này không tin được -> không thêm điểm
        self.ratio = self.ratio2d = self.ratio3d = None  # hiển thị lên HUD để tự hiệu chỉnh
        self.since = None     # thời điểm bắt đầu chuỗi frame "không tin được"

    @property
    def on_ratio(self):
        return self.limits[self.gesture][0]

    @property
    def off_ratio(self):
        return self.limits[self.gesture][1]

    def shift(self, delta):
        """Dịch cả 2 ngưỡng của cử chỉ đang dùng (giữ nguyên khoảng hysteresis) – phím , và . trong app."""
        lim = self.limits[self.gesture]
        if lim[0] + delta > 0.05:
            lim[0] += delta
            lim[1] += delta

    def toggle_mode(self):
        self.mode = "3d" if self.mode == "2d" else "2d"

    def toggle_gesture(self):
        self.gesture = "two_finger" if self.gesture == "pinch" else "pinch"
        self.pinched = self.holding = False
        self.since = None

    def update(self, hand, t):
        if hand is None:
            self.ratio = self.ratio2d = self.ratio3d = None
        else:
            p = hand["pts"]
            a, b = PAIRS[self.gesture]
            self.ratio2d = math.dist(p[a], p[b]) / max(math.dist(p[0], p[9]), 1e-6)
            self.ratio3d = math.dist(hand[f"w{a}"], hand[f"w{b}"]) / max(math.dist(hand["w0"], hand["w9"]), 1e-6)
            self.ratio = self.ratio2d if self.mode == "2d" else self.ratio3d
        # Cử chỉ 2 ngón chỉ tính khi cả 2 ngón duỗi (nắm tay thì 2 đầu ngón cũng sát nhau);
        # ngón gập coi như frame không tin được -> đang bấm thì giữ `grace` giây rồi nhả
        ratio = self.ratio
        if hand is not None and self.gesture == "two_finger" and not (
                _extended(hand["pts"], 8, 6) and _extended(hand["pts"], 12, 10)):
            ratio = None

        if not self.pinched:
            self.holding = False
            if ratio is not None and ratio < self.on_ratio:
                self.pinched = True
            return self.pinched

        if ratio is not None and ratio <= self.off_ratio:
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


def draw_point(hand, gesture="pinch"):
    """Cử chỉ 2 ngón: điểm vẽ = đầu ngón trỏ (lúc chỉ giơ ngón trỏ, ngón giữa đang gập nên trung điểm
    8-12 sẽ nhảy khi giơ ngón giữa lên).

    Chụm: điểm vẽ = trung điểm ngón cái (4) và ngón trỏ (8), không phải riêng đầu ngón trỏ.
    Khi khép/mở ngón, đầu ngón trỏ đi xuống/lên một quãng sau khi đã vượt ngưỡng chụm -> đoạn thừa
    ở đầu và cuối nét. Hai ngón đi về phía nhau nên trung điểm gần như đứng yên."""
    if gesture == "two_finger":
        return hand["p8"]
    (x4, y4), (x8, y8) = hand["p4"], hand["p8"]
    return (x4 + x8) / 2, (y4 + y8) / 2
