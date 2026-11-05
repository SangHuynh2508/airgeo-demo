import pytest

from airgeo import app
from airgeo.config import Config


def test_run_exits_with_message_when_camera_missing(monkeypatch):
    def no_camera(*args, **kwargs):
        raise RuntimeError("Khong mo duoc camera 0")
    monkeypatch.setattr(app, "open_camera", no_camera)
    with pytest.raises(SystemExit, match="camera 0"):
        app.run(Config())


def test_run_stops_cleanly_when_camera_stops_sending_frames(monkeypatch, tmp_path, capsys):
    class DeadCap:
        released = False

        def read(self):
            return False, None

        def release(self):
            DeadCap.released = True

    class FakeTracker:
        closed = False

        def __init__(self, **kwargs):
            pass

        def close(self):
            FakeTracker.closed = True

    monkeypatch.setattr(app, "open_camera", lambda *args, **kwargs: DeadCap())
    monkeypatch.setattr(app, "HandTracker", FakeTracker)
    monkeypatch.setattr(app.cv2, "namedWindow", lambda *args, **kwargs: None)
    monkeypatch.setattr(app.cv2, "destroyAllWindows", lambda: None)
    app.run(Config(data_dir=str(tmp_path)))
    assert DeadCap.released and FakeTracker.closed
    assert "Camera ngung gui hinh" in capsys.readouterr().out   # không thoát im lặng
