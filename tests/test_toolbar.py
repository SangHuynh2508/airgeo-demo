import pytest

from airgeo.config import Config
from airgeo.interaction.toolbar import BUTTONS, Toolbar


def center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


@pytest.mark.parametrize("width", [1280, 640])
def test_buttons_fit_in_toolbar(width):
    tb = Toolbar(width, Config())
    assert list(tb.rects) == BUTTONS
    rects = list(tb.rects.values())
    assert all(0 <= x0 < x1 <= width and 0 <= y0 < y1 <= 70 for x0, y0, x1, y1 in rects)
    assert all(a[2] < b[0] for a, b in zip(rects, rects[1:]))       # không chồng nhau


def test_hit_and_contains():
    tb = Toolbar(1280, Config())
    assert tb.hit(center(tb.rects["undo"])) == "undo"
    assert tb.hit((5, 35)) is None                                  # khe giữa mép và nút đầu
    assert tb.contains((500, 69)) and not tb.contains((500, 70))
    assert tb.hit((500, 300)) is None


def test_press_returns_action():
    tb = Toolbar(1280, Config())
    assert tb.press(center(tb.rects["undo"]), 0.0) == "undo"


def test_clear_needs_second_press_within_window():
    tb = Toolbar(1280, Config())
    clear = center(tb.rects["clear"])
    assert tb.press(clear, 0.0) is None and tb.clear_armed(1.0)
    assert tb.press(clear, 1.5) == "clear" and not tb.clear_armed(1.6)


def test_clear_confirmation_expires():
    tb = Toolbar(1280, Config())
    clear = center(tb.rects["clear"])
    tb.press(clear, 0.0)
    assert tb.press(clear, 2.5) is None                             # quá 2 s: chỉ bật xác nhận lại
    assert tb.press(clear, 3.0) == "clear"


def test_other_button_cancels_clear_confirmation():
    tb = Toolbar(1280, Config())
    tb.press(center(tb.rects["clear"]), 0.0)
    assert tb.press(center(tb.rects["undo"]), 0.5) == "undo"
    assert tb.press(center(tb.rects["clear"]), 1.0) is None
