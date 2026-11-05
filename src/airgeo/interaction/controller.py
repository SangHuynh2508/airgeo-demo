"""Bộ điều phối: chuyển sự kiện con trỏ tới bảng nhập / thanh nút / công cụ đang bật;
nút trên không và phím tắt gọi chung một hàm do().

Một lần chụm bắt đầu ở đâu (bảng nhập / thanh nút / vùng vẽ) thì cả lần chụm đó thuộc về chỗ đó:
chụm ở nút rồi kéo xuống vùng vẽ cũng không tạo nét. Khi bảng nhập mở, mọi lần chụm thuộc về bảng.
"""
from airgeo.document.board import Board
from airgeo.interaction.edit_panel import EditPanel
from airgeo.interaction.toolbar import Toolbar
from airgeo.tools.draw import DrawTool
from airgeo.tools.erase import EraseTool
from airgeo.tools.select import SelectTool

KEY_ACTIONS = {ord("u"): "undo", ord("c"): "clear", ord("s"): "smart", ord("n"): "unit",
               ord("v"): "draw", ord("g"): "select", ord("x"): "erase"}


class Controller:
    def __init__(self, config, width, height):
        self.board = Board(config.history_limit)
        self.toolbar = Toolbar(width, config)
        self.panel = EditPanel(config, width, height)
        self.bounds = (0, config.toolbar_height, width, height)   # vùng vẽ, dưới thanh nút
        self.tools = {"draw": DrawTool(), "select": SelectTool(config, width), "erase": EraseTool(config)}
        self.tool = "draw"
        self._owner = None          # ai nhận lần chụm hiện tại: "panel" | "toolbar" | "tool"

    def dispatch(self, ev):
        if ev.kind == "down":
            if self.panel.is_open:
                self._owner = "panel"
            else:
                self._owner = "toolbar" if self.toolbar.contains(ev.pos) else "tool"
        if ev.kind == "hover":
            owner = "panel" if self.panel.is_open else "tool"
        else:
            owner = self._owner
        if ev.kind == "up":
            self._owner = None
        if owner == "panel":
            self.panel.on_event(ev, self)
        elif owner == "toolbar":
            if ev.kind == "down":
                action = self.toolbar.press(ev.pos, ev.t)
                if action:
                    self.do(action)
        elif owner == "tool":
            self.tools[self.tool].on_event(ev, self)

    def gesture_for(self, pos):
        """Cử chỉ bấm ở chỗ con trỏ: vẽ trong vùng vẽ bằng chụm ngón cái + trỏ; thanh nút, bảng nhập,
        Chọn, Xóa bằng áp 2 ngón trỏ + giữa (với tới mép trên camera mà ngón cái không bị mất)."""
        if self.tool == "draw" and not self.panel.is_open and (pos is None or not self.toolbar.contains(pos)):
            return "pinch"
        return "two_finger"

    def do(self, action):
        if action in self.tools:
            self.set_tool(action)
        elif action == "undo":
            self.board.undo()
        elif action == "clear":
            self.board.clear()
            self.panel.close()
        elif action == "unit":
            self.board.cycle_unit()
        elif action == "smart":
            self.board.set_smart(not self.board.smart)

    def set_tool(self, name):
        if name != self.tool:
            self.tools[self.tool].end(self)
            self.tool = name

    def key(self, code, t):
        """Phím tắt. Trả về True nếu phím đã được dùng (app khỏi xử lý tiếp).
        Bảng nhập mở thì bảng được hỏi trước (số, dấu chấm, Backspace, Enter, Esc, Tab)."""
        if self.panel.is_open and self.panel.key(code, self):
            return True
        action = KEY_ACTIONS.get(code)
        if action is None:
            return False
        self.do(action)     # phím C xóa ngay, không cần xác nhận (bàn phím là thao tác có chủ đích)
        return True
