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


from airgeo.interaction.pointer import PointerEvent  # noqa: E402


@pytest.fixture
def stroke():
    """Chụm ở pts[0], kéo qua các điểm, nhả ở điểm cuối (gửi thẳng sự kiện vào Controller)."""
    def _stroke(ctl, pts, t0=0.0):
        ctl.dispatch(PointerEvent("down", pts[0], t0))
        for i, p in enumerate(pts[1:], 1):
            ctl.dispatch(PointerEvent("move", p, t0 + i * 0.033))
        ctl.dispatch(PointerEvent("up", pts[-1], t0 + len(pts) * 0.033))
    return _stroke


@pytest.fixture
def press():
    """Chụm rồi nhả tại 1 điểm (bấm nút / chọn hình / bấm phím số)."""
    def _press(ctl, pos, t=0.0):
        ctl.dispatch(PointerEvent("down", pos, t))
        ctl.dispatch(PointerEvent("up", pos, t + 0.1))
    return _press


@pytest.fixture
def button():
    """Tâm của nút trên thanh công cụ."""
    def _button(ctl, name):
        x0, y0, x1, y1 = ctl.toolbar.rects[name]
        return ((x0 + x1) / 2, (y0 + y1) / 2)
    return _button
