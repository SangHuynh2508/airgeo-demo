from airgeo.interaction.pointer import PointerTracker
from airgeo.pinch_filter import FrameResult


def frame(pinched, fpt=None, holding=False):
    return FrameResult(fpt, fpt, pinched, holding)


def kinds(events):
    return [(e.kind, e.pos) for e in events]


def test_pinch_cycle_gives_hover_down_move_up():
    tr = PointerTracker()
    assert kinds(tr.update(frame(False, (1, 1)), 0.0)) == [("hover", (1, 1))]
    assert kinds(tr.update(frame(True, (2, 2)), 0.1)) == [("down", (2, 2))]
    assert kinds(tr.update(frame(True, (3, 3)), 0.2)) == [("move", (3, 3))]
    assert kinds(tr.update(frame(False, (4, 4)), 0.3)) == [("up", (3, 3)), ("hover", (4, 4))]


def test_holding_frame_gives_no_event_and_up_uses_last_valid_point():
    tr = PointerTracker()
    tr.update(frame(True, (2, 2)), 0.0)
    assert tr.update(frame(True, None, holding=True), 0.1) == []
    assert kinds(tr.update(frame(False, None), 0.4)) == [("up", (2, 2))]   # mất tay quá 0.2 s


def test_down_waits_for_first_point():
    tr = PointerTracker()
    assert tr.update(frame(True, None), 0.0) == []
    assert kinds(tr.update(frame(True, (5, 5)), 0.1)) == [("down", (5, 5))]


def test_no_hand_no_event():
    assert PointerTracker().update(frame(False, None), 0.0) == []
