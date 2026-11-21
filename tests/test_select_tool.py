from helpers import place_tri, tri_path
import math
from airgeo.config import Config
from airgeo.interaction.controller import Controller
from airgeo.interaction.pointer import PointerEvent as E


def _ctl_with_line(stroke):
    c = Controller(Config(), 1280, 720)
    place_tri(c, 300)
    c.do("select")
    return c


def test_press_on_shape_selects_and_empty_deselects(stroke, press):
    c = _ctl_with_line(stroke)
    sel = c.tools["select"]
    press(c, (200, 310))
    assert sel.selected == c.board.shapes[0]["id"]
    press(c, (600, 600))
    assert sel.selected is None


def test_drag_moves_shape_in_one_undo_step(stroke):
    c = _ctl_with_line(stroke)
    before = list(c.board.shapes[0]["pts"])
    stroke(c, [(200, 300), (205, 300), (250, 350), (260, 350)])   # quá 10 px -> kéo
    moved = c.board.shapes[0]
    assert moved["pts"][0] == (160, 350)
    c.do("undo")
    assert c.board.shapes[0]["pts"] == before


def test_small_wobble_selects_without_moving(stroke):
    c = _ctl_with_line(stroke)
    before = list(c.board.shapes[0]["pts"])
    stroke(c, [(200, 300), (206, 304), (203, 298)])               # rung tay < 10 px
    assert c.board.shapes[0]["pts"] == before and c.tools["select"].selected is not None


def test_switching_tool_mid_pinch_is_safe():
    c = Controller(Config(), 1280, 720)
    tri = tri_path()
    c.dispatch(E("down", tri[0], 0.0))
    for i, p in enumerate(tri[1:], 1):
        c.dispatch(E("move", p, 0.03 * i))
    assert c.key(ord("g"), 0.5)                  # đổi sang Chọn khi đang vẽ: nét được giữ lại
    c.dispatch(E("move", (250, 300), 0.51))
    c.dispatch(E("up", (250, 300), 0.55))
    assert len(c.board.shapes) == 1 and c.tool == "select"


def test_leaving_select_clears_selection(stroke, press):
    c = _ctl_with_line(stroke)
    press(c, (200, 300))
    c.do("draw")
    assert c.tools["select"].selected is None


def test_pinch_near_middle_of_selected_edge_grabs_it_not_label(press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append({"kind": "triangle", "pts": [(100.0, 300.0), (300.0, 300.0), (200.0, 150.0)], "id": 1})
    c.do("select")
    press(c, (200, 300))
    press(c, (200, 310))                          # 10 px ngoài trung điểm cạnh đáy: vẫn là cầm hình
    assert not c.panel.is_open and c.tools["select"].selected == 1


TRI = {"kind": "triangle", "pts": [(490.0, 450.0), (790.0, 450.0), (640.0, 250.0)], "raw": [],
       "id": 1, "locked": False}


def _center(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def test_measure_menu_depends_on_kind():
    from airgeo.tools.select import SelectTool
    tool = SelectTool(Config(), 1280)
    keys = lambda kind, **extra: [k for k, _ in tool.menu({"kind": kind, "pts": [], **extra})]  # noqa: E731
    assert keys("triangle") == ["angles", "perimeter", "area"] == keys("rect")     # cạnh ghi trên nhãn cạnh
    assert keys("circle") == ["perimeter", "area"]
    assert keys("free") == []
    assert all(1280 - 170 <= r[0] and r[2] <= 1280 and r[1] >= 70 for _, r in tool.menu(TRI))


def test_measures_show_only_after_pressing_their_button(press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(TRI))
    c.do("select")
    sel = c.tools["select"]
    press(c, (640, 450))                          # chọn tam giác: chưa tính gì
    assert sel.selected == 1 and sel.show == set()
    angles = dict(sel.menu(c.board.shapes[0]))["angles"]
    press(c, _center(angles))
    assert sel.show == {"angles"} and sel.selected == 1
    press(c, _center(angles))                     # bấm lần nữa: ẩn
    assert sel.show == set()


def test_changing_selection_clears_measures(press, stroke):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(TRI))
    c.do("select")
    sel = c.tools["select"]
    press(c, (640, 450))
    press(c, _center(dict(sel.menu(c.board.shapes[0]))["area"]))
    stroke(c, [(640, 450), (660, 470), (680, 490)])   # kéo chính hình đó: vẫn giữ
    assert sel.show == {"area"}
    press(c, (100, 650))                          # bấm chỗ trống: bỏ chọn, tắt hết
    assert sel.selected is None and sel.show == set()


def test_press_inside_triangle_grabs_and_drags_it(stroke):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(TRI))
    c.do("select")
    stroke(c, [(640, 380), (660, 380), (690, 400)])   # giữa tam giác, không chạm cạnh
    assert c.tools["select"].selected == 1 and c.board.shapes[0]["pts"][0] == (540.0, 470.0)


def test_stray_press_while_moving_to_menu_keeps_selection(stroke, press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(TRI))
    c.do("select")
    sel = c.tools["select"]
    press(c, (640, 380))                                       # chọn tam giác -> cột "Tinh:" hiện
    stroke(c, [(850, 400), (950, 300), (1100, 200)], t0=1.0)   # 2 ngón vô tình áp lúc đang di tay
    assert sel.selected == 1
    press(c, (900, 600), t=1.5)                                # chạm rồi nhả tại chỗ trống: vẫn bỏ chọn được
    assert sel.selected is None
    press(c, (640, 380), t=1.8)
    assert sel.selected == 1
    _, (x0, y0, x1, y1) = sel.menu(c.board.get(1))[0]
    press(c, ((x0 + x1) / 2, (y0 + y1) / 2), t=2.0)
    assert sel.show == {"angles"}


def test_dragged_shape_undone_mid_drag_does_not_crash(stroke):
    c = Controller(Config(), 1280, 720)
    place_tri(c, 300)
    c.do("draw")
    place_tri(c, 500)
    c.do("select")
    c.dispatch(E("down", (200, 500), 1.0))
    c.dispatch(E("move", (200, 550), 1.03))
    c.key(ord("u"), 1.04)
    c.key(ord("u"), 1.05)                                # gỡ luôn nét đang kéo
    c.dispatch(E("move", (200, 600), 1.06))
    c.dispatch(E("up", (200, 600), 1.1))
    assert [s["id"] for s in c.board.shapes] == [1]


RECT = {"kind": "rect", "pts": [(500.0, 350.0), (700.0, 350.0), (700.0, 450.0), (500.0, 450.0)], "raw": [],
        "id": 1, "locked": False}


def _rotate_drag(c, deg, t0=1.0):
    """Áp 2 ngón vào tay cầm rồi kéo vòng quanh tâm (600, 400) thêm deg độ."""
    h = c.tools["select"].handle(c.board.get(1))
    c.dispatch(E("down", h, t0))
    cx, cy = 600, 400
    a0 = math.atan2(h[1] - cy, h[0] - cx)
    a1 = a0 + math.radians(deg)
    end = (cx + 120 * math.cos(a1), cy + 120 * math.sin(a1))
    for k in range(1, 11):                               # đi vòng quanh tâm
        a = a0 + (a1 - a0) * k / 10
        c.dispatch(E("move", (cx + 120 * math.cos(a), cy + 120 * math.sin(a)), t0 + k * 0.03))
    c.dispatch(E("up", end, t0 + 0.4))


def test_rotation_handle_turns_shape_and_snaps_to_axis(press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(RECT))
    c.do("select")
    press(c, (600, 450))
    assert c.tools["select"].handle(c.board.get(1)) is not None
    _rotate_drag(c, 87)                                   # thiếu 3° nữa là đứng: hít về 90°
    pts = c.board.get(1)["pts"]
    xs = sorted(round(p[0]) for p in pts)
    assert xs == [550, 550, 650, 650]                     # quay đúng 90°, hít thẳng trục
    c.do("undo")
    assert c.board.get(1)["pts"] == RECT["pts"]          # cả lần xoay = 1 bước Undo


def test_circle_has_no_rotation_handle():
    from airgeo.tools.select import SelectTool
    tool = SelectTool(Config(), 1280, 720)
    assert tool.handle({"kind": "circle", "pts": [], "center": (600.0, 530.0), "radius": 40.0}) is None


def _drag_to(c, pts, t0=3.0):
    for i, p in enumerate(pts):
        c.dispatch(E("down" if i == 0 else "move", p, t0 + i * 0.03))


def test_drag_into_top_left_corner_zone_deletes_at_once_and_undo_puts_it_back(stroke):
    c = _ctl_with_line(stroke)
    before = list(c.board.shapes[0]["pts"])
    _drag_to(c, [(200, 300), (220, 320), (150, 150), (60, 60)])     # vào vùng góc trên trái: xóa ngay, chưa cần nhả
    assert c.board.shapes == [] and c.tools["select"].selected is None and c.message == "Đã xóa hình"
    c.dispatch(E("move", (300, 300), 3.2))
    c.dispatch(E("up", (300, 300), 4.0))                            # rê / nhả sau đó không làm gì thêm
    assert c.board.shapes == []
    c.do("undo")
    assert c.board.shapes[0]["pts"] == before                       # về chỗ cũ trước khi kéo


def test_drag_near_but_outside_corner_zone_keeps_shape(stroke):
    c = _ctl_with_line(stroke)
    _drag_to(c, [(200, 300), (220, 320), (200, 200), (600, 500)])   # (200, 200) cách góc 283 px
    c.dispatch(E("up", (600, 500), 4.0))
    assert len(c.board.shapes) == 1


def test_corner_zone_ignores_rotation(stroke):
    c = _ctl_with_line(stroke)
    sel = c.tools["select"]
    c.dispatch(E("down", (200, 300), 2.0)); c.dispatch(E("up", (200, 300), 2.1))
    h = sel.handle(c.board.shapes[0])
    _drag_to(c, [h, (h[0] + 30, h[1] + 30), (60, 60)])
    c.dispatch(E("up", (60, 60), 4.0))
    assert len(c.board.shapes) == 1


def test_corner_zone_is_drawn_only_while_dragging(stroke):
    import numpy as np
    from airgeo.ui.render import draw_tool_overlay
    c = _ctl_with_line(stroke)
    frame = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(frame, c)
    assert not frame[60:120, 60:120].any()
    _drag_to(c, [(200, 300), (220, 320), (600, 500)])
    draw_tool_overlay(frame, c)
    assert frame[60:120, 60:120].any()


def test_near_corner_zone_warns_grows_and_paints_shape_red(stroke):
    import numpy as np
    from airgeo.tools.select import TRASH_R
    from airgeo.ui.render import ERASE_COLOR, draw_tool_overlay
    c = _ctl_with_line(stroke)
    sel = c.tools["select"]
    _drag_to(c, [(200, 300), (220, 320), (400, 400)])
    far = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(far, c)
    assert not sel.near_trash and not far[2:6, TRASH_R + 12].any()
    c.dispatch(E("move", (130, 130), 3.2))          # cách góc 184 px: ngoài vùng xóa, trong dải cảnh báo
    near = np.zeros((720, 1280, 3), np.uint8)
    draw_tool_overlay(near, c)
    assert sel.near_trash and len(c.board.shapes) == 1
    assert near[2:6, TRASH_R + 12].any()                          # vùng xóa to ra
    assert tuple(near[130, 180]) == ERASE_COLOR                   # hình tô đỏ: sắp xóa
    c.dispatch(E("move", (600, 500), 3.3))
    assert not sel.near_trash
    c.dispatch(E("move", (60, 60), 3.4))                          # vào hẳn mới xóa
    assert c.board.shapes == [] and not sel.near_trash


def test_dragged_shape_stays_inside_the_frame_and_keeps_its_grip(stroke):
    c = _ctl_with_line(stroke)
    _drag_to(c, [(200, 300), (220, 320), (1250, 700)])            # tay kéo quá mép phải
    assert max(p[0] for p in c.board.shapes[0]["pts"]) == 1280
    c.dispatch(E("move", (1100, 700), 3.2))                       # tay quay lại: hình theo tay như lúc cầm
    assert c.board.shapes[0]["pts"][0] == (1000, 700)
    c.do("bar")                                                   # dải nút hiện: mép trên vùng vẽ hạ xuống
    c.dispatch(E("move", (1100, 10), 3.3))
    assert min(p[1] for p in c.board.shapes[0]["pts"]) == c.toolbar.height


def test_undo_twice_mid_drag_then_corner_does_not_claim_a_deletion(stroke):
    c = _ctl_with_line(stroke)
    _drag_to(c, [(200, 300), (220, 320), (400, 400)])
    c.key(ord("u"), 3.5)                                          # gỡ lần kéo
    c.key(ord("u"), 3.6)                                          # gỡ luôn nét vẽ
    c.dispatch(E("move", (60, 60), 3.7))
    c.dispatch(E("up", (60, 60), 4.0))
    assert c.board.shapes == [] and c.message != "Đã xóa hình"


def test_drag_undo_redo_and_new_drag_drops_redo(stroke):
    c = _ctl_with_line(stroke)
    before = list(c.board.shapes[0]["pts"])
    stroke(c, [(200, 300), (205, 300), (250, 350), (260, 350)])
    moved = list(c.board.shapes[0]["pts"])
    c.key(ord("u"), 5.0)
    assert c.board.shapes[0]["pts"] == before
    c.key(ord("y"), 5.1)
    assert c.board.shapes[0]["pts"] == moved
    c.key(ord("u"), 5.2)
    stroke(c, [(200, 300), (205, 300), (200, 400)], t0=6.0)       # kéo mới sau Undo: nhánh làm lại bỏ đi
    assert not c.board.redo()


def test_rotation_handle_stays_near_a_345_triangle_when_angle_chips_take_the_corner():
    import numpy as np
    from airgeo.geometry.hit import distance_to_shape
    from airgeo.tools.select import HANDLE_R
    from airgeo.ui.render import draw_tool_overlay
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append({"kind": "triangle", "pts": [(300.0, 500.0), (600.0, 500.0), (600.0, 100.0)], "raw": [],
                           "id": 1, "locked": False})
    c.board.fit(1, c.fit_box)
    c.board.scale = math.dist(*c.board.get(1)["pts"][:2]) / 3
    c.do("select")
    sel = c.tools["select"]
    sel.selected, sel.show = 1, {"angles", "perimeter", "area"}
    for bar in (False, True):
        if bar:
            c.do("bar")
        draw_tool_overlay(np.zeros((720, 1280, 3), np.uint8), c)   # như app: viên góc của frame trước
        s = c.board.get(1)
        hx, hy = sel.handle(s)
        assert distance_to_shape((hx, hy), s) <= 120, (bar, hx, hy)  # không ra góc trống xa hình
        assert all(math.dist((hx, hy), p) > 60 for p in s["pts"])
        assert not any(x0 - HANDLE_R <= hx <= x1 + HANDLE_R and y0 - HANDLE_R <= hy <= y1 + HANDLE_R
                       for x0, y0, x1, y1 in sel.avoid)
        assert hy - HANDLE_R > c.bounds[1]
    # góc trên phải khung bao trống nhưng xa hình (cạnh huyền đi xuống phải): cũng không đặt ở đó
    tri = {"kind": "triangle", "pts": [(130.0, 540.0), (990.0, 540.0), (130.0, 90.0)]}
    sel.avoid = []
    assert distance_to_shape(sel.handle(tri), tri) <= 120


def test_rotation_undo_then_redo(press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(RECT))
    c.do("select")
    press(c, (600, 450))
    _rotate_drag(c, 87)
    turned = list(c.board.get(1)["pts"])
    c.key(ord("u"), 2.0)
    assert c.board.get(1)["pts"] == RECT["pts"]
    c.key(ord("y"), 2.1)
    assert c.board.get(1)["pts"] == turned


def test_corner_delete_undo_then_redo_deletes_again(stroke):
    c = _ctl_with_line(stroke)
    before = list(c.board.shapes[0]["pts"])
    _drag_to(c, [(200, 300), (220, 320), (150, 150), (60, 60)])
    c.dispatch(E("up", (60, 60), 4.0))
    c.key(ord("u"), 4.1)
    assert c.board.shapes[0]["pts"] == before
    c.key(ord("y"), 4.2)
    assert c.board.shapes == []
    c.key(ord("u"), 4.3)
    c.key(ord("u"), 4.4)                                          # gỡ tiếp: về trước lúc đặt hình
    assert c.board.shapes == [] and c.key(ord("y"), 4.5) and c.board.shapes[0]["pts"] == before


def test_rotation_handle_keeps_off_vertices_where_angle_values_sit():
    from airgeo.tools.select import SelectTool
    tool = SelectTool(Config(), 1280, 720)
    pts = [(370.0, 610.0), (750.0, 610.0), (750.0, 110.0)]          # đỉnh C đúng góc trên phải khung bao
    for shape in ({"kind": "triangle", "pts": pts},
                  {"kind": "rect", "pts": [(310.0, 110.0), (810.0, 110.0), (810.0, 610.0), (310.0, 610.0)]}):
        hx, hy = tool.handle(shape)                                  # chữ nhật: góc nào cũng có đỉnh -> ra xa hơn
        assert all(math.dist((hx, hy), p) > 60 for p in shape["pts"])


def test_rotation_handle_tries_every_distance_top_right_first_and_avoids_angle_chips():
    from airgeo.tools.select import SelectTool
    tool = SelectTool(Config(), 1280, 720)
    tri = {"kind": "triangle", "pts": [(370.0, 610.0), (750.0, 610.0), (750.0, 110.0)]}   # C ở góc trên phải
    hx, hy = tool.handle(tri)
    assert hx > 750 and hy < 110                                 # vẫn góc trên phải, ra xa hơn (không nhảy sang trái)
    tool.avoid = [(hx - 60, hy - 15, hx + 60, hy + 15)]          # viên "góc C = ..." nằm đúng chỗ đó
    hx2, hy2 = tool.handle(tri)
    assert (hx2, hy2) != (hx, hy) and not (hx - 80 <= hx2 <= hx + 80 and hy - 35 <= hy2 <= hy + 35)


def test_rotation_handle_grabs_within_35_px(press):
    c = Controller(Config(), 1280, 720)
    c.board.shapes.append(dict(RECT))
    c.do("select")
    press(c, (600, 450))
    sel = c.tools["select"]
    h = sel.handle(c.board.get(1))
    c.dispatch(E("down", (h[0] + 33, h[1]), 1.0))
    assert sel.rotation is not None


def test_rotation_handle_stays_below_visible_toolbar():
    c = Controller(Config(), 1280, 720)
    c.do("bar")                                                        # hiện dải nút
    tri = {"kind": "triangle", "pts": [(310.0, 300.0), (810.0, 300.0), (310.0, 90.0)]}   # góc trên phải trống
    hx, hy = c.tools["select"].handle(tri)
    assert hy - 14 > c.toolbar.height


def test_rotation_handle_never_sits_on_an_angle_chip_under_visible_toolbar():
    c = Controller(Config(), 1280, 720)
    c.do("bar")
    sel = c.tools["select"]
    tri = {"kind": "triangle", "pts": [(390.0, 540.0), (730.0, 540.0), (730.0, 90.0)]}   # C sát dải nút
    sel.avoid = [(257, 553, 383, 593), (709, 563, 835, 601), (746, 73, 886, 107)]     # viên góc A, B, C
    hx, hy = sel.handle(tri)
    assert not any(x0 - 20 <= hx <= x1 + 20 and y0 - 20 <= hy <= y1 + 20 for x0, y0, x1, y1 in sel.avoid)
    assert hy - 20 > c.toolbar.height
