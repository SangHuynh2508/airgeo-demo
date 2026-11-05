"""Công cụ Xóa: rê con trỏ thì hình bên dưới được tô đỏ; chụm vào hình thì xóa hình đó (1 bước Undo)."""


class EraseTool:
    def __init__(self, config):
        self.hit_radius = config.hit_radius
        self.hovered = None         # id hình dưới con trỏ (để tô đỏ)

    def on_event(self, ev, ctl):
        shape = ctl.board.shape_at(ev.pos, self.hit_radius)
        if ev.kind == "hover":
            self.hovered = shape["id"] if shape else None
        elif ev.kind == "down" and shape:
            ctl.board.remove(shape["id"])
            self.hovered = None

    def end(self, ctl):
        self.hovered = None
