"""Vòng lặp chính: camera -> theo dõi tay -> chụm + lọc -> sự kiện con trỏ -> Controller -> vẽ -> phím tắt.

FPS làm mượt bằng EMA dựa trên paint.py của AI-Virtual-Painter (MIT, Sagnik Barman):
https://github.com/hanessn1/AI-Virtual-Painter
"""
import threading
import time
from collections import deque

import cv2

from airgeo.config import Config
from airgeo.gesture.digits import read_digit
from airgeo.gesture.pose import classify
from airgeo.interaction.controller import LEGEND_SECONDS, Controller
from airgeo.interaction.fitts import FittsTask
from airgeo.interaction.pointer import PointerEvent, PointerTracker
from airgeo.pinch_filter import PinchFilter
from airgeo.recording.csv_logger import CsvLogger
from airgeo.tracking.camera import FrameGrabber, open_camera
from airgeo.tracking.hand_tracker import HandTracker
from airgeo.ui.edit_panel import draw_edit_panel
from airgeo.ui.hud import draw_help, draw_hud, draw_legend, draw_status, hud_lines
from airgeo.ui.render import (draw_canvas, draw_fitts, draw_hand, draw_pose_progress, draw_radial_menu,
                              draw_tool_overlay, draw_trails)
from airgeo.ui.toolbar import draw_toolbar

WIN = "AirGeo"
FILTER_KEYS = {ord("0"): "none", ord("1"): "moving_avg", ord("2"): "one_euro"}


def run(config: Config):
    try:
        cap = FrameGrabber(open_camera(config.camera, config.width, config.height))
    except RuntimeError as e:
        raise SystemExit(str(e))
    tracker = HandTracker(model_complexity=config.model_complexity)
    threading.Thread(target=read_digit, args=([[(0, 0), (0, 1)]],), daemon=True).start()   # huấn luyện kNN trước
    pf, pointer, ctl = PinchFilter(config), PointerTracker(), None
    cursor = None                 # con trỏ frame trước: quyết định cử chỉ bấm (chụm / 2 ngón) cho frame này
    logger = CsvLogger(config.data_dir)

    compare, show_help, show_skeleton = False, True, True
    tech = False                  # phím D: thông số kỹ thuật (HUD, phím lọc, khung xương) – người dùng không cần
    raw_trail, filt_trail = deque(maxlen=config.trail_len), deque(maxlen=config.trail_len)
    fps, n_frames, t_start, t_prev = 0.0, 0, time.perf_counter(), time.perf_counter()
    status_msg, status_until = "", 0.0
    last_hand = float("-inf")     # lúc cuối thấy tay: bảng gợi ý tư thế chỉ hiện khi giáo viên hạ tay
    fitts, fitts_saved = None, False  # bài đo bấm mục tiêu (phím K)
    shown = None                      # khung hình vừa hiện (giữ lại khi camera khựng)
    helped = False                    # frame vừa rồi có vẽ bảng gợi ý / dòng trợ giúp (phím H: đang hiện thì ẩn)

    # Toàn màn hình (máy chiếu), giữ tỉ lệ khung hình camera; phím F bật / tắt
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    full = True
    cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    try:
        while True:
            ok, frame, t = cap.read()   # frame mới nhất + timestamp lúc chụp (không giả định FPS cố định)
            if not ok:
                if shown is None or not cap.alive:
                    # Ví dụ webcam đang bị Teams/OBS giữ: MSMF báo mở được nhưng không có hình
                    print("Camera ngung gui hinh (dang bi ung dung khac dung?) -> thoat")
                    break
                # camera khựng giữa giờ: giữ hình cũ, báo, chờ tiếp (thoát là mất bảng đang dạy)
                stall = shown.copy()
                draw_status(stall, "Mất hình từ camera – đang chờ… (Q: thoát)")
                cv2.imshow(WIN, stall)
                if cv2.pollKey() & 0xFF in (ord("q"), 27):
                    break
                continue
            frame = cv2.flip(frame, 1)  # lật gương cho tự nhiên
            if ctl is None:             # bố cục thanh nút theo kích thước khung hình thật của camera
                h, w = frame.shape[:2]
                ctl = Controller(config, w, h)
            board = ctl.board

            hand = tracker.process(frame, t)
            if hand:
                last_hand = t
            res = pf.step(hand, t, fitts.gesture if fitts else ctl.gesture_for(cursor))
            cursor = res.fpt or cursor
            if res.raw is not None:
                raw_trail.append(res.raw)
                filt_trail.append(res.fpt)
            for ev in pointer.update(res, t):
                if fitts:
                    fitts.on_event(ev, pf.stabilize)
                else:
                    ctl.dispatch(ev)
            if fitts and fitts.done and not fitts_saved:
                fitts_saved = True
                status_msg, status_until = fitts.save_status(config.data_dir), t + 4
            # tư thế tay giữ yên -> đổi công cụ / Undo / menu tròn (Controller bỏ qua khi đang chụm, bảng nhập mở)
            if fitts is None:
                ctl.on_pose(classify(hand["pts"]) if hand else None, hand["pts"][9] if hand else (0, 0), t)
            logger.log(**pf.csv_row(hand, t, res, True))    # cột mode: nhận dạng luôn bật

            # ---- Vẽ ----
            dt, t_prev = t - t_prev, t
            if dt > 0:
                fps = 1 / dt if fps == 0 else 0.9 * fps + 0.1 / dt
            n_frames += 1

            active = ctl.tools["select"].selected if ctl.tool == "select" else None
            frame = draw_canvas(frame, board.shapes, ctl.tools["draw"].cur, active)
            if tech:
                # HUD vẽ trước lớp công cụ: khung hình hẹp (640) thì bảng công thức / cột Tinh nằm đè lên HUD
                draw_hud(frame, hud_lines(pf, board, ctl.tool, fps, compare,
                                          logger.session_id if logger.active else None),
                         recording=logger.active, top=config.toolbar_height)
            if fitts:
                draw_fitts(frame, fitts)
            else:
                draw_tool_overlay(frame, ctl)
            if compare:
                draw_trails(frame, raw_trail, filt_trail)
            draw_hand(frame, hand, res, show_skeleton and tech, pf.pinch.gesture, None if fitts else ctl.tool)
            if fitts is None:
                draw_toolbar(frame, ctl, t, res.fpt)
                if ctl.menu.is_open:
                    draw_radial_menu(frame, ctl.menu, board, t, res.fpt, ctl.toolbar.visible)
                if ctl.panel.is_open:
                    draw_edit_panel(frame, ctl.panel, board.unit, res.fpt)
                draw_pose_progress(frame, res.fpt, ctl.poses.progress)
            helped = True
            if show_help and tech:
                draw_help(frame)
            elif t < ctl.legend_until or (show_help and t - last_hand > 1.5 and not ctl.board.shapes):
                draw_legend(frame)      # có hình rồi thì ẩn để không che hình; mục Gợi ý / phím H bật lại vài giây
            else:
                helped = False
            if t < ctl.message_until:
                draw_status(frame, ctl.message)
            elif t < status_until:
                draw_status(frame, status_msg)
            cv2.imshow(WIN, frame)
            shown = frame

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
                pf.toggle_mode()
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
            elif key == ord("h"):     # đang hiện thì ẩn; đang ẩn thì hiện (cả khi đã có hình, LEGEND_SECONDS giây)
                show_help = not helped
                ctl.legend_until = t + LEGEND_SECONDS if show_help else 0.0
            elif key == ord("d"):
                tech = not tech
            elif key == ord("k"):
                if pointer.down and fitts is None:      # đang chụm: kết thúc thao tác dở trước khi chuyển
                    ctl.dispatch(PointerEvent("up", pointer.last, t))
                pointer.down = False
                if fitts is None:
                    fitts, fitts_saved = FittsTask(frame.shape[1], frame.shape[0]), False
                else:
                    if fitts.records and not fitts_saved:
                        status_msg, status_until = fitts.save_status(config.data_dir), t + 4
                    fitts = None
            elif key == ord("b") and fitts:
                fitts.gesture = "pinch" if fitts.gesture == "two_finger" else "two_finger"
            elif key == ord("s"):
                pf.stabilize = not pf.stabilize
                status_msg, status_until = f"Ổn định điểm bấm: {'bật' if pf.stabilize else 'tắt'}", t + 2
            elif key == ord("f"):
                full = not full
                cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN if full else cv2.WINDOW_NORMAL)
                if not full:
                    cv2.resizeWindow(WIN, *frame.shape[1::-1])
            elif key == ord("r"):
                if logger.active:
                    logger.stop()
                    status_msg = "Đã dừng ghi CSV"
                else:
                    status_msg = f"Đang ghi: {logger.start()}"
                status_until = t + 3
    finally:
        logger.stop()
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        elapsed = time.perf_counter() - t_start
        if n_frames:
            print(f"{n_frames} frame trong {elapsed:.1f}s -> FPS trung binh {n_frames / elapsed:.1f}")
