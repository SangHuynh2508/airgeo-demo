import math

import pytest

from airgeo.geometry.measure import polygon_metrics
from airgeo.geometry.shapes import is_right, shape_name, tidy


def _rect(w, h, cx=400, cy=300):
    return {"kind": "rect", "pts": [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2),
                                    (cx - w / 2, cy + h / 2)]}


def _tri(*pts):
    return {"kind": "triangle", "pts": list(pts)}


def _m(s):
    return polygon_metrics(s["pts"])


def test_near_square_rect_becomes_square_keeping_center():
    s = tidy(_rect(200, 190))
    sides = _m(s)["sides"]
    assert sides[0] == pytest.approx(195) and sides[1] == pytest.approx(195)
    assert sum(p[0] for p in s["pts"]) / 4 == pytest.approx(400)
    assert shape_name(s) == "Hình vuông"


def test_clear_rectangle_is_kept():
    s = tidy(_rect(200, 150))
    assert _m(s)["sides"][:2] == pytest.approx([200, 150]) and shape_name(s) == "Hình chữ nhật"


def test_near_equilateral_becomes_equilateral():
    s = tidy(_tri((100, 300), (300, 300), (205, 130)))       # cạnh 200, ~195, ~201
    sides = _m(s)["sides"]
    assert max(sides) == pytest.approx(min(sides)) and shape_name(s) == "Tam giác đều"


def test_near_right_becomes_right():
    s = tidy(_tri((100, 400), (400, 400), (115, 200)))       # góc ở A ~86°
    assert max(_m(s)["angles"]) == pytest.approx(90, abs=0.01)
    assert shape_name(s) == "Tam giác vuông"


def test_near_right_isosceles():
    s = tidy(_tri((100, 400), (300, 400), (108, 210)))       # góc A ~87°, AB 200, AC ~190
    m = _m(s)
    assert m["angles"][0] == pytest.approx(90, abs=0.01) and m["sides"][0] == pytest.approx(m["sides"][2])
    assert shape_name(s) == "Tam giác vuông cân"


def test_near_isosceles_apex_moves_to_bisector():
    s = tidy(_tri((100, 400), (300, 400), (210, 150)))       # CA ~ CB, không vuông
    m = _m(s)
    assert m["sides"][1] == pytest.approx(m["sides"][2]) and shape_name(s) == "Tam giác cân"


def test_scalene_untouched():
    pts = [(100, 400), (400, 400), (150, 150)]       # góc 79°, 45°, 56°; cạnh 300, 255, 354
    s = tidy(_tri(*pts))
    assert s["pts"] == pts and shape_name(s) == "Tam giác thường"


def test_names_for_line_circle_and_right_angle_helper():
    assert shape_name({"kind": "line", "pts": [(0, 0), (1, 0)]}) == "Đoạn thẳng"
    assert shape_name({"kind": "circle", "pts": [], "center": (0, 0), "radius": 5}) == "Hình tròn"
    assert is_right(90.3) and not is_right(88)
    assert math.isclose(polygon_metrics(_rect(10, 20)["pts"])["angles"][0], 90)
