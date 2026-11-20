"""Phân tích file CSV phiên ghi (phím R) – số liệu cho luận văn.

    python -m airgeo.analyze data/session_*.csv

- FPS trung bình và FPS ở 5% frame chậm nhất.
- Độ rung khi giữ tay yên: cửa sổ 1 s mà đầu ngón trỏ (thô) dao động < STILL_SPAN px; RMS khoảng cách tới điểm
  trung bình của cửa sổ, cho điểm thô và điểm đã lọc (con trỏ). Trung vị qua các cửa sổ.
- Bấm (pinch 0 -> 1): trễ phát hiện = từ lúc khoảng cách ngón cái - trỏ bắt đầu giảm (đã giảm 10% quãng khép) tới
  lúc pinch = 1; độ trôi = đầu ngón trỏ (thô) / con trỏ đã đi bao xa trong quãng đó ("hiệu ứng Heisenberg").
  Chỉ tính với lần khép ngón rõ (giảm >= MIN_CLOSE px; bấm áp 2 ngón không đo được bằng khoảng cách 4-8).
- Nhả (pinch 1 -> 0): trễ từ lúc khoảng cách bắt đầu tăng (10% quãng mở) tới lúc pinch = 0.
"""
import csv
import math
import statistics
import sys

STILL_SPAN = 10.0     # px: cửa sổ 1 s có đầu ngón trỏ dao động nhỏ hơn chừng này = giữ yên
MIN_CLOSE = 15.0      # px: khoảng cách 4-8 phải giảm ít nhất chừng này mới tính trễ / trôi của lần bấm
LOOKBACK = 0.5        # s: tìm lúc ngón bắt đầu khép / mở trong khoảng này trước sự kiện


def _f(v):
    return None if v in ("", None) else float(v)


def _median(xs):
    return statistics.median(xs) if xs else math.nan


def _rms(pts):
    mx, my = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    return math.sqrt(sum((x - mx) ** 2 + (y - my) ** 2 for x, y in pts) / len(pts))


def summarize(rows):
    t = [float(r["t"]) for r in rows]
    p8 = [(_f(r["x8_raw"]), _f(r["y8_raw"])) if _f(r["x8_raw"]) is not None else None for r in rows]
    p4 = [(_f(r["x4_raw"]), _f(r["y4_raw"])) if _f(r["x4_raw"]) is not None else None for r in rows]
    cur = [(_f(r["x_filt"]), _f(r["y_filt"])) if _f(r["x_filt"]) is not None else None for r in rows]
    pinch = [int(r["pinch"]) for r in rows]
    d48 = [math.dist(a, b) if a and b else None for a, b in zip(p4, p8)]
    n = len(rows)
    out = {"frames": n}

    dts = sorted(b - a for a, b in zip(t, t[1:]) if b > a)
    out["fps_mean"] = (n - 1) / (t[-1] - t[0]) if n > 1 and t[-1] > t[0] else math.nan
    out["fps_p5"] = 1 / dts[int(0.95 * (len(dts) - 1))] if dts else math.nan

    raw_j, filt_j, i = [], [], 0
    while i < n:                                  # cửa sổ 1 s nối tiếp nhau
        j = i
        while j < n and t[j] - t[i] < 1.0:
            j += 1
        raw, filt = p8[i:j], cur[i:j]
        if j - i >= 5 and all(raw) and all(filt) and \
                max(p[0] for p in raw) - min(p[0] for p in raw) < STILL_SPAN and \
                max(p[1] for p in raw) - min(p[1] for p in raw) < STILL_SPAN:
            raw_j.append(_rms(raw))
            filt_j.append(_rms(filt))
        i = j
    out["still_windows"] = len(raw_j)
    out["jitter_raw_px"], out["jitter_filt_px"] = _median(raw_j), _median(filt_j)

    lat, drift_raw, drift_cur, rel = [], [], [], []
    presses = releases = 0
    for i in range(1, n):
        if pinch[i] == pinch[i - 1] or d48[i] is None:
            presses += pinch[i] > pinch[i - 1]
            releases += pinch[i] < pinch[i - 1]
            continue
        win = [k for k in range(i) if t[i] - t[k] <= LOOKBACK and d48[k] is not None]
        if pinch[i]:
            presses += 1
            d_open = max((d48[k] for k in win), default=d48[i])
            fall = d_open - d48[i]
            on = [k for k in win if d48[k] >= d_open - 0.1 * fall]
            if fall >= MIN_CLOSE and on:
                k = on[-1]
                lat.append((t[i] - t[k]) * 1000)
                if p8[k] and p8[i]:
                    drift_raw.append(math.dist(p8[k], p8[i]))
                if cur[k] and cur[i]:
                    drift_cur.append(math.dist(cur[k], cur[i]))
        else:
            releases += 1
            d_min = min((d48[k] for k in win), default=d48[i])
            rise = d48[i] - d_min
            low = [k for k in win if d48[k] <= d_min + 0.1 * rise]
            if rise >= MIN_CLOSE and low:
                rel.append((t[i] - t[low[-1]]) * 1000)
    out.update(presses=presses, press_latency_ms=_median(lat), press_drift_raw_px=_median(drift_raw),
               press_drift_cursor_px=_median(drift_cur), releases=releases, release_latency_ms=_median(rel))
    return out


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    for path in sys.argv[1:]:
        print(path)
        for k, v in summarize(load(path)).items():
            print(f"  {k:24s} {v:.2f}" if isinstance(v, float) else f"  {k:24s} {v}")
