"""Mở webcam trên Windows.

MSMF: webcam laptop cho 1280x720 @ 30 FPS. DSHOW (cách của repo gốc AI-Virtual-Painter) chỉ được
~10 FPS ở 720p vì không nhận MJPG -> nét gãy khúc, quẹt nhanh bị mất tay. DSHOW chỉ để dự phòng.
"""
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
