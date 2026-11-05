"""Bộ điều phối: chuyển sự kiện con trỏ tới thanh nút hoặc công cụ đang bật;
nút trên không và phím tắt gọi chung một hàm do().

Một lần chụm bắt đầu ở đâu (thanh nút / vùng vẽ) thì cả lần chụm đó thuộc về chỗ đó:
chụm ở nút rồi kéo xuống vùng vẽ cũng không tạo nét.
"""
from airgeo.document.board import Board
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
        self.bounds = (0, config.toolbar_height, width, height)   # vùng vẽ, dưới thanh nút
        self.tools = {"draw": DrawTool(), "select": SelectTool(config), "erase": EraseTool(config)}
        self.tool = "draw"
        self._owner = None          # ai nhận lần chụm hiện tại: "toolbar" | "tool"

    def dispatch(self, ev):
        if ev.kind == "down":
            self._owner = "toolbar" if self.toolbar.contains(ev.pos) else "tool"
        owner = "tool" if ev.kind == "hover" else self._owner
        if ev.kind == "up":
            self._owner = None
        if owner == "toolbar":
            if ev.kind == "down":
                action = self.toolbar.press(ev.pos, ev.t)
                if action:
                    self.do(action)
        elif owner == "tool":
            self.tools[self.tool].on_event(ev, self)

    def do(self, action):
        if action in self.tools:
            self.set_tool(action)
        elif action == "undo":
            self.board.undo()
        elif action == "clear":
            self.board.clear()
        elif action == "unit":
            self.board.cycle_unit()
        elif action == "smart":
            self.board.set_smart(not self.board.smart)

    def set_tool(self, name):
        if name != self.tool:
            self.tools[self.tool].end(self)
            self.tool = name

    def key(self, code, t):
        """Phím tắt. Trả về True nếu phím đã được dùng (app khỏi xử lý tiếp)."""
        action = KEY_ACTIONS.get(code)
        if action is None:
            return False
        self.do(action)     # phím C xóa ngay, không cần xác nhận (bàn phím là thao tác có chủ đích)
        return True
