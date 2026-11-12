import pytest

from airgeo.cli import parse_args
from airgeo.config import Config


def test_defaults_match_demo_values():
    c = Config()
    assert (c.camera, c.width, c.height, c.model_complexity) == (0, 1280, 720, 1)
    assert (c.pinch_on, c.pinch_off, c.pinch_grace, c.pinch_mode) == (0.20, 0.35, 0.2, "2d")
    assert (c.ma_window, c.one_euro_mincutoff, c.one_euro_beta, c.one_euro_dcutoff) == (5, 1.0, 0.007, 1.0)
    assert (c.data_dir, c.trail_len) == ("data", 60)


def test_cli_without_args_gives_defaults():
    assert parse_args([]) == Config()


def test_cli_overrides():
    c = parse_args(["--camera", "1", "--width", "640", "--height", "480", "--model", "0"])
    assert (c.camera, c.width, c.height, c.model_complexity) == (1, 640, 480, 0)
    assert c.pinch_on == Config().pinch_on


def test_cli_rejects_bad_model():
    with pytest.raises(SystemExit):
        parse_args(["--model", "2"])


def test_interaction_defaults():
    c = Config()
    assert (c.toolbar_height, c.key_size, c.hit_radius, c.label_radius) == (60, 80, 15, 25)
    assert (c.drag_threshold, c.min_side_px, c.history_limit, c.confirm_window) == (10, 10, 50, 2.0)


def test_two_finger_defaults():
    c = Config()
    assert (c.two_finger_on, c.two_finger_off) == (0.25, 0.40) and not hasattr(c, "gesture")
