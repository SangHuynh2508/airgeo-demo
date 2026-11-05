from airgeo.config import Config
from airgeo.session import DrawingSession


def _session(smart=False):
    s = DrawingSession(Config())
    s.select_filter("none")          # không lọc -> dễ kiểm tra tọa độ
    if smart:
        s.toggle_smart()
    return s


def _square(n=20):
    c = [(100, 100), (300, 100), (300, 300), (100, 300)]
    pts = []
    for (ax, ay), (bx, by) in zip(c, c[1:] + c[:1]):
        pts += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
    return pts + [c[0]]


def _draw_stroke(s, make_hand, pts, t0=0.0):
    """Chụm, đi qua các điểm, rồi mở tay đủ lâu để nét kết thúc. Trả về thời điểm cuối."""
    t = t0
    for x, y in pts:
        s.step(make_hand(x, y, ratio=0.1), t)
        t += 0.033
    s.step(make_hand(*pts[-1], ratio=0.6), t)
    s.step(make_hand(*pts[-1], ratio=0.6), t + 0.3)
    return t + 0.3


def test_pinch_draws_and_release_finishes_stroke(make_hand):
    s = _session()
    for i, x in enumerate((100, 110, 120)):
        res = s.step(make_hand(x, 200, ratio=0.1), i * 0.033)
        assert res.pinched and res.fpt == (x, 200)
    assert [p[:2] for p in s.cur] == [(100, 200), (110, 200), (120, 200)]
    s.step(make_hand(130, 200, ratio=0.6), 0.10)    # mở tay: còn trong thời gian giữ nét
    assert s.strokes == [] and len(s.cur) == 3
    s.step(make_hand(130, 200, ratio=0.6), 0.40)    # quá 0.2 s -> nhả
    assert s.cur is None and len(s.strokes) == 1
    assert s.strokes[0]["kind"] == "free" and len(s.strokes[0]["raw"]) == 3


def test_holding_frames_add_no_points(make_hand):
    s = _session()
    s.step(make_hand(100, 200, ratio=0.1), 0.0)
    res = s.step(make_hand(500, 500, ratio=0.6), 0.05)   # MediaPipe đặt sai điểm 1 frame
    assert res.holding and res.raw is None and res.fpt is None
    s.step(None, 0.08)                                    # mất tay 1 frame
    s.step(make_hand(110, 200, ratio=0.1), 0.12)
    assert [p[:2] for p in s.cur] == [(100, 200), (110, 200)]


def test_single_point_stroke_is_dropped(make_hand):
    s = _session()
    s.step(make_hand(100, 200, ratio=0.1), 0.0)
    s.step(make_hand(100, 200, ratio=0.6), 0.1)
    s.step(make_hand(100, 200, ratio=0.6), 0.4)
    assert s.strokes == [] and s.cur is None


def test_smart_mode_recognizes_square_as_rect(make_hand):
    s = _session(smart=True)
    _draw_stroke(s, make_hand, _square())
    assert s.strokes[0]["kind"] == "rect"
    assert s.last_info.startswith("rect")


def test_toggle_smart_rerecognizes_existing_strokes(make_hand):
    s = _session()
    _draw_stroke(s, make_hand, _square())
    assert s.strokes[0]["kind"] == "free"
    s.toggle_smart()
    assert s.strokes[0]["kind"] == "rect"
    s.toggle_smart()
    assert s.strokes[0]["kind"] == "free"


def test_undo_and_clear_are_safe_when_empty_or_drawing(make_hand):
    s = _session()
    s.undo()
    s.clear()                                            # chưa có nét: không lỗi
    end = _draw_stroke(s, make_hand, _square())
    s.step(make_hand(50, 50, ratio=0.1), end + 0.1)      # đang vẽ nét mới
    s.clear()
    assert s.strokes == [] and s.cur is not None         # xóa hình cũ, nét đang vẽ vẫn tiếp tục
    s.undo()
    assert s.strokes == []


def test_hand_lost_while_released_resets_filter(make_hand):
    s = DrawingSession(Config())                         # 1€ mặc định
    s.step(make_hand(100, 100, ratio=0.6), 0.0)
    s.step(None, 0.033)
    res = s.step(make_hand(600, 400, ratio=0.6), 0.066)
    assert res.fpt == (600, 400)                         # không bị kéo từ (100, 100)


def test_select_filter_switches_and_resets(make_hand):
    s = DrawingSession(Config())
    assert s.flt.name == "one_euro"
    s.select_filter("moving_avg")
    assert s.flt is s.moving_avg


def test_csv_row_keeps_raw_landmarks(make_hand):
    s = _session()
    hand = make_hand(100, 200, ratio=0.1)                # p4 = (100, 205), p8 = (100, 195)
    row = s.csv_row(hand, 1.5, s.step(hand, 1.5))
    assert row["t"] == "1.500000"
    assert row["x8_raw"] == "100.00" and row["y8_raw"] == "195.00" and row["y4_raw"] == "205.00"
    assert row["x_filt"] == "100.00" and row["y_filt"] == "200.00"
    assert row["pinch"] == 1 and row["filter_name"] == "none" and row["mode"] == "free"
    empty = s.csv_row(None, 1.6, s.step(None, 1.6))
    assert empty["x8_raw"] is None and empty["x_filt"] is None
