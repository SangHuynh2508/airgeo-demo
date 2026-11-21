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


def test_small_values_in_dm_and_m_do_not_round_to_zero():
    assert [trim(v) for v in (0.045, 0.0012, 0.00003)] == ["0.045", "0.0012", "0.00003"]
    rect = {"kind": "rect", "pts": [(0.0, 0.0), (300.0, 0.0), (300.0, 400.0), (0.0, 400.0)]}   # 3 x 4 cm
    assert formula(rect, "perimeter", 100, "m")[2:] == ["= 2(0.03 + 0.04)", "= 0.14 m"]
    assert formula(rect, "area", 100, "m")[3] == "= 0.0012 m²"


def test_without_scale_formula_has_no_px_numbers():
    assert formula(TRI, "perimeter", None, "cm") == ["Chu vi", "P = AB + BC + CA", "Nhập số đo cạnh để tính"]
    assert formula(TRI, "area", None, "cm")[2:] == ["Nhập số đo cạnh để tính"]


def _nums(line):
    import re
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", line)]


@pytest.mark.parametrize("pts", [[(0, 0), (512, 0), (130, 290)], [(0, 0), (377, 0), (188, 327)],
                                 [(10, 10), (433, 61), (97, 350)]])
def test_shown_numbers_add_up_to_the_shown_result(pts):
    tri = {"kind": "triangle", "pts": [tuple(map(float, p)) for p in pts]}
    for unit in ("cm", "mm", "dm"):
        *_, sub, total = formula(tri, "perimeter", 101.3, unit)
        assert trim(sum(_nums(sub))) == trim(_nums(total)[0]), (sub, total)
        *_, sub, total = formula(tri, "area", 101.3, unit)
        ab, h = _nums(sub)                                             # "= ½ · AB · h" (½ không khớp regex)
        assert trim(ab * h / 2) == trim(_nums(total)[0]), (sub, total)


def test_rounded_angles_always_sum_to_the_exact_total():
    from airgeo.geometry.units import round_sum
    shown = round_sum([54.62, 70.76, 54.62], 180)
    assert sum(shown) == 180 and all(abs(a - b) < 1 for a, b in zip(shown, [54.62, 70.76, 54.62]))


def test_isosceles_base_angles_are_shown_equal_and_still_sum_to_180():
    from airgeo.geometry.units import round_sum
    for vals in ([72.5424, 72.5424, 34.9152], [65.3757, 65.3757, 49.2486], [44.4153, 44.4153, 91.1694]):
        shown = round_sum(vals, 180)
        assert shown[0] == shown[1] and abs(sum(shown) - 180) < 1e-9, (vals, shown)
        assert all(abs(a - b) <= 0.5 for a, b in zip(shown, vals)), (vals, shown)
    assert round_sum([90.0, 53.1301, 36.8699], 180) == [90, 53, 37]      # bình thường vẫn là số nguyên


def test_trim_rounds_half_up_like_at_school():
    assert trim(0.5 * 1 * 2.17) == "1.09" and trim(2.675) == "2.68" and trim(1.005) == "1.01"
