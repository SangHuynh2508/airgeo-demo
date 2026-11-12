"""Vẽ lên khung hình: nét, hình đã chuẩn hóa, số đo, vết so sánh, bàn tay, con trỏ, nút bấm.

Cách trộn lớp canvas lên khung hình webcam (addWeighted) lấy từ paint.py của
AI-Virtual-Painter (MIT, Sagnik Barman): https://github.com/hanessn1/AI-Virtual-Painter
"""
import math

import cv2
import numpy as np

from airgeo.geometry.construct import label_anchors
from airgeo.geometry.formulas import formula, triangle_height
from airgeo.geometry.measure import measure
from airgeo.geometry.units import fmt_area, fmt_length
from airgeo.gesture.pinch import draw_point
from airgeo.tools.select import MENU_W
from airgeo.tracking.hand_tracker import CONNECTIONS
from airgeo.ui.text import put_text, text_size

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


def draw_measurements(img, s, scale=None, unit="cm", show=()):
    """Chỉ vẽ các số đo có trong `show` ("sides", "angles", "perimeter", "area", "radius").
    Theo đơn vị nếu đã có tỉ lệ (scale = px/cm), chưa có thì hiện px."""
    m = measure(s)
    if not m or not show:
        return

    def length(px):
        return fmt_length(px, scale, unit)

    totals = []                         # chu vi, diện tích: mỗi thứ 1 dòng để không đè lên nhau
    if "perimeter" in show:
        totals.append(f"{'C' if s['kind'] == 'circle' else 'P'}={length(m['perimeter'])}")
    if "area" in show:
        totals.append(f"S={fmt_area(m['area'], scale, unit)}")
    if s["kind"] == "circle":
        c, r = s["center"], s["radius"]
        if "radius" in show:
            cv2.line(img, ip(c), ip((c[0] + r, c[1])), SHAPE_COLOR, 1, cv2.LINE_AA)
            cv2.circle(img, ip(c), 3, SHAPE_COLOR, -1)
            text(img, f"r={length(r)}", ip((c[0] + 8, c[1] - 6)))
        for i, line in enumerate(totals):
            text(img, line, ip((c[0] - r, c[1] + r + 20 + 22 * i)))
        return
    pts = s["pts"]
    if s["kind"] == "line":
        if "sides" in show:
            mid = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
            text(img, length(m["sides"][0]), ip((mid[0] + 8, mid[1] - 8)))
        return
    n = len(pts)
    cx, cy = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        # Nhãn cạnh đẩy ra ngoài hình, nhãn góc đẩy vào trong (theo hướng trọng tâm)
        if "sides" in show:
            text(img, length(m["sides"][i]),
                 ip((mid[0] + (mid[0] - cx) * 0.15 - 12, mid[1] + (mid[1] - cy) * 0.15)))
        if "angles" in show:
            v = pts[i]
            text(img, f"{m['angles'][i]:.0f}deg", ip((v[0] + (cx - v[0]) * 0.2 - 20, v[1] + (cy - v[1]) * 0.2)),
                 0.45, ANGLE_COLOR)
    for i, line in enumerate(totals):
        text(img, line, ip((cx - 60, cy + 22 * i - 11 * (len(totals) - 1))))


DIM = 0.45     # hình không được chọn: còn thấy để tránh vẽ đè, nhưng lùi lại sau hình đang thao tác


def draw_canvas(frame, shapes, cur, active=None):
    """Vẽ các nét lên lớp canvas đen rồi trộn lên khung hình. Số đo chỉ vẽ khi được yêu cầu
    (cột "Tinh:" của công cụ Chọn, xem draw_tool_overlay). Có active (id hình đang chọn) thì hình khác vẽ mờ."""
    canvas = np.zeros_like(frame)
    for s in shapes:
        if active is None or s["id"] == active:
            draw_shape(canvas, s)
        else:
            draw_shape(canvas, s, tuple(round(c * DIM) for c in (FREE_COLOR if s["kind"] == "free" else SHAPE_COLOR)), 2)
    if cur and len(cur) >= 2:
        cv2.polylines(canvas, [np.array([ip(p) for p in cur], dtype=np.int32)], False, FREE_COLOR, 3, cv2.LINE_AA)
    return cv2.addWeighted(frame, 0.6, canvas, 1, 0)


def draw_trails(img, raw_trail, filt_trail):
    """Chế độ so sánh (phím M): vết điểm thô (xám) và điểm đã lọc (xanh)."""
    if raw_trail:
        cv2.polylines(img, [np.array([ip(p) for p in raw_trail], np.int32)], False, RAW_COLOR, 1, cv2.LINE_AA)
        cv2.polylines(img, [np.array([ip(p) for p in filt_trail], np.int32)], False, FILT_COLOR, 2, cv2.LINE_AA)


def draw_hand(img, hand, res, show_skeleton, gesture="pinch"):
    if hand and show_skeleton:
        for a, b in CONNECTIONS:
            cv2.line(img, ip(hand["pts"][a]), ip(hand["pts"][b]), SKELETON_COLOR, 1, cv2.LINE_AA)
    if hand:
        cv2.circle(img, ip(hand["p4"]), 5, RAW_COLOR, -1)
        cv2.circle(img, ip(hand["p8"]), 5, RAW_COLOR, -1)
    if res.fpt:
        cv2.circle(img, ip(res.fpt), 9, PINCH_COLOR if res.pinched else FILT_COLOR, 2)
    elif res.holding and hand:
        cv2.circle(img, ip(draw_point(hand, gesture)), 9, HOLD_COLOR, 2)


SELECT_COLOR = (255, 200, 0)     # xanh dương nhạt: hình đang chọn
ERASE_COLOR = (0, 0, 255)        # đỏ: hình sắp bị xóa
MEASURE_LABELS = {"sides": "Canh", "angles": "Goc", "perimeter": "Chu vi", "area": "Dien tich", "radius": "Ban kinh"}


def draw_selection(img, s, color=SELECT_COLOR):
    """Viền nổi bật hình đang chọn (đỏ khi đang kéo đè lên hình khác); tam giác ghi tên đỉnh A, B, C;
    nhãn cạnh bấm được để sửa số đo."""
    draw_shape(img, s, color, 6)
    if s["kind"] == "triangle":
        pts = s["pts"]
        cx, cy = sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3
        for name, (x, y) in zip("ABC", pts):
            text(img, name, ip((x + (x - cx) * 0.15 - 6, y + (y - cy) * 0.15 + 6)), 0.7, color)
    for f, (x, y) in label_anchors(s).items():
        draw_button(img, (x - 28, y - 16, x + 28, y + 16), f, scale=0.55)


def draw_tool_overlay(img, ctl):
    """Hình đang chọn (công cụ Chọn) hoặc hình dưới con trỏ sắp bị xóa (công cụ Xóa)."""
    tool = ctl.tools[ctl.tool]
    sid = getattr(tool, "selected", None) or getattr(tool, "hovered", None)
    shape = ctl.board.get(sid) if sid else None
    if shape is None:
        return
    if ctl.tool == "select":
        draw_selection(img, shape, ERASE_COLOR if tool.blocked else SELECT_COLOR)
        # chu vi / diện tích nằm trong bảng công thức, không ghi lại trên hình
        draw_measurements(img, shape, ctl.board.scale, ctl.board.unit, tool.show - {"perimeter", "area"})
        menu = tool.menu(shape)
        if menu:
            x0, y0 = menu[0][1][:2]
            text(img, "Tinh:", (int(x0), int(y0) - 10), 0.6)
        for k, rect in menu:
            label = "Do dai" if shape["kind"] == "line" else MEASURE_LABELS[k]
            draw_button(img, rect, label, on=k in tool.show)
        if shape["kind"] == "triangle" and "area" in tool.show:
            draw_height(img, shape["pts"])
        draw_formulas(img, shape, tool, ctl.board.scale, ctl.board.unit)
    else:
        draw_shape(img, shape, ERASE_COLOR, 6)


# Bảng công thức: tiêu đề vàng nhỏ, công thức trắng, thế số xám (phụ), kết quả đậm và lớn hơn (dòng cần đọc)
FORMULA_STYLE = [(-2, (0, 220, 255), False), (0, (255, 255, 255), False), (0, (200, 200, 200), False),
                 (2, (255, 255, 255), True)]     # (chênh cỡ chữ, màu BGR, đậm) cho từng dòng của 1 khối
PANEL_PAD, BLOCK_GAP = 10, 14


def dashed_line(img, p, q, color, dash=8):
    n = max(1, int(math.dist(p, q) // dash))
    for i in range(0, n, 2):
        a = (p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n)
        b = (p[0] + (q[0] - p[0]) * (i + 1) / n, p[1] + (q[1] - p[1]) * (i + 1) / n)
        cv2.line(img, ip(a), ip(b), color, 2, cv2.LINE_AA)


def draw_height(img, pts):
    """Đường cao nét đứt từ C xuống AB; chân ngoài đoạn AB (tam giác tù) thì kéo dài AB bằng nét đứt."""
    c, foot, h = triangle_height(pts)
    if h < 1:
        return
    a, b = pts[0], pts[1]
    if math.dist(a, foot) + math.dist(foot, b) > math.dist(a, b) + 1:
        dashed_line(img, min((a, b), key=lambda p: math.dist(p, foot)), foot, SELECT_COLOR)
    dashed_line(img, c, foot, SELECT_COLOR)
    cv2.circle(img, ip(foot), 4, SELECT_COLOR, -1)
    text(img, "h", ip(((c[0] + foot[0]) / 2 + 8, (c[1] + foot[1]) / 2)), 0.6, SELECT_COLOR)


def _block_size(block, size):
    dims = [text_size([s], size + ds, bold) for s, (ds, _, bold) in zip(block, FORMULA_STYLE)]
    return max(w for w, _ in dims), sum(h for _, h in dims)


def draw_formulas(img, shape, tool, scale, unit):
    """Bảng công thức dưới cột "Tinh:", căn phải theo cột. Khung hình thấp không đủ chỗ thì đặt sang trái cột,
    ngang đầu cột; chữ thu nhỏ tới 14 px. Trả về khung bảng (x0, y0, x1, y1), None nếu không có gì để vẽ."""
    blocks = [b for b in (formula(shape, k, scale, unit) for k in ("perimeter", "area") if k in tool.show) if b]
    menu = tool.menu(shape)
    if not blocks or not menu:
        return
    def panel(size):
        dims = [_block_size(b, size) for b in blocks]
        return (max(MENU_W, max(w for w, _ in dims) + 2 * PANEL_PAD),
                sum(h for _, h in dims) + BLOCK_GAP * (len(blocks) - 1) + 2 * PANEL_PAD)

    def fit(top):                    # cỡ chữ lớn nhất (20 -> 14) vừa chiều cao còn lại từ top, None nếu không vừa
        return next((sz for sz in range(20, 13, -2) if panel(sz)[1] <= img.shape[0] - 45 - top), None)

    top, right = int(menu[-1][1][3]) + 16, tool.menu_x + MENU_W
    size = fit(top)
    if size is None:                 # sang trái cột nút, ngang đầu cột
        top, right = int(menu[0][1][1]), tool.menu_x - 10
        size = fit(top) or 14
    w, h = panel(size)
    x0, y1 = max(right - w, 0), min(top + h, img.shape[0])
    roi = img[top:y1, x0:right]
    roi[:] = (roi * 0.25).astype(np.uint8)      # nền tối: chữ trắng vẫn đọc được trên tường sáng
    cv2.rectangle(img, (x0, top), (right, y1), BUTTON_EDGE, 1)
    y = top + PANEL_PAD
    for b in blocks:
        for s, (ds, color, bold) in zip(b, FORMULA_STYLE):
            y += put_text(img, [s], (x0 + PANEL_PAD, y), size + ds, color, bold)[1]
        y += BLOCK_GAP
    return x0, top, right, top + h
