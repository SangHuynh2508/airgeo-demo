import math
from airgeo.config import Config
from airgeo.pinch_filter import PinchFilter


def _pf():
    pf = PinchFilter(Config())
    pf.select_filter("none")          # không lọc -> dễ kiểm tra tọa độ
    return pf


def test_pinched_frame_gives_filtered_midpoint(make_hand):
    res = _pf().step(make_hand(100, 200, ratio=0.1), 0.0)
    assert res.pinched and not res.holding
    assert res.raw == (100, 200) and res.fpt == (100, 200)


def test_holding_frame_has_no_point(make_hand):
    pf = _pf()
    pf.step(make_hand(100, 200, ratio=0.1), 0.0)
    res = pf.step(make_hand(500, 500, ratio=0.6), 0.05)    # MediaPipe đặt sai điểm 1 frame
    assert res.pinched and res.holding and res.raw is None and res.fpt is None


def test_hand_lost_while_released_resets_filter(make_hand):
    pf = PinchFilter(Config())              # 1€ mặc định
    pf.step(make_hand(100, 100, ratio=0.6), 0.0)
    pf.step(None, 0.033)
    assert pf.step(make_hand(600, 400, ratio=0.6), 0.066).fpt == (600, 370)   # đầu ngón trỏ


def test_select_filter_switches():
    pf = PinchFilter(Config())
    assert pf.flt.name == "one_euro"
    pf.select_filter("moving_avg")
    assert pf.flt is pf.moving_avg


def test_csv_row_keeps_raw_landmarks_and_mode(make_hand):
    pf = _pf()
    hand = make_hand(100, 200, ratio=0.1)                   # p4 = (100, 205), p8 = (100, 195)
    row = pf.csv_row(hand, 1.5, pf.step(hand, 1.5))
    assert row["t"] == "1.500000"
    assert row["x8_raw"] == "100.00" and row["y8_raw"] == "195.00" and row["y4_raw"] == "205.00"
    assert row["x_filt"] == "100.00" and row["y_filt"] == "200.00"
    assert row["pinch"] == 1 and row["filter_name"] == "none" and row["mode"] == "smart"
    empty = pf.csv_row(None, 1.6, pf.step(None, 1.6))
    assert empty["x8_raw"] is None and empty["x_filt"] is None and empty["mode"] == "smart"


def test_hover_cursor_is_index_tip_and_pinch_draws_at_midpoint(make_hand):
    pf = _pf()
    assert pf.step(make_hand(100, 200, ratio=0.6), 0.0, want="pinch").fpt == (100, 170)   # p8
    res = pf.step(make_hand(100, 200, ratio=0.1), 0.1, want="pinch")
    assert res.raw == (100, 200) and res.fpt == (100, 200)   # vẽ theo trung điểm 4-8, con trỏ nằm ngay chỗ chụm


def test_two_fingers_press_only_where_wanted_and_need_a_fresh_close(make_two_finger):
    pf = _pf()
    together, apart = make_two_finger(300, 200, ratio=0.1), make_two_finger(300, 200, ratio=0.6)
    assert not pf.step(together, 0.0, want="pinch").pinched        # vùng vẽ: 2 ngón không vẽ
    assert not pf.step(together, 0.1, want="two_finger").pinched   # đưa vào menu lúc 2 ngón đã áp: chưa bấm
    for i, r in enumerate((0.25, 0.4, 0.6)):                         # tách 2 ngón ra (mở dần như tay thật)
        pf.step(make_two_finger(300, 200, ratio=r), 0.15 + i * 0.033, want="two_finger")
    pf.step(apart, 0.3, want="two_finger")
    res = pf.step(together, 0.35, want="two_finger")
    assert res.pinched and res.fpt == (300, 200) and pf.pinch.gesture == "two_finger"


def test_gesture_is_kept_until_release(make_hand):
    pf = _pf()
    pf.step(make_hand(100, 200, ratio=0.1), 0.0, want="pinch")
    res = pf.step(make_hand(100, 200, ratio=0.1), 0.03, want="two_finger")   # đang vẽ mà kéo vào thanh nút
    assert res.pinched and pf.pinch.gesture == "pinch"


def test_fingers_together_palm_is_not_a_two_finger_press(make_two_finger):
    pf = PinchFilter(Config())
    pf.select_filter("none")
    h = make_two_finger(300, 200, ratio=0.1)
    pts = list(h["pts"])
    pts[16], pts[14], pts[20], pts[18] = (320, 205), (320, 235), (335, 210), (335, 240)   # áp út + út duỗi
    palm = dict(h, pts=pts)
    pf.step(make_two_finger(300, 200, ratio=0.6), 0.0, want="two_finger")
    assert not pf.step(palm, 0.1, want="two_finger").pinched       # xòe tay khép ngón: là tư thế, không phải bấm
    pf.step(make_two_finger(300, 200, ratio=0.6), 0.2, want="two_finger")
    assert pf.step(h, 0.3, want="two_finger").pinched


def _press_after_drift(pf, make_hand):
    """Rê yên ở x=100 tới 0.2 s, ngón khép kéo tay sang x=120, 140, chụm được ở x=150 lúc 0.3 s."""
    for i in range(7):
        pf.step(make_hand(100, 200, ratio=0.6), i * 0.033)           # đầu ngón trỏ (100, 170)
    pf.step(make_hand(120, 200, ratio=0.6), 0.233)
    pf.step(make_hand(140, 200, ratio=0.6), 0.266)
    return pf.step(make_hand(150, 200, ratio=0.1), 0.3)


def test_press_point_is_where_cursor_was_before_fingers_closed(make_hand):
    pf = _pf()
    res = _press_after_drift(pf, make_hand)
    assert res.pinched and res.fpt == (100, 200)                     # điểm chụm 0.12 s trước, không phải (150, 200)
    assert pf.step(make_hand(160, 200, ratio=0.1), 0.333).fpt == (110, 200)   # đi theo tay, không nhảy


def test_release_does_not_jump_then_eases_back_to_fingertip(make_hand):
    pf = _pf()
    _press_after_drift(pf, make_hand)
    pf.step(make_hand(160, 200, ratio=0.1), 0.333)
    res = pf.step(make_hand(160, 200, ratio=0.6), 0.4)               # mở ngón (tăng dần)
    res = pf.step(make_hand(160, 200, ratio=0.6), 0.5)
    res = pf.step(make_hand(160, 200, ratio=0.6), 0.65)          # nhảy 0.1 -> 0.6: giữ 0.2 s rồi nhả
    assert not res.pinched
    first = res.fpt
    assert abs(first[0] - 110) < 25                                  # ngay sau nhả vẫn gần chỗ cũ
    assert pf.step(make_hand(160, 200, ratio=0.6), 0.9).fpt == (160, 170)    # rồi về đầu ngón trỏ


def test_stabilize_off_keeps_old_behaviour(make_hand):
    pf = _pf()
    pf.stabilize = False
    assert _press_after_drift(pf, make_hand).fpt == (150, 200)


def test_hand_lost_forgets_old_positions(make_hand):
    pf = _pf()
    pf.step(make_hand(100, 200, ratio=0.6), 0.0)
    pf.step(None, 0.033)
    assert pf.step(make_hand(400, 300, ratio=0.1), 0.066).fpt == (400, 300)


def test_press_while_sweeping_does_not_pull_cursor_far_back(make_hand):
    pf = _pf()
    for i in range(10):                                              # quét ngang ~1000 px/s
        pf.step(make_hand(100 + 33 * i, 200, ratio=0.6), i * 0.033)
    res = pf.step(make_hand(430, 200, ratio=0.1), 0.33)
    assert res.pinched and math.dist(res.fpt, res.raw) <= Config().press_rewind_max_px + 1e-6


def test_closing_fingers_in_place_keeps_cursor_on_the_pinch(make_hand):
    pf = _pf()
    for i, r in enumerate([0.6, 0.6, 0.6, 0.5, 0.4, 0.3, 0.25]):     # tay đứng yên, chỉ ngón trỏ đi xuống
        pf.step(make_hand(300, 200, ratio=r), i * 0.033)
    res = pf.step(make_hand(300, 200, ratio=0.1), 0.233)
    assert res.pinched and math.dist(res.fpt, (300, 200)) < 2         # con trỏ nằm ngay chỗ chụm, không treo lơ lửng


def _feed(pf, frames, t0=0.0, dt=0.033):
    """Cho chuỗi (tay, cử chỉ muốn) vào bộ lọc; trả (kết quả cuối, danh sách pinched từng frame, t tiếp theo)."""
    out, res, t = [], None, t0
    for h, want in frames:
        res = pf.step(h, t, want)
        out.append(res.pinched)
        t += dt
    return res, out, t


def test_blocked_gesture_still_switches_back_so_pinch_draws(make_two_finger):
    pf = _pf()
    tog = make_two_finger(300, 300, 0.1)                                # trỏ + giữa áp sát (tư thế chỉ tay)
    _, _, t = _feed(pf, [(tog, "pinch")] * 3 + [(make_two_finger(300, 30, 0.1), "two_finger")] * 3
                    + [(tog, "pinch")] * 3)
    h = make_two_finger(300, 300, 0.1)
    h["pts"][4] = h["p4"] = (300, 302)                                  # chụm cái + trỏ để vẽ
    res, _, _ = _feed(pf, [(h, "pinch")] * 5, t)
    assert pf.active == "pinch" and res.pinched


def test_one_frame_hand_loss_does_not_unblock_into_a_false_press(make_two_finger):
    pf = _pf()
    bar = make_two_finger(300, 30, 0.1)
    _, _, t = _feed(pf, [(make_two_finger(300, 300, 0.1), "pinch")] * 5 + [(bar, "two_finger")] * 3)
    _, out, _ = _feed(pf, [(None, "two_finger")] + [(bar, "two_finger")] * 3, t)   # ngón chưa hề tách
    assert not any(out)


def test_gesture_switch_forgets_press_points_of_the_old_gesture(make_hand, make_two_finger):
    pf = _pf()
    _, _, t = _feed(pf, [(make_hand(300, 300, 0.6), "pinch")] * 7)     # trung điểm 4-8 = (300, 300)
    res, _, _ = _feed(pf, [(make_two_finger(300, 270, 0.6), "two_finger"),
                           (make_two_finger(300, 270, 0.1), "two_finger")], t)
    assert res.pinched and math.dist(res.fpt, (300, 270)) < 2          # đầu ngón trỏ, không phải trung điểm cũ


def test_quick_re_press_after_short_stroke_is_not_pulled_back(make_hand):
    pf = _pf()
    frames = [(make_hand(100, 300, 0.6), "pinch")] * 10
    frames += [(make_hand(100 + 200 * i / 7, 300, 0.1), "pinch") for i in range(8)]   # nét ngắn tới x=300
    frames += [(make_hand(300, 300, r), "pinch") for r in (0.3, 0.4, 0.5, 0.6)]       # mở ngón -> nhả
    frames += [(make_hand(300, 300, 0.1), "pinch")]                                    # chụm lại ngay
    res, _, _ = _feed(pf, frames)
    assert res.pinched and math.dist(res.fpt, (300, 300)) < 10


def test_block_ignores_the_pinch_already_held_until_fingers_open(make_hand):
    pf = _pf()
    pf.step(make_hand(100, 200, ratio=0.1), 0.0)            # đang chụm lúc bật / tắt bài đo K
    pf.block()
    assert not pf.step(make_hand(100, 200, ratio=0.1), 0.033).pinched     # không thành lần bấm ma
    for i, r in enumerate((0.25, 0.4, 0.6, 0.6, 0.6, 0.6)):          # mở hẳn > 0.07 s mới nhả
        pf.step(make_hand(100, 200, ratio=r), 0.066 + i * 0.033)
    assert pf.step(make_hand(100, 200, ratio=0.1), 0.3).pinched           # chụm lại thật thì bấm
