import math

from airgeo.gesture.digits import DigitReader, accuracy, read_digit

H = 150     # chiều cao chữ số khi viết (px)


def _at(pts, x0, y0=100, h=H):
    return [(x0 + x * h, y0 + y * h) for x, y in pts]


# Nét "viết tay" vẽ riêng cho test (không lấy từ mẫu huấn luyện): hơi lệch, ít điểm
ONE = [[(0.32, 0.02), (0.30, 0.5), (0.31, 0.98)]]
TWO = [[(0.05, 0.25), (0.15, 0.05), (0.35, 0.0), (0.52, 0.1), (0.55, 0.3), (0.4, 0.55), (0.05, 0.98), (0.6, 0.97)]]
FOUR = [[(0.4, 0.0), (0.02, 0.62), (0.6, 0.62)], [(0.42, 0.25), (0.43, 1.0)]]
FIVE = [[(0.55, 0.02), (0.1, 0.02), (0.08, 0.45), (0.3, 0.38), (0.52, 0.5), (0.58, 0.7), (0.45, 0.92), (0.25, 0.98),
         (0.03, 0.88)]]
SEVEN = [[(0.02, 0.03), (0.58, 0.0), (0.25, 0.98)]]
ZERO = [[(0.3 + 0.28 * math.cos(a / 10), 0.5 + 0.48 * math.sin(a / 10)) for a in range(64)]]
DOT = [[(0.0, 0.0), (0.03, 0.02)]]


def test_held_out_synthetic_accuracy():
    assert accuracy(seed=99, per_digit=30) >= 0.95


def test_reads_hand_drawn_polylines():
    for strokes, d in ((ONE, "1"), (TWO, "2"), (FOUR, "4"), (FIVE, "5"), (SEVEN, "7"), (ZERO, "0")):
        assert read_digit([_at(s, 100) for s in strokes]) == d, d


def _write(r, strokes, x0, y0=100):
    for s in strokes:
        r.add(_at(s, x0, y0))


def test_reader_groups_strokes_into_digits():
    r = DigitReader(H)
    _write(r, ONE, 100)
    _write(r, TWO, 200)
    assert r.text == "12"
    r.clear()
    _write(r, FOUR, 100)                         # 2 nét, cùng 1 chữ số
    assert r.text == "4"


def test_reader_decimal_point_and_delete():
    r = DigitReader(H)
    _write(r, DOT, 50, 240)                      # chấm chập chờn trước chữ số đầu: bỏ
    _write(r, SEVEN, 100)
    _write(r, DOT, 200, 240)
    _write(r, FIVE, 240)
    assert r.text == "7.5"
    r.pop()
    assert r.text == "7."
    r.clear()
    assert r.text == ""
