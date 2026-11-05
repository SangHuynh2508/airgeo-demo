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
    assert (s1["id"], s2["id"]) == (1, 2) and s1["kind"] == "free" and s1["locked"] is False
    assert b.last_info == "free"


def test_undo_restores_add_remove_and_clear():
    b = Board()
    s = b.add_stroke(line_raw())
    b.add_stroke(line_raw(400))
    b.remove(s["id"])
    assert [x["id"] for x in b.shapes] == [2]
    b.clear()
    assert b.shapes == []
    b.undo()
    assert [x["id"] for x in b.shapes] == [2]
    b.undo()
    assert [x["id"] for x in b.shapes] == [1, 2]
    b.undo()
    b.undo()
    assert b.shapes == []


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


def test_set_smart_rerecognizes_only_unlocked():
    b = Board()
    b.add_stroke(square_raw())
    b.add_stroke(square_raw())
    b.shapes[1]["locked"] = True      # hình đã sửa số đo
    b.set_smart(True)
    assert [s["kind"] for s in b.shapes] == ["rect", "free"] and [s["id"] for s in b.shapes] == [1, 2]
    b.set_smart(False)
    assert b.shapes[0]["kind"] == "free"


def test_undo_after_smart_toggle_follows_current_mode():
    b = Board()
    b.add_stroke(square_raw())
    b.add_stroke(line_raw(400))
    b.set_smart(True)
    b.undo()                          # bản sao được lưu lúc Smart tắt
    assert len(b.shapes) == 1 and b.shapes[0]["kind"] == "rect"


def test_history_is_limited():
    b = Board(history_limit=3)
    for y in range(5):
        b.add_stroke(line_raw(100 + 50 * y))
    for _ in range(5):
        b.undo()
    assert len(b.shapes) == 2


def test_cycle_unit():
    b = Board()
    seen = []
    for _ in range(4):
        b.cycle_unit()
        seen.append(b.unit)
    assert seen == ["dm", "m", "mm", "cm"]


def test_shape_at_prefers_topmost_and_misses_far():
    b = Board()
    b.add_stroke(line_raw(300))
    top = b.add_stroke([(200, 250 + 10 * i, i / 30) for i in range(11)])
    assert b.shape_at((200, 300), 15)["id"] == top["id"]
    assert b.shape_at((120, 310), 15)["id"] == 1
    assert b.shape_at((600, 600), 15) is None
