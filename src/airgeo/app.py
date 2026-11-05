"""Vòng lặp chính: camera -> theo dõi tay -> DrawingSession -> vẽ -> phím tắt.

FPS làm mượt bằng EMA dựa trên paint.py của AI-Virtual-Painter (MIT, Sagnik Barman):
https://github.com/hanessn1/AI-Virtual-Painter
"""
import time
from collections import deque

import cv2

from airgeo.config import Config
from airgeo.recording.csv_logger import CsvLogger
from airgeo.session import DrawingSession
from airgeo.tracking.camera import open_camera
from airgeo.tracking.hand_tracker import HandTracker
from airgeo.ui.hud import draw_help, draw_hud, draw_status, hud_lines
from airgeo.ui.render import draw_canvas, draw_hand, draw_trails

WIN = "AirGeo"
FILTER_KEYS = {ord("0"): "none", ord("1"): "moving_avg", ord("2"): "one_euro"}


def run(config: Config):
    try:
        cap = open_camera(config.camera, config.width, config.height)
    except RuntimeError as e:
        raise SystemExit(str(e))
    tracker = HandTracker(model_complexity=config.model_complexity)
    session = DrawingSession(config)
    logger = CsvLogger(config.data_dir)

    compare, show_help, show_skeleton = False, True, True
    raw_trail, filt_trail = deque(maxlen=config.trail_len), deque(maxlen=config.trail_len)
    fps, n_frames, t_start, t_prev = 0.0, 0, time.perf_counter(), time.perf_counter()
    status_msg, status_until = "", 0.0

    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    try:
        while True:
            ok, frame = cap.read()
            t = time.perf_counter()   # timestamp thật của frame, không giả định FPS cố định
            if not ok:
                break
            frame = cv2.flip(frame, 1)  # lật gương cho tự nhiên

            hand = tracker.process(frame, t)
            res = session.step(hand, t)
            if res.raw is not None:
                raw_trail.append(res.raw)
                filt_trail.append(res.fpt)
            logger.log(**session.csv_row(hand, t, res))

            # ---- Vẽ ----
            frame = draw_canvas(frame, session.strokes, session.cur)
            if compare:
                draw_trails(frame, raw_trail, filt_trail)
            draw_hand(frame, hand, res, show_skeleton)

            dt, t_prev = t - t_prev, t
            if dt > 0:
                fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt
            n_frames += 1

            draw_hud(frame, hud_lines(session, fps, compare, logger.session_id if logger.active else None),
                     recording=logger.active)
            if show_help:
                draw_help(frame)
            if t < status_until:
                draw_status(frame, status_msg)
            cv2.imshow(WIN, frame)

            # ---- Phím tắt ----
            # pollKey không chờ; waitKey(1) trên Windows tốn ~15 ms/frame (độ phân giải timer) -> tụt FPS
            key = cv2.pollKey() & 0xFF
            if key in (ord("q"), 27) or cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
                break
            elif key in FILTER_KEYS:
                session.select_filter(FILTER_KEYS[key])
            elif key == ord("["):
                session.one_euro.set_params(mincutoff=max(0.01, session.one_euro.mincutoff / 1.25))
            elif key == ord("]"):
                session.one_euro.set_params(mincutoff=session.one_euro.mincutoff * 1.25)
            elif key == ord(";"):
                session.one_euro.set_params(beta=max(1e-4, session.one_euro.beta / 1.5))
            elif key == ord("'"):
                session.one_euro.set_params(beta=session.one_euro.beta * 1.5)
            elif key == ord("p"):
                session.pinch.toggle_mode()
            elif key == ord("l"):
                show_skeleton = not show_skeleton
            elif key == ord(","):
                session.pinch.shift(-0.02)
            elif key == ord("."):
                session.pinch.shift(0.02)
            elif key == ord("-"):
                session.moving_avg.set_n(session.moving_avg.n - 1)
            elif key == ord("="):
                session.moving_avg.set_n(session.moving_avg.n + 1)
            elif key == ord("s"):
                session.toggle_smart()
            elif key == ord("m"):
                compare = not compare
            elif key == ord("h"):
                show_help = not show_help
            elif key == ord("u"):
                session.undo()
            elif key == ord("c"):
                session.clear()
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
