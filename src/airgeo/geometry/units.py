"""Đơn vị đo. Tỉ lệ bản vẽ lưu bằng số px ứng với 1 cm; đổi đơn vị chỉ đổi số hiển thị."""
import math
from decimal import ROUND_HALF_UP, Decimal

UNITS = ["mm", "cm", "dm", "m"]
TO_CM = {"mm": 0.1, "cm": 1.0, "dm": 10.0, "m": 100.0}


def to_px(value, unit, scale):
    return value * TO_CM[unit] * scale


def to_units(px, unit, scale):
    return px / scale / TO_CM[unit]


def fmt_length(px, scale, unit):
    """Độ dài px theo đơn vị, số gọn: "9 cm", "2.4 cm" (cần có tỉ lệ)."""
    return f"{trim(to_units(px, unit, scale))} {unit}"


def trim(v):
    """Số gọn, bỏ 0 thừa: 2 chữ số thập phân (5, 2.4, 18.85); số nhỏ hơn 1 giữ 3 chữ số có nghĩa
    để đổi sang dm / m không thành 0 (0.045, 0.0012)."""
    d = 2 if abs(v) >= 1 or v == 0 else 2 - math.floor(math.log10(abs(v)))
    # làm tròn 5 lên như ở trường (1.085 -> 1.09); f"{:.2f}" làm trên số nhị phân 1.08499... -> 1.08
    q = Decimal(repr(v)).quantize(Decimal(1).scaleb(-d), ROUND_HALF_UP)
    return f"{q:f}".rstrip("0").rstrip(".")


def round_sum(vals, total):
    """Làm tròn từng số về số nguyên mà tổng vẫn đúng bằng total (góc tam giác: 55 + 70 + 55 = 180, không 181):
    lấy phần nguyên rồi cộng 1 cho các số có phần lẻ lớn nhất (largest remainder).
    Hai số bằng nhau (2 góc đáy tam giác cân) mà bị làm tròn khác nhau thì làm tròn tới 0.5 (72.5 + 72.5 + 35)."""
    for step in (1, 0.5, 0.1):
        out = [math.floor(v / step) for v in vals]
        for i in sorted(range(len(vals)), key=lambda i: out[i] - vals[i] / step)[:round(total / step) - sum(out)]:
            out[i] += 1
        out = [o * step if step < 1 else o for o in out]
        if all(out[i] == out[j] for i in range(len(vals)) for j in range(i) if abs(vals[i] - vals[j]) < 1e-6):
            break
    return [round(o, 1) for o in out] if step < 1 else out
