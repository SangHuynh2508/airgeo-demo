import pytest

from airgeo.geometry.units import UNITS, fmt_area, fmt_length, to_px, to_units


def test_units_order():
    assert UNITS == ["mm", "cm", "dm", "m"]


def test_conversions():
    assert to_px(1, "cm", 50) == 50 and to_px(10, "mm", 50) == pytest.approx(50)
    assert to_units(50, "mm", 50) == pytest.approx(10) and to_units(5000, "m", 50) == pytest.approx(1)


def test_fmt_length_px_until_scale_is_set():
    assert fmt_length(123.4, None, "cm") == "123px"
    assert fmt_length(250, 50, "cm") == "5.00 cm" and fmt_length(250, 50, "mm") == "50.00 mm"


def test_fmt_area_uses_square_units():
    assert fmt_area(10, None, "cm") == "10px2"
    assert fmt_area(2500, 50, "cm") == "1.00 cm2" and fmt_area(2500, 50, "mm") == "100.00 mm2"
