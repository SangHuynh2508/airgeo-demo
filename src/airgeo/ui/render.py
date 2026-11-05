"""Vẽ lên khung hình: nét, hình đã chuẩn hóa, số đo, vết so sánh, bàn tay, con trỏ, nút bấm.

Cách trộn lớp canvas lên khung hình webcam (addWeighted) lấy từ paint.py của
AI-Virtual-Painter (MIT, Sagnik Barman): https://github.com/hanessn1/AI-Virtual-Painter
"""
import cv2
import numpy as np

from airgeo.geometry.measure import measure
from airgeo.geometry.units import fmt_area, fmt_length
from airgeo.gesture.pinch import draw_point
from airgeo.tracking.hand_tracker import CONNECTIONS

FREE_COLOR = (255, 255, 255)
SHAPE_COLOR = (0, 220, 255)
RAW_COLOR = (160, 160, 160)
FILT_COLOR = (0, 255, 0)
PINCH_COLOR = (0, 0, 255)
HOLD_COLOR = (0, 165, 255)       # cam: đang giữ nét, frame bị bỏ qua
SKELETON_COLOR = (255, 0, 255)
ANGLE_COLOR = (180, 255, 180)
BUTTON_ON = (160, 90, 0)         # nền nút đang bật
BUTTON_EDGE = (200, 200, 200)
BUTTON_HOVER = (0, 255, 255)     # viền nút dưới con trỏ


def ip(p):
    return int(round(p[0])), int(round(p[1]))


def text(img, s, org, scale=0.5, color=(255, 255, 255)):
    # Viền đen để chữ đọc được trên mọi nền. OpenCV không vẽ được tiếng Việt có dấu.
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def draw_button(img, rect, label, on=False, hover=False, scale=0.6):
    """Nút chữ nhật dùng chung cho thanh nút, bàn phím số, nhãn cạnh."""
    x0, y0, x1, y1 = (int(round(v)) for v in rect)
    if on:
        cv2.rectangle(img, (x0, y0), (x1, y1), BUTTON_ON, -1)
    cv2.rectangle(img, (x0, y0), (x1, y1), BUTTON_HOVER if hover else BUTTON_EDGE, 3 if hover else 1)
    if label:
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        text(img, label, ((x0 + x1 - tw) // 2, (y0 + y1 + th) // 2), scale)


def draw_shape(img, s, color=None, thickness=3):
    kind = s["kind"]
    if color is None:
        color = FREE_COLOR if kind == "free" else SHAPE_COLOR
    if kind == "circle":
        cv2.circle(img, ip(s["center"]), int(round(s["radius"])), color, thickness, cv2.LINE_AA)
        return
    pts = np.array([ip(p) for p in s["pts"]], dtype=np.int32)
    cv2.polylines(img, [pts], kind in ("triangle", "rect"), color, thickness, cv2.LINE_AA)


def draw_measurements(img, s, scale=None, unit="cm"):
    """Số đo theo đơn vị nếu đã có tỉ lệ (scale = px/cm), chưa có thì hiện px."""
    m = measure(s)
    if not m:
        return

    def length(px):
        return fmt_length(px, scale, unit)

    if s["kind"] == "circle":
        c, r = s["center"], s["radius"]
        cv2.line(img, ip(c), ip((c[0] + r, c[1])), SHAPE_COLOR, 1, cv2.LINE_AA)
        cv2.circle(img, ip(c), 3, SHAPE_COLOR, -1)
        text(img, f"r={length(r)}", ip((c[0] + 8, c[1] - 6)))
        text(img, f"C={length(m['perimeter'])}  S={fmt_area(m['area'], scale, unit)}",
             ip((c[0] - r, c[1] + r + 20)))
        return
    pts = s["pts"]
    if s["kind"] == "line":
        mid = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
        text(img, length(m["sides"][0]), ip((mid[0] + 8, mid[1] - 8)))
        return
    n = len(pts)
    cx, cy = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        # Nhãn cạnh đẩy ra ngoài hình, nhãn góc đẩy vào trong (theo hướng trọng tâm)
        text(img, length(m["sides"][i]), ip((mid[0] + (mid[0] - cx) * 0.15 - 12, mid[1] + (mid[1] - cy) * 0.15)))
        v = pts[i]
        text(img, f"{m['angles'][i]:.0f}deg", ip((v[0] + (cx - v[0]) * 0.2 - 20, v[1] + (cy - v[1]) * 0.2)),
             0.45, ANGLE_COLOR)
    text(img, f"P={length(m['perimeter'])}  S={fmt_area(m['area'], scale, unit)}", ip((cx - 70, cy)))


def draw_canvas(frame, shapes, cur, scale=None, unit="cm"):
    """Vẽ các nét lên lớp canvas đen, trộn lên khung hình, rồi ghi số đo (chữ rõ, không bị làm mờ)."""
    canvas = np.zeros_like(frame)
    for s in shapes:
        draw_shape(canvas, s)
    if cur and len(cur) >= 2:
        cv2.polylines(canvas, [np.array([ip(p) for p in cur], dtype=np.int32)], False, FREE_COLOR, 3, cv2.LINE_AA)
    frame = cv2.addWeighted(frame, 0.6, canvas, 1, 0)
    for s in shapes:
        draw_measurements(frame, s, scale, unit)
    return frame


def draw_trails(img, raw_trail, filt_trail):
    """Chế độ so sánh (phím M): vết điểm thô (xám) và điểm đã lọc (xanh)."""
    if raw_trail:
        cv2.polylines(img, [np.array([ip(p) for p in raw_trail], np.int32)], False, RAW_COLOR, 1, cv2.LINE_AA)
        cv2.polylines(img, [np.array([ip(p) for p in filt_trail], np.int32)], False, FILT_COLOR, 2, cv2.LINE_AA)


def draw_hand(img, hand, res, show_skeleton):
    if hand and show_skeleton:
        for a, b in CONNECTIONS:
            cv2.line(img, ip(hand["pts"][a]), ip(hand["pts"][b]), SKELETON_COLOR, 1, cv2.LINE_AA)
    if hand:
        cv2.circle(img, ip(hand["p4"]), 5, RAW_COLOR, -1)
        cv2.circle(img, ip(hand["p8"]), 5, RAW_COLOR, -1)
    if res.fpt:
        cv2.circle(img, ip(res.fpt), 9, PINCH_COLOR if res.pinched else FILT_COLOR, 2)
    elif res.holding and hand:
        cv2.circle(img, ip(draw_point(hand)), 9, HOLD_COLOR, 2)
