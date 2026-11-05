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


TRI = {"kind": "triangle", "pts": [(490.0, 450.0), (790.0, 450.0), (640.0, 250.0)], "raw": [],
       "id": 1, "locked": False}


def _center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def test_measure_menu_depends_on_kind():
    from airgeo.tools.select import SelectTool
    tool = SelectTool(Config(), 1280)
    keys = lambda kind, **extra: [k for k, _ in tool.menu({"kind": kind, "pts": [], **extra})]  # noqa: E731
    assert keys("triangle") == ["sides", "angles", "perimeter", "area"] == keys("rect")
    assert keys("circle") == ["radius", "perimeter", "area"]
    assert keys("line") == ["sides"] and keys("free") == []
    assert all(1280 - 170 <= r[0] and r[2] <= 1280 and r[1] >= 70 for _, r in tool.menu(TRI))


def test_measures_show_only_after_pressing_their_button(press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(TRI))
    c.do("select")
    sel = c.tools["select"]
    press(c, (640, 450))                          # chọn tam giác: chưa tính gì
    assert sel.selected == 1 and sel.show == set()
    angles = dict(sel.menu(c.board.shapes[0]))["angles"]
    press(c, _center(angles))
    assert sel.show == {"angles"} and sel.selected == 1
    press(c, _center(angles))                     # bấm lần nữa: ẩn
    assert sel.show == set()


def test_changing_selection_clears_measures(press, stroke):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(TRI))
    c.do("select")
    sel = c.tools["select"]
    press(c, (640, 450))
    press(c, _center(dict(sel.menu(c.board.shapes[0]))["area"]))
    stroke(c, [(640, 450), (660, 470), (680, 490)])   # kéo chính hình đó: vẫn giữ
    assert sel.show == {"area"}
    press(c, (100, 650))                          # bấm chỗ trống: bỏ chọn, tắt hết
    assert sel.selected is None and sel.show == set()


def test_press_inside_triangle_grabs_and_drags_it(stroke):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(TRI))
    c.do("select")
    stroke(c, [(640, 380), (660, 380), (690, 400)])   # giữa tam giác, không chạm cạnh
    assert c.tools["select"].selected == 1 and c.board.shapes[0]["pts"][0] == (540.0, 470.0)


def test_stray_press_while_moving_to_menu_keeps_selection(stroke, press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(TRI))
    c.do("select")
    sel = c.tools["select"]
    press(c, (640, 380))                                       # chọn tam giác -> cột "Tinh:" hiện
    stroke(c, [(850, 400), (950, 300), (1100, 200)], t0=1.0)   # 2 ngón vô tình áp lúc đang di tay
    assert sel.selected == 1
    press(c, (900, 600), t=1.5)                                # chạm rồi nhả tại chỗ trống: vẫn bỏ chọn được
    assert sel.selected is None
    press(c, (640, 380), t=1.8)
    assert sel.selected == 1
    _, (x0, y0, x1, y1) = sel.menu(c.board.get(1))[0]
    press(c, ((x0 + x1) / 2, (y0 + y1) / 2), t=2.0)
    assert sel.show == {"sides"}
