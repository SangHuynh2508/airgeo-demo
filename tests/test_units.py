import pytest

from airgeo.geometry.units import UNITS, fmt_length, to_px, to_units


def test_units_order():
    assert UNITS == ["mm", "cm", "dm", "m"]


def test_conversions():
    assert to_px(1, "cm", 50) == 50 and to_px(10, "mm", 50) == pytest.approx(50)
    assert to_units(50, "mm", 50) == pytest.approx(10) and to_units(5000, "m", 50) == pytest.approx(1)


def test_fmt_length_is_compact():
    assert fmt_length(250, 50, "cm") == "5 cm" and fmt_length(250, 50, "mm") == "50 mm"
    assert fmt_length(120, 50, "cm") == "2.4 cm"
