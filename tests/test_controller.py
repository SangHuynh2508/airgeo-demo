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
