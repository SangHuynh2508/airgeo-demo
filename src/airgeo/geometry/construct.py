"""Dựng lại hình từ số đo người dùng nhập (đơn vị px; quy đổi đơn vị làm ở interaction/edit_panel.py).

Mọi hình giữ trọng tâm và hướng cạnh đầu tiên của hình cũ, để không bị nhảy chỗ khi sửa số.
Tam giác dựng từ 3 cạnh bằng định lý cos; đỉnh C giữ cùng phía với cạnh AB như trước.
"""
import math

from airgeo.geometry.hit import bbox
from airgeo.geometry.measure import centroid

FIELDS = {"triangle": ["AB", "BC", "CA"], "rect": ["dai", "rong"], "circle": ["r"]}
FIELD_LABELS = {"dai": "dài", "rong": "rộng"}     # chữ có dấu hiện cho học sinh (mã trường không dấu)


def field_names(kind):
    return FIELDS.get(kind, [])


def current_lengths(shape):
    """Độ dài hiện tại (px) của từng ô. Cạnh thứ i nối đỉnh i với đỉnh i+1."""
    if shape["kind"] == "circle":
        return {"r": float(shape["radius"])}
    pts = shape["pts"]
    return {f: math.dist(pts[i], pts[(i + 1) % len(pts)]) for i, f in enumerate(field_names(shape["kind"]))}


def _unit(a, b):
    d = math.dist(a, b)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d) if d else (1.0, 0.0)


def label_edges(shape):
    """{ô: (đầu, cuối) của cạnh mang nhãn}. Cạnh thứ i nối đỉnh i với i+1; hình chữ nhật mỗi ô có 2 cạnh bằng nhau –
    lấy cạnh phía trên / trái (xa cột Tính bên phải và mép dưới, chỗ tay với thấp thì mất tay)."""
    pts, kind = shape["pts"], shape["kind"]
    n, out = len(pts), {}
    for i, f in enumerate(FIELDS.get(kind, []) if kind != "circle" else []):
        j = min((i, i + 2) if kind == "rect" else (i,), key=lambda j: sum(pts[j % n]) + sum(pts[(j + 1) % n]))
        out[f] = pts[j % n], pts[(j + 1) % n]
    return out


def label_anchors(shape, offset=60, half=None):
    """Vị trí nhãn bấm được của từng ô: giữa cạnh, đẩy ra ngoài hình; hình tròn: giữa bán kính.
    offset > label_radius (25) + hit_radius (15) để vùng bấm nhãn không đè lên vùng cầm hình;
    60 (không phải 45) để nhãn cạnh chữ cỡ 28 không đè lên chính cạnh đó khi cạnh dọc / xiên.
    half: {ô: (nửa rộng, nửa cao)} của viên nhãn – viên rộng ("AB = 3 cm") được đẩy xa thêm cho cả viên cách
    cạnh >= 12 px."""
    kind = shape["kind"]
    if kind == "circle":
        (cx, cy), r = shape["center"], shape["radius"]
        return {"r": (cx + r / 2, cy - offset / 2)}
    if kind not in FIELDS:
        return {}
    pts = shape["pts"]
    cx, cy = centroid(pts)
    out = {}
    for f, (a, b) in label_edges(shape).items():
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        ex, ey = _unit(a, b)
        ux, uy = _unit((cx, cy), (mx, my))       # hướng đẩy nhãn ra ngoài
        off = offset
        if half:        # khoảng cách tới cạnh đo theo pháp tuyến (-ey, ex): khung viên chiếu lên pháp tuyến
            hw, hh = half[f]
            off = max(offset, (hw * abs(ey) + hh * abs(ex) + 12) / max(abs(ux * ey - uy * ex), 0.3))
        out[f] = (mx + ux * off, my + uy * off)
    return out


def fit(shape, box):
    """Co giãn hình quanh tâm khung bao cho vừa khít box (x0, y0, x1, y1), giữ tỉ lệ, rồi dời vào giữa box
    (học sinh nhìn rõ: hình luôn to và ở giữa). Trả về (hình mới, hệ số k)."""
    x0, y0, x1, y1 = bbox(shape)
    lo, hi = (x0, y0), (x1, y1)
    w, h = hi[0] - lo[0], hi[1] - lo[1]
    k = min((box[2] - box[0]) / w, (box[3] - box[1]) / h)
    c, bc = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2), ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)

    def move(p):
        return (bc[0] + (p[0] - c[0]) * k, bc[1] + (p[1] - c[1]) * k)

    new = dict(shape, pts=[move(p) for p in shape["pts"]])
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
        if kind == "triangle":
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
        (ox, oy), (lx, ly) = centroid(old), centroid(local)
        pts = [(x - lx + ox, y - ly + oy) for x, y in local]
        new = {"kind": kind, "pts": pts}
    new["id"] = shape["id"]
    return new
