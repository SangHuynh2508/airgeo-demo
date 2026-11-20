"""Vẽ lên khung hình: nét, hình đã chuẩn hóa, số đo, vết so sánh, bàn tay, con trỏ, nút bấm.

Cách trộn lớp canvas lên khung hình webcam (addWeighted) lấy từ paint.py của
AI-Virtual-Painter (MIT, Sagnik Barman): https://github.com/hanessn1/AI-Virtual-Painter
"""
import math

import cv2
import numpy as np

from airgeo.geometry.construct import FIELD_LABELS, current_lengths, label_anchors, label_edges
from airgeo.geometry.formulas import formula, triangle_height
from airgeo.geometry.measure import measure
from airgeo.geometry.rotate import edge_angle
from airgeo.geometry.shapes import is_right, shape_name
from airgeo.geometry.units import fmt_length, round_sum
from airgeo.gesture.pinch import draw_point
from airgeo.interaction.controller import FIT_MARGIN
from airgeo.tools.select import HANDLE_R, MENU_W
from airgeo.tracking.hand_tracker import CONNECTIONS
from airgeo.ui.text import put_text, text_size

FREE_COLOR = (255, 255, 255)
SHAPE_COLOR = (0, 220, 255)
RAW_COLOR = (160, 160, 160)
FILT_COLOR = (0, 255, 0)
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


def fit_size(labels, width, size):
    """Cỡ chữ lớn nhất (<= size, >= 12) để mọi nhãn vừa nút rộng width."""
    while size > 12 and max(text_size([s], size)[0] for s in labels) > width - 8:
        size -= 1
    return size


def draw_button(img, rect, label, on=False, hover=False, scale=0.6, primary=False):
    """Nút chữ nhật dùng chung (dải trạng thái, cột Tính, bàn phím số, nhãn cạnh). Nền tối riêng để chữ đọc được
    trên mọi nền camera (tường trắng), nền xanh khi đang bật, viền vàng dày khi con trỏ ở trên.
    primary: nút chính (OK) – viền trắng dày, không tô nền xanh (nền xanh là ô / nút đang chọn).
    Chữ Pillow (có dấu), cỡ theo scale, tự thu nhỏ cho vừa nút; label là list thì mỗi phần tử 1 dòng."""
    x0, y0, x1, y1 = (int(round(v)) for v in rect)
    roi = img[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)]
    roi[:] = BUTTON_ON if on else (roi * 0.3).astype(np.uint8)
    edge = BUTTON_HOVER if hover else (255, 255, 255) if primary else BUTTON_EDGE
    cv2.rectangle(img, (x0, y0), (x1, y1), edge, 5 if primary else 3 if hover else 1)
    if label:
        lines = label if isinstance(label, list) else [label]
        size = fit_size(lines, x1 - x0, round(scale * 36))
        w, h = text_size(lines, size)
        put_text(img, lines, ((x0 + x1 - w) // 2, (y0 + y1 - h) // 2 + 2), size)


def draw_shape(img, s, color=None, thickness=4):
    kind = s["kind"]
    if color is None:
        color = FREE_COLOR if kind == "free" else SHAPE_COLOR
    if kind == "circle":
        cv2.circle(img, ip(s["center"]), int(round(s["radius"])), color, thickness, cv2.LINE_AA)
        return
    pts = np.array([ip(p) for p in s["pts"]], dtype=np.int32)
    cv2.polylines(img, [pts], kind in ("triangle", "rect"), color, thickness, cv2.LINE_AA)


HALO = 6       # quầng đen dày hơn nét chừng này px (mỗi bên 3): nét sáng không bạc màu trên tường trắng


def draw_shape_halo(img, s, color, thickness):
    """Nét vẽ thẳng lên khung hình (viền hình đang chọn / sắp xóa) có quầng tối bên dưới."""
    draw_shape(img, s, (0, 0, 0), thickness + HALO)
    draw_shape(img, s, color, thickness)


CHIP_W, CHIP_H = 56, 42               # nút nhãn cạnh (AB, dài, r...) quanh label_anchors; rộng thêm theo chữ


VALUE_SIZE = 28                       # cỡ chữ số đo trên hình (cạnh, góc, bán kính): đọc được từ cuối lớp


def side_chips(s, scale, unit):
    """Nhãn cạnh bấm được: {ô: (dòng chữ, tâm, (nửa rộng, nửa cao))} – render vẽ, công cụ Chọn bấm theo cùng khung.
    Chưa nhập số đo: tên cạnh (AB, dài, r); nhập rồi: "AB = 3 cm" để học sinh nối số với công thức (không bao giờ px).
    Cạnh dốc (nhãn nằm bên cạnh) xuống 2 dòng "AB =" / "3 cm": viên hẹp, hình sát lề trái / cột Tính vẫn đủ chỗ."""
    edges, texts, half = label_edges(s), {}, {}
    for f, v in current_lengths(s).items():
        name = FIELD_LABELS.get(f, f)
        if scale is None:
            lines = [name]
        else:
            a, b = edges.get(f, ((0, 0), (1, 0)))         # hình tròn: bán kính vẽ ngang
            steep = abs(b[1] - a[1]) > abs(b[0] - a[0])
            lines = [f"{name} =", fmt_length(v, scale, unit)] if steep else [f"{name} = {fmt_length(v, scale, unit)}"]
        w, h = text_size(lines, VALUE_SIZE)
        texts[f], half[f] = lines, (max(CHIP_W, w + 20) / 2, max(CHIP_H, h + 4) / 2)
    anchors = label_anchors(s, half=half)
    return {f: (texts[f], anchors[f], half[f]) for f in texts}
ANGLE_R, RIGHT_MARK = 26, 16          # bán kính cung góc / cạnh ô vuông góc vuông (px)
LEADER = 34                           # khoảng từ đỉnh tới mép viên số đo góc (đường chỉ)


def _value(img, s, center):
    """Số đo s (chữ Pillow có dấu) trên nền tối, tâm ở center."""
    w, h = text_size([s], VALUE_SIZE)
    _label_chip(img, [s], (int(center[0] - w / 2), int(center[1] - h / 2)), VALUE_SIZE)


def angle_chip_center(v, b, hw, hh, W, H, top=0):
    """Tâm viên số đo góc (nửa khung hw x hh) ở đỉnh v, b = phân giác trong (đơn vị): trên phân giác ngoài, đủ xa để
    cả viên nằm ngoài đỉnh, giữ trong vùng vẽ (top = mép trên: không chui dưới dải nút). Đỉnh sát mép (bị kẹp ngược
    về đè đỉnh) thì đặt ngay trên / dưới đỉnh phía ngoài hình, không được thì ngang đỉnh phía ngoài, cuối cùng mới
    phía trong."""
    bx, by = b
    reach = min(hw / max(abs(bx), 1e-3), hh / max(abs(by), 1e-3)) + LEADER
    x = min(max(v[0] - bx * reach, hw + 4), W - hw - 4)
    y = min(max(v[1] - by * reach, top + hh + 4), H - hh - 4)
    if abs(x - v[0]) < hw + 6 and abs(y - v[1]) < hh + 6:
        out = 1 if -by > 0.1 else -1                            # phía ngoài hình theo chiều dọc
        side = (v[0] + (hw + 16) * (1 if bx <= 0 else -1), min(max(v[1], top + hh + 4), H - hh - 4))
        for x, y in ((x, v[1] + out * (hh + LEADER)), side, (x, v[1] - out * (hh + LEADER))):
            if hw + 4 <= x <= W - hw - 4 and top + hh + 4 <= y <= H - hh - 4:
                break
    return x, y


def draw_angle(img, v, p, n, angle, name=None, top=0):
    """Ký hiệu góc tại đỉnh v (2 cạnh tới p, n) như SGK: góc vuông = ô vuông nhỏ, góc khác = cung tròn nhỏ.
    Có name: viên "góc A = 60°" đặt ngoài hình theo phân giác ngoài, đường chỉ mảnh từ viên tới ký hiệu
    (học sinh đọc được số mà số không đè lên hình); trả về khung viên (x0, y0, x1, y1), không có viên thì None."""
    d1, d2 = math.dist(v, p) or 1.0, math.dist(v, n) or 1.0
    u1 = ((p[0] - v[0]) / d1, (p[1] - v[1]) / d1)
    u2 = ((n[0] - v[0]) / d2, (n[1] - v[1]) / d2)
    bx, by = u1[0] + u2[0], u1[1] + u2[1]
    b = math.hypot(bx, by) or 1.0
    bx, by = bx / b, by / b                       # phân giác trong (đơn vị)
    if is_right(angle):
        s = RIGHT_MARK
        corner = [(v[0] + s * u1[0], v[1] + s * u1[1]), (v[0] + s * (u1[0] + u2[0]), v[1] + s * (u1[1] + u2[1])),
                  (v[0] + s * u2[0], v[1] + s * u2[1])]
        cv2.polylines(img, [np.array([ip(q) for q in corner], np.int32)], False, ANGLE_COLOR, 2, cv2.LINE_AA)
        mark = RIGHT_MARK * 1.41
    else:
        a1, a2 = math.degrees(math.atan2(u1[1], u1[0])), math.degrees(math.atan2(u2[1], u2[0]))
        sweep = (a2 - a1) % 360
        start = a1 if sweep <= 180 else a2
        cv2.ellipse(img, ip(v), (ANGLE_R, ANGLE_R), 0, start, start + min(sweep, 360 - sweep), ANGLE_COLOR, 2,
                    cv2.LINE_AA)
        mark = ANGLE_R
    if name is None:
        return
    label = f"góc {name} = {angle:.0f}°"
    w, h = text_size([label], VALUE_SIZE)
    hw, hh = w / 2 + 10, h / 2 + 5                # nửa khung viên (cả nền tối)
    c = angle_chip_center(v, (bx, by), hw, hh, img.shape[1], img.shape[0], top)
    edge = min(hw / max(abs(c[0] - v[0]), 1e-3), hh / max(abs(c[1] - v[1]), 1e-3), 1.0)
    start = (c[0] + (v[0] - c[0]) * edge, c[1] + (v[1] - c[1]) * edge)      # mép viên phía đỉnh
    cv2.line(img, ip(start), ip((v[0] + bx * mark, v[1] + by * mark)), ANGLE_COLOR, 1, cv2.LINE_AA)
    _value(img, label, c)
    return c[0] - hw, c[1] - hh, c[0] + hw, c[1] + hh


def draw_angles(img, s, top=0):
    """Tam giác: ký hiệu + viên số đo từng góc. Hình chữ nhật: 4 góc vuông nên chỉ ô vuông, không ghi số.
    Trả về khung các viên số đo đã vẽ."""
    if s["kind"] not in ("triangle", "rect"):
        return []
    pts, angles = s["pts"], measure(s)["angles"]
    angles = round_sum(angles, 180 * (len(pts) - 2))     # số hiện cộng lại đúng 180° (không 179 / 181)
    names = "ABC" if s["kind"] == "triangle" else [None] * 4
    chips = [draw_angle(img, pts[i], pts[i - 1], pts[(i + 1) % len(pts)], angles[i], names[i], top)
             for i in range(len(pts))]
    return [r for r in chips if r]


def draw_canvas(frame, shapes, cur):
    """Vẽ các nét lên lớp canvas đen rồi trộn lên khung hình. Số đo chỉ vẽ khi được yêu cầu
    (cột "Tinh:" của công cụ Chọn, xem draw_tool_overlay).
    Dưới mỗi nét, video được tô đen dày hơn HALO px: phép cộng không làm nét bạc màu trên tường sáng."""
    canvas, frame = np.zeros_like(frame), frame.copy()
    for s in shapes:
        draw_shape(frame, s, (0, 0, 0), 4 + HALO)
        draw_shape(canvas, s, None, 4)
    if cur and len(cur) >= 2:
        line = [np.array([ip(p) for p in cur], dtype=np.int32)]
        cv2.polylines(frame, line, False, (0, 0, 0), 3 + HALO, cv2.LINE_AA)
        cv2.polylines(canvas, line, False, FREE_COLOR, 3, cv2.LINE_AA)
    return cv2.addWeighted(frame, 0.6, canvas, 1, 0)


def draw_trails(img, raw_trail, filt_trail):
    """Chế độ so sánh (phím M): vết điểm thô (xám) và điểm đã lọc (xanh)."""
    if raw_trail:
        cv2.polylines(img, [np.array([ip(p) for p in raw_trail], np.int32)], False, RAW_COLOR, 1, cv2.LINE_AA)
        cv2.polylines(img, [np.array([ip(p) for p in filt_trail], np.int32)], False, FILT_COLOR, 2, cv2.LINE_AA)


CURSOR_R = 14
PRESS_COLOR = (0, 255, 255)      # vàng: đang chụm / bấm (đỏ chỉ dành cho xóa)


def draw_hand(img, hand, res, show_skeleton, gesture="pinch", tool=None):
    """Con trỏ to cho học sinh nhìn từ xa, hình dạng cho biết cách bấm ở chỗ đó (gesture: cử chỉ đang chờ):
    vòng mảnh + chấm tâm = chụm cái + trỏ (vẽ), vòng đôi = áp 2 ngón; công cụ Xóa vòng đỏ;
    đang chụm / bấm tô đặc vàng. tool None: màn bài đo K."""
    if hand and show_skeleton:
        for a, b in CONNECTIONS:
            cv2.line(img, ip(hand["pts"][a]), ip(hand["pts"][b]), SKELETON_COLOR, 1, cv2.LINE_AA)
    if hand:
        cv2.circle(img, ip(hand["p4"]), 5, RAW_COLOR, -1)
        cv2.circle(img, ip(hand["p8"]), 5, RAW_COLOR, -1)
    if res.fpt:
        c, color = ip(res.fpt), ERASE_COLOR if tool == "erase" else FILT_COLOR
        if res.pinched:
            cv2.circle(img, c, CURSOR_R, PRESS_COLOR, -1, cv2.LINE_AA)
        elif gesture == "two_finger":
            cv2.circle(img, c, CURSOR_R, color, 3, cv2.LINE_AA)
            cv2.circle(img, c, CURSOR_R - 6, color, 2, cv2.LINE_AA)
        else:
            cv2.circle(img, c, CURSOR_R, color, 2, cv2.LINE_AA)
            cv2.circle(img, c, 3, color, -1, cv2.LINE_AA)
    elif res.holding and hand:
        cv2.circle(img, ip(draw_point(hand, gesture)), CURSOR_R, HOLD_COLOR, 3, cv2.LINE_AA)


SELECT_COLOR = (255, 200, 0)     # xanh dương nhạt: hình đang chọn
ERASE_COLOR = (0, 0, 255)        # đỏ: hình sắp bị xóa
MEASURE_LABELS = {"angles": "Góc", "perimeter": "Chu vi", "area": "Diện tích"}


def draw_letters(img, s, color, avoid=()):
    """Tên đỉnh A, B, C (D) cách đỉnh 24 px ra phía ngoài (hình to nhỏ đều sát đỉnh); bỏ chữ nào bị viên số đo góc
    (avoid: khung các viên) đè lên – viên đã ghi "góc A" thì vẫn đọc được tên đỉnh."""
    if s["kind"] not in ("triangle", "rect"):
        return
    pts = s["pts"]
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    for name, (x, y) in zip("ABCD", pts):
        d = math.hypot(x - cx, y - cy) or 1.0
        lx, ly = x + (x - cx) / d * 24, y + (y - cy) / d * 24          # tâm chữ (chữ cao ~20 px)
        if not any(x0 - 12 <= lx <= x1 + 12 and y0 - 12 <= ly <= y1 + 12 for x0, y0, x1, y1 in avoid):
            text(img, name, ip((lx - 7, ly + 7)), 0.7, color)


def draw_selection(img, s, color=SELECT_COLOR, scale=None, unit="cm", letters=True):
    """Viền nổi bật hình đang chọn (đỏ khi sắp xóa / kéo đè lên hình khác); tên đỉnh (letters); hình tròn có đường
    bán kính; nhãn cạnh bấm được để sửa số đo, ghi "AB = 3 cm" khi đã có tỉ lệ."""
    draw_shape_halo(img, s, color, 6)
    if letters:
        draw_letters(img, s, color)
    if s["kind"] == "circle":
        c, r = s["center"], s["radius"]
        cv2.line(img, ip(c), ip((c[0] + r, c[1])), color, 2, cv2.LINE_AA)
        cv2.circle(img, ip(c), 4, color, -1, cv2.LINE_AA)
    for lines, (x, y), (hw, hh) in side_chips(s, scale, unit).values():
        draw_button(img, (x - hw, y - hh, x + hw, y + hh), lines, scale=VALUE_SIZE / 36)


def draw_rotation_handle(img, shape, tool):
    """Chấm tay cầm xoay nối với góc khung bao; đang xoay thì vẽ đường từ tâm tới tay + góc nghiêng cạnh đầu."""
    h = tool.handle(shape)
    if h is None:
        return
    rot = tool.rotation if tool._dragging else None
    if rot:
        dashed_line(img, rot["pivot"], rot["pos"], SELECT_COLOR)
        h = rot["pos"]
        a = (edge_angle(*shape["pts"][:2]) + 90) % 180 - 90
        _label_chip(img, [f"{abs(a):.0f}°"], (int(h[0]) + 24, int(h[1]) - 14), 22, bold=True)
    else:
        xs, ys = [p[0] for p in shape["pts"]], [p[1] for p in shape["pts"]]
        corner = (min(max(h[0], min(xs)), max(xs)), min(max(h[1], min(ys)), max(ys)))
        cv2.line(img, ip(corner), ip(h), SELECT_COLOR, 1, cv2.LINE_AA)
    cv2.circle(img, ip(h), HANDLE_R, (40, 40, 40), -1, cv2.LINE_AA)
    cv2.circle(img, ip(h), HANDLE_R, SELECT_COLOR, 2, cv2.LINE_AA)
    cv2.ellipse(img, ip(h), (10, 10), 0, -60, 210, SELECT_COLOR, 2, cv2.LINE_AA)      # mũi tên vòng
    tip = (h[0] + 10 * math.cos(math.radians(-60)), h[1] + 10 * math.sin(math.radians(-60)))
    cv2.circle(img, ip(tip), 4, SELECT_COLOR, -1, cv2.LINE_AA)


def draw_trash(img, near=False):
    """Vùng xóa ở góc trên trái (chỉ hiện khi đang kéo hình): kéo hình vào là xóa. near: tay sắp vào – vùng to thêm
    20 px, đỏ tươi hơn, viền trắng dày (vùng bấm vẫn là TRASH_R)."""
    from airgeo.tools.select import TRASH_R
    r = TRASH_R + 20 if near else TRASH_R
    roi = img[:r + 1, :r + 1]
    disk = roi.copy()
    cv2.circle(disk, (0, 0), r, (0, 0, 230) if near else (0, 0, 170), -1, cv2.LINE_AA)
    roi[:] = cv2.addWeighted(roi, 0.25, disk, 0.75, 0)
    edge = (255, 255, 255)
    cv2.circle(img, (0, 0), r, edge if near else ERASE_COLOR, 5 if near else 3, cv2.LINE_AA)
    # biểu tượng thùng rác (nắp + quai, thân hình thang, 3 vạch), cỡ 0.8, giữa 1/4 hình tròn
    ox, oy, k = 54, 56, 0.8

    def q(dx, dy):
        return int(round(ox + dx * k)), int(round(oy + dy * k))
    cv2.line(img, q(-22, -16), q(22, -16), edge, 3, cv2.LINE_AA)
    cv2.rectangle(img, q(-7, -22), q(7, -16), edge, 2, cv2.LINE_AA)
    body = np.array([q(-17, -10), q(17, -10), q(13, 22), q(-13, 22)], np.int32)
    cv2.polylines(img, [body], True, edge, 3, cv2.LINE_AA)
    for dx in (-6, 0, 6):
        cv2.line(img, q(dx, -4), q(dx, 16), edge, 2, cv2.LINE_AA)


def draw_tool_overlay(img, ctl):
    """Hình đang chọn (công cụ Chọn) hoặc hình dưới con trỏ sắp bị xóa (công cụ Xóa)."""
    tool = ctl.tools[ctl.tool]
    sid = getattr(tool, "selected", None) or getattr(tool, "hovered", None)
    shape = ctl.board.get(sid) if sid else None
    if shape is None:
        return
    if ctl.tool == "select":
        angles = "angles" in tool.show
        draw_selection(img, shape, ERASE_COLOR if tool.near_trash else SELECT_COLOR, ctl.board.scale,
                       ctl.board.unit, letters=False)
        # chu vi / diện tích nằm trong bảng công thức; khung viên góc giữ lại để tay cầm xoay không đè lên
        tool.avoid = draw_angles(img, shape, ctl.bounds[1]) if angles else []
        draw_letters(img, shape, SELECT_COLOR, tool.avoid)
        name = shape_name(shape)                  # tên hình làm tiêu đề cột Tính, căn phải theo cột
        w, _ = text_size([name], 22, True)
        _label_chip(img, [name], (tool.menu_x + MENU_W - w - 10, tool.menu_y - 40), 22, bold=True)
        for k, rect in tool.menu(shape):
            draw_button(img, rect, MEASURE_LABELS[k], on=k in tool.show)
        if shape["kind"] == "triangle" and "area" in tool.show:
            draw_height(img, shape["pts"], ctl.board.scale, ctl.board.unit)
        draw_formulas(img, shape, tool, ctl.board.scale, ctl.board.unit)
        draw_rotation_handle(img, shape, tool)
        if tool._dragging and not tool.rotation:
            draw_trash(img, tool.near_trash)
    else:
        draw_shape_halo(img, shape, ERASE_COLOR, 6)


# Bảng công thức: tiêu đề vàng nhỏ, công thức trắng, thế số xám (phụ), kết quả đậm và lớn hơn (dòng cần đọc)
FORMULA_STYLE = [(-4, (0, 220, 255), False), (0, (255, 255, 255), False), (0, (200, 200, 200), False),
                 (8, (255, 255, 255), True)]     # (chênh cỡ chữ, màu BGR, đậm) cho từng dòng của 1 khối
PANEL_PAD, BLOCK_GAP = 10, 14


def dashed_line(img, p, q, color, dash=8):
    n = max(1, int(math.dist(p, q) // dash))
    for i in range(0, n, 2):
        a = (p[0] + (q[0] - p[0]) * i / n, p[1] + (q[1] - p[1]) * i / n)
        b = (p[0] + (q[0] - p[0]) * (i + 1) / n, p[1] + (q[1] - p[1]) * (i + 1) / n)
        cv2.line(img, ip(a), ip(b), color, 2, cv2.LINE_AA)


def draw_height(img, pts, scale=None, unit="cm"):
    """Đường cao nét đứt từ C xuống AB; chân ngoài đoạn AB (tam giác tù) thì kéo dài AB bằng nét đứt.
    Viên "h = 4 cm" (chưa có tỉ lệ: "h"); tam giác vuông tại B / A thì đường cao chính là cạnh: "h = BC" / "h = CA"."""
    c, foot, h = triangle_height(pts)
    if h < 1:
        return
    a, b = pts[0], pts[1]
    if math.dist(a, foot) + math.dist(foot, b) > math.dist(a, b) + 1:
        dashed_line(img, min((a, b), key=lambda p: math.dist(p, foot)), foot, SELECT_COLOR)
    dashed_line(img, c, foot, SELECT_COLOR)
    cv2.circle(img, ip(foot), 4, SELECT_COLOR, -1)
    label = ("h = BC" if math.dist(foot, b) < 1 else "h = CA" if math.dist(foot, a) < 1
             else "h" if scale is None else f"h = {fmt_length(h, scale, unit)}")
    # viên nằm cạnh đường cao, lệch theo AB vào phía trong tam giác: đường cao trùng cạnh thì không đè nhãn cạnh
    m = ((c[0] + foot[0]) / 2, (c[1] + foot[1]) / 2)
    g = (sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3)
    ux, uy = (b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b)
    side = 1 if (g[0] - m[0]) * ux + (g[1] - m[1]) * uy >= 0 else -1
    reach = side * (text_size([label], VALUE_SIZE)[0] / 2 + 20)        # nửa viên (cả lề nền 10) + 10 px
    _value(img, label, (m[0] + ux * reach, m[1] + uy * reach))


def _block_size(block, size):
    dims = [text_size([s], size + ds, bold) for s, (ds, _, bold) in zip(block, FORMULA_STYLE)]
    return max(w for w, _ in dims), sum(h for _, h in dims)


def draw_formulas(img, shape, tool, scale, unit):
    """Bảng công thức dưới cột "Tinh:", căn phải theo cột. Khung hình thấp không đủ chỗ thì đặt sang trái cột,
    ngang đầu cột; chữ 26 px (kết quả 34 đậm, cho cuối lớp), thiếu chỗ thì thu nhỏ tới 14 px. Trả về khung bảng (x0, y0, x1, y1), None nếu không có gì để vẽ."""
    blocks = [b for b in (formula(shape, k, scale, unit) for k in ("perimeter", "area") if k in tool.show) if b]
    menu = tool.menu(shape)
    if not blocks or not menu:
        return
    def panel(size):
        dims = [_block_size(b, size) for b in blocks]
        return (max(MENU_W, max(w for w, _ in dims) + 2 * PANEL_PAD),
                sum(h for _, h in dims) + BLOCK_GAP * (len(blocks) - 1) + 2 * PANEL_PAD)

    wide = MENU_W + FIT_MARGIN - 40  # bảng dưới cột không lấn vào vùng đặt hình (fit_box chừa FIT_MARGIN trái cột) + chữ đỉnh

    def fit(top, max_w=wide):        # cỡ chữ lớn nhất (26 -> 14) vừa chỗ còn lại từ top, None nếu không vừa
        return next((sz for sz in range(26, 13, -2)
                     if panel(sz)[1] <= img.shape[0] - 45 - top and panel(sz)[0] <= max_w), None)

    top, right = int(menu[-1][1][3]) + 16, tool.menu_x + MENU_W
    size = fit(top)
    if size is None:                 # sang trái cột nút, ngang đầu cột
        top, right = int(menu[0][1][1]), tool.menu_x - 10
        size = fit(top, img.shape[1]) or 14
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


POSE_LABELS = {"draw": "Vẽ", "select": "Chọn", "erase": "Xóa", "undo": "Hoàn tác", "menu": "Menu"}


def _label_chip(img, lines, org, size, bold=False):
    """Khối chữ trên nền tối (đọc được trên mọi nền camera)."""
    w, h = text_size(lines, size, bold)
    x, y = org
    roi = img[max(y - 6, 0):max(y + h + 4, 0), max(x - 10, 0):max(x + w + 10, 0)]
    roi[:] = (roi * 0.25).astype(np.uint8)
    put_text(img, lines, (x, y), size, bold=bold)


def draw_pose_progress(img, pos, progress):
    """Vòng tiến độ quanh đầu ngón khi đang giữ một tư thế + tên lệnh sắp chạy. Giữ chưa tới 20% thì chưa vẽ
    (tay đang chuyển tư thế thoáng qua, không nên nhấp nháy)."""
    if progress is None or pos is None or progress[1] < 0.2:
        return
    action, frac = progress
    c = ip(pos)
    cv2.circle(img, c, 30, (70, 70, 70), 6, cv2.LINE_AA)
    cv2.ellipse(img, c, (30, 30), -90, 0, 360 * frac, BUTTON_HOVER, 6, cv2.LINE_AA)
    w, h = text_size([POSE_LABELS[action]], 22, True)
    x = c[0] + 46 if c[0] + 46 + w + 10 <= img.shape[1] else c[0] - 46 - w     # gần mép phải: lật sang trái
    _label_chip(img, [POSE_LABELS[action]], (x, c[1] - h // 2), 22, bold=True)


def draw_radial_menu(img, menu, board, t, cursor, bar_on=False):
    """Menu tròn: 6 mục quanh tâm, mục dưới con trỏ viền vàng; Xóa hết đã bấm 1 lần nền đỏ.
    board, bar_on: để ghi đơn vị hiện tại và chữ Hiện / Ẩn của mục dải nút."""
    from airgeo.interaction.radial_menu import ITEM_R
    armed = menu.clear_armed(t)
    labels = {"unit": ["Đơn vị", board.unit], "bar": ["Ẩn nút" if bar_on else "Hiện", "" if bar_on else "nút"],
              "clear": ["Chắc", "chưa?"] if armed else ["Xóa", "hết"], "close": ["Đóng"],
              "redo": ["Làm", "lại"], "help": ["Gợi ý"]}
    hover = menu.hit(cursor) if cursor is not None else None
    for a, p in menu.positions():
        cx, cy = ip(p)
        x0, y0 = max(cx - ITEM_R, 0), max(cy - ITEM_R, 0)
        roi = img[y0:cy + ITEM_R + 1, x0:cx + ITEM_R + 1]
        disk = roi.copy()
        fill = (0, 0, 170) if a == "clear" and armed else (0, 0, 0)
        cv2.circle(disk, (cx - x0, cy - y0), ITEM_R, fill, -1, cv2.LINE_AA)
        roi[:] = cv2.addWeighted(roi, 0.1, disk, 0.9, 0)      # phủ ~90%: chữ đọc được cả trên nền rối
        cv2.circle(img, (cx, cy), ITEM_R, BUTTON_HOVER if a == hover else BUTTON_EDGE, 3 if a == hover else 1,
                   cv2.LINE_AA)
        lh = round(18 * 1.3)                     # canh giữa từng dòng
        for i, s in enumerate(labels[a]):
            w, _ = text_size([s], 18, True)
            put_text(img, [s], (cx - w // 2, cy - lh * len(labels[a]) // 2 + i * lh), 18, bold=True)
    cv2.circle(img, ip(menu.center), 5, BUTTON_EDGE, -1, cv2.LINE_AA)


def draw_fitts(img, task):
    """Bài đo bấm mục tiêu (phím K): nền tối, mục tiêu xám, mục tiêu cần bấm tô vàng; xong thì bảng kết quả."""
    img[:] = (img * 0.45).astype(np.uint8)
    if task.done:
        lines = ["Kết quả bài đo (đã lưu data/fitts_*.csv) – K: thoát"] + [
            f"D={b['D']:.0f} W={b['W']:.0f}: {b['tp']:.2f} bit/s, trượt {b['error_rate'] * 100:.0f}%, "
            f"MT {b['mt_ms']:.0f} ms" for b in task.summary()]
        w, h = text_size(lines, 22)
        _label_chip(img, lines, ((img.shape[1] - w) // 2, (img.shape[0] - h) // 2), 22)
        return
    W = task.blocks[task.block][1]
    for i, p in enumerate(task.targets()):
        if i == task.current:
            cv2.circle(img, ip(p), int(W / 2), BUTTON_HOVER, -1, cv2.LINE_AA)
        cv2.circle(img, ip(p), int(W / 2), BUTTON_EDGE, 2, cv2.LINE_AA)
    D, Wb = task.blocks[task.block]
    bam = "áp 2 ngón" if task.gesture == "two_finger" else "chụm"
    lines = [f"Bài đo: khối {task.block + 1}/{len(task.blocks)}  D={D:.0f} W={Wb:.0f}  lần {task.step}/{task.n}",
             f"Bấm vào hình tròn vàng ({bam}, B: đổi)  ·  S: ổn định điểm bấm  ·  K: thoát"]
    w, _ = text_size(lines, 20)
    _label_chip(img, lines, ((img.shape[1] - w) // 2, 16), 20)
