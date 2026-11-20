import math

from airgeo.analyze import summarize


def _row(t, x8, y8, x4, y4, pinch, xf, yf):
    return {"t": t, "x8_raw": x8, "y8_raw": y8, "x4_raw": x4, "y4_raw": y4, "pinch": pinch,
            "x_filt": xf, "y_filt": yf}


def _session():
    rows, t = [], 0.0
    for i in range(60):                       # 2 s giữ yên: thô rung ±2 px, đã lọc đứng yên
        n = 2 * (-1) ** i
        rows.append(_row(t, 300 + n, 200, 300, 260, 0, 300, 200))
        t += 1 / 30
    for k in range(6):                        # ngón khép dần: khoảng cách 4-8 từ 60 -> 10, ngón trỏ trôi xuống 3 px/frame
        rows.append(_row(t, 300, 200 + 3 * k, 300, 260 - 7 * k, 0, 300, 200))
        t += 1 / 30
    rows.append(_row(t, 300, 218, 300, 228, 1, 300, 200))            # nhận ra bấm
    t += 1 / 30
    for k in range(10):
        rows.append(_row(t, 300, 218, 300, 228, 1, 300, 200))
        t += 1 / 30
    for k in range(1, 5):                     # mở ngón
        rows.append(_row(t, 300, 218, 300, 228 + 12 * k, 1 if k < 4 else 0, 300, 200))
        t += 1 / 30
    return rows


def test_fps_jitter_and_press_metrics():
    s = summarize(_session())
    assert abs(s["fps_mean"] - 30) < 0.5
    assert s["still_windows"] >= 1 and abs(s["jitter_raw_px"] - 2) < 0.2 and s["jitter_filt_px"] == 0
    assert s["presses"] == 1
    assert abs(s["press_latency_ms"] - 6 / 30 * 1000) < 40           # từ lúc ngón bắt đầu khép
    assert 12 <= s["press_drift_raw_px"] <= 18 and s["press_drift_cursor_px"] == 0
    assert s["releases"] == 1 and 0 < s["release_latency_ms"] <= 150


def test_empty_and_missing_hand_rows_do_not_crash():
    assert summarize([])["frames"] == 0
    rows = [_row(i / 30, "", "", "", "", 0, "", "") for i in range(10)]
    s = summarize(rows)
    assert s["frames"] == 10 and s["presses"] == 0 and math.isnan(s["jitter_raw_px"])
