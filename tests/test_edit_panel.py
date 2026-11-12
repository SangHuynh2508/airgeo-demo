from types import SimpleNamespace

import pytest

from airgeo.config import Config
from airgeo.document.board import Board
from airgeo.geometry.measure import polygon_metrics
from airgeo.interaction.edit_panel import EditPanel
from airgeo.interaction.pointer import PointerEvent as E

BOUNDS = (0, 70, 1280, 720)


def _setup(scale=None, unit="cm"):
    board = Board()
    board.shapes.append({"kind": "triangle", "pts": [(490.0, 450.0), (790.0, 450.0), (640.0, 250.0)],
                         "raw": [], "id": 1, "locked": False})        # AB = 300 px, BC = CA = 250 px
    board.scale, board.unit = scale, unit
    panel = EditPanel(Config(), 1280, 720)
    panel.open(board.shapes[0], "AB", board)
    return board, panel, SimpleNamespace(board=board, bounds=BOUNDS)


def _center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def _fill(panel, values):
    for f, v in values.items():
        panel.focus_field(f)
        for ch in v:
            panel.type(ch)


def test_open_without_scale_shows_px_hints():
    _, p, _ = _setup()
    assert p.fields == ["AB", "BC", "CA"] and p.focus == "AB" and p.is_open
    assert p.values == {"AB": "", "BC": "", "CA": ""}
    assert p.hints == {"AB": "~300px", "BC": "~250px", "CA": "~250px"}


def test_open_with_scale_prefills_in_current_unit():
    _, p, _ = _setup(scale=100)
    assert p.values == {"AB": "3", "BC": "2.5", "CA": "2.5"}
    _, p, _ = _setup(scale=100, unit="mm")
    assert p.values["AB"] == "30"


def test_typing_replaces_prefill_then_edits():
    _, p, _ = _setup(scale=100)
    for ch in ["5", ".", ".", "2"]:
        p.type(ch)
    assert p.values["AB"] == "5.2"                 # dấu chấm thứ hai bị bỏ qua
    p.type("<-")
    assert p.values["AB"] == "5."
    p.focus_field("BC")
    p.type("<-")
    assert p.values["BC"] == "2."                  # xóa ngay sau khi chọn ô: xóa 1 ký tự
    p.focus_field("CA")
    for _ in range(12):
        p.type("9")
    assert p.values["CA"] == "99999999"            # tối đa 8 ký tự


def test_first_ok_sets_scale_and_keeps_that_side():
    board, p, _ = _setup()
    p.type("3")
    assert p.submit(board, BOUNDS) and not p.is_open
    assert board.scale == pytest.approx(100)
    assert polygon_metrics(board.shapes[0]["pts"])["sides"] == pytest.approx([300, 250, 250])


def test_3_4_5_builds_right_triangle():
    board, p, _ = _setup()
    _fill(p, {"AB": "3", "BC": "4", "CA": "5"})
    assert p.submit(board, BOUNDS)
    assert polygon_metrics(board.shapes[0]["pts"])["angles"][1] == pytest.approx(90)


@pytest.mark.parametrize("typed", [".", "0"])
def test_invalid_number_keeps_panel_open(typed):
    board, p, _ = _setup()
    _fill(p, {"AB": typed})
    assert not p.submit(board, BOUNDS) and p.is_open and p.error == "AB khong hop le"
    assert board.scale is None and board.shapes[0]["pts"][2] == (640.0, 250.0)


def test_nothing_entered_without_scale():
    board, p, _ = _setup()
    assert not p.submit(board, BOUNDS) and p.error == "Chua nhap so nao"


def test_empty_field_with_scale_is_an_error():
    board, p, _ = _setup(scale=100)
    p.focus_field("BC")
    for _ in range(3):
        p.type("<-")
    assert not p.submit(board, BOUNDS) and p.error == "Chua nhap BC"


def test_degenerate_triangle_message_uses_units():
    board, p, _ = _setup(scale=50)
    _fill(p, {"AB": "1", "BC": "2", "CA": "3"})
    assert not p.submit(board, BOUNDS) and p.error == "CA phai nho hon AB + BC = 3.00 cm"


def test_too_big_for_screen_is_rejected():
    board, p, _ = _setup(scale=100)
    _fill(p, {"AB": "30", "BC": "30", "CA": "30"})
    assert not p.submit(board, BOUNDS) and p.error.startswith("Hinh vuot khoi man hinh")


def test_reset_scale_recalibrates_from_first_field():
    board, p, ctl = _setup(scale=100)
    p.on_event(E("down", _center(p.reset_rect), 0.0), ctl)
    assert p.reset_scale
    _fill(p, {"AB": "2"})
    assert p.submit(board, BOUNDS) and board.scale == pytest.approx(150)


def test_undo_after_ok_restores_shape_and_scale():
    board, p, _ = _setup()
    _fill(p, {"AB": "3", "BC": "4", "CA": "5"})
    p.submit(board, BOUNDS)
    board.undo()
    assert board.scale is None and board.shapes[0]["pts"][2] == (640.0, 250.0)


def test_submit_after_shape_deleted_closes_panel():
    board, p, _ = _setup()
    board.shapes = []                              # ví dụ: Undo xóa mất hình đang sửa
    assert not p.submit(board, BOUNDS) and not p.is_open


def test_hit_regions():
    _, p, _ = _setup()
    assert p.hit(_center(p.key_rects["5"])) == ("key", "5")
    assert p.hit(_center(p.ok_rect)) == ("ok", None) and p.hit(_center(p.cancel_rect)) == ("cancel", None)
    assert p.hit(_center(p.field_rects[1])) == ("field", "BC")
    assert p.hit((0, 0)) is None


def test_line_panel_has_one_field():
    board = Board()
    board.shapes.append({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)], "raw": [], "id": 1, "locked": False})
    p = EditPanel(Config(), 1280, 720)
    p.open(board.shapes[0], "d", board)
    assert p.fields == ["d"] and p.hit(_center(p.field_rects[1])) is None


def test_pointer_and_keyboard_drive_panel():
    _, p, ctl = _setup()
    p.on_event(E("down", _center(p.key_rects["7"]), 0.0), ctl)
    p.on_event(E("move", _center(p.key_rects["8"]), 0.1), ctl)     # chỉ "down" mới bấm
    assert p.values["AB"] == "7"
    assert p.key(9, ctl) and p.focus == "BC"                        # Tab: ô kế tiếp
    assert p.key(ord("4"), ctl) and p.values["BC"] == "4"
    assert p.key(8, ctl) and p.values["BC"] == ""                   # Backspace
    assert not p.key(ord("q"), ctl)
    assert p.key(27, ctl) and not p.is_open                         # Esc: Huy


def test_panel_fits_small_camera_frame():
    p = EditPanel(Config(), 640, 480)
    x0, y0, x1, y1 = p.rect
    assert 0 <= x0 and x1 <= 640 and 70 <= y0 and y1 <= 480
    for kx0, ky0, kx1, ky1 in [*p.key_rects.values(), p.ok_rect, p.cancel_rect]:
        assert x0 <= kx0 and kx1 <= x1 and y0 <= ky0 and ky1 <= y1


def test_first_scale_shrinks_until_shape_fits_screen():
    board = Board()
    board.shapes.append({"kind": "rect", "pts": [(440.0, 300.0), (840.0, 300.0), (840.0, 500.0), (440.0, 500.0)],
                         "raw": [], "id": 1, "locked": False})        # dai 400 px, rong 200 px
    p = EditPanel(Config(), 1280, 720)
    p.open(board.shapes[0], "dai", board)
    _fill(p, {"dai": "5", "rong": "9"})            # giữ dai 400 px -> rong 720 px, vượt màn hình
    assert p.submit(board, BOUNDS), p.error
    side = polygon_metrics(board.shapes[0]["pts"])["sides"]
    assert side[1] / side[0] == pytest.approx(9 / 5) and side[0] / board.scale == pytest.approx(5)
    assert all(70 <= y <= 720 for _, y in board.shapes[0]["pts"])


def test_resize_into_neighbour_is_refused():
    board, p, _ = _setup(scale=100.0)
    board.shapes.append({"kind": "circle", "pts": [], "center": (640.0, 180.0), "radius": 30.0, "raw": [],
                         "id": 2, "locked": False})        # cách đỉnh C 40 px
    _fill(p, {"AB": "3", "BC": "3.5", "CA": "3.5"})       # tam giác cao lên, đỉnh C lọt vào hình tròn
    assert not p.submit(board, BOUNDS) and p.error.startswith("Hinh de len hinh khac") and p.is_open
    assert board.shapes[0]["pts"][2] == (640.0, 250.0)
