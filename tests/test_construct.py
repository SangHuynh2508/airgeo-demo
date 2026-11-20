import math

import pytest

from airgeo.geometry.construct import build, current_lengths, field_names, label_anchors
from airgeo.geometry.measure import polygon_metrics

def tri(c=(640.0, 250.0)):
    return {"kind": "triangle", "pts": [(490.0, 450.0), (790.0, 450.0), c], "raw": [(1, 2, 0.0)],
            "id": 7, "locked": False}


def centroid(pts):
    n = len(pts)
    return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)


def test_triangle_3_4_5_has_right_angle_at_B():
    m = polygon_metrics(build(tri(), {"AB": 300, "BC": 400, "CA": 500})["pts"])
    assert m["sides"] == pytest.approx([300, 400, 500])
    assert m["angles"][1] == pytest.approx(90)


@pytest.mark.parametrize("c", [(640.0, 250.0), (640.0, 600.0)])     # C phía trên / phía dưới AB
def test_triangle_keeps_centroid_direction_and_side(c):
    old = tri(c)
    (ax, ay), (bx, by), (cx, cy) = new = build(old, {"AB": 200, "BC": 180, "CA": 160})["pts"]
    assert centroid(new) == pytest.approx(centroid(old["pts"]))
    assert by == pytest.approx(ay) and bx > ax                      # AB vẫn nằm ngang, cùng hướng
    assert (cy < ay) == (c[1] < 450)                                # C vẫn cùng phía AB


def test_degenerate_triangle_is_rejected_with_message():
    with pytest.raises(ValueError, match=r"CA phải nhỏ hơn AB \+ BC = 3.00 cm"):
        build(tri(), {"AB": 50, "BC": 100, "CA": 150}, fmt=lambda px: f"{px / 50:.2f} cm")


def test_rect_keeps_center_and_rotation():
    a = math.radians(30)
    u, v = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    p0 = (640 - u[0] * 100 - v[0] * 50, 400 - u[1] * 100 - v[1] * 50)
    p1 = (p0[0] + u[0] * 200, p0[1] + u[1] * 200)
    p2 = (p1[0] + v[0] * 100, p1[1] + v[1] * 100)
    p3 = (p0[0] + v[0] * 100, p0[1] + v[1] * 100)
    new = build({"kind": "rect", "pts": [p0, p1, p2, p3], "raw": [], "id": 1}, {"dai": 300, "rong": 150})["pts"]
    assert polygon_metrics(new)["sides"] == pytest.approx([300, 150, 300, 150])
    assert centroid(new) == pytest.approx((640, 400))
    assert math.degrees(math.atan2(new[1][1] - new[0][1], new[1][0] - new[0][0])) == pytest.approx(30)


def test_line_keeps_midpoint_and_direction():
    new = build({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)], "raw": [], "id": 1},
                {"d": 100})["pts"]
    assert new[0] == pytest.approx((150, 300)) and new[1] == pytest.approx((250, 300))


def test_circle_keeps_center():
    new = build({"kind": "circle", "pts": [], "center": (640.0, 400.0), "radius": 50.0, "raw": [], "id": 1},
                {"r": 120})
    assert new["center"] == (640.0, 400.0) and new["radius"] == 120


def test_result_keeps_id():
    new = build(tri(), {"AB": 300, "BC": 250, "CA": 250})
    assert new["id"] == 7


def test_fields_and_current_lengths():
    assert field_names("triangle") == ["AB", "BC", "CA"] and field_names("rect") == ["dai", "rong"]
    assert field_names("free") == []
    assert current_lengths(tri()) == pytest.approx({"AB": 300, "BC": 250, "CA": 250})


def test_label_anchors_sit_outside_the_triangle():
    t = tri()
    pts, (cx, cy) = t["pts"], centroid(t["pts"])
    for i, (x, y) in enumerate(label_anchors(t).values()):
        a, b = pts[i], pts[(i + 1) % 3]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        assert math.dist((x, y), (cx, cy)) > math.dist(mid, (cx, cy))
    assert label_anchors({"kind": "free", "pts": [(0, 0), (1, 1)]}) == {}


def test_free_stroke_cannot_be_rebuilt():
    with pytest.raises(ValueError):
        build({"kind": "free", "pts": [(0, 0), (1, 1)], "raw": [], "id": 1}, {})


def test_fit_scales_about_bbox_and_centers_in_box():
    from airgeo.geometry.construct import fit
    rect = {"kind": "rect", "pts": [(0, 0), (100, 0), (100, 50), (0, 50)]}
    new, k = fit(rect, (100, 100, 1000, 600))
    assert k == pytest.approx(9) and new["pts"][0] == pytest.approx((100, 125)) and new["pts"][2] == pytest.approx((1000, 575))
    line, k = fit({"kind": "line", "pts": [(0, 10), (50, 10)], "raw": []}, (0, 0, 500, 300))   # khung cao 0
    assert k == pytest.approx(10) and line["pts"] == [pytest.approx((0, 150)), pytest.approx((500, 150))]
    circle, k = fit({"kind": "circle", "pts": [], "center": (5, 5), "radius": 5, "raw": []}, (0, 0, 400, 200))
    assert circle["radius"] == pytest.approx(100) and circle["center"] == pytest.approx((200, 100))
