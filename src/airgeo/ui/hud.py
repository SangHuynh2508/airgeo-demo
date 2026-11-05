"""HUD trạng thái (góc trên trái, dưới thanh nút), dòng trợ giúp (dưới cùng) và thông báo ngắn.
Chữ không dấu vì cv2.putText không vẽ được Unicode."""
import cv2
import numpy as np

from airgeo.ui.render import text

TOOL_NAMES = {"draw": "Ve", "select": "Chon", "erase": "Xoa"}
HELP = [
    "Chum vao nut o thanh tren de bam | 0/1/2: loc  [ ]: mincutoff  ; ': beta  - =: MA n  , .: nguong chum",
    "V/G/X: Ve/Chon/Xoa  N: don vi  S: Smart  U: undo  C: xoa het  M: so sanh  P: 2D/3D  L: xuong  R: CSV  H: an  Q: thoat",
]


def hud_lines(pf, board, tool, fps, compare, rec_session_id):
    """pf: PinchFilter; board: Board; tool: tên công cụ đang bật; rec_session_id: None nếu không ghi CSV."""
    pinch = pf.pinch
    ratio = "-" if pinch.ratio is None else f"2D={pinch.ratio2d:.2f} 3D={pinch.ratio3d:.2f}"
    state = "giu" if pinch.holding else ("ON" if pinch.pinched else "off")
    scale = "chua dat" if board.scale is None else f"{board.scale:.1f} px/cm"
    lines = [
        f"FPS: {fps:.1f}",
        f"Cong cu: {TOOL_NAMES[tool]}  Ti le: {scale}",
        f"Loc: {pf.flt.name} ({pf.flt.describe()})",
        f"1euro: {pf.one_euro.describe()}  MA: {pf.moving_avg.describe()}",
        f"Che do: {'SMART SHAPE' if board.smart else 've tu do'}" + ("  | so sanh" if compare else ""),
        f"Chum: {state}  ratio {ratio}",
        f"Do theo: {pinch.mode.upper()}  on<{pinch.on_ratio:.2f} off>{pinch.off_ratio:.2f}",
    ]
    if board.smart and board.last_info:
        lines.append(f"Net cuoi: {board.last_info}")
    if rec_session_id:
        lines.append(f"REC session {rec_session_id}")
    return lines


def draw_hud(img, lines, recording, top=0):
    h = 22 * len(lines) + 10
    roi = img[top:top + h, 0:540]
    roi[:] = (roi * 0.4).astype(np.uint8)
    for i, s in enumerate(lines):
        text(img, s, (10, top + 22 + 22 * i), 0.55)
    if recording:
        cv2.circle(img, (520, top + 20), 7, (0, 0, 255), -1)


def draw_help(img):
    h = img.shape[0]
    for i, s in enumerate(HELP):
        text(img, s, (10, h - 32 + 20 * i), 0.5, (220, 220, 220))


def draw_status(img, msg):
    text(img, msg, (10, img.shape[0] - 60), 0.6, (0, 255, 255))
