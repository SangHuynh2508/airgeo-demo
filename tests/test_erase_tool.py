from airgeo.config import Config
from airgeo.interaction.controller import Controller
from airgeo.interaction.pointer import PointerEvent as E


def _two_lines(stroke):
    c = Controller(Config(), 1280, 720)
    stroke(c, [(100, 300), (200, 300), (300, 300)])     # ngang
    stroke(c, [(200, 250), (200, 300), (200, 350)])     # dọc, vẽ sau -> nằm trên
    c.do("erase")
    return c


def test_hover_marks_topmost_shape_under_cursor(stroke):
    c = _two_lines(stroke)
    c.dispatch(E("hover", (200, 300), 1.0))
    assert c.tools["erase"].hovered == c.board.shapes[1]["id"]
    c.dispatch(E("hover", (600, 600), 1.1))
    assert c.tools["erase"].hovered is None


def test_press_removes_only_shape_under_cursor(stroke, press):
    c = _two_lines(stroke)
    keep = c.board.shapes[1]["id"]
    press(c, (120, 300))                               # chỉ trúng đường ngang
    assert [s["id"] for s in c.board.shapes] == [keep]


def test_undo_restores_erased_shape(stroke, press):
    c = _two_lines(stroke)
    press(c, (120, 300))
    c.do("undo")
    assert len(c.board.shapes) == 2


def test_press_on_empty_area_does_nothing(stroke, press):
    c = _two_lines(stroke)
    press(c, (900, 600))
    assert len(c.board.shapes) == 2
