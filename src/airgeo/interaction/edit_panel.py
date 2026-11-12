"""Bảng nhập số đo + bàn phím số trên không (logic và bố cục; vẽ ở ui/edit_panel.py).

Bảng có đủ các ô của hình (tam giác AB BC CA, chữ nhật dai rong, tròn r, đoạn thẳng d) để nhập
cả bộ số rồi dựng hình 1 lần (sửa lần lượt từng cạnh có thể kẹt ở bước giữa vì bất đẳng thức tam giác).

Tỉ lệ: lần OK đầu tiên (hoặc khi bật "Dat lai ti le") lấy ô đầu tiên có giá trị làm chuẩn,
scale = độ dài hiện tại của cạnh đó (px) / giá trị (cm) -> cạnh đó giữ nguyên kích thước;
nếu vậy mà hình tràn màn hình thì tỉ lệ tự thu nhỏ tới khi vừa.
"""
from airgeo.geometry.construct import OUT_OF_SCREEN, build, current_lengths, field_names
from airgeo.geometry.units import fmt_length, to_px, to_units, trim

KEYS = [["7", "8", "9"], ["4", "5", "6"], ["1", "2", "3"], [".", "0", "<-"]]
MAX_LEN = 8
GAP = 10
FIELD_W = 140


class EditPanel:
    def __init__(self, config, width, height):
        self.min_side = config.min_side_px
        self.W, self.H, self.top = width, height, config.toolbar_height
        # ponytail: phím co lại theo chiều cao khung hình (480p -> ~57 px); khung < 400 px thì bảng vẫn tràn
        self.k = max(30, min(config.key_size, int((height - self.top - GAP - 170) / 4)))
        self.is_open = False
        self.kind, self.fields, self.values, self.hints = None, [], {}, {}
        self.focus, self.fresh, self.error, self.reset_scale = None, False, "", False
        self._layout()

    def _layout(self):
        k, g = self.k, GAP
        inner_w = 3 * FIELD_W + 2 * g                          # 440 px
        pw, ph = inner_w + 2 * g, 170 + 4 * k                  # tiêu đề, hàng ô, 4 hàng phím, dòng lỗi
        x0 = (self.W - pw) // 2
        y0 = max(self.top + g, (self.top + self.H - ph) // 2)
        self.rect = (x0, y0, x0 + pw, y0 + ph)
        ix, iy = x0 + g, y0 + g
        self.title_pos = (ix, iy + 20)
        self.reset_rect = (ix + inner_w - 170, iy, ix + inner_w, iy + 26)
        self.field_rects = [(ix + i * (FIELD_W + g), iy + 30, ix + i * (FIELD_W + g) + FIELD_W, iy + 80)
                            for i in range(3)]
        ky = iy + 80 + g
        self.key_rects = {ch: (ix + c * (k + g), ky + r * (k + g), ix + c * (k + g) + k, ky + r * (k + g) + k)
                          for r, row in enumerate(KEYS) for c, ch in enumerate(row)}
        rx = ix + 3 * (k + g) + g
        self.ok_rect = (rx, ky, ix + inner_w, ky + k)
        self.cancel_rect = (rx, ky + k + g, ix + inner_w, ky + 2 * k + g)
        self.error_pos = (ix, ky + 4 * k + 3 * g + 22)

    # ---- Mở / đóng ----
    def open(self, shape, field, board):
        self.shape_id, self.kind = shape["id"], shape["kind"]
        self.fields = field_names(self.kind)
        cur = current_lengths(shape)
        self.hints = {f: f"~{cur[f]:.0f}px" for f in self.fields}
        self.values = {f: "" if board.scale is None else trim(to_units(cur[f], board.unit, board.scale))
                       for f in self.fields}
        self.focus, self.fresh = field, True
        self.error, self.reset_scale, self.is_open = "", False, True

    def close(self):
        self.is_open = False

    # ---- Gõ số ----
    def focus_field(self, f):
        self.focus, self.fresh = f, True

    def next_field(self):
        i = self.fields.index(self.focus)
        self.focus_field(self.fields[(i + 1) % len(self.fields)])

    def type(self, ch):
        v = self.values[self.focus]
        if self.fresh and ch != "<-":
            v = ""                      # phím đầu tiên sau khi chọn ô thay hẳn số điền sẵn
        self.fresh = False
        if ch == "<-":
            v = v[:-1]
        elif ch == "." and "." in v:
            pass
        elif len(v) < MAX_LEN:
            v += ch
        self.values[self.focus] = v
        self.error = ""

    # ---- OK ----
    def submit(self, board, bounds):
        shape = board.get(self.shape_id)
        if shape is None or shape["kind"] != self.kind:
            # hình đã bị xóa / Undo mất, hoặc Smart nhận dạng lại thành loại khác trong lúc bảng mở
            self.close()
            return False
        scale = None if self.reset_scale else board.scale
        entered = {}
        for f in self.fields:
            s = self.values[f]
            if s == "":
                if scale is not None:
                    self.error = f"Chua nhap {f}"
                    return False
                continue                # chưa có tỉ lệ: ô trống giữ độ dài hiện tại
            try:
                v = float(s)
            except ValueError:
                v = 0.0
            if v <= 0:
                self.error = f"{f} khong hop le"
                return False
            entered[f] = v
        if not entered:
            self.error = "Chua nhap so nao"
            return False
        cur, unit = current_lengths(shape), board.unit
        new_scale = scale is None
        if new_scale:
            first = next(f for f in self.fields if f in entered)
            scale = cur[first] / to_px(entered[first], unit, 1.0)
        for _ in range(20):
            lengths = {f: to_px(entered[f], unit, scale) if f in entered else cur[f] for f in self.fields}
            try:
                new = build(shape, lengths, bounds, self.min_side, lambda px: fmt_length(px, scale, unit))
                break
            except ValueError as e:
                self.error = str(e)
                # Đang chọn tỉ lệ mới mà hình tràn màn hình (vd. dai 5 rong 9 trên hình đang dẹt):
                # thu nhỏ tỉ lệ tới khi vừa. Tỉ lệ đã đặt thì không tự đổi, báo lỗi để người dùng sửa số.
                if not (new_scale and self.error == OUT_OF_SCREEN):
                    return False
                scale *= 0.8
        else:
            return False
        if board.collides(new, self.shape_id):
            self.error = "Hinh de len hinh khac - nhap so nho hon"
            return False
        board.apply_edit(self.shape_id, new, scale)
        self.close()
        return True

    # ---- Con trỏ / bàn phím ----
    def hit(self, pos):
        def inside(r):
            return r[0] <= pos[0] <= r[2] and r[1] <= pos[1] <= r[3]
        for f, r in zip(self.fields, self.field_rects):
            if inside(r):
                return ("field", f)
        for ch, r in self.key_rects.items():
            if inside(r):
                return ("key", ch)
        for name, r in (("ok", self.ok_rect), ("cancel", self.cancel_rect), ("reset", self.reset_rect)):
            if inside(r):
                return (name, None)
        return None

    def on_event(self, ev, ctl):
        """Khi bảng mở, mọi lần chụm thuộc về bảng; chỉ lúc bắt đầu chụm mới bấm."""
        if ev.kind != "down":
            return
        h = self.hit(ev.pos)
        if h is None:
            return
        what, arg = h
        if what == "field":
            self.focus_field(arg)
        elif what == "key":
            self.type(arg)
        elif what == "ok":
            self.submit(ctl.board, ctl.bounds)
        elif what == "cancel":
            self.close()
        elif what == "reset":
            self.reset_scale = not self.reset_scale

    def key(self, code, ctl):
        """Bàn phím máy tính khi bảng mở. Trả về True nếu đã dùng phím."""
        if 0 <= code < 128 and chr(code) in "0123456789.":
            self.type(chr(code))
        elif code == 8:
            self.type("<-")
        elif code == 13:
            self.submit(ctl.board, ctl.bounds)
        elif code == 27:
            self.close()                # Esc = Huy, không thoát app
        elif code == 9:
            self.next_field()
        else:
            return False
        return True
