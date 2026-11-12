from airgeo.config import Config
from airgeo.interaction.controller import Controller

LINE = [(100, 300), (150, 300), (200, 300), (250, 300)]


def _ctl():
    return Controller(Config(), 1280, 720)


def test_pinch_in_canvas_draws_a_stroke(stroke):
    c = _ctl()
    stroke(c, LINE)
    assert len(c.board.shapes) == 1 and c.board.shapes[0]["kind"] == "free"


def test_pinch_started_on_toolbar_never_draws(stroke, button):
    c = _ctl()
    stroke(c, [button(c, "unit"), (300, 300), (400, 400)])   # chụm ở nút rồi kéo xuống vùng vẽ
    assert c.board.shapes == [] and c.tools["draw"].cur is None
    assert c.board.unit == "dm"                              # nút được bấm đúng 1 lần


def test_toolbar_buttons_run_actions(stroke, press, button):
    c = _ctl()
    stroke(c, LINE)
    press(c, button(c, "smart"))
    assert c.board.smart
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
    assert c.key(ord("s"), 0) and c.board.smart
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
    assert not c.panel.is_open and c.board.scale == pytest.approx(100)
    assert polygon_metrics(c.board.shapes[0]["pts"])["angles"][1] == pytest.approx(90)


def test_clear_closes_panel(press):
    c = _ctl_with_selected_triangle(press)
    press(c, label_anchors(c.board.shapes[0])["AB"])
    c.key(ord("c"), 0)
    assert not c.panel.is_open and c.board.shapes == []


def test_smart_toggle_under_open_panel_does_not_crash_on_ok(press):
    c = _ctl_with_selected_triangle(press)
    c.board.shapes[0]["raw"] = [(100 + 10 * i, 600, i / 30) for i in range(30)]   # nét gốc là đường thẳng
    press(c, label_anchors(c.board.shapes[0])["AB"])
    c.key(ord("s"), 0)                            # Smart nhận dạng lại: hình dưới bảng không còn là tam giác
    for code in b"3\r":
        c.key(code, 0)
    assert not c.panel.is_open and c.board.scale is None


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
    assert c.gesture_for((400, 400)) == "two_finger"


def test_recognized_shape_is_selected_and_tool_becomes_select(stroke):
    c = _ctl()
    c.board.set_smart(True)
    stroke(c, [(100 + 10 * i, 300) for i in range(21)])           # đoạn thẳng -> nhận dạng được
    assert c.board.shapes[0]["kind"] == "line"
    assert c.tool == "select" and c.tools["select"].selected == c.board.shapes[0]["id"]


def test_free_stroke_stays_in_draw_and_overlap_is_refused(stroke):
    c = _ctl()
    stroke(c, [(100, 300), (200, 300), (300, 300)])
    assert c.tool == "draw" and len(c.board.shapes) == 1
    stroke(c, [(200, 250), (200, 300), (200, 350)], t0=1.0)       # cắt nét cũ
    assert len(c.board.shapes) == 1 and c.message.startswith("Hinh moi de len") and c.message_until > 1.0


def test_switching_tool_mid_stroke_keeps_shape_without_auto_select():
    from airgeo.interaction.pointer import PointerEvent as E
    c = _ctl()
    c.board.set_smart(True)
    c.dispatch(E("down", (100, 300), 0.0))
    for i in range(1, 21):
        c.dispatch(E("move", (100 + 10 * i, 300), i * 0.03))
    c.do("erase")                                   # đổi công cụ giữa nét: giữ nét, không nhảy sang Chọn
    assert c.tool == "erase" and len(c.board.shapes) == 1 and c.tools["select"].selected is None
