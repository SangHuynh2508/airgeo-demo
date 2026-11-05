from types import SimpleNamespace

from airgeo.config import Config
from airgeo.document.board import Board
from airgeo.interaction.pointer import PointerTracker
from airgeo.pinch_filter import PinchFilter
from airgeo.tools.draw import DrawTool


def _pipeline(smart=False):
    """Bàn tay giả -> PinchFilter (không lọc) -> PointerTracker -> DrawTool -> Board."""
    pf = PinchFilter(Config(gesture="pinch"))
    pf.select_filter("none")
    ctl = SimpleNamespace(board=Board())
    ctl.board.set_smart(smart)
    tool, pointer = DrawTool(), PointerTracker()

    def step(hand, t):
        for ev in pointer.update(pf.step(hand, t), t):
            tool.on_event(ev, ctl)
    return ctl, tool, step


def _square(n=20):
    c = [(100, 100), (300, 100), (300, 300), (100, 300)]
    pts = []
    for (ax, ay), (bx, by) in zip(c, c[1:] + c[:1]):
        pts += [(ax + (bx - ax) * k / n, ay + (by - ay) * k / n) for k in range(n)]
    return pts + [c[0]]


def test_pinch_draws_and_release_finishes_stroke(make_hand):
    ctl, tool, step = _pipeline()
    for i, x in enumerate((100, 110, 120)):
        step(make_hand(x, 200, ratio=0.1), i * 0.033)
    assert [p[:2] for p in tool.cur] == [(100, 200), (110, 200), (120, 200)]
    step(make_hand(130, 200, ratio=0.6), 0.10)     # mở tay: còn trong thời gian giữ nét
    assert ctl.board.shapes == [] and len(tool.cur) == 3
    step(make_hand(130, 200, ratio=0.6), 0.40)     # quá 0.2 s -> nhả
    assert tool.cur is None and len(ctl.board.shapes) == 1
    assert ctl.board.shapes[0]["kind"] == "free" and len(ctl.board.shapes[0]["raw"]) == 3


def test_holding_frames_add_no_points(make_hand):
    ctl, tool, step = _pipeline()
    step(make_hand(100, 200, ratio=0.1), 0.0)
    step(make_hand(500, 500, ratio=0.6), 0.05)     # MediaPipe đặt sai điểm 1 frame
    step(None, 0.08)                               # mất tay 1 frame
    step(make_hand(110, 200, ratio=0.1), 0.12)
    assert [p[:2] for p in tool.cur] == [(100, 200), (110, 200)]


def test_single_point_stroke_is_dropped(make_hand):
    ctl, tool, step = _pipeline()
    step(make_hand(100, 200, ratio=0.1), 0.0)
    step(make_hand(100, 200, ratio=0.6), 0.1)
    step(make_hand(100, 200, ratio=0.6), 0.4)
    assert ctl.board.shapes == [] and tool.cur is None


def test_smart_mode_turns_square_into_rect(make_hand):
    ctl, tool, step = _pipeline(smart=True)
    t = 0.0
    for x, y in _square():
        step(make_hand(x, y, ratio=0.1), t)
        t += 0.033
    step(make_hand(100, 100, ratio=0.6), t)
    step(make_hand(100, 100, ratio=0.6), t + 0.3)
    assert ctl.board.shapes[0]["kind"] == "rect" and ctl.board.last_info.startswith("rect")


def test_end_keeps_unfinished_stroke(make_hand):
    ctl, tool, step = _pipeline()
    step(make_hand(100, 200, ratio=0.1), 0.0)
    step(make_hand(150, 200, ratio=0.1), 0.033)
    tool.end(ctl)                                  # ví dụ: đổi công cụ khi đang vẽ
    assert tool.cur is None and len(ctl.board.shapes) == 1
