"""Nhận dạng chữ số viết trên không (nhập số đo bằng tay, không cần bàn phím).

Cách làm (máy học có giám sát):
  - Mỗi chữ số được vẽ lại thành ảnh 32x32 (giữ tỉ lệ khung, căn giữa) -> đặc trưng HOG (324 chiều).
  - Bộ phân loại k láng giềng gần nhất (cv2.ml.KNearest, k = 3).
  - Dữ liệu huấn luyện tổng hợp: mỗi chữ số có vài mẫu đường nét (TEMPLATES, kiểu viết 1 nét / 2 nét), mỗi mẫu được
    tăng cường ngẫu nhiên (xoay, nghiêng, co giãn ngang, rung tay) -> hàng nghìn mẫu, huấn luyện lúc dùng lần đầu.
  - accuracy(): độ chính xác trên tập kiểm tra sinh với seed khác (đánh giá trong luận văn).

DigitReader gom các nét viết trong ô viết thành dãy chữ số theo vị trí ngang; chấm nhỏ sau 1 chữ số là dấu ".".
"""
import math

import cv2
import numpy as np

SIZE, BOX, K = 32, 24, 3
_HOG = cv2.HOGDescriptor((SIZE, SIZE), (16, 16), (8, 8), (8, 8), 9)


def _arc(cx, cy, rx, ry, a0, a1, n=24):
    """Cung elip (trục y hướng xuống như ảnh), góc độ từ a0 tới a1."""
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


_EIGHT = [(0.3 + 0.27 * math.sin(2 * t / 20 * math.pi), 0.5 - 0.5 * math.cos(t / 20 * math.pi)) for t in range(41)]

# Mẫu đường nét trong khung rộng 0.6 x cao 1 (y hướng xuống). Mỗi mẫu là danh sách nét.
TEMPLATES = {
    "0": [[_arc(.3, .5, .3, .5, -90, 270)], [_arc(.25, .5, .2, .5, -80, 280)]],
    "1": [[[(.3, 0), (.3, 1)]], [[(.1, .22), (.3, 0), (.3, 1)]], [[(.1, .22), (.3, 0), (.3, 1)], [(.08, 1), (.52, 1)]]],
    "2": [[_arc(.3, .28, .28, .28, 190, 390) + [(0, 1), (.6, 1)]],
          [_arc(.3, .3, .28, .3, 200, 380) + [(.05, 1), (.6, .98)]]],
    "3": [[_arc(.28, .25, .28, .25, 200, 450) + _arc(.28, .75, .3, .25, 270, 520)],
          [[(0, 0), (.6, 0), (.22, .42)] + _arc(.28, .71, .3, .29, 250, 515)]],
    "4": [[[(.42, 0), (0, .65), (.6, .65)], [(.45, .2), (.45, 1)]],
          [[(.05, 0), (.05, .6), (.6, .6)], [(.45, 0), (.45, 1)]],
          [[(.45, 1), (.45, 0), (0, .65), (.6, .65)]]],
    "5": [[[(.55, 0), (.08, 0), (.05, .45)] + _arc(.27, .7, .3, .27, 220, 510)],
          [[(.08, 0), (.05, .45)] + _arc(.27, .7, .3, .27, 220, 510), [(.08, 0), (.55, 0)]]],
    "6": [[_arc(.35, .5, .33, .48, 290, 150) + _arc(.3, .72, .27, .26, 180, -180)],
          [[(.5, 0), (.15, .45)] + _arc(.3, .72, .27, .26, 200, -160)]],
    "7": [[[(0, 0), (.6, 0), (.2, 1)]], [[(0, 0), (.6, 0), (.2, 1)], [(.12, .5), (.5, .5)]],
          [[(0, .12), (0, 0), (.6, 0), (.25, 1)]]],
    "8": [[_EIGHT], [_arc(.3, .25, .22, .25, 90, 450), _arc(.3, .75, .28, .25, -90, 270)]],
    "9": [[_arc(.3, .28, .28, .27, 0, -360) + [(.58, .28), (.55, 1)]],
          [_arc(.3, .28, .28, .27, 0, -360) + [(.58, .28), (.56, .7), (.45, .95), (.2, 1)]]],
}


def _resample(stroke, n=40):
    """n điểm cách đều dọc theo nét."""
    p = np.asarray(stroke, float)
    if len(p) < 2:
        return np.repeat(p, n, axis=0)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    t = np.linspace(0, seg[-1], n)
    return np.c_[np.interp(t, seg, p[:, 0]), np.interp(t, seg, p[:, 1])]


def _augment(strokes, rng):
    """Biến dạng ngẫu nhiên như người viết thật: xoay, nghiêng chữ, chữ béo / gầy, tay rung."""
    a, sh, sx = math.radians(rng.uniform(-10, 10)), rng.uniform(-0.3, 0.3), rng.uniform(0.75, 1.25)
    c, s = math.cos(a), math.sin(a)
    out = []
    for st in strokes:
        p = _resample(st)
        wobble = np.apply_along_axis(lambda v: np.convolve(v, np.ones(5) / 5, "same"), 0,
                                     rng.normal(0, 0.03, p.shape))
        p = p + wobble
        x, y = sx * (p[:, 0] + sh * p[:, 1]), p[:, 1]
        out.append(np.c_[c * x - s * y, s * x + c * y])
    return out


def _raster(strokes, thick=2):
    """Vẽ các nét vào ảnh SIZE x SIZE: giữ tỉ lệ khung bao, cạnh dài nhất = BOX, căn giữa."""
    allp = np.concatenate([np.asarray(s, float).reshape(-1, 2) for s in strokes])
    lo, hi = allp.min(0), allp.max(0)
    k = BOX / max((hi - lo).max(), 1e-6)
    off = (SIZE - (hi - lo) * k) / 2 - lo * k
    img = np.zeros((SIZE, SIZE), np.uint8)
    for s in strokes:
        p = np.round(np.asarray(s, float).reshape(-1, 2) * k + off).astype(np.int32)
        cv2.polylines(img, [p], False, 255, thick, cv2.LINE_AA)
    return img


def _features(strokes, thick=2):
    return _HOG.compute(_raster(strokes, thick)).ravel()


def _dataset(seed, per_digit):
    rng = np.random.default_rng(seed)
    X, y = [], []
    for d, variants in TEMPLATES.items():
        for _ in range(per_digit):
            v = variants[rng.integers(len(variants))]
            X.append(_features(_augment(v, rng), int(rng.integers(1, 4))))
            y.append(int(d))
    return np.array(X, np.float32), np.array(y, np.float32)


_model = None


def _knn():
    global _model
    if _model is None:
        X, y = _dataset(seed=0, per_digit=200)
        _model = cv2.ml.KNearest_create()
        _model.train(X, cv2.ml.ROW_SAMPLE, y)
    return _model


def read_digit(strokes):
    """strokes: danh sách nét, mỗi nét [(x, y), ...] (tọa độ màn hình). Trả về "0".."9"."""
    _, res, _, _ = _knn().findNearest(_features(strokes)[None, :], K)
    return str(int(res[0, 0]))


def accuracy(seed=99, per_digit=30):
    X, y = _dataset(seed, per_digit)
    _, res, _, _ = _knn().findNearest(X, K)
    return float((res.ravel() == y).mean())


DOT = 0.12      # nét có khung bao chéo < DOT x chiều cao chữ là chấm


class DigitReader:
    """Gom nét thành chữ số theo vị trí ngang: nét mới có tâm nằm trong khoảng ngang của chữ số cuối (nới thêm 10%
    chiều cao) thì thuộc chữ số đó (vd. nét sổ của số 4), không thì là chữ số mới bên phải."""

    def __init__(self, height):
        self.h = height             # chiều cao ô viết (px)
        self.groups = []            # [{"strokes", "x0", "x1", "ch"}]

    @property
    def text(self):
        return "".join(g["ch"] for g in self.groups)

    def add(self, stroke):
        xs, ys = [p[0] for p in stroke], [p[1] for p in stroke]
        x0, x1 = min(xs), max(xs)
        if math.hypot(x1 - x0, max(ys) - min(ys)) < DOT * self.h:
            # chấm: chỉ là dấu thập phân khi đã có chữ số và chưa có dấu (chụm chập chờn trước đó thì bỏ)
            if self.groups and "." not in self.text:
                self.groups.append({"strokes": [stroke], "x0": x0, "x1": x1, "ch": "."})
            return
        last = self.groups[-1] if self.groups and self.groups[-1]["ch"] != "." else None
        m = 0.1 * self.h
        if last and last["x0"] - m <= (x0 + x1) / 2 <= last["x1"] + m:
            last["strokes"].append(stroke)
            last["x0"], last["x1"] = min(last["x0"], x0), max(last["x1"], x1)
        else:
            last = {"strokes": [stroke], "x0": x0, "x1": x1}
            self.groups.append(last)
        last["ch"] = read_digit(last["strokes"])

    def pop(self):
        if self.groups:
            self.groups.pop()

    def clear(self):
        self.groups = []
