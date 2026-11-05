"""Vòng lặp chính: camera -> theo dõi tay -> chụm + lọc -> sự kiện con trỏ -> Controller -> vẽ -> phím tắt.

FPS làm mượt bằng EMA dựa trên paint.py của AI-Virtual-Painter (MIT, Sagnik Barman):
https://github.com/hanessn1/AI-Virtual-Painter
"""
import time
from collections import deque

import cv2

from airgeo.config import Config
from airgeo.interaction.controller import Controller
from airgeo.interaction.pointer import PointerTracker
from airgeo.pinch_filter import PinchFilter
from airgeo.recording.csv_logger import CsvLogger
from airgeo.tracking.camera import open_camera
from airgeo.tracking.hand_tracker import HandTracker
from airgeo.ui.edit_panel import draw_edit_panel
from airgeo.ui.hud import draw_help, draw_hud, draw_status, hud_lines
from airgeo.ui.render import draw_canvas, draw_hand, draw_tool_overlay, draw_trails
from airgeo.ui.toolbar import draw_toolbar

WIN = "AirGeo"
FILTER_KEYS = {ord("0"): "none", ord("1"): "moving_avg", ord("2"): "one_euro"}


def run(config: Config):
    try:
        cap = open_camera(config.camera, config.width, config.height)
    except RuntimeError as e:
        raise SystemExit(str(e))
    tracker = HandTracker(model_complexity=config.model_complexity)
    pf, pointer, ctl = PinchFilter(config), PointerTracker(), None
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
                # Ví dụ webcam đang bị Teams/OBS giữ: MSMF báo mở được nhưng không có hình
                print("Camera ngung gui hinh (dang bi ung dung khac dung?) -> thoat")
                break
            frame = cv2.flip(frame, 1)  # lật gương cho tự nhiên
            if ctl is None:             # bố cục thanh nút theo kích thước khung hình thật của camera
                h, w = frame.shape[:2]
                ctl = Controller(config, w, h)
            board = ctl.board

            hand = tracker.process(frame, t)
            res = pf.step(hand, t)
            if res.raw is not None:
                raw_trail.append(res.raw)
                filt_trail.append(res.fpt)
            for ev in pointer.update(res, t):
                ctl.dispatch(ev)
            logger.log(**pf.csv_row(hand, t, res, board.smart))

            # ---- Vẽ ----
            frame = draw_canvas(frame, board.shapes, ctl.tools["draw"].cur, board.scale, board.unit)
            draw_tool_overlay(frame, ctl)
            if compare:
                draw_trails(frame, raw_trail, filt_trail)
            draw_hand(frame, hand, res, show_skeleton)

            dt, t_prev = t - t_prev, t
            if dt > 0:
                fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt
            n_frames += 1

            draw_toolbar(frame, ctl, t, res.fpt)
            draw_hud(frame, hud_lines(pf, board, ctl.tool, fps, compare,
                                      logger.session_id if logger.active else None),
                     recording=logger.active, top=config.toolbar_height)
            if ctl.panel.is_open:
                draw_edit_panel(frame, ctl.panel, board.unit, res.fpt)
            if show_help:
                draw_help(frame)
            if t < status_until:
                draw_status(frame, status_msg)
            cv2.imshow(WIN, frame)

            # ---- Phím tắt ----
            # pollKey không chờ; waitKey(1) trên Windows tốn ~15 ms/frame (độ phân giải timer) -> tụt FPS
            key = cv2.pollKey() & 0xFF
            if cv2.getWindowProperty(WIN, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key == 255 or ctl.key(key, t):
                pass    # không bấm phím, hoặc phím đã được Controller dùng (công cụ, Undo, Xoa het...)
            elif key in (ord("q"), 27):
                break
            elif key in FILTER_KEYS:
                pf.select_filter(FILTER_KEYS[key])
            elif key == ord("["):
                pf.one_euro.set_params(mincutoff=max(0.01, pf.one_euro.mincutoff / 1.25))
            elif key == ord("]"):
                pf.one_euro.set_params(mincutoff=pf.one_euro.mincutoff * 1.25)
            elif key == ord(";"):
                pf.one_euro.set_params(beta=max(1e-4, pf.one_euro.beta / 1.5))
            elif key == ord("'"):
                pf.one_euro.set_params(beta=pf.one_euro.beta * 1.5)
            elif key == ord("p"):
                pf.pinch.toggle_mode()
            elif key == ord("l"):
                show_skeleton = not show_skeleton
            elif key == ord(","):
                pf.pinch.shift(-0.02)
            elif key == ord("."):
                pf.pinch.shift(0.02)
            elif key == ord("-"):
                pf.moving_avg.set_n(pf.moving_avg.n - 1)
            elif key == ord("="):
                pf.moving_avg.set_n(pf.moving_avg.n + 1)
            elif key == ord("m"):
                compare = not compare
            elif key == ord("h"):
                show_help = not show_help
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
