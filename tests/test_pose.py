from airgeo.gesture.pose import PoseTrigger, classify

XS = {1: -30, 2: -10, 3: 10, 4: 30}              # trỏ, giữa, áp út, út
TIP, PIP = {1: 8, 2: 12, 3: 16, 4: 20}, {1: 6, 2: 10, 3: 14, 4: 18}


def _hand(up, rot=False):
    """Bàn tay giả: cổ tay (0, 0); ngón duỗi thì đầu ngón xa cổ tay hơn khớp giữa, co thì gần hơn."""
    pts = [(0.0, -40.0)] * 21
    pts[0] = (0.0, 0.0)
    for f, x in XS.items():
        pts[PIP[f]] = (x, -60.0)
        pts[TIP[f]] = (x, -110.0) if up[f - 1] else (x, -30.0)
    return [(y, -x) for x, y in pts] if rot else pts


def test_classify_four_poses_ignores_pointing_and_rotation():
    assert classify(_hand((1, 1, 1, 0))) == "three"
    assert classify(_hand((1, 1, 1, 1))) == "palm"
    assert classify(_hand((1, 0, 0, 1))) == "rock"
    assert classify(_hand((0, 0, 0, 0))) == "fist"
    assert classify(_hand((1, 0, 0, 0))) is None and classify(_hand((1, 1, 0, 0))) is None
    assert classify(_hand((1, 1, 1, 0), rot=True)) == "three" and classify(_hand((0, 0, 0, 0), rot=True)) == "fist"


def test_trigger_fires_once_after_hold_and_survives_short_glitch():
    p = PoseTrigger()
    assert p.update("three", 0.0) is None
    assert p.update("three", 0.25) is None and p.progress == ("draw", 0.5)
    assert p.update("three", 0.4) is None
    assert p.update(None, 0.45) is None                  # nhiễu 1 frame: không đếm lại
    assert p.update("three", 0.5) == "draw"
    assert p.update("three", 1.0) is None                # giữ tiếp: không bắn lại
    p.update(None, 1.1)
    assert p.update(None, 1.3) is None and p.progress is None   # mất > 0.15 s: đếm lại từ đầu
    p.update("three", 1.4)
    assert p.update("three", 1.8) is None and p.update("three", 1.9) == "draw"


def test_palm_fires_select_then_menu_and_change_restarts():
    p = PoseTrigger()
    fired = [p.update("palm", t / 10) for t in range(0, 16)]
    assert [f for f in fired if f] == ["select", "menu"]
    p.update("fist", 2.0)
    assert p.update("fist", 2.7) is None and p.update("fist", 2.8) == "undo"
