from airgeo.config import Config
from airgeo.interaction.controller import Controller
from airgeo.interaction.pointer import PointerEvent as E


def _ctl_with_line(stroke):
    c = Controller(Config(), 1280, 720)
    stroke(c, [(100, 300), (200, 300), (300, 300)])
    c.do("select")
    return c


def test_press_on_shape_selects_and_empty_deselects(stroke, press):
    c = _ctl_with_line(stroke)
    sel = c.tools["select"]
    press(c, (200, 310))
    assert sel.selected == c.board.shapes[0]["id"]
    press(c, (600, 600))
    assert sel.selected is None


def test_drag_moves_shape_and_its_raw_in_one_undo_step(stroke):
    c = _ctl_with_line(stroke)
    before = list(c.board.shapes[0]["pts"])
    stroke(c, [(200, 300), (205, 300), (250, 350), (260, 350)])   # quá 10 px -> kéo
    moved = c.board.shapes[0]
    assert moved["pts"][0] == (160, 350) and moved["raw"][0][:2] == (160, 350)
    c.do("undo")
    assert c.board.shapes[0]["pts"] == before


def test_small_wobble_selects_without_moving(stroke):
    c = _ctl_with_line(stroke)
    before = list(c.board.shapes[0]["pts"])
    stroke(c, [(200, 300), (206, 304), (203, 298)])               # rung tay < 10 px
    assert c.board.shapes[0]["pts"] == before and c.tools["select"].selected is not None


def test_switching_tool_mid_pinch_is_safe():
    c = Controller(Config(), 1280, 720)
    c.dispatch(E("down", (100, 300), 0.0))
    c.dispatch(E("move", (200, 300), 0.03))
    assert c.key(ord("g"), 0.05)                 # đổi sang Chọn khi đang vẽ: nét được giữ lại
    c.dispatch(E("move", (250, 300), 0.06))
    c.dispatch(E("up", (250, 300), 0.1))
    assert len(c.board.shapes) == 1 and c.tool == "select"


def test_leaving_select_clears_selection(stroke, press):
    c = _ctl_with_line(stroke)
    press(c, (200, 300))
    c.do("draw")
    assert c.tools["select"].selected is None


def test_pinch_near_middle_of_selected_line_grabs_it_not_label(press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)], "raw": [],
                           "id": 1, "locked": False})
    c.do("select")
    press(c, (200, 300))
    press(c, (200, 310))                          # 10 px cạnh trung điểm: vẫn là cầm đoạn thẳng
    assert not c.panel.is_open and c.tools["select"].selected == 1
