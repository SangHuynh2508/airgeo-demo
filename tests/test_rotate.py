import math

import pytest

from airgeo.document.board import Board, make_shape
from airgeo.geometry.rotate import edge_angle, rotate_points, snap_delta


def _rect(cx, cy, w, h, deg):
    a = math.radians(deg)
    pts = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    return [(cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)) for x, y in pts]


def _stroke(pts, n=15):
    out = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        out += [(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n, 0.0) for k in range(n)]
    return out + [(*pts[0], 0.0)]


def test_snap_delta_picks_nearest_axis_edge_within_tolerance():
    assert snap_delta({"kind": "rect", "pts": _rect(400, 400, 200, 100, 5)}, 8) == pytest.approx(-5, abs=1e-6)
    assert snap_delta({"kind": "rect", "pts": _rect(400, 400, 200, 100, 20)}, 8) == 0
    tri = [(100.0, 400.0), (300.0, 400.0 + 200 * math.tan(math.radians(3))), (180.0, 250.0)]
    assert snap_delta({"kind": "triangle", "pts": tri}, 8) == pytest.approx(-3, abs=1e-6)
    assert snap_delta({"kind": "circle", "pts": [], "center": (0, 0), "radius": 5}, 8) == 0


def test_smart_straightens_slightly_tilted_rect_and_line_only():
    rect = make_shape(_stroke(_rect(400, 400, 300, 150, 6)), smart=True)
    assert rect["kind"] == "rect" and all(abs(edge_angle(a, b) % 90) < 0.5 or abs(edge_angle(a, b) % 90) > 89.5
                                          for a, b in zip(rect["pts"], rect["pts"][1:]))
    line = make_shape([(100 + 10 * i, 300 + 0.6 * i, 0.0) for i in range(21)], smart=True)
    assert line["kind"] == "line" and line["pts"][0][1] == pytest.approx(line["pts"][1][1])
    steep = make_shape([(100 + 10 * i, 300 + 6 * i, 0.0) for i in range(21)], smart=True)   # ~31°: giữ nguyên
    assert steep["pts"][1][1] - steep["pts"][0][1] > 100


def test_board_rotate_turns_points_raw_and_center_about_pivot():
    b = Board()
    b.shapes.append({"kind": "line", "pts": [(100.0, 0.0), (200.0, 0.0)], "raw": [(100.0, 0.0, 1.0)], "id": 1,
                     "locked": False})
    b.rotate(1, 90, (0.0, 0.0))
    (x0, y0), (x1, y1) = b.shapes[0]["pts"]
    assert (x0, y0, x1, y1) == pytest.approx((0, 100, 0, 200), abs=1e-9)
    assert b.shapes[0]["raw"][0] == pytest.approx((0, 100, 1.0), abs=1e-9)
    assert rotate_points([(1.0, 0.0)], 180, (0.0, 0.0))[0] == pytest.approx((-1, 0), abs=1e-9)


def test_rotated_shape_keeps_its_angle_across_smart_toggle():
    from airgeo.geometry.rotate import center
    b = Board()
    b.set_smart(True)
    s = b.add_stroke(_stroke(_rect(500, 400, 300, 150, 6)))      # tự làm thẳng về 0°
    b.rotate(s["id"], 30, center(s))
    b.set_smart(False)
    b.set_smart(True)
    a = edge_angle(*b.shapes[0]["pts"][:2]) % 90
    assert min(abs(a - 30), abs(a - 60)) < 1                    # vẫn nghiêng 30°, không thành 36°


def test_angle_left_just_outside_drag_snap_is_not_straightened_later():
    rect = make_shape(_stroke(_rect(400, 400, 300, 150, 9)), smart=True)   # 9° > ngưỡng hít 8°: giữ nguyên
    a = edge_angle(*rect["pts"][:2]) % 90
    assert min(abs(a - 9), abs(a - 81)) < 1.5
