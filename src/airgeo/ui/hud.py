"""HUD trạng thái (góc trên trái), dòng trợ giúp (dưới cùng) và thông báo ngắn.
Chữ không dấu vì cv2.putText không vẽ được Unicode."""
import cv2
import numpy as np

from airgeo.ui.render import text

HELP = [
    "0/1/2: loc none/MA/1euro  [ ]: mincutoff -/+  ; ': beta -/+  - =: MA n -/+  , .: nguong chum -/+",
    "S: Smart Shape  M: so sanh  P: do chum 2D/3D  L: khung xuong  R: ghi CSV  U: undo  C: xoa  H: an/hien  Q: thoat",
]


def hud_lines(session, fps, compare, rec_session_id):
    """rec_session_id: mã phiên đang ghi CSV, None nếu không ghi."""
    pinch = session.pinch
    ratio = "-" if pinch.ratio is None else f"2D={pinch.ratio2d:.2f} 3D={pinch.ratio3d:.2f}"
    state = "giu" if pinch.holding else ("ON" if pinch.pinched else "off")
    lines = [
        f"FPS: {fps:.1f}",
        f"Loc: {session.flt.name} ({session.flt.describe()})",
        f"1euro: {session.one_euro.describe()}  MA: {session.moving_avg.describe()}",
        f"Che do: {'SMART SHAPE' if session.smart else 've tu do'}" + ("  | so sanh" if compare else ""),
        f"Chum: {state}  ratio {ratio}",
        f"Do theo: {pinch.mode.upper()}  on<{pinch.on_ratio:.2f} off>{pinch.off_ratio:.2f}",
    ]
    if session.smart and session.last_info:
        lines.append(f"Net cuoi: {session.last_info}")
    if rec_session_id:
        lines.append(f"REC session {rec_session_id}")
    return lines


def draw_hud(img, lines, recording):
    h = 22 * len(lines) + 10
    roi = img[0:h, 0:540]
    roi[:] = (roi * 0.4).astype(np.uint8)
    for i, s in enumerate(lines):
        text(img, s, (10, 22 + 22 * i), 0.55)
    if recording:
        cv2.circle(img, (520, 20), 7, (0, 0, 255), -1)


def draw_help(img):
    h = img.shape[0]
    for i, s in enumerate(HELP):
        text(img, s, (10, h - 32 + 20 * i), 0.5, (220, 220, 220))


def draw_status(img, msg):
    text(img, msg, (10, img.shape[0] - 60), 0.6, (0, 255, 255))
