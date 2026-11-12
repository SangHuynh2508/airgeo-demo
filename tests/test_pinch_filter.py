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
    row = pf.csv_row(hand, 1.5, pf.step(hand, 1.5), smart=False)
    assert row["t"] == "1.500000"
    assert row["x8_raw"] == "100.00" and row["y8_raw"] == "195.00" and row["y4_raw"] == "205.00"
    assert row["x_filt"] == "100.00" and row["y_filt"] == "200.00"
    assert row["pinch"] == 1 and row["filter_name"] == "none" and row["mode"] == "free"
    empty = pf.csv_row(None, 1.6, pf.step(None, 1.6), smart=True)
    assert empty["x8_raw"] is None and empty["x_filt"] is None and empty["mode"] == "smart"


def test_hover_cursor_is_index_tip_and_pinch_draws_at_midpoint(make_hand):
    pf = _pf()
    assert pf.step(make_hand(100, 200, ratio=0.6), 0.0, want="pinch").fpt == (100, 170)   # p8
    assert pf.step(make_hand(100, 200, ratio=0.1), 0.1, want="pinch").fpt == (100, 200)   # trung điểm 4-8


def test_two_fingers_press_only_where_wanted_and_need_a_fresh_close(make_two_finger):
    pf = _pf()
    together, apart = make_two_finger(300, 200, ratio=0.1), make_two_finger(300, 200, ratio=0.6)
    assert not pf.step(together, 0.0, want="pinch").pinched        # vùng vẽ: 2 ngón không vẽ
    assert not pf.step(together, 0.1, want="two_finger").pinched   # đưa vào menu lúc 2 ngón đã áp: chưa bấm
    pf.step(apart, 0.2, want="two_finger")
    res = pf.step(together, 0.3, want="two_finger")
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
