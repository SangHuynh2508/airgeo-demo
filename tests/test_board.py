import pytest
import math

from airgeo.document.board import Board


def line_raw(y=300, x0=100, x1=300):
    return [(x, y, i / 30) for i, x in enumerate(range(x0, x1 + 1, 10))]


def square_raw(n=20):
    c = [(100, 100), (300, 100), (300, 300), (100, 300)]
    pts = []
    for (ax, ay), (bx, by) in zip(c, c[1:] + c[:1]):
        pts += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
    pts.append(c[0])
    return [(x, y, i / 30) for i, (x, y) in enumerate(pts)]


def test_add_stroke_gives_ids_and_last_info():
    b = Board()
    s1, s2 = b.add_stroke(line_raw()), b.add_stroke(line_raw(400))
    assert (s1["id"], s2["id"]) == (1, 2) and s1["kind"] == "line" and s1["locked"] is False
    assert b.last_info.startswith("line")


def test_undo_restores_add_remove_and_clear():
    b = Board()
    b.add_stroke(line_raw())
    s2 = b.add_stroke(line_raw(400))                 # thay hình 1
    b.remove(s2["id"])
    assert b.shapes == []
    b.undo()
    assert [x["id"] for x in b.shapes] == [2]
    b.clear()
    assert b.shapes == []
    b.undo()
    b.undo()
    assert [x["id"] for x in b.shapes] == [1]


def test_noop_operations_add_no_undo_step():
    b = Board()
    b.undo()                          # lịch sử rỗng: không lỗi
    b.clear()                         # chưa có hình: không lưu bước Undo
    b.add_stroke(line_raw())
    b.remove(999)                     # id không tồn tại: không lưu bước Undo
    b.undo()
    assert b.shapes == []             # 1 lần Undo đã gỡ đúng nét vừa vẽ


def test_translate_moves_points_raw_and_center():
    b = Board()
    s = b.add_stroke(line_raw())
    b.begin()
    b.translate(s["id"], 10, -5)
    assert b.shapes[0]["pts"][0] == (110, 295) and b.shapes[0]["raw"][0][:2] == (110, 295)
    b.shapes.append({"kind": "circle", "pts": [], "center": (0.0, 0.0), "radius": 5.0,
                     "raw": [(1, 2, 0.0)], "id": 9, "locked": False})
    b.translate(9, 10, -5)
    assert b.get(9)["center"] == (10.0, -5.0) and b.get(9)["raw"] == [(11, -3, 0.0)]
    b.translate(12345, 1, 1)          # id không còn: bỏ qua


def test_apply_edit_is_one_undo_step_including_scale():
    b = Board()
    s = b.add_stroke(line_raw())
    b.apply_edit(s["id"], dict(s, pts=[(0, 0), (1, 1)], locked=True), 50.0)
    assert b.scale == 50.0 and b.shapes[0]["locked"] is True
    b.undo()
    assert b.scale is None and b.shapes[0]["pts"] == s["pts"]


def test_redo_reapplies_undone_steps_and_new_action_clears_it():
    b = Board()
    assert b.redo() is False                          # chưa Undo gì: không có gì để làm lại
    s = b.add_stroke(line_raw())
    b.apply_edit(s["id"], dict(s, pts=[(0, 0), (1, 1)], locked=True), 50.0)
    b.undo()
    b.undo()
    assert b.shapes == [] and b.redo() is True and b.shapes[0]["pts"] == s["pts"] and b.scale is None
    assert b.redo() is True and b.scale == 50.0 and b.shapes[0]["locked"] is True
    assert b.redo() is False
    b.undo()
    b.begin()                                         # thao tác mới: nhánh làm lại cũ bỏ đi
    assert b.redo() is False


def test_undo_only_cancels_without_leaving_a_redo_step():
    b = Board()
    s = b.add_stroke(line_raw())
    pts = list(s["pts"])
    snap = b.begin()                                  # bắt đầu kéo
    b.translate(s["id"], 50, 0)
    assert b.undo(snap) is True and b.shapes[0]["pts"] == pts
    assert b.redo() is False                          # lần kéo bị hủy không được "làm lại"
    b.undo()
    assert b.shapes == [] and b.redo() is True and b.shapes[0]["pts"] == pts





def test_history_is_limited():
    b = Board(history_limit=3)
    for y in range(5):
        b.add_stroke(line_raw(100 + 50 * y))
    for _ in range(5):
        b.undo()
    assert [x["id"] for x in b.shapes] == [2]       # chỉ gỡ được 3 bước: về lúc vừa vẽ hình 2


def test_cycle_unit():
    b = Board()
    seen = []
    for _ in range(4):
        b.cycle_unit()
        seen.append(b.unit)
    assert seen == ["dm", "m", "mm", "cm"]


def test_shape_at_hits_edge_or_inside_and_misses_far():
    b = Board()
    b.shapes.append({"kind": "rect", "pts": [(100.0, 100.0), (500.0, 100.0), (500.0, 500.0), (100.0, 500.0)], "id": 1})
    assert b.shape_at((300, 300), 15)["id"] == 1  # giữa hình kín
    assert b.shape_at((510, 300), 15)["id"] == 1  # sát cạnh, ngoài hình
    assert b.shape_at((600, 600), 15) is None


def curve_raw():
    """Nét cong hở (nửa vòng tròn): không ra hình nào."""
    import math
    return [(300 + 100 * math.cos(math.pi * i / 30), 300 - 100 * math.sin(math.pi * i / 30), i / 30) for i in range(31)]


def test_unrecognized_stroke_is_not_kept_and_leaves_no_undo_step():
    b = Board()
    s = b.add_stroke(curve_raw())
    assert s["kind"] == "free" and "id" not in s and b.shapes == [] and not b._history


def test_stroke_is_always_recognized_and_tidied():
    b = Board()
    s = b.add_stroke([(x, y * 0.95, t) for x, y, t in square_raw()])   # 200 x 190 -> hình vuông
    assert s["kind"] == "rect" and abs(math.dist(*s["pts"][:2]) - math.dist(*s["pts"][1:3])) < 1e-6


def test_new_stroke_replaces_the_shape_and_undo_brings_it_back():
    b = Board()
    first = b.add_stroke(line_raw())
    b.scale = 40.0
    b.add_stroke(square_raw())
    assert [s["kind"] for s in b.shapes] == ["rect"] and b.scale is None
    b.undo()
    assert [s["id"] for s in b.shapes] == [first["id"]] and b.scale == 40.0


def test_board_fit_keeps_measurements_in_units():
    b = Board()
    s = b.add_stroke(line_raw())          # 200 px
    b.scale = 20.0                        # 10 cm
    b.fit(s["id"], (0, 0, 1000, 500))
    assert math.dist(*b.shapes[0]["pts"]) == pytest.approx(1000) and b.scale == pytest.approx(100)
