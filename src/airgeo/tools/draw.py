"""Công cụ Vẽ: chụm = vẽ, nhả = kết thúc nét (nhận dạng trong Board.add_stroke)."""


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
        Nét không ra hình bị bỏ + thông báo; hình mới thay hình cũ, được phóng to ra giữa; nhả tay thì chuyển sang
        Chọn hình đó (đổi công cụ giữa chừng thì chỉ giữ hình)."""
        raw, self.cur = self.cur, None
        if raw is None or len(raw) < 2:
            return
        shape = ctl.board.add_stroke(raw)
        t = raw[-1][2]
        if shape["kind"] == "free":
            ctl.notify("Không nhận ra hình – vẽ lại", t)
        else:
            ctl.board.fit(shape["id"], ctl.fit_box)     # hình ra giữa, to rõ cho học sinh (tên hình ở cột Tính)
            if not select:
                return
            ctl.set_tool("select")      # chọn luôn để đo / kéo / sửa số
            ctl.tools["select"].selected = shape["id"]
