"""Công cụ Chọn: chụm vào hình để chọn; chụm rồi kéo quá drag_threshold px thì hình đi theo tay.
Chụm vào nhãn cạnh (AB, BC, dai, r...) của hình đang chọn thì mở bảng nhập số đo.
Cột nút "Tinh:" ở mép phải: bấm nút nào thì mới hiện số đo đó (cạnh, góc, chu vi...) của hình đang chọn;
đổi / bỏ chọn hình thì tắt hết.

Tay cầm xoay (chấm ở góc trên phải khung bao hình đang chọn, trừ hình tròn): áp 2 ngón vào rồi kéo vòng quanh
hình thì hình xoay quanh tâm; cạnh gần trục lệch <= SNAP_DEG thì hít thẳng ngang / dọc.

Kéo hình vào vùng xóa ở góc trên trái (hiện ra khi đang kéo) là xóa ngay, không cần nhả (nhả sát mép dễ mất tay);
Undo trả hình về chỗ cũ. Tay tới gần (cách vùng < TRASH_WARN px) thì vùng to ra và hình tô đỏ để kịp rút tay.
Hình kéo không ra khỏi vùng vẽ (khung bao kẹp trong 0..W, top..H); tay quay lại thì hình theo tay như lúc cầm. Không để ở góc dưới: đưa tay xuống thì cổ tay ra khỏi khung hình, MediaPipe mất tay.

Cả lần kéo / xoay là 1 bước Undo (begin() 1 lần lúc bắt đầu). Rung tay nhỏ hơn ngưỡng chỉ là chọn.
"""
import math

from airgeo.geometry.hit import _bbox, contains, distance_to_shape
from airgeo.geometry.rotate import SNAP_DEG, center, rotate_points, snap_delta

# độ dài cạnh / bán kính luôn ghi trên nhãn cạnh (draw_selection) nên cột Tính chỉ còn góc, chu vi, diện tích
MEASURES = {"line": [], "triangle": ["angles", "perimeter", "area"],
            "rect": ["angles", "perimeter", "area"], "circle": ["perimeter", "area"]}
MENU_W, MENU_H, MENU_GAP = 150, 44, 8
HANDLE_OFFSET = 32
HANDLE_R, HANDLE_HIT = 20, 35     # bán kính vẽ / vùng bấm tay cầm xoay (px)
HANDLE_NEAR = 110                 # tay cầm cách nét hình không quá chừng này px (góc khung bao trống xa hình thì bỏ)
TRASH_R = 136                     # vùng xóa: 1/4 hình tròn bán kính chừng này px ở góc trên trái
TRASH_WARN = 60                   # dải cảnh báo "sắp xóa" quanh vùng xóa


class SelectTool:
    def __init__(self, config, width=1280, height=720):
        self.hit_radius = config.hit_radius
        self.label_radius = config.label_radius
        self.drag_threshold = config.drag_threshold
        self.menu_x = width - MENU_W - 10
        self.menu_y = config.toolbar_height + 40          # chừa chỗ chữ "Tinh:"
        self.width, self.height = width, height
        self.top = 0                # mép trên vùng vẽ: 0 khi dải nút ẩn (mặc định), Controller cập nhật khi bật / tắt
        self.trash = (0, 0)         # tâm vùng xóa (góc trên trái)
        self.near_trash = False     # đang kéo, tay sát vùng xóa: vùng to ra, hình tô đỏ
        self.avoid = []             # khung viên số đo góc vừa vẽ (render ghi mỗi frame): tay cầm xoay không đè lên
        self.rotation = None        # đang xoay: {"pivot", "a0", "pts0", "kind", "applied", "pos"}
        self.selected = None        # id hình đang chọn
        self.show = set()           # số đo đang hiện của hình đang chọn
        self._grab = None           # điểm bắt đầu chụm trên hình (None = lần chụm này không kéo gì)
        self._last = None
        self._dragging = False
        self._snap = None           # bản sao Undo của lần kéo hiện tại
        self._clear_at = None       # điểm chạm vào chỗ trống: nhả tại đây thì bỏ chọn

    def menu(self, shape):
        """[(số đo, (x0, y0, x1, y1))] – các nút trong cột "Tinh:" cho loại hình này."""
        return [(k, (self.menu_x, self.menu_y + i * (MENU_H + MENU_GAP),
                     self.menu_x + MENU_W, self.menu_y + i * (MENU_H + MENU_GAP) + MENU_H))
                for i, k in enumerate(MEASURES.get(shape["kind"], []))]

    def handle(self, shape):
        """Vị trí tay cầm xoay, trong vùng vẽ, ngoài cột Tính; hình tròn không xoay. Ưu tiên góc trên phải khung bao (thử
        hết các khoảng cách). Góc đó bị đỉnh / viên số đo góc (self.avoid) chiếm thì lấy chỗ trống gần nó nhất quanh các
        đỉnh và các góc khung bao – sát hình, không nhảy ra góc khung bao trống xa hình (tam giác vuông bật Góc).
        Chỗ trống: cách đỉnh (tên đỉnh) > 60 px, không đè viên góc, ngoài hình, cách nét > HANDLE_HIT (không cướp
        lần cầm hình) nhưng không quá HANDLE_NEAR (góc khung bao trống – cạnh huyền đi xuống – cũng là xa hình)."""
        if shape is None or shape["kind"] == "circle":
            return None
        pts = shape["pts"]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        r = HANDLE_R + 4

        def spot(x, y):     # kẹp vào vùng vẽ (dưới dải nút, ngoài cột Tính, không sát mép dưới)
            return min(max(x, 20), self.menu_x - 20), min(max(y, self.top + 40), self.height - 40)

        def free(c):
            return (all(math.dist(c, p) > 60 for p in pts) and HANDLE_HIT + 5 < distance_to_shape(c, shape) <= HANDLE_NEAR
                    and not contains(c, shape) and not any(x0 - r <= c[0] <= x1 + r and y0 - r <= c[1] <= y1 + r
                                                           for x0, y0, x1, y1 in self.avoid))

        ideal = spot(max(xs) + HANDLE_OFFSET, min(ys) - HANDLE_OFFSET)
        for d in (HANDLE_OFFSET, HANDLE_OFFSET + 28):        # sát đỉnh thì ra xa hơn
            c = spot(max(xs) + d, min(ys) - d)
            if free(c):
                return c
        # ponytail: 12 hướng x 2 khoảng quanh mỗi đỉnh (~100 điểm); đủ cho tam giác / chữ nhật
        near = [spot(x + d * math.cos(math.radians(a)), y + d * math.sin(math.radians(a)))
                for x, y in pts for d in (70, 100) for a in range(0, 360, 30)]
        near += [spot(x, y) for d in (HANDLE_OFFSET, HANDLE_OFFSET + 28)
                 for x in (min(xs) - d, max(xs) + d) for y in (min(ys) - d, max(ys) + d)]
        return min(filter(free, near), key=lambda c: math.dist(c, ideal), default=ideal)

    def _label_at(self, board, pos):
        """Ô số đo có viên nhãn dưới pos: cả mặt viên (khung do render dùng để vẽ), ít nhất label_radius quanh tâm."""
        from airgeo.ui.render import side_chips     # render dùng hằng số của file này: nhập muộn tránh vòng lặp
        shape = board.get(self.selected) if self.selected else None
        if shape is None:
            return None, None
        r = self.label_radius
        for f, (_, (x, y), (hw, hh)) in side_chips(shape, board.scale, board.unit).items():
            if abs(pos[0] - x) <= max(hw, r) and abs(pos[1] - y) <= max(hh, r):
                return shape, f
        return shape, None

    def _menu_at(self, board, pos):
        shape = board.get(self.selected) if self.selected else None
        for k, (x0, y0, x1, y1) in self.menu(shape) if shape else []:
            if x0 <= pos[0] <= x1 and y0 <= pos[1] <= y1:
                return k
        return None

    def on_event(self, ev, ctl):
        board = ctl.board
        if ev.kind == "down":
            measure = self._menu_at(board, ev.pos)
            if measure:
                self.show ^= {measure}
                self._grab = None
                return
            h = self.handle(board.get(self.selected)) if self.selected else None
            if h and math.dist(ev.pos, h) <= HANDLE_HIT:
                shape = board.get(self.selected)
                p = center(shape)
                self.rotation = {"pivot": p, "a0": math.atan2(ev.pos[1] - p[1], ev.pos[0] - p[0]), "pos": ev.pos,
                                 "pts0": list(shape["pts"]), "kind": shape["kind"], "applied": 0.0}
                self._grab, self._dragging = ev.pos, False
                return
            shape, field = self._label_at(board, ev.pos)
            if field:
                ctl.panel.open(shape, field, board)
                self._grab = None
                return
            shape = board.shape_at(ev.pos, self.hit_radius)
            self._dragging = False
            if shape is None:
                # Chỗ trống: chỉ bỏ chọn khi chạm rồi nhả tại chỗ. Lúc di tay tới cột "Tinh:", 2 ngón hay
                # vô tình áp sát -> "bấm" giữa đường; tay đang di chuyển thì không tính là bỏ chọn.
                self._grab, self._clear_at = None, ev.pos
                return
            if shape["id"] != self.selected:
                self.show = set()   # số đo chỉ tính khi được yêu cầu, cho từng lần chọn
            self.selected = shape["id"]
            self._grab = ev.pos
        elif ev.kind == "move" and self._clear_at is not None:
            if math.dist(ev.pos, self._clear_at) > self.drag_threshold:
                self._clear_at = None
        elif ev.kind == "move" and self._grab is not None:
            if not self._dragging:
                if math.dist(ev.pos, self._grab) <= self.drag_threshold:
                    return
                self._dragging, self._last = True, self._grab
                self._snap = board.begin()
            if self.rotation:
                self._rotate(board, ev.pos)
                self._last = ev.pos
            else:
                # phần bị kẹp không tính vào _last: tay quay lại thì hình theo tay đúng chỗ cầm
                dx, dy = self._clamp(board.get(self.selected), ev.pos[0] - self._last[0], ev.pos[1] - self._last[1])
                board.translate(self.selected, dx, dy)
                self._last = (self._last[0] + dx, self._last[1] + dy)
            shape = board.get(self.selected)       # None nếu U gỡ mất hình giữa lúc kéo
            gap = math.dist(ev.pos, self.trash) if shape is not None and not self.rotation else math.inf
            self.near_trash = gap <= TRASH_R + TRASH_WARN
            if gap <= TRASH_R:
                board.undo(self._snap)   # hình về chỗ cũ rồi mới xóa: Undo trả hình về đúng chỗ trước khi kéo
                board.remove(self.selected)
                self.selected, self.show, self._grab, self._dragging = None, set(), None, False
                self.near_trash = False
                ctl.notify("Đã xóa hình", ev.t)
                return
        elif ev.kind == "up":
            if self._clear_at is not None:
                self.selected, self.show = None, set()
            self._grab, self._dragging, self._clear_at = None, False, None
            self.rotation, self.near_trash = None, False

    def _clamp(self, shape, dx, dy):
        """Dời (dx, dy) sao cho khung bao hình vẫn trong vùng vẽ; hình đã lỡ ra ngoài thì chỉ không cho ra thêm."""
        if shape is None:
            return dx, dy
        x0, y0, x1, y1 = _bbox(shape)
        return (min(max(dx, min(0, -x0)), max(0, self.width - x1)),
                min(max(dy, min(0, self.top - y0)), max(0, self.height - y1)))

    def _rotate(self, board, pos):
        r = self.rotation
        p = r["pivot"]
        delta = math.degrees(math.atan2(pos[1] - p[1], pos[0] - p[0]) - r["a0"])
        delta = (delta + 180) % 360 - 180
        target = delta + snap_delta({"kind": r["kind"], "pts": rotate_points(r["pts0"], delta, p)}, SNAP_DEG)
        board.rotate(self.selected, target - r["applied"], p)
        r["applied"], r["pos"] = target, pos

    def end(self, ctl):
        self.selected, self._grab, self._dragging, self._clear_at = None, None, False, None
        self.show, self.rotation, self.near_trash = set(), None, False
