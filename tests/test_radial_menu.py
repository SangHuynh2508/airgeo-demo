import math

from airgeo.interaction.radial_menu import ITEM_R, RadialMenu


def _at(menu, action):
    return dict(menu.positions())[action]


def test_menu_near_edge_stays_on_screen():
    m = RadialMenu(1280, 720, top=60)
    m.open((5, 70), 0.0)
    assert all(ITEM_R <= x <= 1280 - ITEM_R and 60 + ITEM_R <= y <= 720 - ITEM_R for _, (x, y) in m.positions())


def test_press_item_returns_action_and_closes():
    m = RadialMenu(1280, 720, top=60)
    m.open((640, 400), 0.0)
    assert m.hit(_at(m, "unit")) == "unit" and m.hit((640, 400)) is None
    assert m.press(_at(m, "unit"), 1.0) == "unit" and not m.is_open


def test_clear_needs_two_presses_and_outside_or_close_closes():
    m = RadialMenu(1280, 720, top=60)
    m.open((640, 400), 0.0)
    assert m.press(_at(m, "clear"), 1.0) is None and m.is_open and m.clear_armed(1.5)
    assert m.press(_at(m, "clear"), 1.5) == "clear"
    m.open((640, 400), 2.0)
    assert m.press((100, 650), 2.5) is None and not m.is_open
    m.open((640, 400), 3.0)
    assert m.press(_at(m, "close"), 3.5) is None and not m.is_open


def test_menu_expires_after_timeout():
    m = RadialMenu(1280, 720, top=60)
    m.open((640, 400), 0.0)
    assert not m.expired(5.9) and m.expired(6.1)
    assert all(math.dist(p, m.center) > ITEM_R for _, p in m.positions())
