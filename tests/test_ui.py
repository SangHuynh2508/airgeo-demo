import numpy as np

from airgeo.config import Config
from airgeo.session import DrawingSession, FrameResult
from airgeo.ui.hud import draw_help, draw_hud, hud_lines
from airgeo.ui.render import draw_canvas, draw_hand, draw_trails


def test_hud_lines_show_filter_mode_and_pinch_state():
    s = DrawingSession(Config())
    lines = hud_lines(s, fps=29.94, compare=True, rec_session_id=None)
    assert lines[0] == "FPS: 29.9"
    assert "Loc: one_euro (mincutoff=1.000 beta=0.0070)" in lines
    assert "Che do: ve tu do  | so sanh" in lines
    assert "Chum: off  ratio -" in lines
    assert "Do theo: 2D  on<0.20 off>0.35" in lines
    assert not any(line.startswith("REC") for line in lines)
    assert hud_lines(s, 30, False, "20261105_101010")[-1] == "REC session 20261105_101010"


def test_hud_shows_last_recognition_only_in_smart_mode():
    s = DrawingSession(Config())
    s.last_info = "rect ho=0.01 tron=0.69 dinh=4"
    assert not any(line.startswith("Net cuoi") for line in hud_lines(s, 30, False, None))
    s.smart = True
    assert "Net cuoi: rect ho=0.01 tron=0.69 dinh=4" in hud_lines(s, 30, False, None)


def test_drawing_functions_paint_on_frame(make_hand):
    strokes = [{"kind": "line", "pts": [(100, 400), (400, 500)], "raw": []},
               {"kind": "circle", "pts": [], "center": (600, 300), "radius": 80, "raw": []},
               {"kind": "rect", "pts": [(700, 100), (900, 100), (900, 250), (700, 250)], "raw": []},
               {"kind": "triangle", "pts": [(100, 700), (300, 700), (200, 550)], "raw": []},
               {"kind": "free", "pts": [(50, 600), (80, 620), (120, 610)], "raw": []}]
    frame = draw_canvas(np.zeros((720, 1280, 3), np.uint8), strokes, [(10, 10, 0), (60, 60, 0)])
    hand = make_hand(640, 360, ratio=0.1)
    draw_hand(frame, hand, FrameResult((640, 360), (640, 360), True, False), show_skeleton=True)
    draw_hand(frame, hand, FrameResult(None, None, True, True), show_skeleton=False)
    draw_trails(frame, [(0, 0), (50, 50)], [(0, 0), (40, 40)])
    draw_hud(frame, hud_lines(DrawingSession(Config()), 30, False, None), recording=True)
    draw_help(frame)
    assert frame[300, 680].any()          # điểm nằm trên đường tròn tâm (600, 300), r = 80
