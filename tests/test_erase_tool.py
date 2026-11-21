from helpers import place_tri
from airgeo.config import Config
from airgeo.interaction.controller import Controller
from airgeo.interaction.pointer import PointerEvent as E


def _one_line(stroke):
    c = Controller(Config(), 1280, 720)
    place_tri(c, 300)
    c.do("erase")
    return c


def test_hover_marks_shape_under_cursor(stroke):
    c = _one_line(stroke)
    c.dispatch(E("hover", (200, 300), 1.0))
    assert c.tools["erase"].hovered == c.board.shapes[0]["id"]
    c.dispatch(E("hover", (600, 600), 1.1))
    assert c.tools["erase"].hovered is None


def test_press_removes_shape_under_cursor(stroke, press):
    c = _one_line(stroke)
    press(c, (120, 300))
    assert c.board.shapes == []


def test_undo_restores_erased_shape(stroke, press):
    c = _one_line(stroke)
    press(c, (120, 300))
    c.do("undo")
    assert len(c.board.shapes) == 1


def test_press_on_empty_area_does_nothing(stroke, press):
    c = _one_line(stroke)
    press(c, (900, 600))
    assert len(c.board.shapes) == 1
