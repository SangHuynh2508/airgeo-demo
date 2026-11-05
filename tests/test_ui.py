import numpy as np

from airgeo.config import Config
from airgeo.document.board import Board
from airgeo.interaction.controller import Controller
from airgeo.pinch_filter import FrameResult, PinchFilter
from airgeo.ui.hud import draw_help, draw_hud, hud_lines
from airgeo.ui.render import draw_canvas, draw_hand, draw_trails
from airgeo.ui.toolbar import draw_toolbar


def test_hud_lines_show_tool_scale_filter_and_pinch_state():
    pf, board = PinchFilter(Config()), Board()
    lines = hud_lines(pf, board, "draw", fps=29.94, compare=True, rec_session_id=None)
    assert lines[0] == "FPS: 29.9"
    assert "Cong cu: Ve  Ti le: chua dat" in lines
    assert "Loc: one_euro (mincutoff=1.000 beta=0.0070)" in lines
    assert "Che do: ve tu do  | so sanh" in lines
    assert "Chum: off  ratio -" in lines
    assert "Bam: 2 ngon  Do theo: 2D  on<0.25 off>0.40" in lines
    assert not any(line.startswith("REC") for line in lines)
    board.scale = 50
    assert "Cong cu: Chon  Ti le: 50.0 px/cm" in hud_lines(pf, board, "select", 30, False, None)
    assert hud_lines(pf, board, "draw", 30, False, "20261105_101010")[-1] == "REC session 20261105_101010"


def test_hud_shows_last_recognition_only_in_smart_mode():
    pf, board = PinchFilter(Config()), Board()
    board.last_info = "rect ho=0.01 tron=0.69 dinh=4"
    assert not any(line.startswith("Net cuoi") for line in hud_lines(pf, board, "draw", 30, False, None))
    board.smart = True
    assert "Net cuoi: rect ho=0.01 tron=0.69 dinh=4" in hud_lines(pf, board, "draw", 30, False, None)


def test_drawing_functions_paint_on_frame(make_hand):
    strokes = [{"kind": "line", "pts": [(100, 400), (400, 500)], "raw": []},
               {"kind": "circle", "pts": [], "center": (600, 300), "radius": 80, "raw": []},
               {"kind": "rect", "pts": [(700, 100), (900, 100), (900, 250), (700, 250)], "raw": []},
               {"kind": "triangle", "pts": [(100, 700), (300, 700), (200, 550)], "raw": []},
               {"kind": "free", "pts": [(50, 600), (80, 620), (120, 610)], "raw": []}]
    frame = draw_canvas(np.zeros((720, 1280, 3), np.uint8), strokes, [(10, 10, 0), (60, 60, 0)],
                        scale=50, unit="cm")
    hand = make_hand(640, 360, ratio=0.1)
    draw_hand(frame, hand, FrameResult((640, 360), (640, 360), True, False), show_skeleton=True)
    draw_hand(frame, hand, FrameResult(None, None, True, True), show_skeleton=False)
    draw_trails(frame, [(0, 0), (50, 50)], [(0, 0), (40, 40)])
    ctl = Controller(Config(), 1280, 720)
    draw_toolbar(frame, ctl, 0.0, (100, 35))
    draw_hud(frame, hud_lines(PinchFilter(Config()), ctl.board, "draw", 30, False, None), recording=True, top=70)
    draw_help(frame)
    assert frame[300, 680].any()                     # điểm trên đường tròn tâm (600, 300), r = 80
    x0, y0, x1, y1 = ctl.toolbar.rects["draw"]
    assert frame[35, int((x0 + x1) / 2) - 40].any()  # nút "Ve" đang bật được tô nền


def test_selection_overlay_paints(stroke, press):
    from airgeo.ui.render import draw_tool_overlay
    c = Controller(Config(), 1280, 720)
    stroke(c, [(100, 300), (200, 300), (300, 300)])
    c.do("select")
    press(c, (200, 300))
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert frame[300, 200].any()


def test_erase_overlay_paints_red(stroke):
    from airgeo.interaction.pointer import PointerEvent
    from airgeo.ui.render import draw_tool_overlay
    c = Controller(Config(), 1280, 720)
    stroke(c, [(100, 300), (200, 300), (300, 300)])
    c.do("erase")
    c.dispatch(PointerEvent("hover", (200, 300), 1.0))
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert tuple(frame[300, 200]) == (0, 0, 255)


def test_edit_panel_and_side_labels_paint(press):
    from airgeo.ui.edit_panel import draw_edit_panel
    from airgeo.ui.render import draw_tool_overlay
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append({"kind": "triangle", "pts": [(490.0, 450.0), (790.0, 450.0), (640.0, 250.0)],
                           "raw": [], "id": 1, "locked": False})
    c.do("select")
    press(c, (640, 450))
    c.panel.open(c.board.shapes[0], "AB", c.board)
    c.panel.error = "AB khong hop le"
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    draw_edit_panel(frame, c.panel, "cm", (640, 400))
    x0, y0, x1, y1 = c.panel.rect
    assert frame[y0, x0:x1].any()                        # viền bảng
