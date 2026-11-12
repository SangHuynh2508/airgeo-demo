import pytest

from airgeo.geometry.formulas import formula, triangle_height
from airgeo.geometry.units import trim

TRI = {"kind": "triangle", "pts": [(100.0, 400.0), (400.0, 400.0), (400.0, 0.0)]}   # AB 300, BC 400, CA 500
RECT = {"kind": "rect", "pts": [(100.0, 100.0), (600.0, 100.0), (600.0, 1000.0), (100.0, 1000.0)]}  # 500 x 900
CIRCLE = {"kind": "circle", "pts": [], "center": (0.0, 0.0), "radius": 300.0}


def test_trim():
    assert [trim(v) for v in (5.0, 2.4, 18.8496, 60000.0, 0.0)] == ["5", "2.4", "18.85", "60000", "0"]


def test_triangle_3_4_5_cm():
    assert formula(TRI, "perimeter", 100, "cm") == ["Chu vi", "P = AB + BC + CA", "= 3 + 4 + 5", "= 12 cm"]
    assert formula(TRI, "area", 100, "cm") == ["Diện tích", "S = ½ · AB · h", "= ½ · 3 · 4", "= 6 cm²"]


def test_triangle_without_scale_uses_px():
    assert formula(TRI, "perimeter", None, "cm")[2:] == ["= 300 + 400 + 500", "= 1200 px"]
    assert formula(TRI, "area", None, "cm")[3] == "= 60000 px²"


def test_rect_5_by_9_cm_and_mm():
    assert formula(RECT, "perimeter", 100, "cm") == ["Chu vi (a = dài, b = rộng)", "P = 2(a + b)", "= 2(5 + 9)",
                                                     "= 28 cm"]
    assert formula(RECT, "area", 100, "cm")[1:] == ["S = a · b", "= 5 · 9", "= 45 cm²"]
    assert formula(RECT, "area", 100, "mm")[2:] == ["= 50 · 90", "= 4500 mm²"]


def test_circle_r_3_cm():
    assert formula(CIRCLE, "perimeter", 100, "cm") == ["Chu vi", "C = 2πr", "= 2π · 3", "= 18.85 cm"]
    assert formula(CIRCLE, "area", 100, "cm")[1:] == ["S = πr²", "= π · 3²", "= 28.27 cm²"]


def test_no_formula_for_line_free_or_other_keys():
    assert formula({"kind": "line", "pts": [(0, 0), (10, 0)]}, "perimeter", None, "cm") == []
    assert formula({"kind": "free", "pts": [(0, 0), (10, 0)]}, "area", None, "cm") == []
    assert formula(TRI, "sides", 100, "cm") == []


def test_triangle_height_foot_is_perpendicular_on_line_ab():
    c, foot, h = triangle_height(TRI["pts"])
    assert c == (400.0, 0.0) and foot == pytest.approx((400.0, 400.0)) and h == pytest.approx(400.0)
    c, foot, h = triangle_height([(0.0, 0.0), (100.0, 0.0), (150.0, 80.0)])   # tam giác tù: chân ngoài AB
    assert foot == pytest.approx((150.0, 0.0)) and h == pytest.approx(80.0)
    assert triangle_height([(5.0, 5.0), (5.0, 5.0), (9.0, 9.0)])[2] == 0.0        # AB suy biến
