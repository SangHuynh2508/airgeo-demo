from airgeo.config import Config
from airgeo.interaction.controller import Controller

LINE = [(100 + 10 * i, 300) for i in range(16)]   # đoạn thẳng


def _ctl():
    return Controller(Config(), 1280, 720)


def test_pinch_in_canvas_draws_a_stroke(stroke):
    c = _ctl()
    stroke(c, LINE)
    assert len(c.board.shapes) == 1 and c.board.shapes[0]["kind"] == "line"


def test_pinch_started_on_toolbar_never_draws(stroke, button):
    c = _ctl()
    stroke(c, [button(c, "unit"), (300, 300), (400, 400)])   # chụm ở nút rồi kéo xuống vùng vẽ
    assert c.board.shapes == [] and c.tools["draw"].cur is None
    assert c.board.unit == "dm"                              # nút được bấm đúng 1 lần


def test_toolbar_buttons_run_actions(stroke, press, button):
    c = _ctl()
    stroke(c, LINE)
    press(c, button(c, "undo"))
    assert c.board.shapes == []


def test_clear_button_needs_two_presses(stroke, press, button):
    c = _ctl()
    stroke(c, LINE)
    press(c, button(c, "clear"), t=5.0)
    assert len(c.board.shapes) == 1
    press(c, button(c, "clear"), t=6.0)
    assert c.board.shapes == []


def test_keys_call_the_same_actions(stroke):
    c = _ctl()
    stroke(c, LINE)
    assert c.key(ord("n"), 0) and c.board.unit == "dm"
    assert c.key(ord("u"), 0) and c.board.shapes == []
    assert not c.key(ord("q"), 0) and not c.key(255, 0) and not c.key(ord("0"), 0)


def test_key_c_clears_without_confirmation(stroke):
    c = _ctl()
    stroke(c, LINE)
    assert c.key(ord("c"), 0) and c.board.shapes == []


import pytest  # noqa: E402

from airgeo.geometry.construct import label_anchors  # noqa: E402
from airgeo.geometry.measure import polygon_metrics  # noqa: E402


def _ctl_with_selected_triangle(press):
    c = _ctl()
    c.board.shapes.append({"kind": "triangle", "pts": [(490.0, 450.0), (790.0, 450.0), (640.0, 250.0)],
                           "raw": [], "id": 1, "locked": False})
    c.do("select")
    press(c, (640, 450))                         # chụm trúng cạnh AB -> chọn tam giác
    return c


def test_pressing_side_label_opens_panel(press):
    c = _ctl_with_selected_triangle(press)
    press(c, label_anchors(c.board.shapes[0])["BC"])
    assert c.panel.is_open and c.panel.focus == "BC"


def test_open_panel_owns_pinches_and_keys(press, stroke):
    c = _ctl_with_selected_triangle(press)
    press(c, label_anchors(c.board.shapes[0])["AB"])
    c.set_tool("draw")
    stroke(c, [(50, 650), (100, 650), (150, 650)])      # bảng đang mở: chụm không vẽ
    assert len(c.board.shapes) == 1
    assert c.key(ord("0"), 0) and c.panel.values["AB"] == "0"
    assert c.key(27, 0) and not c.panel.is_open          # Esc đóng bảng, không thoát app
    assert not c.key(ord("0"), 0)                         # bảng đóng: phím 0 để app đổi bộ lọc


def test_type_3_4_5_gives_right_triangle(press):
    c = _ctl_with_selected_triangle(press)
    press(c, label_anchors(c.board.shapes[0])["AB"])
    for code in b"3\t4\t5\r":
        c.key(code, 0)
    m = polygon_metrics(c.board.shapes[0]["pts"])
    assert not c.panel.is_open and m["sides"][0] / c.board.scale == pytest.approx(3)
    assert m["angles"][1] == pytest.approx(90)


def test_clear_closes_panel(press):
    c = _ctl_with_selected_triangle(press)
    press(c, label_anchors(c.board.shapes[0])["AB"])
    c.key(ord("c"), 0)
    assert not c.panel.is_open and c.board.shapes == []




def test_gesture_depends_on_tool_and_place(button):
    c = _ctl()
    assert c.gesture_for((400, 400)) == "pinch" and c.gesture_for(None) == "pinch"   # vẽ: chụm
    assert c.gesture_for(button(c, "undo")) == "two_finger"                          # thanh nút: 2 ngón
    c.do("select")
    assert c.gesture_for((400, 400)) == "two_finger"
    c.do("erase")
    assert c.gesture_for((400, 400)) == "two_finger"
    c.do("draw")
    c.panel.is_open = True
    assert c.gesture_for(c.panel.button_rects["ok"][:2]) == "two_finger"
    x0, y0, x1, y1 = c.panel.pad_rect
    assert c.gesture_for(((x0 + x1) / 2, (y0 + y1) / 2)) == "pinch"           # ô viết số: chụm như vẽ


def test_recognized_shape_is_selected_and_tool_becomes_select(stroke):
    c = _ctl()
    stroke(c, [(100 + 10 * i, 300) for i in range(21)])           # đoạn thẳng -> nhận dạng được
    assert c.board.shapes[0]["kind"] == "line"
    assert c.tool == "select" and c.tools["select"].selected == c.board.shapes[0]["id"]


def test_switching_tool_mid_stroke_keeps_shape_without_auto_select():
    from airgeo.interaction.pointer import PointerEvent as E
    c = _ctl()
    c.dispatch(E("down", (100, 300), 0.0))
    for i in range(1, 21):
        c.dispatch(E("move", (100 + 10 * i, 300), i * 0.03))
    c.do("erase")                                   # đổi công cụ giữa nét: giữ nét, không nhảy sang Chọn
    assert c.tool == "erase" and len(c.board.shapes) == 1 and c.tools["select"].selected is None


def _hold(c, pose, t0, secs, center=(640, 400)):
    for i in range(int(round(secs * 10)) + 1):
        c.on_pose(pose, center, t0 + i / 10)


def test_three_finger_pose_switches_to_draw_with_message(stroke):
    c = _ctl()
    c.do("select")
    _hold(c, "three", 0.0, 0.5)
    assert c.tool == "draw" and c.message == "Vẽ"


def test_fist_pose_undoes_one_step(stroke):
    c = _ctl()
    stroke(c, LINE)
    c.do("draw")
    stroke(c, [(p[0], 500) for p in LINE], t0=1.0)
    _hold(c, "palm", 1.6, 0.2)                          # xòe tay rồi nắm lại
    _hold(c, "fist", 2.0, 2.0)                          # giữ lâu vẫn chỉ Undo 1 bước
    assert len(c.board.shapes) == 1 and c.message == "Đã hoàn tác"


def test_poses_ignored_while_panel_open_or_pressing(stroke):
    from airgeo.interaction.pointer import PointerEvent as E
    c = _ctl()
    c.dispatch(E("down", (300, 300), 0.0))              # đang chụm vẽ
    _hold(c, "rock", 0.0, 1.0)
    assert c.tool == "draw"
    c.dispatch(E("up", (310, 300), 1.0))
    c.board.shapes.append({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)], "raw": [], "id": 9, "locked": False})
    c.panel.open(c.board.shapes[-1], "AB", c.board)
    _hold(c, "rock", 2.0, 1.0)
    assert c.tool == "draw"


def test_long_palm_opens_menu_which_takes_presses(press):
    c = _ctl()
    _hold(c, "palm", 0.0, 1.5)
    assert c.tool == "select" and c.menu.is_open and c.gesture_for((640, 400)) == "two_finger"
    unit = dict(c.menu.positions())["unit"]
    press(c, unit, 2.0)
    assert c.board.unit == "dm" and not c.menu.is_open and c.board.shapes == []


def test_palm_again_closes_menu_without_reopening():
    c = _ctl()
    _hold(c, "palm", 0.0, 1.5)
    c.on_pose(None, (640, 400), 1.8)
    c.on_pose(None, (640, 400), 2.0)
    _hold(c, "palm", 2.1, 2.0)
    assert not c.menu.is_open


def test_menu_closes_after_timeout():
    c = _ctl()
    _hold(c, "palm", 0.0, 1.5)
    c.on_pose(None, (640, 400), 8.0)
    assert not c.menu.is_open


def test_relaxed_fist_right_after_drawing_does_not_undo(stroke):
    c = _ctl()
    stroke(c, [(100 + 10 * i, 300) for i in range(21)], t0=0.0)   # nhả tay lúc ~0.6 s
    _hold(c, "fist", 0.7, 3.0)                                     # tay khép hờ suốt lúc đang nói
    assert len(c.board.shapes) == 1
    _hold(c, "palm", 3.8, 0.2)                                     # xòe tay rồi nắm lại: Undo có chủ đích
    _hold(c, "fist", 4.1, 0.8)
    assert c.board.shapes == []


def test_menu_opens_with_close_item_above_the_hand():
    from airgeo.interaction.radial_menu import ITEMS
    assert ITEMS[0] == "close"          # đầu ngón trỏ nằm trên tâm bàn tay: áp 2 ngón ngay chỉ đóng menu


def test_scribble_is_deleted_with_message_and_shape_name_is_announced(stroke):
    import math
    c = _ctl()
    stroke(c, [(300 + 100 * math.cos(math.pi * i / 30), 300 - 100 * math.sin(math.pi * i / 30)) for i in range(31)])
    assert c.board.shapes == [] and c.message == "Không nhận ra hình – vẽ lại" and c.tool == "draw"
    stroke(c, [(100 + 10 * i, 500) for i in range(21)], t0=2.0)
    assert c.message == "Đoạn thẳng" and c.tool == "select"


def test_smart_is_gone():
    c = _ctl()
    assert not c.key(ord("s"), 0) and not hasattr(c.board, "smart")


def test_toolbar_hidden_by_default_and_top_edge_belongs_to_canvas(stroke):
    c = _ctl()
    assert not c.toolbar.visible and c.gesture_for((300, 20)) == "pinch"
    stroke(c, [(100 + 10 * i, 25) for i in range(16)])          # vẽ sát mép trên: không bị nút nuốt
    assert len(c.board.shapes) == 1


def test_toolbar_reopens_by_key_or_menu_item():
    from airgeo.interaction.pointer import PointerEvent as E
    c = _ctl()
    assert c.key(ord("t"), 0) and c.toolbar.visible
    c.key(ord("t"), 0)
    c.menu.open((640, 400), 0.0)
    pos = dict(c.menu.positions())["bar"]
    c.dispatch(E("down", pos, 0.1))
    c.dispatch(E("up", pos, 0.2))
    assert c.toolbar.visible and not c.menu.is_open


def test_edit_bounds_follow_toolbar_visibility():
    c = _ctl()
    assert c.bounds[1] == 0                  # dải ẩn: hình sát mép trên vẫn trong vùng vẽ
    c.key(ord("t"), 0)
    assert c.bounds[1] == c.toolbar.height


def test_drawn_shape_is_centered_and_enlarged(stroke):
    c = _ctl()
    sq = [(100 + 5 * i, 100) for i in range(20)] + [(200, 100 + 5 * i) for i in range(20)] + \
         [(200 - 5 * i, 200) for i in range(20)] + [(100, 200 - 5 * i) for i in range(21)]
    stroke(c, sq)
    x0, y0, x1, y1 = c.fit_box
    xs, ys = [p[0] for p in c.board.shapes[0]["pts"]], [p[1] for p in c.board.shapes[0]["pts"]]
    assert max(ys) - min(ys) == pytest.approx(y1 - y0) and (min(xs) + max(xs)) / 2 == pytest.approx((x0 + x1) / 2)
    assert y1 - y0 >= 0.65 * 720


def test_undo_with_nothing_left_says_so():
    c = _ctl()
    assert c.board.undo() is False
    _hold(c, "palm", 0.0, 0.2)
    _hold(c, "fist", 0.5, 1.0)
    assert c.message == "Không còn gì để hoàn tác"
