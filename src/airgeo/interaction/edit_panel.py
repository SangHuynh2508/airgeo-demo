"""Bảng nhập số đo (logic và bố cục; vẽ ở ui/edit_panel.py).

Nhập số bằng 2 cách cùng lúc vào ô đang chọn:
  - Viết số trên không trong ô viết (chụm ngón cái + trỏ như vẽ); gesture/digits.py nhận dạng từng chữ số.
  - Bàn phím máy tính: số, dấu chấm, Backspace, Enter = OK, Tab = ô kế, Esc = Hủy.
Nút (áp 2 ngón): `.` `←` (xóa chữ số cuối) `Xóa` (xóa cả ô) `OK` `Hủy`.

Bảng có đủ các ô của hình (tam giác AB BC CA, chữ nhật dai rong, tròn r, đoạn thẳng d) để nhập cả bộ số rồi dựng
hình 1 lần. Chưa có tỉ lệ: ô đầu tiên có số làm chuẩn, ô trống giữ tỉ lệ cạnh như đang vẽ. Dựng xong hình được
phóng to ra giữa vùng vẽ (construct.fit) – tỉ lệ px/cm nhân theo nên số đo giữ đúng số đã nhập.
"""
from airgeo.geometry.construct import build, current_lengths, field_names, fit
from airgeo.geometry.units import fmt_length, to_px, to_units, trim
from airgeo.gesture.digits import DigitReader

MAX_LEN = 8
GAP = 12
PAD_SLOP = 16       # chụm (trung điểm cái-trỏ) lệch mép ô viết tới chừng này vẫn là viết; ô / nút cách xa hơn
BUTTONS = ["dot", "back", "clear", "ok", "cancel"]


class EditPanel:
    def __init__(self, config, width, height):
        self.W, self.H, self.top = width, height, config.toolbar_height
        self.is_open = False
        self.kind, self.fields, self.values = None, [], {}
        self.focus, self.fresh, self.error = None, False, ""
        self.base, self.cur = "", None          # phần số có trước khi viết / nét đang viết
        self._layout()
        self.reader = DigitReader(self.pad_rect[3] - self.pad_rect[1])

    def _layout(self):
        g = GAP
        pw = min(760, self.W - 2 * g)
        bh = 56 if self.H >= 600 else 44
        s = 2 * PAD_SLOP
        pad_h = max(110, min(220, self.H - 2 * g - (40 + 60 + bh + 34 + 5 * g + s)))
        ph = 40 + 60 + pad_h + bh + 34 + 5 * g + s
        x0, y0 = (self.W - pw) // 2, max(g, (self.H - ph) // 2)
        ix, iw = x0 + g, pw - 2 * g
        self.rect = (x0, y0, x0 + pw, y0 + ph)
        self.title_pos = (ix, y0 + g)
        fy = y0 + g + 40
        fw = (iw - 2 * g) // 3
        self.field_rects = [(ix + i * (fw + g), fy, ix + i * (fw + g) + fw, fy + 60) for i in range(3)]
        py = fy + 60 + g + PAD_SLOP
        self.pad_rect = (ix, py, ix + iw, py + pad_h)
        by = py + pad_h + g + PAD_SLOP
        bw = (iw - 4 * g) // 5
        self.button_rects = {b: (ix + i * (bw + g), by, ix + i * (bw + g) + bw, by + bh) for i, b in enumerate(BUTTONS)}
        self.error_pos = (ix, by + bh + g // 2)

    # ---- Mở / đóng ----
    def open(self, shape, field, board):
        self.shape_id, self.kind = shape["id"], shape["kind"]
        self.fields = field_names(self.kind)
        cur = current_lengths(shape)
        self.values = {f: "" if board.scale is None else trim(to_units(cur[f], board.unit, board.scale))
                       for f in self.fields}
        self.focus_field(field)
        self.error, self.is_open = "", True

    def close(self):
        self.is_open = False
        self.cur = None

    # ---- Nhập số ----
    def focus_field(self, f):
        self.focus, self.fresh = f, True
        self.reader.clear()
        self.cur = None

    def next_field(self):
        i = self.fields.index(self.focus)
        self.focus_field(self.fields[(i + 1) % len(self.fields)])

    def type(self, ch):
        """Bàn phím / nút: chữ số, ".", "<-". Phần đã viết trong ô viết được giữ lại thành số thường."""
        self.reader.clear()
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

    def in_pad(self, pos):
        x0, y0, x1, y1 = self.pad_rect
        return x0 - PAD_SLOP <= pos[0] <= x1 + PAD_SLOP and y0 - PAD_SLOP <= pos[1] <= y1 + PAD_SLOP

    def _pen(self, ev):
        """Nét viết trong ô viết: down bắt đầu, move nối thêm, up nhận dạng lại cả dãy."""
        if ev.kind == "down":
            if not self.reader.groups:      # chữ số viết đầu tiên thay số điền sẵn, sau khi gõ thì viết tiếp vào
                self.base = "" if self.fresh else self.values[self.focus]
            self.cur = [ev.pos]
        elif ev.kind == "move":
            self.cur.append(ev.pos)
        elif ev.kind == "up":
            self.reader.add(self.cur, self.base)
            self.cur = None
            if self.reader.groups:          # chụm chập chờn bị bỏ thì ô giữ nguyên
                self.values[self.focus] = (self.base + self.reader.text)[:MAX_LEN]
                self.fresh, self.error = False, ""

    def press(self, name):
        if name == "back":
            if self.reader.groups:
                self.reader.pop()
                self.values[self.focus] = self.base + self.reader.text
            else:
                self.type("<-")
        elif name == "dot":
            self.type(".")
        elif name == "clear":
            self.reader.clear()
            self.values[self.focus], self.base, self.fresh = "", "", False

    # ---- OK ----
    def submit(self, board, box):
        shape = board.get(self.shape_id)
        if shape is None or shape["kind"] != self.kind:
            self.close()                # hình đã bị xóa / Undo mất trong lúc bảng mở
            return False
        scale = board.scale
        entered = {}
        for f in self.fields:
            s = self.values[f]
            if s == "":
                if scale is not None:
                    self.error = f"Chưa nhập {f}"
                    return False
                continue                # chưa có tỉ lệ: ô trống giữ tỉ lệ cạnh hiện tại
            try:
                v = float(s)
            except ValueError:
                v = 0.0
            if v <= 0:
                self.error = f"{f} không hợp lệ"
                return False
            entered[f] = v
        if not entered:
            self.error = "Chưa nhập số nào"
            return False
        cur, unit = current_lengths(shape), board.unit
        if scale is None:
            first = next(f for f in self.fields if f in entered)
            scale = cur[first] / to_px(entered[first], unit, 1.0)
        lengths = {f: to_px(entered[f], unit, scale) if f in entered else cur[f] for f in self.fields}
        try:
            new = build(shape, lengths, lambda px: fmt_length(px, scale, unit))    # phóng to / thu nhỏ sau
        except ValueError as e:
            self.error = str(e)
            return False
        new, k = fit(new, box)
        board.apply_edit(self.shape_id, new, scale * k)
        self.close()
        return True

    # ---- Con trỏ / bàn phím ----
    def hit(self, pos):
        def inside(r):
            return r[0] <= pos[0] <= r[2] and r[1] <= pos[1] <= r[3]
        for f, r in zip(self.fields, self.field_rects):
            if inside(r):
                return ("field", f)
        for b, r in self.button_rects.items():
            if inside(r):
                return ("button", b)
        return None

    def on_event(self, ev, ctl):
        """Khi bảng mở, mọi lần chụm thuộc về bảng. Chụm bắt đầu trong ô viết là viết; còn lại chỉ lúc bắt đầu chụm
        (down) mới bấm."""
        if self.cur is not None or (ev.kind == "down" and self.in_pad(ev.pos)):
            if ev.kind != "hover":
                self._pen(ev)
            return
        if ev.kind != "down":
            return
        h = self.hit(ev.pos)
        if h is None:
            return
        what, arg = h
        if what == "field":
            self.focus_field(arg)
        elif arg == "ok":
            self.submit(ctl.board, ctl.fit_box)
        elif arg == "cancel":
            self.close()
        else:
            self.press(arg)

    def key(self, code, ctl):
        """Bàn phím máy tính khi bảng mở. Trả về True nếu đã dùng phím."""
        if 0 <= code < 128 and chr(code) in "0123456789.":
            self.type(chr(code))
        elif code == 8:
            self.type("<-")
        elif code == 13:
            self.submit(ctl.board, ctl.fit_box)
        elif code == 27:
            self.close()                # Esc = Hủy, không thoát app
        elif code == 9:
            self.next_field()
        else:
            return False
        return True
