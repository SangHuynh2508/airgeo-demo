"""Bộ điều phối: chuyển sự kiện con trỏ tới bảng nhập / thanh nút / công cụ đang bật;
nút trên không và phím tắt gọi chung một hàm do().

Một lần chụm bắt đầu ở đâu (bảng nhập / thanh nút / vùng vẽ) thì cả lần chụm đó thuộc về chỗ đó:
chụm ở nút rồi kéo xuống vùng vẽ cũng không tạo nét. Khi bảng nhập mở, mọi lần chụm thuộc về bảng.
"""
from airgeo.document.board import Board
from airgeo.gesture.pose import PoseTrigger
from airgeo.interaction.edit_panel import EditPanel
from airgeo.interaction.radial_menu import RadialMenu
from airgeo.interaction.toolbar import Toolbar
from airgeo.tools.draw import DrawTool
from airgeo.tools.erase import EraseTool
from airgeo.tools.select import SelectTool

KEY_ACTIONS = {ord("u"): "undo", ord("c"): "clear", ord("s"): "smart", ord("n"): "unit",
               ord("v"): "draw", ord("g"): "select", ord("x"): "erase"}
TOOL_LABELS = {"draw": "Vẽ", "select": "Chọn", "erase": "Xóa"}


class Controller:
    def __init__(self, config, width, height):
        self.board = Board(config.history_limit)
        self.toolbar = Toolbar(width, config)
        self.panel = EditPanel(config, width, height)
        self.bounds = (0, config.toolbar_height, width, height)   # vùng vẽ, dưới thanh nút
        self.tools = {"draw": DrawTool(), "select": SelectTool(config, width), "erase": EraseTool(config)}
        self.tool = "draw"
        self.menu = RadialMenu(width, height, config.toolbar_height, config.confirm_window)
        self.poses = PoseTrigger()  # tư thế tay giữ yên -> lệnh (xem gesture/pose.py)
        self._fist_ok = True        # False sau mỗi lần nhả: tay thả lỏng khép hờ sau khi vẽ không được là Undo
        self._owner = None          # ai nhận lần chụm hiện tại: "panel" | "toolbar" | "tool"
        self.message, self.message_until = "", 0.0   # thông báo ngắn trên màn hình (vd. bị chặn đè hình)

    def dispatch(self, ev):
        if ev.kind == "down":
            if self.panel.is_open:
                self._owner = "panel"
            elif self.menu.is_open:
                self._owner = "menu"
            else:
                self._owner = "toolbar" if self.toolbar.contains(ev.pos) else "tool"
        if ev.kind == "hover":
            owner = "panel" if self.panel.is_open else "tool"
        else:
            owner = self._owner
        if ev.kind == "up":
            self._owner = None
            self._fist_ok = False
        if owner == "panel":
            self.panel.on_event(ev, self)
        elif owner == "menu":
            if ev.kind == "down":
                action = self.menu.press(ev.pos, ev.t)
                if action:
                    self.do(action)
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
        if self.tool == "draw" and not self.panel.is_open and not self.menu.is_open and (pos is None or not self.toolbar.contains(pos)):
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
            self.menu.close()
        elif action == "unit":
            self.board.cycle_unit()
        elif action == "smart":
            self.board.set_smart(not self.board.smart)

    def set_tool(self, name):
        if name != self.tool:
            self.tools[self.tool].end(self)
            self.tool = name

    def on_pose(self, pose, center, t):
        """Gọi mỗi frame với tư thế tay hiện tại (gesture/pose.classify, None nếu không có) và tâm bàn tay.
        Bỏ qua tư thế khi đang chụm / áp 2 ngón (đang thao tác) hoặc bảng nhập đang mở."""
        if self.menu.expired(t):
            self.menu.close()
        if self._owner is not None or self.panel.is_open:
            pose = None
        if pose in ("three", "palm", "rock"):
            self._fist_ok = True        # tay đã mở ra: nắm lại lần sau là có chủ đích
        elif pose == "fist" and not self._fist_ok:
            pose = None
        action = self.poses.update(pose, t)
        if action is None:
            return
        if self.menu.is_open and action in ("select", "menu"):
            self.menu.close()           # xòe tay lần nữa: đóng menu, và không mở lại trong cùng lần giữ
            self.poses.consume()
        elif action == "menu":
            self.menu.open(center, t)
        elif action == "undo":
            self.board.undo()
            self.notify("Đã hoàn tác", t)
        elif action != self.tool:
            self.set_tool(action)
            self.notify(TOOL_LABELS[action], t)

    def notify(self, msg, t, seconds=2.0):
        self.message, self.message_until = msg, t + seconds

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
