"""Bọc MediaPipe Hands: trả về landmark 4 (ngón cái) và 8 (ngón trỏ) theo pixel + timestamp.

Phần gọi mp.solutions.hands.Hands(...) và đổi tọa độ chuẩn hóa -> pixel dựa trên
handTracker.py của AI-Virtual-Painter (MIT, Sagnik Barman):
https://github.com/hanessn1/AI-Virtual-Painter

Dùng API cũ `mp.solutions.hands` (mediapipe==0.10.21). Nếu sau này chuyển sang
MediaPipe Tasks `HandLandmarker`, chỉ cần sửa file này, giữ nguyên dict trả về.
"""
import cv2
import mediapipe as mp

# Các cặp landmark nối thành khung xương bàn tay (để app vẽ, không phải import mediapipe)
CONNECTIONS = list(mp.solutions.hands.HAND_CONNECTIONS)


class HandTracker:
    def __init__(self, model_complexity=1, min_detection_confidence=0.6, min_tracking_confidence=0.5):
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def process(self, frame_bgr, t):
        """frame_bgr: ảnh BGR (đã lật gương). t: time.perf_counter() lúc đọc frame.

        Trả về None nếu không thấy tay, ngược lại dict:
          t, p4, p8 (pixel, float), pts (cả 21 điểm, pixel – để vẽ khung xương / đo 2D)
          và w0, w4, w8, w9 (tọa độ 3D ước lượng, mét, gốc ở tâm bàn tay).
        """
        h, w = frame_bgr.shape[:2]
        # Repo gốc tạo ảnh RGB nhưng lại đưa ảnh BGR vào process(); ở đây sửa lại cho đúng.
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        res = self.hands.process(rgb)
        if not res.multi_hand_landmarks:
            return None
        lm = res.multi_hand_landmarks[0].landmark
        wl = res.multi_hand_world_landmarks[0].landmark

        def px(i):
            # Giữ số thực (không làm tròn) để bộ lọc và dữ liệu CSV không mất độ chính xác
            return (lm[i].x * w, lm[i].y * h)

        def world(i):
            return (wl[i].x, wl[i].y, wl[i].z)

        pts = [px(i) for i in range(21)]
        return {"t": t, "p4": pts[4], "p8": pts[8], "pts": pts,
                "w0": world(0), "w4": world(4), "w8": world(8), "w9": world(9)}

    def close(self):
        self.hands.close()
