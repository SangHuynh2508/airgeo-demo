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
            self.end(ctl)

    def end(self, ctl):
        """Kết thúc nét đang vẽ (khi nhả, hoặc khi đổi công cụ giữa chừng). Nét < 2 điểm bị bỏ."""
        if self.cur is not None and len(self.cur) >= 2:
            ctl.board.add_stroke(self.cur)
        self.cur = None
