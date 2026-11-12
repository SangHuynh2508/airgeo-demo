"""Công thức tính (công thức -> thế số -> kết quả) cho Chu vi / Diện tích của hình cơ bản.
Số lấy từ measure() / current_lengths(); ở đây chỉ đổi đơn vị và định dạng."""
import math

from airgeo.geometry.construct import current_lengths
from airgeo.geometry.measure import measure
from airgeo.geometry.units import to_units, trim


def triangle_height(pts):
    """Đường cao từ C xuống đường thẳng AB: (C, chân đường cao, h px). Chân có thể nằm ngoài đoạn AB."""
    (ax, ay), (bx, by), c = pts
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return c, c, 0.0
    u = ((c[0] - ax) * dx + (c[1] - ay) * dy) / l2
    foot = (ax + u * dx, ay + u * dy)
    return c, foot, math.dist(c, foot)


def formula(shape, key, scale, unit):
    """Các dòng của 1 khối: tiêu đề, công thức, thế số, kết quả. [] nếu hình / phép tính không có công thức."""
    kind = shape["kind"]
    if kind not in ("triangle", "rect", "circle") or key not in ("perimeter", "area"):
        return []
    u = "px" if scale is None else unit

    def n(px):                       # độ dài px -> số theo đơn vị hiện tại
        return trim(px if scale is None else to_units(px, unit, scale))

    def n2(px2):                     # diện tích: đổi đơn vị 2 lần (px² -> cm²)
        return trim(px2 if scale is None else to_units(to_units(px2, unit, scale), unit, scale))

    m, cur = measure(shape), current_lengths(shape)
    if key == "perimeter":
        total = f"= {n(m['perimeter'])} {u}"
        if kind == "triangle":
            return ["Chu vi", "P = AB + BC + CA", f"= {n(cur['AB'])} + {n(cur['BC'])} + {n(cur['CA'])}", total]
        if kind == "rect":
            return ["Chu vi (a = dài, b = rộng)", "P = 2(a + b)", f"= 2({n(cur['dai'])} + {n(cur['rong'])})", total]
        return ["Chu vi", "C = 2πr", f"= 2π · {n(cur['r'])}", total]
    total = f"= {n2(m['area'])} {u}²"
    if kind == "triangle":
        return ["Diện tích", "S = ½ · AB · h", f"= ½ · {n(cur['AB'])} · {n(triangle_height(shape['pts'])[2])}", total]
    if kind == "rect":
        return ["Diện tích (a = dài, b = rộng)", "S = a · b", f"= {n(cur['dai'])} · {n(cur['rong'])}", total]
    return ["Diện tích", "S = πr²", f"= π · {n(cur['r'])}²", total]
