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

KEY_ACTIONS = {ord("u"): "undo", ord("y"): "redo", ord("c"): "clear", ord("n"): "unit", ord("t"): "bar",
               ord("v"): "draw", ord("g"): "select", ord("x"): "erase"}
UNDO_MESSAGES = {"undo": ("Đã hoàn tác", "Không còn gì để hoàn tác"),
                 "redo": ("Đã làm lại", "Không còn gì để làm lại")}
TOOL_LABELS = {"draw": "Vẽ", "select": "Chọn", "erase": "Xóa"}
LEGEND_SECONDS = 8.0   # mục Gợi ý / phím H: bảng gợi ý hiện chừng này giây rồi tự ẩn (không che bài giảng mãi)
FIT_MARGIN = 130      # lề trái / phải quanh hình đã phóng to: chỗ cho nhãn cạnh dọc 2 dòng ("CA =" / "1.5 cm"),
                      # số đo góc, tay cầm xoay; cạnh dọc bên phải thì nhãn không lấn cột Tính
FIT_TOP, FIT_BOTTOM = 90, 180   # lề dưới rộng hơn: nhãn cạnh đáy không sát mép dưới (tay thấp thì mất tay)


class Controller:
    def __init__(self, config, width, height):
        self.board = Board(config.history_limit)
        self.toolbar = Toolbar(width, config)
        self.panel = EditPanel(config, width, height)
        self.width, self.height = width, height
        self.tools = {"draw": DrawTool(), "select": SelectTool(config, width, height), "erase": EraseTool(config)}
        self.tool = "draw"
        self.menu = RadialMenu(width, height, config.toolbar_height, config.confirm_window,
                               right=self.tools["select"].menu_x - 210)     # không đè cột Tính + bảng công thức
        self.poses = PoseTrigger()  # tư thế tay giữ yên -> lệnh (xem gesture/pose.py)
        self._fist_ok = True        # False sau mỗi lần nhả: tay thả lỏng khép hờ sau khi vẽ không được là Undo
        self._owner = None          # ai nhận lần chụm hiện tại: "panel" | "toolbar" | "tool"
        self.legend_until = 0.0     # hiện bảng gợi ý tới lúc này (kể cả khi bảng đã có hình)
        self.message, self.message_until = "", 0.0   # thông báo ngắn trên màn hình (vd. bị chặn đè hình)

    @property
    def bounds(self):
        """Vùng vẽ (x0, y0, x1, y1) cho bảng nhập dựng lại hình: dải nút đang hiện thì trừ phần trên cùng."""
        return 0, self.toolbar.height if self.toolbar.visible else 0, self.width, self.height

    @property
    def fit_box(self):
        """Vùng đặt hình sau khi vẽ / nhập số đo: vùng vẽ trừ cột Tính bên phải, chừa lề cho nhãn."""
        m = FIT_MARGIN
        return m, self.bounds[1] + FIT_TOP, self.tools["select"].menu_x - m, self.height - FIT_BOTTOM

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
                    self.do(action, ev.t)
                if action == "unit":        # menu đã đóng: không còn chỗ nào hiện đơn vị mới
                    self.notify(f"Đơn vị: {self.board.unit}", ev.t)
                elif action == "clear":
                    self.notify("Đã xóa hết", ev.t)
        elif owner == "toolbar":
            if ev.kind == "down":
                action = self.toolbar.press(ev.pos, ev.t)
                if action:
                    self.do(action, ev.t)
        elif owner == "tool":
            self.tools[self.tool].on_event(ev, self)

    def gesture_for(self, pos):
        """Cử chỉ bấm ở chỗ con trỏ: vẽ trong vùng vẽ bằng chụm ngón cái + trỏ; thanh nút, bảng nhập,
        Chọn, Xóa bằng áp 2 ngón trỏ + giữa (với tới mép trên camera mà ngón cái không bị mất).
        Bảng nhập mở: ô viết số dùng chụm (viết như vẽ), nút và ô cạnh dùng 2 ngón."""
        if self.panel.is_open:
            return "pinch" if pos is not None and self.panel.in_pad(pos) else "two_finger"
        if self.tool == "draw" and not self.panel.is_open and not self.menu.is_open and (pos is None or not self.toolbar.contains(pos)):
            return "pinch"
        return "two_finger"

    def do(self, action, t=None):
        """t: lúc bấm – có thì Hoàn tác / Làm lại báo kết quả lên màn hình."""
        if action in self.tools:
            self.set_tool(action)
        elif action in UNDO_MESSAGES:
            ok = self.board.undo() if action == "undo" else self.board.redo()
            if t is not None:
                self.notify(UNDO_MESSAGES[action][not ok], t)
        elif action == "clear":
            self.board.clear()
            self.panel.close()
            self.menu.close()
        elif action == "unit":
            self.board.cycle_unit()
        elif action == "help":
            self.legend_until = (t or 0.0) + LEGEND_SECONDS
        elif action == "bar":
            self.toolbar.visible = not self.toolbar.visible
            self.tools["select"].top = self.bounds[1]

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
            self.do("undo", t)
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
        self.do(action, t)  # phím C xóa ngay, không cần xác nhận (bàn phím là thao tác có chủ đích)
        return True
