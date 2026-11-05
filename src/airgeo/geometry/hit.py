"""Khoảng cách từ con trỏ tới hình, để biết đang chạm hình nào (công cụ Chọn / Xóa)."""
import math


def _segment_distance(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    u = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + u * dx), py - (ay + u * dy))


def distance_to_shape(pos, shape):
    if shape["kind"] == "circle":
        return abs(math.dist(pos, shape["center"]) - shape["radius"])
    pts = list(shape["pts"])
    if shape["kind"] in ("triangle", "rect"):
        pts.append(pts[0])            # đường kín: thêm cạnh đóng hình
    if len(pts) == 1:
        return math.dist(pos, pts[0])
    return min(_segment_distance(pos, a, b) for a, b in zip(pts, pts[1:]))
