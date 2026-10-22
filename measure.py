"""Đo đạc hình: độ dài cạnh (px), góc trong (độ), chu vi (px), diện tích (px^2)."""
import math


def polygon_metrics(pts):
    """pts: các đỉnh theo thứ tự. Diện tích theo công thức shoelace."""
    n = len(pts)
    sides = [math.dist(pts[i], pts[(i + 1) % n]) for i in range(n)]
    angles = []
    for i in range(n):
        (px, py), (cx, cy), (nx, ny) = pts[i - 1], pts[i], pts[(i + 1) % n]
        ax, ay, bx, by = px - cx, py - cy, nx - cx, ny - cy
        denom = math.hypot(ax, ay) * math.hypot(bx, by)
        cos = (ax * bx + ay * by) / denom if denom else 1.0
        angles.append(math.degrees(math.acos(max(-1.0, min(1.0, cos)))))
    area = abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))) / 2
    return {"sides": sides, "angles": angles, "perimeter": sum(sides), "area": area}


def measure(shape):
    kind = shape["kind"]
    if kind == "line":
        return {"sides": [math.dist(*shape["pts"])]}
    if kind == "circle":
        r = shape["radius"]
        return {"radius": r, "perimeter": 2 * math.pi * r, "area": math.pi * r * r}
    if kind in ("triangle", "rect"):
        return polygon_metrics(shape["pts"])
    return {}


if __name__ == "__main__":
    sq = polygon_metrics([(0, 0), (100, 0), (100, 100), (0, 100)])
    assert sq["sides"] == [100] * 4 and sq["perimeter"] == 400 and sq["area"] == 10000
    assert all(abs(a - 90) < 1e-9 for a in sq["angles"])
    tri = polygon_metrics([(0, 0), (4, 0), (0, 3)])
    assert tri["sides"] == [4, 5, 3] and tri["area"] == 6 and abs(sum(tri["angles"]) - 180) < 1e-9
    assert abs(measure({"kind": "circle", "radius": 1})["area"] - math.pi) < 1e-12
    print("measure OK")
