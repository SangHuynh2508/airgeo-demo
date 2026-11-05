import math

from airgeo.geometry.measure import measure, polygon_metrics


def test_square():
    sq = polygon_metrics([(0, 0), (100, 0), (100, 100), (0, 100)])
    assert sq["sides"] == [100] * 4 and sq["perimeter"] == 400 and sq["area"] == 10000
    assert all(abs(a - 90) < 1e-9 for a in sq["angles"])


def test_right_triangle_3_4_5():
    tri = polygon_metrics([(0, 0), (4, 0), (0, 3)])
    assert tri["sides"] == [4, 5, 3] and tri["area"] == 6
    assert abs(sum(tri["angles"]) - 180) < 1e-9


def test_circle_line_and_free():
    c = measure({"kind": "circle", "radius": 1})
    assert abs(c["area"] - math.pi) < 1e-12 and abs(c["perimeter"] - 2 * math.pi) < 1e-12
    assert measure({"kind": "line", "pts": [(0, 0), (3, 4)]}) == {"sides": [5.0]}
    assert measure({"kind": "free", "pts": []}) == {}


def test_repeated_vertex_does_not_divide_by_zero():
    m = polygon_metrics([(0, 0), (0, 0), (10, 0)])
    assert m["area"] == 0 and len(m["angles"]) == 3
