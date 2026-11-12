"""Xoay hình: quanh tâm, hít về trục ngang / dọc khi một cạnh lệch ít (vẽ tay hay bị nghiêng vài độ)."""
import math

SNAP_KINDS = ("line", "triangle", "rect")
SNAP_DEG = 8.0      # cạnh lệch trục <= bấy nhiêu độ thì hít thẳng (cả lúc vẽ lẫn lúc xoay)


def edge_angle(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def rotate_points(pts, deg, about):
    """Xoay các điểm (x, y, ...) quanh about; phần sau (vd. thời gian t của nét gốc) giữ nguyên."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    ox, oy = about
    return [(ox + (p[0] - ox) * c - (p[1] - oy) * s, oy + (p[0] - ox) * s + (p[1] - oy) * c, *p[2:]) for p in pts]


def center(shape):
    if shape["kind"] == "circle":
        return shape["center"]
    pts = shape["pts"]
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def snap_delta(shape, tol):
    """Góc (độ) cần xoay thêm để cạnh gần trục nhất nằm đúng ngang / dọc; 0 nếu không cạnh nào lệch <= tol."""
    if shape["kind"] not in SNAP_KINDS:
        return 0
    pts = shape["pts"]
    edges = zip(pts, pts[1:] + pts[:1]) if shape["kind"] != "line" else [pts]
    deltas = [-((edge_angle(a, b) + 45) % 90 - 45) for a, b in edges]
    return min((d for d in deltas if abs(d) <= tol), key=abs, default=0)


def straighten(shape, tol=SNAP_DEG):
    """Hình nhận dạng được mà lệch trục <= tol độ thì xoay cho thẳng. Xoay cả nét gốc raw (nếu có) để bật / tắt
    Smart nhận dạng lại ra đúng hình này – nếu không, góc lệch ẩn trong raw sẽ cộng vào mỗi lần xoay sau đó."""
    d = snap_delta(shape, tol)
    if d:
        c = center(shape)
        shape["pts"] = rotate_points(shape["pts"], d, c)
        if "raw" in shape:
            shape["raw"] = rotate_points(shape["raw"], d, c)
    return shape
