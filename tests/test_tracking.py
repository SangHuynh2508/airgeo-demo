import numpy as np
import pytest

from airgeo.tracking import camera
from airgeo.tracking.hand_tracker import CONNECTIONS, HandTracker


def test_no_hand_in_blank_frame_returns_none():
    tr = HandTracker()
    try:
        assert tr.process(np.zeros((480, 640, 3), np.uint8), 1.0) is None
    finally:
        tr.close()


def test_connections_cover_all_21_landmarks():
    assert {i for pair in CONNECTIONS for i in pair} == set(range(21))


def _fake_videocapture(monkeypatch, opened_by):
    """Thay cv2.VideoCapture bằng bản giả; opened_by: backend nào mở được."""
    calls = []

    class FakeCap:
        def __init__(self, index, backend):
            self.backend, self.props = backend, {}
            calls.append(backend)

        def isOpened(self):
            return opened_by.get(self.backend, False)

        def set(self, prop, value):
            self.props[prop] = value
            return True

    monkeypatch.setattr(camera.cv2, "VideoCapture", FakeCap)
    return calls


def test_open_camera_prefers_msmf(monkeypatch):
    calls = _fake_videocapture(monkeypatch, {camera.cv2.CAP_MSMF: True})
    cap = camera.open_camera(0, 1280, 720)
    assert calls == [camera.cv2.CAP_MSMF]
    assert cap.props[camera.cv2.CAP_PROP_FRAME_WIDTH] == 1280
    assert cap.props[camera.cv2.CAP_PROP_FRAME_HEIGHT] == 720


def test_open_camera_falls_back_to_dshow_with_mjpg(monkeypatch):
    calls = _fake_videocapture(monkeypatch, {camera.cv2.CAP_DSHOW: True})
    cap = camera.open_camera(0, 1280, 720)
    assert calls == [camera.cv2.CAP_MSMF, camera.cv2.CAP_DSHOW]
    assert cap.props[camera.cv2.CAP_PROP_FOURCC] == camera.cv2.VideoWriter_fourcc(*"MJPG")


def test_open_camera_raises_when_no_backend_works(monkeypatch):
    _fake_videocapture(monkeypatch, {})
    with pytest.raises(RuntimeError, match="camera 3"):
        camera.open_camera(3, 1280, 720)
