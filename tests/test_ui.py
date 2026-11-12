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
    assert "Bam: chum  Do theo: 2D  on<0.20 off>0.35" in lines
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
    frame = draw_canvas(np.zeros((720, 1280, 3), np.uint8), strokes, [(10, 10, 0), (60, 60, 0)])
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


def test_canvas_draws_no_measurements_until_asked():
    from airgeo.ui.render import draw_measurements
    circle = {"kind": "circle", "pts": [], "center": (600, 300), "radius": 80, "raw": []}
    frame = draw_canvas(np.zeros((720, 1280, 3), np.uint8), [circle], None)
    assert not frame[300, 600].any()                 # chưa vẽ tâm / bán kính
    draw_measurements(frame, circle, show={"radius"})
    assert frame[300, 600].any()
    blank = np.zeros((720, 1280, 3), np.uint8)
    draw_measurements(blank, circle, show=set())
    assert not blank.any()


def _selected(shape, show, height=720, width=1280):
    c = Controller(Config(), width, height)
    c.board.shapes.append(dict(shape, raw=[], id=1, locked=False))
    c.board.scale = 100.0
    c.do("select")
    sel = c.tools["select"]
    sel.selected, sel.show = 1, set(show)
    return c, sel


TRI_345 = {"kind": "triangle", "pts": [(300.0, 500.0), (600.0, 500.0), (600.0, 100.0)]}


def test_formula_panel_only_after_pressing_perimeter_or_area():
    from airgeo.ui.render import draw_tool_overlay
    c, sel = _selected(TRI_345, {"sides"})
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    below = sel.menu(c.board.get(1))[-1][1][3] + 10
    assert not frame[below:690, 1000:1270].any()            # chỉ Cạnh: chưa có bảng công thức
    sel.show = {"perimeter", "area"}
    draw_tool_overlay(frame, c)
    assert frame[below:690, 1000:1270].any()


def test_triangle_area_draws_dashed_height_also_when_obtuse():
    from airgeo.ui.render import draw_tool_overlay
    acute = {"kind": "triangle", "pts": [(300.0, 500.0), (700.0, 500.0), (450.0, 200.0)]}   # chân (450, 500)
    c, sel = _selected(acute, {"perimeter"})
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert not frame[350, 450].any()                        # chưa bật Diện tích: không có đường cao
    sel.show = {"area"}
    draw_tool_overlay(frame, c)
    assert frame[350, 450].any()
    c, _ = _selected({"kind": "triangle", "pts": [(300.0, 500.0), (500.0, 500.0), (650.0, 300.0)]}, {"area"})
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)                             # tam giác tù: chân (650, 500) ngoài AB
    assert frame[500, 580:640].any() and frame[400, 650].any()


def test_formula_panel_fits_small_frame_and_skips_line():
    from airgeo.ui.render import draw_tool_overlay
    c, _ = _selected(TRI_345, {"perimeter", "area"}, height=480, width=640)
    frame = np.zeros((480, 640, 3), np.uint8)
    from airgeo.ui.render import draw_formulas
    x0, y0, x1, y1 = draw_formulas(frame, c.board.get(1), c.tools["select"], 100.0, "cm")
    assert 0 <= x0 and y1 <= 480 - 40 and x1 <= c.tools["select"].menu_x   # sang trái cột nút, đủ chỗ
    assert frame[y1 - 30:y1 - 8, x0 + 8:x1 - 8].any()                      # dòng kết quả cuối có trong ảnh
    c, sel = _selected({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)]}, {"sides"})
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    below = sel.menu(c.board.get(1))[-1][1][3] + 10
    assert not frame[below:690, 1000:1270].any()            # đoạn thẳng: không có bảng công thức


def test_perimeter_and_area_are_not_duplicated_on_the_shape():
    from airgeo.ui.render import draw_tool_overlay
    c, sel = _selected(TRI_345, {"perimeter", "area"})
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert not frame[345:385, 455:560].any()                # chỗ nhãn P= / S= cũ quanh trọng tâm (500, 366)


def test_canvas_dims_shapes_other_than_active():
    a = {"kind": "line", "pts": [(100, 100), (300, 100)], "id": 1}
    b = {"kind": "line", "pts": [(100, 300), (300, 300)], "id": 2}
    bright = draw_canvas(np.zeros((400, 400, 3), np.uint8), [a, b], None)
    dim = draw_canvas(np.zeros((400, 400, 3), np.uint8), [a, b], None, active=1)
    assert (dim[100, 200] == bright[100, 200]).all() and 0 < dim[300, 200].sum() < bright[300, 200].sum()


def test_blocked_drag_paints_shape_red():
    from airgeo.ui.render import draw_tool_overlay
    c, sel = _selected({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)]}, set())
    sel.blocked = True
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert tuple(frame[300, 150]) == (0, 0, 255)


def test_canvas_ignores_active_id_that_no_longer_exists():
    a = {"kind": "line", "pts": [(100, 100), (300, 100)], "id": 1}
    bright = draw_canvas(np.zeros((400, 400, 3), np.uint8), [a], None)
    stale = draw_canvas(np.zeros((400, 400, 3), np.uint8), [a], None, active=9)   # hình đã bị Undo
    assert (stale == bright).all()


def test_button_has_dark_backing_and_vietnamese_label():
    from airgeo.ui.render import draw_button
    frame = np.full((100, 300, 3), 255, np.uint8)           # tường trắng
    draw_button(frame, (20, 20, 200, 70), "Đơn vị: cm")
    inside = frame[22:68, 22:198]
    assert (inside < 128).mean() > 0.5 and (inside > 200).any()   # nền tối, chữ sáng
    assert (frame[0:15] == 255).all()                       # ngoài nút không đổi


def test_toolbar_only_paints_its_band_and_groups_tools_left():
    c = Controller(Config(), 1280, 720)
    frame = np.full((720, 1280, 3), 200, np.uint8)
    draw_toolbar(frame, c, 0.0, None)
    assert (frame[60:] == 200).all() and (frame[:60] != 200).any()
    r = c.toolbar.rects
    assert r["erase"][2] + 30 < r["undo"][0]                 # 2 cụm: công cụ | lệnh
    assert r["clear"][2] <= 1280 - 5


def test_toast_legend_progress_and_radial_menu_paint():
    from airgeo.ui.hud import draw_legend, draw_status
    from airgeo.ui.render import draw_pose_progress, draw_radial_menu
    c = Controller(Config(), 1280, 720)
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_status(frame, "Đã hoàn tác")
    assert frame[60:140, 500:780].any()                      # thông báo giữa, dưới dải trạng thái
    blank = np.zeros((720, 1280, 3), np.uint8)
    draw_legend(blank)
    assert blank[600:715, 0:400].any() and not blank[:500].any()
    ring = np.zeros((720, 1280, 3), np.uint8)
    draw_pose_progress(ring, (640, 400), ("draw", 0.5))
    assert ring[400 - 40:400 + 40, 640 - 40:640 + 40].any()
    nothing = np.zeros((720, 1280, 3), np.uint8)
    draw_pose_progress(nothing, (640, 400), ("draw", 0.1))   # mới thoáng qua: chưa vẽ
    draw_pose_progress(nothing, (640, 400), None)
    assert not nothing.any()
    c.menu.open((640, 400), 0.0)
    menu = np.zeros((720, 1280, 3), np.uint8)
    draw_radial_menu(menu, c.menu, c.board, 0.0, (640, 280))
    ux, uy = dict(c.menu.positions())["unit"]
    assert menu[int(uy) - 20:int(uy) + 20, int(ux) - 30:int(ux) + 30].any()


def test_side_values_sit_outside_the_label_chips():
    from airgeo.geometry.construct import label_anchors
    from airgeo.ui.render import draw_measurements
    for shape in ({"kind": "rect", "pts": [(400.0, 300.0), (820.0, 300.0), (820.0, 480.0), (400.0, 480.0)]},
                  {"kind": "line", "pts": [(300.0, 300.0), (700.0, 380.0)]},
                  {"kind": "circle", "pts": [], "center": (600.0, 400.0), "radius": 120.0}):
        frame = np.zeros((720, 1280, 3), np.uint8)
        draw_measurements(frame, shape, show={"sides", "radius"})
        assert frame.any()
        for x, y in label_anchors(shape).values():               # chỗ nút nhãn (56 x 32) phải trống
            assert not frame[int(y) - 16:int(y) + 16, int(x) - 28:int(x) + 28].any()


def test_rotation_handle_is_drawn_for_selected_rect():
    from airgeo.ui.render import draw_tool_overlay
    c, sel = _selected({"kind": "rect", "pts": [(500.0, 350.0), (700.0, 350.0), (700.0, 450.0), (500.0, 450.0)]},
                       set())
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    hx, hy = sel.handle(c.board.get(1))
    assert frame[int(hy) - 3:int(hy) + 4, int(hx) - 3:int(hx) + 4].any()
