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
