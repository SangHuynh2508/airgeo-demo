from types import SimpleNamespace

import pytest

from airgeo.config import Config
from airgeo.document.board import Board
from airgeo.geometry.measure import polygon_metrics
from airgeo.interaction.edit_panel import EditPanel
from airgeo.interaction.pointer import PointerEvent as E
from test_digits import DOT, FIVE, ONE, SEVEN, TWO

BOX = (110, 110, 1010, 610)


def _setup(scale=None, unit="cm", W=1280, H=720):
    board = Board()
    board.shapes.append({"kind": "triangle", "pts": [(490.0, 450.0), (790.0, 450.0), (640.0, 250.0)],
                         "raw": [], "id": 1, "locked": False})        # AB = 300 px, BC = CA = 250 px
    board.scale, board.unit = scale, unit
    panel = EditPanel(Config(), W, H)
    panel.open(board.shapes[0], "AB", board)
    return board, panel, SimpleNamespace(board=board, fit_box=BOX)


def _center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def _fill(panel, values):
    for f, v in values.items():
        panel.focus_field(f)
        for ch in v:
            panel.type(ch)


def _write(panel, ctl, digits, t=0.0):
    """Viết các chữ số (danh sách nét chuẩn hóa) lần lượt từ trái sang phải trong ô viết."""
    x0, y0, x1, y1 = panel.pad_rect
    h = (y1 - y0) * 0.7
    x = x0 + 20
    for strokes in digits:
        for s in strokes:
            pts = [(x + px * h, y0 + 0.15 * (y1 - y0) + py * h) for px, py in s]
            if strokes is DOT:
                pts = [(x, y0 + 0.8 * (y1 - y0)), (x + 3, y0 + 0.8 * (y1 - y0) + 2)]
            panel.on_event(E("down", pts[0], t), ctl)
            for p in pts[1:]:
                panel.on_event(E("move", p, t), ctl)
            panel.on_event(E("up", pts[-1], t), ctl)
        x += 0.25 * h if strokes is DOT else 0.8 * h


def _press(panel, ctl, rect):
    panel.on_event(E("down", _center(rect), 0.0), ctl)
    panel.on_event(E("up", _center(rect), 0.1), ctl)


def test_open_without_scale_is_empty_and_with_scale_prefilled():
    _, p, _ = _setup()
    assert p.values == {"AB": "", "BC": "", "CA": ""} and p.focus == "AB"
    _, p, _ = _setup(scale=50.0, unit="cm")
    assert p.values == {"AB": "6", "BC": "5", "CA": "5"}


def test_keyboard_typing_replaces_prefill_then_edits():
    _, p, _ = _setup(scale=50.0)
    for ch in ("1", "2", "<-", "5"):
        p.type(ch)
    assert p.values["AB"] == "15"


def test_writing_in_pad_fills_the_focused_field():
    _, p, ctl = _setup()
    _write(p, ctl, [ONE, TWO])
    assert p.values["AB"] == "12"
    p.focus_field("BC")
    _write(p, ctl, [SEVEN, DOT, FIVE])
    assert p.values["BC"] == "7.5" and p.values["AB"] == "12"


def test_writing_and_keyboard_mix_in_order():
    _, p, ctl = _setup()
    _write(p, ctl, [ONE])
    p.type("5")                                   # bàn phím máy tính gõ tiếp
    _write(p, ctl, [TWO])
    assert p.values["AB"] == "152"


def test_back_and_clear_buttons():
    _, p, ctl = _setup()
    _write(p, ctl, [ONE, TWO])
    _press(p, ctl, p.button_rects["back"])
    assert p.values["AB"] == "1"
    _press(p, ctl, p.button_rects["dot"])
    assert p.values["AB"] == "1."
    _press(p, ctl, p.button_rects["clear"])
    assert p.values["AB"] == ""


def test_ok_builds_3_4_5_and_enlarges_into_box():
    board, p, ctl = _setup()
    _fill(p, {"AB": "3", "BC": "4", "CA": "5"})
    _press(p, ctl, p.button_rects["ok"])
    assert not p.is_open
    s = board.shapes[0]
    m = polygon_metrics(s["pts"])
    assert m["angles"][1] == pytest.approx(90) and m["sides"][0] / board.scale == pytest.approx(3)
    xs, ys = [q[0] for q in s["pts"]], [q[1] for q in s["pts"]]
    assert min(xs) >= BOX[0] - 1e-6 and max(xs) <= BOX[2] + 1e-6 and max(ys) - min(ys) == pytest.approx(500)


def test_errors_keep_panel_open():
    board, p, ctl = _setup()
    p.submit(board, BOX)
    assert p.is_open and p.error == "Chưa nhập số nào"
    _fill(p, {"AB": "10", "BC": "3", "CA": "4"})
    p.submit(board, BOX)
    assert p.is_open and p.error.startswith("AB phải nhỏ hơn BC + CA")
    board, p, ctl = _setup(scale=50.0)
    _fill(p, {"BC": ""})
    p.focus_field("BC")
    _press(p, ctl, p.button_rects["clear"])
    p.submit(board, BOX)
    assert p.error == "Chưa nhập BC"


def test_scale_from_first_entered_field_keeps_ratio_of_blank_ones():
    board, p, ctl = _setup()
    _fill(p, {"AB": "6"})
    p.submit(board, BOX)
    m = polygon_metrics(board.shapes[0]["pts"])["sides"]
    assert m[0] / board.scale == pytest.approx(6) and m[1] / board.scale == pytest.approx(5)


def test_undo_after_ok_restores_shape_and_scale():
    board, p, ctl = _setup()
    before = list(board.shapes[0]["pts"])
    _fill(p, {"AB": "3", "BC": "4", "CA": "5"})
    p.submit(board, BOX)
    board.undo()
    assert board.shapes[0]["pts"] == before and board.scale is None


def test_submit_after_shape_deleted_closes_panel():
    board, p, _ = _setup()
    board.shapes = []
    assert not p.submit(board, BOX) and not p.is_open


def test_hit_regions_and_pad():
    _, p, _ = _setup()
    assert p.hit(_center(p.field_rects[1])) == ("field", "BC")
    assert p.hit(_center(p.button_rects["ok"])) == ("button", "ok")
    assert p.in_pad(_center(p.pad_rect)) and not p.in_pad(_center(p.button_rects["ok"]))


def test_line_panel_has_one_field():
    board = Board()
    board.shapes.append({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)], "raw": [], "id": 1, "locked": False})
    p = EditPanel(Config(), 1280, 720)
    p.open(board.shapes[0], "d", board)
    assert p.fields == ["d"] and len(p.field_rects) >= 1


@pytest.mark.parametrize("W,H", [(1280, 720), (640, 480)])
def test_panel_fits_frame(W, H):
    _, p, _ = _setup(W=W, H=H)
    for x0, y0, x1, y1 in [p.rect, p.pad_rect, *p.button_rects.values(), *p.field_rects]:
        assert 0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H
