import math

import numpy as np

from airgeo.geometry.recognize import recognize

rng = np.random.default_rng(0)


def stroke(xy, noise=1.5):
    xy = np.asarray(xy, dtype=float) + rng.normal(0, noise, (len(xy), 2))
    return [(x, y, i / 30) for i, (x, y) in enumerate(xy)]


def polygon(corners, per_side=20):
    corners = np.asarray(corners, dtype=float)
    out = []
    for a, b in zip(corners, np.roll(corners, -1, axis=0)):
        out += [a + (b - a) * k / per_side for k in range(per_side)]
    return out + [corners[0]]


def test_circle_center_and_radius():
    ang = np.linspace(0, 2 * np.pi, 80)
    r = recognize(stroke(np.c_[300 + 100 * np.cos(ang), 300 + 100 * np.sin(ang)]))
    assert r["kind"] == "circle"
    assert abs(r["radius"] - 100) < 5 and math.dist(r["center"], (300, 300)) < 5


def test_straight_stroke_is_line_between_endpoints():
    r = recognize(stroke(np.c_[np.linspace(0, 300, 40), np.linspace(0, 100, 40)]))
    assert r["kind"] == "line" and len(r["pts"]) == 2


def test_rectangle():
    assert recognize(stroke(polygon([(100, 100), (400, 100), (400, 300), (100, 300)])))["kind"] == "rect"


def test_triangle():
    r = recognize(stroke(polygon([(100, 300), (400, 300), (250, 50)])))
    assert r["kind"] == "triangle" and len(r["pts"]) == 3


def test_open_curve_stays_free():
    xy = np.c_[np.linspace(0, 300, 40), 100 * np.sin(np.linspace(0, 3, 40))]
    assert recognize(stroke(xy))["kind"] == "free"


def test_info_explains_decision():
    r = recognize(stroke(polygon([(100, 100), (400, 100), (400, 300), (100, 300)])))
    assert set(r["info"]) == {"ho", "tron", "dinh"} and r["info"]["dinh"] == 4


def test_degenerate_strokes_are_free():
    assert recognize([(50, 50, i / 30) for i in range(20)])["kind"] == "free"   # mọi điểm trùng nhau
    assert recognize([(0, 0, 0), (100, 0, 0.03)])["kind"] == "free"            # quá ít điểm
    assert recognize([])["kind"] == "free"


def test_doubled_back_stroke_without_area_is_free():
    # Đi tới rồi quay lại đúng đường cũ: nét "kín" nhưng không bao diện tích -> không phải hình chữ nhật
    pts = [(100, 300), (400, 300), (250, 50), (400, 300), (100, 300)]
    xy = []
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        xy += [(ax + (bx - ax) * k / 20, ay + (by - ay) * k / 20) for k in range(20)]
    xy.append(pts[-1])
    assert recognize([(x, y, i / 30) for i, (x, y) in enumerate(xy)])["kind"] == "free"
