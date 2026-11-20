"""Nắn hình vẽ tay gần đặc biệt cho đúng luôn, và gọi tên hình như sách giáo khoa.

Tên hình phải khớp số đo hiện ra (không gọi "tam giác vuông" khi góc ghi 87°), nên lúc nhận dạng (tidy):
chữ nhật 2 cạnh lệch <= SIDE_TOL -> hình vuông; tam giác gần đều / gần vuông / gần cân -> nắn đúng.
shape_name xét với dung sai rất nhỏ trên hình đã nắn hoặc hình dựng lại từ số đo nhập vào.
"""
import math

from airgeo.geometry.measure import polygon_metrics

SIDE_TOL, DEG_TOL = 0.08, 8.0           # nắn: cạnh lệch <= 8%, góc lệch 90° <= 8° (cùng ngưỡng hít thẳng trục)
NAME_SIDE_TOL, NAME_DEG_TOL = 1e-4, 0.5       # hình đã nắn / dựng từ số nhập là chính xác; số hiện 2 chữ số lẻ


def _close(a, b, tol):
    return abs(a - b) <= tol * max(a, b)


def is_right(angle):
    return abs(angle - 90) <= NAME_DEG_TOL


def _unit(p, q):
    d = math.dist(p, q) or 1.0
    return (q[0] - p[0]) / d, (q[1] - p[1]) / d


def _toward(p, q, v):
    """Pháp tuyến đơn vị của đoạn pq, quay về phía điểm v."""
    ux, uy = _unit(p, q)
    n = (-uy, ux)
    m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    return n if n[0] * (v[0] - m[0]) + n[1] * (v[1] - m[1]) >= 0 else (-n[0], -n[1])


def _square(pts):
    w, h = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
    if not _close(w, h, SIDE_TOL):
        return pts
    s, (ux, uy), (vx, vy) = (w + h) / 4, _unit(pts[0], pts[1]), _unit(pts[1], pts[2])
    cx, cy = sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
    return [(cx + a * s * ux + b * s * vx, cy + a * s * uy + b * s * vy) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _triangle(pts):
    m = polygon_metrics(pts)
    sides, angles = m["sides"], m["angles"]
    if _close(max(sides), min(sides), SIDE_TOL):                       # đều: giữ cạnh AB, dựng C
        a, b, c = pts
        L = sum(sides) / 3
        mid, u, n = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), _unit(a, b), _toward(a, b, c)
        h = L * math.sqrt(3) / 2
        return [(mid[0] - u[0] * L / 2, mid[1] - u[1] * L / 2), (mid[0] + u[0] * L / 2, mid[1] + u[1] * L / 2),
                (mid[0] + n[0] * h, mid[1] + n[1] * h)]
    # đỉnh j có 2 cạnh kề sides[j - 1], sides[j] gần bằng nhau nhất (ứng viên tam giác cân)
    j = min(range(3), key=lambda k: abs(sides[k - 1] - sides[k]) / max(sides[k - 1], sides[k]))
    iso = _close(sides[j - 1], sides[j], SIDE_TOL)
    i = min(range(3), key=lambda k: abs(angles[k] - 90))
    # vuông, trừ khi là tam giác cân đỉnh hẹp (góc đáy ~85° gần vuông nhưng cân ở đỉnh khác) -> nắn cân
    if abs(angles[i] - 90) <= DEG_TOL and not (iso and j != i):          # đỉnh lên đường tròn đường kính huyền
        p, v, q = pts[i - 1], pts[i], pts[(i + 1) % 3]
        mid, r = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), math.dist(p, q) / 2
        if _close(math.dist(v, p), math.dist(v, q), SIDE_TOL):          # vuông cân: đỉnh trên trung trực
            d = _toward(p, q, v)
        else:
            d = _unit(mid, v)
        out = list(pts)
        out[i] = (mid[0] + d[0] * r, mid[1] + d[1] * r)
        return out
    if not iso:                                                          # cân: chiếu đỉnh j lên trung trực đáy
        return pts
    i = j
    p, v, q = pts[i - 1], pts[i], pts[(i + 1) % 3]
    mid, n = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), _toward(p, q, v)
    h = n[0] * (v[0] - mid[0]) + n[1] * (v[1] - mid[1])
    out = list(pts)
    out[i] = (mid[0] + n[0] * h, mid[1] + n[1] * h)
    return out


def tidy(shape):
    if shape["kind"] == "rect":
        shape["pts"] = _square(shape["pts"])
    elif shape["kind"] == "triangle":
        shape["pts"] = _triangle(shape["pts"])
    return shape


def shape_name(shape):
    kind = shape["kind"]
    if kind == "line":
        return "Đoạn thẳng"
    if kind == "circle":
        return "Hình tròn"
    if kind not in ("rect", "triangle"):
        return ""
    m = polygon_metrics(shape["pts"])
    sides = m["sides"]
    if kind == "rect":
        return "Hình vuông" if _close(sides[0], sides[1], NAME_SIDE_TOL) else "Hình chữ nhật"
    if _close(max(sides), min(sides), NAME_SIDE_TOL):
        return "Tam giác đều"
    iso = any(_close(sides[k - 1], sides[k], NAME_SIDE_TOL) for k in range(3))
    if any(is_right(a) for a in m["angles"]):
        return "Tam giác vuông cân" if iso else "Tam giác vuông"
    return "Tam giác cân" if iso else "Tam giác thường"
