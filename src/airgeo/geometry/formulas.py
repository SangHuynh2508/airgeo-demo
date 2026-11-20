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


NEED_SCALE = "Nhập số đo cạnh để tính"
_FORMULAS = {"triangle": {"perimeter": ["Chu vi", "P = AB + BC + CA"], "area": ["Diện tích", "S = ½ · AB · h"]},
             "rect": {"perimeter": ["Chu vi (a = dài, b = rộng)", "P = 2(a + b)"],
                      "area": ["Diện tích (a = dài, b = rộng)", "S = a · b"]},
             "circle": {"perimeter": ["Chu vi", "C = 2πr"], "area": ["Diện tích", "S = πr²"]}}


def formula(shape, key, scale, unit):
    """Các dòng của 1 khối: tiêu đề, công thức, thế số, kết quả. [] nếu hình / phép tính không có công thức.
    Chưa có tỉ lệ (chưa nhập số đo): tiêu đề, công thức, lời nhắc – không hiện số px cho học sinh."""
    kind = shape["kind"]
    if kind not in ("triangle", "rect", "circle") or key not in ("perimeter", "area"):
        return []
    if scale is None:
        return [*_FORMULAS[kind][key], NEED_SCALE]

    def n(px):                       # độ dài px -> số theo đơn vị hiện tại
        return trim(to_units(px, unit, scale))

    m, cur = measure(shape), current_lengths(shape)
    if key == "perimeter":
        total = f"= {n(m['perimeter'])} {unit}"
        if kind == "triangle":
            sub = f"= {n(cur['AB'])} + {n(cur['BC'])} + {n(cur['CA'])}"
        elif kind == "rect":
            sub = f"= 2({n(cur['dai'])} + {n(cur['rong'])})"
        else:
            sub = f"= 2π · {n(cur['r'])}"
    else:
        total = f"= {trim(to_units(to_units(m['area'], unit, scale), unit, scale))} {unit}²"   # px² -> cm²
        if kind == "triangle":
            sub = f"= ½ · {n(cur['AB'])} · {n(triangle_height(shape['pts'])[2])}"
        elif kind == "rect":
            sub = f"= {n(cur['dai'])} · {n(cur['rong'])}"
        else:
            sub = f"= π · {n(cur['r'])}²"
    return [*_FORMULAS[kind][key], sub, total]
