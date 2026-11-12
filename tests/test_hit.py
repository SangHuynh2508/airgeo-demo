from airgeo.geometry.hit import distance_to_shape

LINE = {"kind": "line", "pts": [(100, 100), (300, 100)]}


def test_line_distance_inside_and_outside_hit_radius():
    assert distance_to_shape((200, 114), LINE) == 14
    assert distance_to_shape((200, 116), LINE) == 16


def test_beyond_segment_end_measures_to_endpoint():
    assert distance_to_shape((303, 104), LINE) == 5


def test_closed_shape_includes_closing_side():
    tri = {"kind": "triangle", "pts": [(0, 0), (100, 0), (0, 100)]}
    assert distance_to_shape((-5, 50), tri) == 5          # cạnh CA (đóng hình)


def test_open_free_stroke_is_not_closed():
    free = {"kind": "free", "pts": [(0, 0), (100, 0), (100, 100)]}
    assert distance_to_shape((50, 50), free) == 50        # nếu coi là kín thì sẽ ra 0


def test_circle_distance_is_to_the_rim():
    c = {"kind": "circle", "pts": [], "center": (0, 0), "radius": 50}
    assert distance_to_shape((60, 0), c) == 10 and distance_to_shape((0, 0), c) == 50


def test_zero_length_segment():
    assert distance_to_shape((13, 14), {"kind": "free", "pts": [(10, 10), (10, 10)]}) == 5


def test_contains_closed_shapes_only():
    from airgeo.geometry.hit import contains
    tri = {"kind": "triangle", "pts": [(0, 0), (100, 0), (0, 100)]}
    assert contains((20, 20), tri) and not contains((80, 80), tri)
    assert contains((10, 0), {"kind": "circle", "pts": [], "center": (0, 0), "radius": 50})
    assert not contains((50, 0), LINE) and not contains((50, 50), {"kind": "free", "pts": [(0, 0), (100, 100)]})


def test_overlaps_detects_crossing_inside_and_touching_only():
    from airgeo.geometry.hit import overlaps
    rect = {"kind": "rect", "pts": [(100, 100), (300, 100), (300, 300), (100, 300)]}
    far = {"kind": "line", "pts": [(400, 100), (400, 300)]}
    cross = {"kind": "line", "pts": [(50, 200), (350, 210)]}
    inner = {"kind": "circle", "pts": [], "center": (200, 200), "radius": 40}
    touch = {"kind": "line", "pts": [(302, 120), (302, 280)]}
    near = {"kind": "line", "pts": [(320, 120), (320, 280)]}
    big = {"kind": "circle", "pts": [], "center": (650, 200), "radius": 250}   # cắt đoạn far tại x = 400
    assert not overlaps(rect, far) and overlaps(rect, cross) and overlaps(cross, rect)
    assert overlaps(rect, inner) and overlaps(inner, rect) and overlaps(rect, touch) and not overlaps(rect, near)
    assert overlaps(big, far) and overlaps(far, big)
