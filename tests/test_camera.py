import time

from airgeo.tracking.camera import FrameGrabber


class FakeCap:
    """Camera giả: mỗi lần đọc chờ `period` giây rồi trả frame số tiếp theo; hết thì trả (False, None)."""
    def __init__(self, n, period=0.01):
        self.n, self.period, self.i, self.released = n, period, 0, False

    def read(self):
        time.sleep(self.period)
        if self.i >= self.n:
            return False, None
        self.i += 1
        return True, self.i

    def release(self):
        self.released = True


def test_never_returns_the_same_frame_twice():
    g = FrameGrabber(FakeCap(5))
    seen = [g.read()[1] for _ in range(5)]
    assert seen == sorted(set(seen)) and len(seen) == 5
    g.release()


def test_slow_consumer_gets_the_newest_frame():
    g = FakeCap(100, period=0.005)
    grab = FrameGrabber(g)
    first = grab.read()[1]
    time.sleep(0.1)                                  # xử lý chậm: camera đã chụp thêm nhiều frame
    ok, frame, t = grab.read()
    assert ok and frame - first > 5 and t <= time.perf_counter()
    grab.release()
    assert g.released


def test_camera_failure_ends_reading():
    grab = FrameGrabber(FakeCap(1))
    assert grab.read()[0] is True
    assert grab.read(timeout=1.0)[0] is False
    grab.release()
