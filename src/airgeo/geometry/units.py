"""Đơn vị đo. Tỉ lệ bản vẽ lưu bằng số px ứng với 1 cm; đổi đơn vị chỉ đổi số hiển thị."""
UNITS = ["mm", "cm", "dm", "m"]
TO_CM = {"mm": 0.1, "cm": 1.0, "dm": 10.0, "m": 100.0}


def to_px(value, unit, scale):
    return value * TO_CM[unit] * scale


def to_units(px, unit, scale):
    return px / scale / TO_CM[unit]


def fmt_length(px, scale, unit):
    """Chưa có tỉ lệ (scale=None) thì hiện px như bản demo."""
    return f"{px:.0f}px" if scale is None else f"{to_units(px, unit, scale):.2f} {unit}"


def fmt_area(px2, scale, unit):
    if scale is None:
        return f"{px2:.0f}px2"
    return f"{px2 / (scale * TO_CM[unit]) ** 2:.2f} {unit}2"
