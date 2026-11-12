"""Công cụ Vẽ: chụm = vẽ, nhả = kết thúc nét (Smart Shape nhận dạng trong Board.add_stroke)."""


class DrawTool:
    def __init__(self):
        self.cur = None     # nét đang vẽ: [(x_filt, y_filt, t)]

    def on_event(self, ev, ctl):
        if ev.kind == "down":
            self.cur = [(ev.pos[0], ev.pos[1], ev.t)]
        elif ev.kind == "move" and self.cur is not None:
            self.cur.append((ev.pos[0], ev.pos[1], ev.t))
        elif ev.kind == "up":
            self.end(ctl, select=True)

    def end(self, ctl, select=False):
        """Kết thúc nét đang vẽ (khi nhả, hoặc khi đổi công cụ giữa chừng). Nét < 2 điểm bị bỏ.
        Nét đè hình khác bị bỏ + thông báo; nhả tay ra hình nhận dạng được thì chuyển sang Chọn hình đó."""
        raw, self.cur = self.cur, None
        if raw is None or len(raw) < 2:
            return
        shape = ctl.board.add_stroke(raw)
        if shape is None:
            ctl.notify("Hinh moi de len hinh khac - ve o cho trong", raw[-1][2])
        elif select and shape["kind"] != "free":
            # hình nhận dạng được: chọn luôn để đo / kéo / sửa số; nét tự do thì vẽ tiếp
            ctl.set_tool("select")
            ctl.tools["select"].selected = shape["id"]
