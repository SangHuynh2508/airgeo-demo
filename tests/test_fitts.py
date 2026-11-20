import math

from airgeo.interaction.fitts import FittsTask
from airgeo.interaction.pointer import PointerEvent as E


def _click(task, pos, t, stabilize=True):
    task.on_event(E("down", pos, t), stabilize)
    task.on_event(E("up", pos, t + 0.05), stabilize)


def _run_block(task, t0=0.0, mt=0.5, off=lambda i: (0.0, 0.0)):
    """Bấm hết 1 khối: lần đầu (không tính) + n lần, mỗi lần cách mt giây; off(i) = lệch khỏi tâm mục tiêu."""
    t = t0
    for i in range(task.n + 1):
        x, y = task.targets()[task.current]
        dx, dy = off(i)
        _click(task, (x + dx, y + dy), t)
        t += mt
    return t


def test_opposite_order_and_targets_on_circle():
    task = FittsTask(1280, 720, blocks=[(300, 50)])
    assert task.order == [0, 6, 1, 7, 2, 8, 3, 9, 4, 10, 5, 0]
    cx, cy = task.center
    assert all(abs(math.dist(p, (cx, cy)) - 150) < 1e-9 for p in task.targets())


def test_first_click_not_measured_and_perfect_block():
    task = FittsTask(1280, 720, blocks=[(300, 50)])
    _run_block(task)
    assert len(task.records) == 11 and task.done
    s = task.summary()[0]
    assert s["error_rate"] == 0 and abs(s["mt_ms"] - 500) < 1e-6 and s["tp"] > 0 and s["we"] == 50   # SD = 0: dùng W


def test_misses_counted_and_blocks_advance():
    task = FittsTask(1920, 1080, blocks=[(300, 50), (500, 90)])      # khung lớn: giữ đúng cỡ D, W
    _run_block(task, off=lambda i: (40.0, 0.0) if i % 2 else (0.0, 0.0))     # lệch 40 > W/2 = 25: trượt
    assert not task.done and task.block == 1
    s = task.summary()[0]
    assert abs(s["error_rate"] - 6 / 11) < 1e-9
    _run_block(task, t0=10.0)
    assert task.done and [b["D"] for b in task.summary()] == [300, 500]


def test_effective_width_from_spread_along_task_axis():
    task = FittsTask(1280, 720, blocks=[(500, 90)])
    tg = task.targets()

    def along_axis(i):                       # lệch ±6 px dọc theo hướng di chuyển tới mục tiêu i
        if i == 0:
            return (0.0, 0.0)
        a, b = tg[task.order[i - 1]], tg[task.order[i]]
        d = math.dist(a, b)
        s = 6 if i % 2 else -6
        return ((b[0] - a[0]) / d * s, (b[1] - a[1]) / d * s)
    _run_block(task, off=along_axis)
    s = task.summary()[0]
    sd = math.sqrt(sum((6 if i % 2 else -6) ** 2 for i in range(1, 12)) / 10 - (6 / 11) ** 2 * 11 / 10)
    assert abs(s["we"] - 4.133 * sd) < 0.5 and s["error_rate"] == 0


def test_save_writes_trials_and_summary(tmp_path):
    task = FittsTask(1280, 720, blocks=[(300, 50)])
    _run_block(task)
    trials, summary = task.save(str(tmp_path))
    assert open(trials, encoding="utf-8").read().count("\n") == 12
    assert "tp" in open(summary, encoding="utf-8").readline()


def test_small_frame_shrinks_targets_to_fit():
    task = FittsTask(640, 480)
    for k in range(len(task.blocks)):
        task.block = k
        W = task.blocks[k][1]
        assert all(W / 2 <= x <= 640 - W / 2 and W / 2 <= y <= 480 - W / 2 for x, y in task.targets())


def test_targets_stay_above_the_bottom_strip():
    task = FittsTask(1280, 720)
    for k in range(len(task.blocks)):
        task.block = k
        W = task.blocks[k][1]
        assert all(90 <= y - W / 2 and y + W / 2 <= 560 for _, y in task.targets())   # tay thấp thì mất tay


def test_draw_highlights_the_target_to_press():
    import numpy as np
    from airgeo.ui.render import draw_fitts
    task = FittsTask(1280, 720)
    frame = np.full((720, 1280, 3), 200, np.uint8)
    draw_fitts(frame, task)
    x, y = task.targets()[task.current]
    assert tuple(frame[int(y), int(x)]) == (0, 255, 255)


def test_condition_switched_mid_block_is_labelled_mixed():
    t = FittsTask(1280, 720, blocks=[(300, 50)], n=3)
    tg = t.targets()
    for k, s in enumerate([True, True, False, False]):
        t.on_event(E("down", tg[t.current], k * 0.5), s)
    assert t.summary()[0]["stabilize"] == "mixed"


def test_save_failure_is_reported_not_raised(tmp_path):
    t = FittsTask(1280, 720)
    blocker = tmp_path / "f"
    blocker.write_text("x")                                          # thư mục đích là 1 file -> OSError
    assert t.save_status(str(blocker)).startswith("Lỗi lưu")
    assert t.save_status(str(tmp_path)).startswith("Đã lưu")
