"""AirGeo demo: bảng vẽ hình học không chạm.

Vòng lặp chính, giao diện OpenCV và phím tắt. Cách mở camera (CAP_DSHOW + MJPG),
trộn lớp canvas lên khung hình (addWeighted) và FPS làm mượt bằng EMA dựa trên
paint.py của AI-Virtual-Painter (MIT, Sagnik Barman): https://github.com/hanessn1/AI-Virtual-Painter

Chạy: python app.py [--camera 0] [--width 1280] [--height 720] [--model 1]
"""
import argparse
import time
from collections import deque

import cv2
import numpy as np

from filters import MovingAverage, NoFilter, OneEuro
from gesture import PinchDetector
from logger import CsvLogger
from measure import measure
from shapes import recognize
from tracker import CONNECTIONS, HandTracker

WIN = "AirGeo demo"
PINCH_ON, PINCH_OFF = 0.20, 0.35   # ngưỡng hysteresis, chỉnh bằng phím , . khi chạy (P: đo 2D/3D)
TRAIL = 60                          # số điểm vết hiển thị ở chế độ so sánh

FREE_COLOR = (255, 255, 255)
SHAPE_COLOR = (0, 220, 255)
RAW_COLOR = (160, 160, 160)
FILT_COLOR = (0, 255, 0)

HELP = [
    "0/1/2: loc none/MA/1euro  [ ]: mincutoff -/+  ; ': beta -/+  - =: MA n -/+  , .: nguong chum -/+",
    "S: Smart Shape  M: so sanh  P: do chum 2D/3D  L: khung xuong  R: ghi CSV  U: undo  C: xoa  H: an/hien  Q: thoat",
]


def ip(p):
    return int(round(p[0])), int(round(p[1]))


def text(img, s, org, scale=0.5, color=(255, 255, 255)):
    # Viền đen để chữ đọc được trên mọi nền. OpenCV không vẽ được tiếng Việt có dấu.
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, s, org, cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)


def draw_point(hand):
    """Điểm vẽ = trung điểm ngón cái (4) và ngón trỏ (8), không phải riêng đầu ngón trỏ.
    Khi khép/mở ngón, đầu ngón trỏ đi xuống/lên một quãng sau khi đã vượt ngưỡng chụm -> đoạn thừa
    ở đầu và cuối nét. Hai ngón đi về phía nhau nên trung điểm gần như đứng yên."""
    (x4, y4), (x8, y8) = hand["p4"], hand["p8"]
    return (x4 + x8) / 2, (y4 + y8) / 2


def make_shape(raw, smart):
    """raw: [(x, y, t)] của nét. Giữ lại raw để nhận dạng lại khi bật/tắt Smart Shape."""
    shape = recognize(raw) if smart else {"kind": "free", "pts": [(x, y) for x, y, _ in raw]}
    shape["raw"] = raw
    return shape


def describe_result(s):
    info = s.get("info", {})
    return s["kind"] + "".join(f" {k}={v}" for k, v in info.items())


def draw_shape(img, s):
    kind = s["kind"]
    if kind == "circle":
        cv2.circle(img, ip(s["center"]), int(round(s["radius"])), SHAPE_COLOR, 3, cv2.LINE_AA)
        return
    pts = np.array([ip(p) for p in s["pts"]], dtype=np.int32)
    color = FREE_COLOR if kind == "free" else SHAPE_COLOR
    cv2.polylines(img, [pts], kind in ("triangle", "rect"), color, 3, cv2.LINE_AA)


def draw_measurements(img, s):
    m = measure(s)
    if not m:
        return
    if s["kind"] == "circle":
        c, r = s["center"], s["radius"]
        cv2.line(img, ip(c), ip((c[0] + r, c[1])), SHAPE_COLOR, 1, cv2.LINE_AA)
        cv2.circle(img, ip(c), 3, SHAPE_COLOR, -1)
        text(img, f"r={r:.0f}", ip((c[0] + 8, c[1] - 6)))
        text(img, f"C={m['perimeter']:.0f}px  S={m['area']:.0f}px2", ip((c[0] - r, c[1] + r + 20)))
        return
    pts = s["pts"]
    if s["kind"] == "line":
        mid = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
        text(img, f"{m['sides'][0]:.0f}px", ip((mid[0] + 8, mid[1] - 8)))
        return
    n = len(pts)
    cx, cy = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        # Nhãn cạnh đẩy ra ngoài hình, nhãn góc đẩy vào trong (theo hướng trọng tâm)
        text(img, f"{m['sides'][i]:.0f}", ip((mid[0] + (mid[0] - cx) * 0.15 - 12, mid[1] + (mid[1] - cy) * 0.15)))
        v = pts[i]
        text(img, f"{m['angles'][i]:.0f}deg", ip((v[0] + (cx - v[0]) * 0.2 - 20, v[1] + (cy - v[1]) * 0.2)),
             0.45, (180, 255, 180))
    text(img, f"P={m['perimeter']:.0f}px  S={m['area']:.0f}px2", ip((cx - 70, cy)))


def draw_hud(img, lines):
    h = 22 * len(lines) + 10
    roi = img[0:h, 0:540]
    roi[:] = (roi * 0.4).astype(np.uint8)
    for i, s in enumerate(lines):
        text(img, s, (10, 22 + 22 * i), 0.55)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--model", type=int, default=1, choices=[0, 1], help="model_complexity của MediaPipe")
    args = ap.parse_args()

    # MSMF: webcam laptop cho 1280x720 @ 30 FPS. DSHOW (repo gốc) chỉ được ~10 FPS ở 720p
    # vì không nhận MJPG -> nét gãy khúc, quẹt nhanh bị mất tay. DSHOW chỉ để dự phòng.
    cap = cv2.VideoCapture(args.camera, cv2.CAP_MSMF)
    if not cap.isOpened():
        cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    cap.set(cv2.CAP_PROP_FPS, 30)
    if not cap.isOpened():
        raise SystemExit(f"Khong mo duoc camera {args.camera}")

    tracker = HandTracker(model_complexity=args.model)
    pinch = PinchDetector(PINCH_ON, PINCH_OFF)
    moving_avg, one_euro = MovingAverage(5), OneEuro(mincutoff=1.0, beta=0.007, dcutoff=1.0)
    filters = {ord("0"): NoFilter(), ord("1"): moving_avg, ord("2"): one_euro}
    flt = one_euro
    logger = CsvLogger("data")

    strokes = []   # các nét đã xong: dict hình (shapes.py) + "raw" = [(x, y, t)]
    cur = None     # nét đang vẽ: [(x_filt, y_filt, t)]
    smart, compare, show_help, show_skeleton = False, False, True, True
    raw_trail, filt_trail = deque(maxlen=TRAIL), deque(maxlen=TRAIL)
    fps, n_frames, t_start, t_prev = 0.0, 0, time.perf_counter(), time.perf_counter()
    status_msg, status_until = "", 0.0
    last_info = ""  # lý do nhận dạng của nét cuối, giúp chỉnh ngưỡng trong shapes.py

    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    try:
        while True:
            ok, frame = cap.read()
            t = time.perf_counter()   # timestamp thật của frame, không giả định FPS cố định
            if not ok:
                break
            frame = cv2.flip(frame, 1)  # lật gương cho tự nhiên

            hand = tracker.process(frame, t)
            pinched = pinch.update(hand, t)
            fpt = None
            if hand and not pinch.holding:
                raw = draw_point(hand)
                fpt = flt.filter(*raw, t)
                raw_trail.append(raw)
                filt_trail.append(fpt)
            elif not hand and not pinched:
                flt.reset()  # tránh điểm lọc bị "kéo" từ vị trí cũ khi tay xuất hiện lại

            # Chụm thì nối điểm đã lọc thành nét, nhả thì kết thúc nét.
            # Frame "holding" (mất tay / tỉ lệ nhảy vọt) bị bỏ qua: không đưa vào bộ lọc, không thêm điểm.
            if pinched:
                if cur is None:
                    cur = []
                if fpt:
                    cur.append((fpt[0], fpt[1], t))
            elif cur is not None:
                if len(cur) >= 2:
                    strokes.append(make_shape(cur, smart))
                    last_info = describe_result(strokes[-1])
                cur = None

            logger.log(
                t=f"{t:.6f}",
                x8_raw=hand and f"{hand['p8'][0]:.2f}", y8_raw=hand and f"{hand['p8'][1]:.2f}",
                x4_raw=hand and f"{hand['p4'][0]:.2f}", y4_raw=hand and f"{hand['p4'][1]:.2f}",
                pinch=int(pinched), filter_name=flt.name,
                x_filt=fpt and f"{fpt[0]:.2f}", y_filt=fpt and f"{fpt[1]:.2f}",
                mode="smart" if smart else "free",
            )

            # ---- Vẽ ----
            canvas = np.zeros_like(frame)
            for s in strokes:
                draw_shape(canvas, s)
            if cur and len(cur) >= 2:
                cv2.polylines(canvas, [np.array([ip(p) for p in cur], dtype=np.int32)], False, FREE_COLOR, 3, cv2.LINE_AA)
            frame = cv2.addWeighted(frame, 0.6, canvas, 1, 0)  # trộn canvas lên webcam (từ AI-Virtual-Painter)
            for s in strokes:
                draw_measurements(frame, s)

            if compare and raw_trail:
                cv2.polylines(frame, [np.array([ip(p) for p in raw_trail], np.int32)], False, RAW_COLOR, 1, cv2.LINE_AA)
                cv2.polylines(frame, [np.array([ip(p) for p in filt_trail], np.int32)], False, FILT_COLOR, 2, cv2.LINE_AA)
            if hand and show_skeleton:
                for a, b in CONNECTIONS:
                    cv2.line(frame, ip(hand["pts"][a]), ip(hand["pts"][b]), (255, 0, 255), 1, cv2.LINE_AA)
            if hand:
                cv2.circle(frame, ip(hand["p4"]), 5, RAW_COLOR, -1)
                cv2.circle(frame, ip(hand["p8"]), 5, RAW_COLOR, -1)
            if fpt:
                cv2.circle(frame, ip(fpt), 9, (0, 0, 255) if pinched else FILT_COLOR, 2)
            elif pinch.holding and hand:
                cv2.circle(frame, ip(draw_point(hand)), 9, (0, 165, 255), 2)  # cam: đang giữ nét, bỏ qua frame

            dt = t - t_prev
            t_prev = t
            if dt > 0:
                fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt
            n_frames += 1

            ratio = "-" if pinch.ratio is None else f"2D={pinch.ratio2d:.2f} 3D={pinch.ratio3d:.2f}"
            state = "giu" if pinch.holding else ("ON" if pinched else "off")
            hud = [
                f"FPS: {fps:.1f}",
                f"Loc: {flt.name} ({flt.describe()})",
                f"1euro: {one_euro.describe()}  MA: {moving_avg.describe()}",
                f"Che do: {'SMART SHAPE' if smart else 've tu do'}" + ("  | so sanh" if compare else ""),
                f"Chum: {state}  ratio {ratio}",
                f"Do theo: {pinch.mode.upper()}  on<{pinch.on_ratio:.2f} off>{pinch.off_ratio:.2f}",
            ]
            if smart and last_info:
                hud.append(f"Net cuoi: {last_info}")
            if logger.active:
                hud.append(f"REC session {logger.session_id}")
            draw_hud(frame, hud)
            if logger.active:
                cv2.circle(frame, (520, 20), 7, (0, 0, 255), -1)
            if show_help:
                h = frame.shape[0]
                for i, s in enumerate(HELP):
                    text(frame, s, (10, h - 32 + 20 * i), 0.5, (220, 220, 220))
            if t < status_until:
                text(frame, status_msg, (10, frame.shape[0] - 60), 0.6, (0, 255, 255))

            cv2.imshow(WIN, frame)

            # ---- Phím tắt ----
            # pollKey không chờ; waitKey(1) trên Windows tốn ~15 ms/frame (độ phân giải timer) -> tụt FPS
            key = cv2.pollKey() & 0xFF
            if key in (ord("q"), 27) or cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
                break
            elif key in filters:
                flt = filters[key]
                flt.reset()
            elif key == ord("["):
                one_euro.set_params(mincutoff=max(0.01, one_euro.mincutoff / 1.25))
            elif key == ord("]"):
                one_euro.set_params(mincutoff=one_euro.mincutoff * 1.25)
            elif key == ord(";"):
                one_euro.set_params(beta=max(1e-4, one_euro.beta / 1.5))
            elif key == ord("'"):
                one_euro.set_params(beta=one_euro.beta * 1.5)
            elif key == ord("p"):
                pinch.toggle_mode()
            elif key == ord("l"):
                show_skeleton = not show_skeleton
            elif key == ord(","):
                pinch.shift(-0.02)
            elif key == ord("."):
                pinch.shift(0.02)
            elif key == ord("-"):
                moving_avg.set_n(moving_avg.n - 1)
            elif key == ord("="):
                moving_avg.set_n(moving_avg.n + 1)
            elif key == ord("s"):
                # Nhận dạng lại cả các nét đã vẽ, để bật/tắt thấy khác biệt ngay
                smart = not smart
                strokes = [make_shape(s["raw"], smart) for s in strokes]
            elif key == ord("m"):
                compare = not compare
            elif key == ord("h"):
                show_help = not show_help
            elif key == ord("u") and strokes:
                strokes.pop()
            elif key == ord("c"):
                strokes.clear()
            elif key == ord("r"):
                if logger.active:
                    logger.stop()
                    status_msg = "Da dung ghi CSV"
                else:
                    status_msg = f"Dang ghi: {logger.start()}"
                status_until = t + 3
    finally:
        logger.stop()
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        elapsed = time.perf_counter() - t_start
        if n_frames:
            print(f"{n_frames} frame trong {elapsed:.1f}s -> FPS trung binh {n_frames / elapsed:.1f}")


if __name__ == "__main__":
    main()
