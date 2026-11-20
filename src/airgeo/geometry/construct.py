"""Dựng lại hình từ số đo người dùng nhập (đơn vị px; quy đổi đơn vị làm ở interaction/edit_panel.py).

Mọi hình giữ trọng tâm và hướng cạnh đầu tiên của hình cũ, để không bị nhảy chỗ khi sửa số.
Tam giác dựng từ 3 cạnh bằng định lý cos; đỉnh C giữ cùng phía với cạnh AB như trước.
"""
import math

FIELDS = {"line": ["d"], "triangle": ["AB", "BC", "CA"], "rect": ["dai", "rong"], "circle": ["r"]}
FIELD_LABELS = {"dai": "dài", "rong": "rộng"}     # chữ có dấu hiện cho học sinh (mã trường không dấu)


def field_names(kind):
    return FIELDS.get(kind, [])


def current_lengths(shape):
    """Độ dài hiện tại (px) của từng ô. Cạnh thứ i nối đỉnh i với đỉnh i+1."""
    if shape["kind"] == "circle":
        return {"r": float(shape["radius"])}
    pts = shape["pts"]
    return {f: math.dist(pts[i], pts[(i + 1) % len(pts)]) for i, f in enumerate(field_names(shape["kind"]))}


def _centroid(pts):
    n = len(pts)
    return sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n


def _unit(a, b):
    d = math.dist(a, b)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d) if d else (1.0, 0.0)


def label_anchors(shape, offset=45):
    """Vị trí nhãn bấm được của từng ô: giữa cạnh, đẩy ra ngoài hình; hình tròn: giữa bán kính.
    offset > label_radius (25) + hit_radius (15) để vùng bấm nhãn không đè lên vùng cầm hình."""
    kind = shape["kind"]
    if kind == "circle":
        (cx, cy), r = shape["center"], shape["radius"]
        return {"r": (cx + r / 2, cy - offset / 2)}
    if kind not in FIELDS:
        return {}
    pts = shape["pts"]
    if kind == "line":
        (ax, ay), (bx, by) = pts
        ux, uy = _unit(pts[0], pts[1])
        return {"d": ((ax + bx) / 2 - uy * offset, (ay + by) / 2 + ux * offset)}
    cx, cy = _centroid(pts)
    out = {}
    for i, f in enumerate(FIELDS[kind]):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ux, uy = _unit((cx, cy), (mx, my))
        out[f] = (mx + ux * offset, my + uy * offset)
    return out


def fit(shape, box):
    """Co giãn hình quanh tâm khung bao cho vừa khít box (x0, y0, x1, y1), giữ tỉ lệ, rồi dời vào giữa box
    (học sinh nhìn rõ: hình luôn to và ở giữa). Trả về (hình mới, hệ số k). Khung bao dẹt (đoạn ngang) chỉ xét chiều
    còn lại."""
    if shape["kind"] == "circle":
        (cx, cy), r = shape["center"], shape["radius"]
        lo, hi = (cx - r, cy - r), (cx + r, cy + r)
    else:
        xs, ys = [p[0] for p in shape["pts"]], [p[1] for p in shape["pts"]]
        lo, hi = (min(xs), min(ys)), (max(xs), max(ys))
    w, h = hi[0] - lo[0], hi[1] - lo[1]
    k = min((box[2] - box[0]) / w if w > 1e-6 else math.inf, (box[3] - box[1]) / h if h > 1e-6 else math.inf)
    k = 1.0 if math.isinf(k) else k
    c, bc = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2), ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

    def move(p):
        return (bc[0] + (p[0] - c[0]) * k, bc[1] + (p[1] - c[1]) * k, *p[2:])

    new = dict(shape, pts=[move(p) for p in shape["pts"]], raw=[move(p) for p in shape.get("raw", [])])
    if shape["kind"] == "circle":
        new["center"], new["radius"] = move(shape["center"]), shape["radius"] * k
    return new, k


def _check_triangle(lengths, fmt):
    names = FIELDS["triangle"]
    for f in names:
        o1, o2 = [g for g in names if g != f]
        if lengths[f] >= lengths[o1] + lengths[o2]:     # bất đẳng thức tam giác chặt
            raise ValueError(f"{f} phải nhỏ hơn {o1} + {o2} = {fmt(lengths[o1] + lengths[o2])}")


def build(shape, lengths, fmt=lambda px: f"{px:.0f}px"):
    """lengths: {tên ô: độ dài px}; fmt: định dạng số trong thông báo lỗi. Hình dựng xong được fit() vào vùng vẽ."""
    kind = shape["kind"]
    if kind == "circle":
        new = {"kind": "circle", "pts": [], "center": shape["center"], "radius": lengths["r"]}
    else:
        old = shape["pts"]
        u = _unit(old[0], old[1])                 # hướng cạnh đầu tiên
        n = (-u[1], u[0])                         # pháp tuyến
        if kind == "line":
            d = lengths["d"]
            local = [(0.0, 0.0), (u[0] * d, u[1] * d)]
        elif kind == "triangle":
            _check_triangle(lengths, fmt)
            c, a, b = lengths["AB"], lengths["BC"], lengths["CA"]
            x = (b * b + c * c - a * a) / (2 * c)
            y = math.sqrt(max(b * b - x * x, 0.0))
            (ax, ay), (bx, by), (cx, cy) = old
            side = 1 if (bx - ax) * (cy - ay) - (by - ay) * (cx - ax) >= 0 else -1
            local = [(0.0, 0.0), (u[0] * c, u[1] * c),
                     (u[0] * x + n[0] * y * side, u[1] * x + n[1] * y * side)]
        elif kind == "rect":
            w, h = lengths["dai"], lengths["rong"]
            v = _unit(old[1], old[2])             # hướng cạnh thứ hai, giữ đúng chiều xoay
            local = [(0.0, 0.0), (u[0] * w, u[1] * w),
                     (u[0] * w + v[0] * h, u[1] * w + v[1] * h), (v[0] * h, v[1] * h)]
        else:
            raise ValueError("Hinh nay khong sua so do duoc")
        (ox, oy), (lx, ly) = _centroid(old), _centroid(local)
        pts = [(x - lx + ox, y - ly + oy) for x, y in local]
        new = {"kind": kind, "pts": pts}
    new.update(id=shape["id"], raw=shape["raw"], locked=True)
    return new
