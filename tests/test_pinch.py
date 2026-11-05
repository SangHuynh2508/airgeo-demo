from airgeo.gesture.pinch import PinchDetector, draw_point


def test_hysteresis_between_thresholds(make_hand):
    d = PinchDetector(0.30, 0.45, grace=0.2)
    seq = [0.6, 0.38, 0.2, 0.38, 0.44]   # 0.38 nằm giữa 2 ngưỡng
    assert [d.update(make_hand(ratio=r), i * 0.033) for i, r in enumerate(seq)] == \
        [False, False, True, True, True]


def test_holds_through_short_glitch_then_releases(make_hand):
    d = PinchDetector(0.30, 0.45, grace=0.2)
    d.update(make_hand(ratio=0.2), 0.0)
    assert d.update(make_hand(ratio=0.6), 1.0) is True and d.holding
    assert d.update(None, 1.1) is True and d.holding
    assert d.update(make_hand(ratio=0.2), 1.15) is True and not d.holding
    d.update(make_hand(ratio=0.6), 2.0)
    assert d.update(make_hand(ratio=0.6), 2.25) is False and not d.holding


def test_hand_lost_when_released_stays_released():
    d = PinchDetector()
    assert d.update(None, 0.0) is False and d.ratio is None


def test_shift_moves_both_thresholds_and_has_floor():
    d = PinchDetector(0.30, 0.45)
    d.shift(-0.05)
    assert abs(d.on_ratio - 0.25) < 1e-9 and abs(d.off_ratio - 0.40) < 1e-9
    d.shift(-1.0)                       # không cho ngưỡng bật xuống dưới 0.05
    assert abs(d.on_ratio - 0.25) < 1e-9


def test_mode_3d_uses_world_landmarks(make_hand):
    d = PinchDetector(mode="3d")
    d.update(make_hand(ratio=0.5), 0.0)
    assert abs(d.ratio3d - 0.5) < 1e-9 and d.ratio == d.ratio3d
    d.toggle_mode()
    assert d.mode == "2d"


def test_defaults_match_demo():
    d = PinchDetector()
    assert (d.on_ratio, d.off_ratio, d.grace, d.mode) == (0.20, 0.35, 0.2, "2d")


def test_draw_point_is_thumb_index_midpoint():
    assert draw_point({"p4": (0, 0), "p8": (10, 20)}) == (5, 10)
