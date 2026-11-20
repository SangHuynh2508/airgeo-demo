import pytest
import math
from helpers import place_line
import cv2
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
    assert "So sanh: bat" in lines
    assert "Chum: off  ratio -" in lines
    assert "Bam: chum  Do theo: 2D  on<0.20 off>0.35" in lines
    assert not any(line.startswith("REC") for line in lines)
    board.scale = 50
    assert "Cong cu: Chon  Ti le: 50.0 px/cm" in hud_lines(pf, board, "select", 30, False, None)
    assert hud_lines(pf, board, "draw", 30, False, "20261105_101010")[-1] == "REC session 20261105_101010"


def test_hud_shows_last_recognition():
    pf, board = PinchFilter(Config()), Board()
    assert not any(line.startswith("Net cuoi") for line in hud_lines(pf, board, "draw", 30, False, None))
    board.last_info = "rect ho=0.01 tron=0.69 dinh=4"
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
    ctl.toolbar.visible = True
    draw_toolbar(frame, ctl, 0.0, (100, 35))
    draw_hud(frame, hud_lines(PinchFilter(Config()), ctl.board, "draw", 30, False, None), recording=True, top=70)
    draw_help(frame)
    assert frame[300, 680].any()                     # điểm trên đường tròn tâm (600, 300), r = 80
    x0, y0, x1, y1 = ctl.toolbar.rects["draw"]
    assert frame[35, int((x0 + x1) / 2) - 40].any()  # nút "Ve" đang bật được tô nền


def test_selection_overlay_paints(stroke, press):
    from airgeo.ui.render import draw_tool_overlay
    c = Controller(Config(), 1280, 720)
    place_line(c, 300)
    c.do("select")
    press(c, (200, 300))
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert frame[300, 200].any()


def test_erase_overlay_paints_red(stroke):
    from airgeo.interaction.pointer import PointerEvent
    from airgeo.ui.render import draw_tool_overlay
    c = Controller(Config(), 1280, 720)
    place_line(c, 300)
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
    c.panel.error = "AB không hợp lệ"
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    draw_edit_panel(frame, c.panel, "cm", (640, 400))
    x0, y0, x1, y1 = c.panel.rect
    assert frame[y0, x0:x1].any()                        # viền bảng


def test_selected_circle_shows_its_radius():
    from airgeo.ui.render import draw_selection
    circle = {"kind": "circle", "pts": [], "center": (600, 300), "radius": 80, "raw": []}
    frame = draw_canvas(np.zeros((720, 1280, 3), np.uint8), [circle], None)
    assert not frame[300, 600:660].any()             # chưa chọn: chỉ có đường tròn
    draw_selection(frame, circle)
    assert frame[300, 600:660].any(axis=1).all()     # chọn: tâm + đường bán kính


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
    c, sel = _selected(TRI_345, {"angles"})
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    below = sel.menu(c.board.get(1))[-1][1][3] + 10
    assert not frame[below:690, 1000:1270].any()            # chỉ Góc: chưa có bảng công thức
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
    c, sel = _selected({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)]}, {"perimeter", "area"})
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert not frame[sel.menu_y:690, 1000:1270].any()       # đoạn thẳng: không có cột nút, bảng công thức


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
    c.toolbar.visible = True
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
    assert frame[720 - 80:720 - 20, 500:780].any()           # thông báo giữa dưới: không che đỉnh hình
    assert not frame[:720 - 90].any()
    blank = np.zeros((720, 1280, 3), np.uint8)
    draw_legend(blank)
    assert blank[540:715, 0:400].any() and not blank[:400].any()
    from airgeo.ui.hud import LEGEND
    assert {"Chụm cái + trỏ: vẽ", "Áp trỏ + giữa: bấm / kéo"} <= set(LEGEND)    # 2 cử chỉ bấm cơ bản
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


def test_rotation_handle_is_drawn_for_selected_rect():
    from airgeo.ui.render import draw_tool_overlay
    c, sel = _selected({"kind": "rect", "pts": [(500.0, 350.0), (700.0, 350.0), (700.0, 450.0), (500.0, 450.0)]},
                       set())
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    hx, hy = sel.handle(c.board.get(1))
    assert frame[int(hy) - 3:int(hy) + 4, int(hx) - 3:int(hx) + 4].any()
    assert frame[int(hy), int(hx) + 19].any()                    # bán kính vẽ 20 px (dễ thấy từ cuối lớp)


def test_angle_chips_drawn_are_kept_for_the_handle_to_avoid():
    from airgeo.ui.render import draw_tool_overlay
    c, sel = _selected(TRI_345, {"angles"})
    draw_tool_overlay(np.zeros((720, 1280, 3), np.uint8), c)
    assert len(sel.avoid) == 3
    sel.show = set()
    draw_tool_overlay(np.zeros((720, 1280, 3), np.uint8), c)
    assert sel.avoid == []


def test_hidden_toolbar_draws_only_a_small_tool_chip():
    from airgeo.ui.toolbar import draw_toolbar
    c = Controller(Config(), 1280, 720)
    frame = np.full((720, 1280, 3), 200, np.uint8)
    draw_toolbar(frame, c, 0.0, None)
    assert (frame[30, 600] == 200).all()                        # giữa mép trên: không có dải tối
    assert (frame[:200, :200] == 200).all()                      # góc trên trái để cho vùng xóa
    assert (frame[720 - 60:720 - 5, 10:120] < 100).any()         # góc dưới trái: viên "Vẽ · cm"
    c.toolbar.visible = True
    draw_toolbar(frame, c, 0.0, None)
    assert (frame[30, 600] < 200).all()


def test_tool_chip_legend_and_status_do_not_overlap():
    from airgeo.ui.hud import draw_legend, draw_status
    c = Controller(Config(), 1280, 720)
    masks = []
    for draw in (lambda f: draw_toolbar(f, c, 0.0, None), draw_legend,
                 lambda f: draw_status(f, "Không nhận ra hình – vẽ lại")):
        f = np.full((720, 1280, 3), 200, np.uint8)
        draw(f)
        masks.append((f != 200).any(axis=2))
    a, b, s = masks
    assert not (a & b).any() and not (a & s).any() and not (b & s).any()


def test_pose_label_flips_left_near_right_edge():
    from airgeo.ui.render import draw_pose_progress
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_pose_progress(frame, (1240, 400), ("undo", 0.5))
    assert frame[380:420, 1080:1195].any()                       # "Hoàn tác" bên trái vòng tiến độ
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_pose_progress(frame, (400, 400), ("undo", 0.5))
    assert frame[380:420, 450:560].any() and not frame[380:420, 250:355].any()   # giữa màn hình: bên phải


def test_angle_chip_stays_below_top_of_canvas():
    from airgeo.ui.render import angle_chip_center
    hw, hh = 70, 17
    x, y = angle_chip_center((640, 110), (0.0, 1.0), hw, hh, 1280, 720, top=60)   # đỉnh trên, viên đẩy lên
    assert y - hh >= 60
    # đỉnh C sát dải nút, phân giác trong chĩa xuống trái: không đủ chỗ phía trên -> sang phải đỉnh, không xuống đè hình
    x, y = angle_chip_center((730, 90), (-0.3, 0.95), hw, hh, 1280, 720, top=60)
    assert x - hw > 730 and y - hh >= 60


def test_radial_menu_items_are_nearly_opaque():
    from airgeo.ui.render import draw_radial_menu
    c = Controller(Config(), 1280, 720)
    c.menu.open((640, 400), 0.0)
    frame = np.full((720, 1280, 3), 250, np.uint8)
    draw_radial_menu(frame, c.menu, c.board, 0.0, None)
    ux, uy = (int(v) for v in dict(c.menu.positions())["unit"])
    assert frame[uy + 30, ux].max() <= 40                         # nền mục phủ ~90%: tường trắng không lộ


def test_right_angle_gets_square_mark_and_other_angles_an_arc():
    from airgeo.ui.render import draw_angles
    tri = {"kind": "triangle", "pts": [(100, 600), (400, 600), (100, 300)], "raw": []}   # vuông tại A, 45° tại B
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_angles(frame, tri)
    assert frame[588:597, 114:119].any()                 # cạnh ô vuông nhỏ ở A (cách đỉnh 16 px)
    assert not frame[597:603, 123:129].any()             # không có cung ở góc vuông
    assert frame[586:594, 372:380].any()                 # cung ở B (bán kính 26, theo phân giác)


def test_column_title_is_the_shape_name(press):
    from airgeo.ui.render import draw_tool_overlay
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append({"kind": "triangle", "pts": [(300, 600), (600, 600), (300, 300)], "raw": [],
                           "id": 1, "locked": False})
    c.do("select")
    press(c, (450, 600))
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    sel = c.tools["select"]
    y0 = sel.menu_y - 34
    assert frame[y0:sel.menu_y - 4, sel.menu_x + 100:sel.menu_x + 150].any()   # tên dài, căn phải theo cột


def test_side_chips_show_names_until_measured_then_name_equals_value():
    from airgeo.ui.render import side_chips

    def lines(s, scale):
        return {f: chip[0] for f, chip in side_chips(s, scale, "cm").items()}
    rect = {"kind": "rect", "pts": [(100.0, 100.0), (550.0, 100.0), (550.0, 400.0), (100.0, 400.0)]}
    assert lines(rect, None) == {"dai": ["dài"], "rong": ["rộng"]}
    # học sinh nối số trên hình với công thức; cạnh dốc (nhãn nằm cạnh bên) xuống 2 dòng cho viên hẹp
    assert lines(rect, 50.0) == {"dai": ["dài = 9 cm"], "rong": ["rộng =", "6 cm"]}
    tri = {"kind": "triangle", "pts": [(0.0, 0.0), (300.0, 0.0), (0.0, 400.0)]}
    assert lines(tri, 100.0) == {"AB": ["AB = 3 cm"], "BC": ["BC =", "5 cm"], "CA": ["CA =", "4 cm"]}
    circle = {"kind": "circle", "pts": [], "center": (300.0, 300.0), "radius": 100.0}
    assert lines(circle, 50.0) == {"r": ["r = 2 cm"]}
    chips = side_chips(rect, 50.0, "cm")          # 2 cạnh bằng nhau: nhãn ở cạnh trên / trái, xa cột Tính và mép dưới
    assert chips["dai"][1][1] < 100 and chips["rong"][1][0] < 100


def test_whole_side_chip_face_opens_the_panel(press):
    from airgeo.ui.render import side_chips
    c, sel = _selected(TRI_345, set())
    c.board.fit(1, c.fit_box)
    c.board.scale = math.dist(*c.board.get(1)["pts"][:2]) / 3
    _, (x, y), (hw, hh) = side_chips(c.board.get(1), c.board.scale, "cm")["AB"]
    press(c, (x + hw - 6, y))                                   # mép viên "AB = 3 cm", xa tâm hơn 25 px
    assert c.panel.is_open and c.panel.focus == "AB"


def test_title_shown_for_line_without_menu():
    from airgeo.ui.render import draw_tool_overlay
    c, sel = _selected({"kind": "line", "pts": [(100.0, 300.0), (300.0, 300.0)]}, set())
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert frame[sel.menu_y - 40:sel.menu_y - 4, sel.menu_x + 100:sel.menu_x + 150].any()   # "Đoạn thẳng"


def test_triangle_angle_values_sit_outside_with_a_leader():
    from airgeo.ui.render import draw_angles
    tri = {"kind": "triangle", "pts": [(300, 500), (700, 500), (300, 200)], "raw": []}   # vuông A, ~37° B, ~53° C
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_angles(frame, tri)
    inside = np.zeros((720, 1280), np.uint8)
    cv2.fillPoly(inside, [np.array(tri["pts"], np.int32)], 1)
    ys, xs = np.nonzero(frame.any(axis=2) & (inside == 0))
    assert (xs > 740).any()                                                          # viên góc B ngoài hình
    assert (ys > 520).any() and (xs < 280).any()                                     # viên góc A (90°) ngoài hình
    assert frame[503:508, 710:714].any()                         # đường chỉ đi qua đỉnh B ra ngoài theo phân giác ngoài


def test_rect_angles_are_only_square_marks():
    from airgeo.ui.render import draw_angles
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_angles(frame, {"kind": "rect", "pts": [(400, 300), (800, 300), (800, 500), (400, 500)], "raw": []})
    ys, xs = np.nonzero(frame.any(axis=2))
    assert len(xs) and xs.min() >= 398 and xs.max() <= 802 and ys.min() >= 298 and ys.max() <= 502


def test_vertex_letters_can_be_hidden():
    from airgeo.ui.render import draw_selection
    tri = {"kind": "triangle", "pts": [(300.0, 500.0), (700.0, 500.0), (300.0, 200.0)]}
    a, b = np.zeros((720, 1280, 3), np.uint8), np.zeros((720, 1280, 3), np.uint8)
    draw_selection(a, tri)
    draw_selection(b, tri, letters=False)
    assert a[505:525, 270:295].any() and not b[505:525, 270:295].any()    # chữ A cạnh đỉnh (300, 500)


def test_vertex_letters_stay_with_angles_unless_a_chip_covers_them():
    from airgeo.ui.render import draw_letters
    tri = {"kind": "triangle", "pts": [(300.0, 500.0), (700.0, 500.0), (300.0, 200.0)]}
    a = np.zeros((720, 1280, 3), np.uint8)
    draw_letters(a, tri, (255, 255, 255), [(260, 500, 300, 530)])        # viên góc A đè chỗ chữ A
    assert not a[505:525, 270:295].any() and a[505:525, 710:735].any()   # bỏ A, giữ B


def test_cursor_is_big_and_filled_while_pinching():
    frame = np.zeros((200, 200, 3), np.uint8)
    draw_hand(frame, None, FrameResult((100, 100), (100, 100), False, False), False, "two_finger")
    assert frame[100, 114].any() and not frame[100, 100].any()           # vòng 14 px, rỗng
    draw_hand(frame, None, FrameResult((100, 100), (100, 100), True, False), show_skeleton=False)
    assert frame[100, 100].any()                                         # đang chụm: tô đặc


def test_height_label_sits_inside_the_triangle():
    from airgeo.ui.render import draw_height
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_height(frame, [(300.0, 500.0), (600.0, 500.0), (600.0, 100.0)])   # đường cao CB trùng cạnh BC
    assert frame[280:320, 570:596].any() and not frame[280:320, 605:640].any()   # "h" bên trong, nhãn BC bên ngoài


def test_height_chip_reads_its_value_or_names_the_side_it_lies_on(monkeypatch):
    from airgeo.ui.render import VALUE_SIZE, draw_height
    calls = _spy_text(monkeypatch)
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_height(frame, [(300.0, 500.0), (700.0, 500.0), (450.0, 200.0)], 100.0, "cm")
    draw_height(frame, [(300.0, 500.0), (700.0, 500.0), (450.0, 200.0)], None, "cm")
    draw_height(frame, [(300.0, 500.0), (600.0, 500.0), (600.0, 100.0)], 100.0, "cm")   # vuông tại B
    draw_height(frame, [(300.0, 500.0), (600.0, 500.0), (300.0, 100.0)], None, "cm")    # vuông tại A
    assert [(s, sz) for s, sz, _ in calls] == [("h = 3 cm", VALUE_SIZE), ("h", VALUE_SIZE), ("h = BC", VALUE_SIZE),
                                               ("h = CA", VALUE_SIZE)]


def test_angle_chip_pushed_back_on_screen_moves_off_the_vertex():
    from airgeo.ui.render import angle_chip_center
    hw, hh = 70, 17
    x, y = angle_chip_center((640, 360), (1.0, 0.0), hw, hh, 1280, 720)
    assert (x, y) == (640 - hw - 34, 360)                              # bình thường: theo phân giác ngoài
    for v, b in (((110, 360), (1.0, 0.0)), ((1170, 360), (-1.0, 0.0)), ((640, 40), (0.0, 1.0))):
        x, y = angle_chip_center(v, b, hw, hh, 1280, 720)
        assert not (x - hw - 4 <= v[0] <= x + hw + 4 and y - hh - 4 <= v[1] <= y + hh + 4), v
        assert hw <= x <= 1280 - hw and hh <= y <= 720 - hh


def _spy_text(monkeypatch):
    """Ghi lại (chữ, cỡ, đậm) mọi lần vẽ chữ Pillow trong render.py (nhãn cạnh, viên góc, bảng công thức, gợi ý)."""
    import airgeo.ui.render as render
    calls, real = [], render.put_text

    def spy(img, lines, org, size=20, color=(255, 255, 255), bold=False):
        calls.append((" ".join(lines), size, bold))
        return real(img, lines, org, size, color, bold)
    monkeypatch.setattr(render, "put_text", spy)
    return calls


def test_numbers_and_formulas_are_big_enough_for_the_back_row(monkeypatch):
    from airgeo.ui.hud import draw_legend
    from airgeo.ui.render import draw_tool_overlay
    c, sel = _selected(TRI_345, {"angles", "perimeter", "area"})
    c.board.fit(1, c.fit_box)
    s = c.board.get(1)
    c.board.scale = math.dist(*s["pts"][:2]) / 3                         # sau khi phóng to: AB = 3 cm
    calls = _spy_text(monkeypatch)
    draw_tool_overlay(np.zeros((720, 1280, 3), np.uint8), c)
    size = {s: (sz, b) for s, sz, b in calls}
    assert size["AB = 3 cm"][0] >= 28                                    # nhãn cạnh
    assert size["h = BC"][0] >= 28                                       # đường cao (vuông tại B: trùng BC)
    assert min(sz for s, sz, _ in calls if s.startswith("góc")) >= 28    # viên góc
    assert size["P = AB + BC + CA"][0] >= 26                                # dòng công thức
    assert size["= 12 cm"] == (34, True)                               # dòng kết quả: to nhất, đậm
    calls.clear()
    draw_legend(np.zeros((720, 1280, 3), np.uint8))
    assert calls[-1][1] >= 24                                            # bảng gợi ý


@pytest.mark.parametrize("shape", [TRI_345, {"kind": "rect", "pts": [(0.0, 0.0), (600.0, 0.0), (600.0, 300.0),
                                                                   (0.0, 300.0)]}])   # chữ nhật 2:1: tiêu đề bảng dài
def test_big_formula_panel_stays_in_frame_and_off_the_fitted_shape(shape):
    from airgeo.ui.render import draw_formulas, side_chips
    for toolbar in (False, True):
        c, sel = _selected(shape, {"angles", "perimeter", "area"})
        if toolbar:
            c.do("bar")
        c.board.fit(1, c.fit_box)
        s = c.board.get(1)
        x0, y0, x1, y1 = draw_formulas(np.zeros((720, 1280, 3), np.uint8), s, sel, 100.0, "cm")
        assert x0 >= 0 and y1 <= 720 - 40 and x1 <= 1280
        right = max([p[0] for p in s["pts"]] + [x + hw for _, (x, _), (hw, _) in side_chips(s, 100.0, "cm").values()])
        assert x0 > right, (toolbar, x0, right)


def test_cursor_shape_tells_which_gesture_presses():
    def cursor(gesture="pinch", tool="draw", pinched=False):
        f = np.zeros((200, 200, 3), np.uint8)
        draw_hand(f, None, FrameResult((100, 100), (100, 100), pinched, False), False, gesture, tool)
        return f
    pinch = cursor()
    assert pinch[100, 114].any() and pinch[100, 100].any() and not pinch[100, 107].any()   # vòng mảnh + chấm tâm
    two = cursor("two_finger", "select")
    assert two[100, 114].any() and two[100, 108].any() and not two[100, 100].any()      # vòng đôi, tâm rỗng
    erase = cursor("two_finger", "erase")
    assert tuple(erase[100, 114]) == (0, 0, 255)                                         # công cụ Xóa: vòng đỏ
    for args in (("pinch", "draw"), ("two_finger", "erase"), ("two_finger", None)):      # None: màn bài đo K
        pressed = cursor(*args, pinched=True)
        assert tuple(pressed[100, 100]) == (0, 255, 255)                                 # đang bấm: vàng đặc


def test_strokes_get_a_dark_halo_on_a_bright_wall():
    from airgeo.ui.render import draw_selection
    white = np.full((200, 400, 3), 255, np.uint8)
    line = {"kind": "line", "pts": [(50, 100), (350, 100)], "id": 1}
    out = draw_canvas(white, [line], [(50, 160), (350, 160)])
    assert out[100, 200].max() > 200 and out[160, 200].min() > 200      # nét vẫn sáng
    assert out[104, 200].max() < 80 and out[163, 200].max() < 80        # viền tối sát nét (không có: 153)
    sel = np.full((200, 400, 3), 255, np.uint8)
    draw_selection(sel, line)
    assert sel[105, 120].max() < 80                                     # viền hình đang chọn cũng có quầng tối


def test_ok_is_primary_with_thick_border_not_a_selected_fill():
    from airgeo.ui.edit_panel import draw_edit_panel
    from airgeo.ui.render import BUTTON_ON
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append({"kind": "triangle", "pts": [(490.0, 450.0), (790.0, 450.0), (640.0, 250.0)],
                           "raw": [], "id": 1, "locked": False})
    c.panel.open(c.board.shapes[0], "AB", c.board)
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_edit_panel(frame, c.panel, "cm", None)
    x0, y0, x1, y1 = (int(v) for v in c.panel.button_rects["ok"])
    cx0, cy0, _, _ = (int(v) for v in c.panel.button_rects["cancel"])
    assert tuple(frame[y0 + 6, x0 + 6]) != BUTTON_ON                    # không tô nền "đang bật"
    assert frame[(y0 + y1) // 2, x0 + 2].min() > 150                    # viền dày
    assert frame[cy0 + 20, cx0 + 2].max() < 100                         # nút thường: viền mảnh


def test_big_side_chips_do_not_sit_on_their_edge():
    from airgeo.geometry.construct import label_edges
    from airgeo.ui.render import side_chips
    wide_rect = {"kind": "rect", "pts": [(100.0, 100.0), (500.0, 100.0), (500.0, 300.0), (100.0, 300.0)]}
    left_leg = {"kind": "triangle", "pts": [(100.0, 500.0), (500.0, 500.0), (100.0, 300.0)]}   # CA dọc sát lề trái
    for shape in (TRI_345, wide_rect, left_leg):
        c, _ = _selected(shape, set())
        c.board.fit(1, c.fit_box)
        s = c.board.get(1)
        pts, edges = s["pts"], label_edges(s)
        for f, (_, (x, y), (hw, hh)) in side_chips(s, math.dist(*pts[:2]) / 3, "cm").items():
            assert 0 <= x - hw and x + hw <= 1280 and 0 <= y - hh and y + hh <= 720, (f, x, y)   # trong khung
            hw, hh = hw + 6, hh + 6                                              # + nửa nét viền và quầng
            a, b = edges[f]
            for k in range(101):
                px, py = a[0] + (b[0] - a[0]) * k / 100, a[1] + (b[1] - a[1]) * k / 100
                assert not (abs(px - x) < hw and abs(py - y) < hh), (shape["kind"], f, (px, py))
