import pytest


def _hand(x=320.0, y=240.0, ratio=0.1, t=0.0):
    """Bàn tay giả: điểm vẽ (trung điểm 4–8) ở (x, y); lòng bàn tay (0 -> 9) dài 100 px / 0.1 m;
    khoảng cách ngón cái – ngón trỏ = ratio × lòng bàn tay, đo 2D hay 3D đều ra cùng ratio."""
    d = ratio * 100
    pts = [(x, y)] * 21
    pts[0], pts[9] = (x, y + 150), (x, y + 50)
    pts[4], pts[8] = (x, y + d / 2), (x, y - d / 2)
    return {"t": t, "p4": pts[4], "p8": pts[8], "pts": pts,
            "w0": (0.0, 0.0, 0.0), "w9": (0.0, 0.1, 0.0),
            "w4": (0.0, 0.0, 0.0), "w8": (0.0, ratio * 0.1, 0.0)}


@pytest.fixture
def make_hand():
    return _hand
