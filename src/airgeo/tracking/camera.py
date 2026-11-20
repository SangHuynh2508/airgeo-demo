"""Mở webcam trên Windows.

MSMF: webcam laptop cho 1280x720 @ 30 FPS. DSHOW (cách của repo gốc AI-Virtual-Painter) chỉ được
~10 FPS ở 720p vì không nhận MJPG -> nét gãy khúc, quẹt nhanh bị mất tay. DSHOW chỉ để dự phòng.

FrameGrabber: đọc camera ở luồng riêng, vòng lặp chính luôn lấy frame MỚI NHẤT (xử lý chậm 1 frame thì bỏ frame
cũ trong bộ đệm thay vì xử lý trễ dần), timestamp lấy lúc chụp.
"""
import threading
import time

import cv2


def open_camera(index, width, height, fps=30):
    cap = cv2.VideoCapture(index, cv2.CAP_MSMF)
    if not cap.isOpened():
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    if not cap.isOpened():
        raise RuntimeError(f"Khong mo duoc camera {index}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)
    return cap


class FrameGrabber:
    def __init__(self, cap):
        self.cap = cap
        self._cond = threading.Condition()
        self._ok, self._frame, self._t = True, None, None
        self._seq = self._read = 0          # số frame đã chụp / đã đưa ra
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop:
            ok, frame = self.cap.read()
            with self._cond:
                self._ok, self._frame, self._t = ok, frame, time.perf_counter()
                self._seq += 1
                self._cond.notify_all()
            if not ok:
                break

    def read(self, timeout=2.0):
        """(ok, frame, t) của frame mới nhất chưa đưa ra; chờ tối đa timeout giây, quá thì ok = False."""
        with self._cond:
            if not self._cond.wait_for(lambda: self._seq != self._read, timeout):
                return False, None, None
            self._read = self._seq
            return self._ok, self._frame, self._t

    def release(self):
        self._stop = True
        self._thread.join(timeout=1.0)
        self.cap.release()
