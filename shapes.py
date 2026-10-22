"""Nhận dạng nét vẽ thành hình và chuẩn hóa thành hình chính xác.

!!! BẢN TẠM THỜI CHO DEMO !!!
Dùng heuristic hình học của OpenCV (approxPolyDP + circularity). Giai đoạn sau sẽ thay
bằng thuật toán tìm góc dựa trên tốc độ + độ cong của Sezgin, Stahovich & Davis (PUI 2001).
Vì vậy recognize() đã nhận điểm kèm timestamp (x, y, t) dù hiện tại chưa dùng t.

Kết quả là dict:
  {"kind": "line" | "circle" | "triangle" | "rect" | "free", "pts": [(x, y), ...]}
  circle có thêm "center", "radius".
"""
import math

import cv2
import numpy as np

MIN_LENGTH = 60         # nét ngắn hơn (px) coi như chấm/nhiễu do chụm chập chờn, giữ nguyên
LINE_STRAIGHTNESS = 0.90  # khoảng cách 2 đầu mút / độ dài nét, lớn hơn -> đoạn thẳng
CLOSED_GAP = 0.20       # khoảng hở 2 đầu mút / độ dài nét, nhỏ hơn -> nét kín
APPROX_EPS = 0.04       # epsilon của approxPolyDP, tính theo chu vi
CIRCLE_STRONG = 0.85    # circularity >= ngưỡng này -> hình tròn (trừ khi là tam giác)
CIRCLE_WEAK = 0.75      # circularity >= ngưỡng này và >= 5 đỉnh -> hình tròn


def recognize(points):
    """points: danh sách (x, y, t). Trả về dict hình đã chuẩn hóa."""
    xy = np.array([(p[0], p[1]) for p in points], dtype=np.float32)
    info = {}  # các đại lượng dùng để quyết định, hiển thị lên HUD để chỉnh ngưỡng
    free = {"kind": "free", "pts": [tuple(p) for p in xy], "info": info}
    if len(xy) < 5:
        return free

    length = float(np.sum(np.linalg.norm(np.diff(xy, axis=0), axis=1)))
    if length < MIN_LENGTH:
        return free
    gap = float(np.linalg.norm(xy[-1] - xy[0]))
    info["ho"] = round(gap / length, 2)  # tỉ lệ hở 2 đầu mút

    # 1) Nét hở, gần thẳng -> đoạn thẳng nối 2 đầu mút
    if gap / length > LINE_STRAIGHTNESS:
        return {"kind": "line", "pts": [tuple(xy[0]), tuple(xy[-1])], "info": info}
    if gap / length > CLOSED_GAP:
        return free  # nét hở nhưng cong: giữ nguyên

    # 2) Nét kín: đếm đỉnh bằng approxPolyDP + độ tròn 4*pi*A/P^2
    cnt = xy.reshape(-1, 1, 2)
    perim = cv2.arcLength(cnt, True)
    area = abs(cv2.contourArea(cnt))
    circularity = 4 * math.pi * area / (perim * perim) if perim > 0 else 0
    approx = cv2.approxPolyDP(cnt, APPROX_EPS * perim, True).reshape(-1, 2)
    v = len(approx)
    info.update(tron=round(circularity, 2), dinh=v)

    if v == 3:
        return {"kind": "triangle", "pts": [tuple(p) for p in approx], "info": info}
    if circularity >= CIRCLE_STRONG or (v >= 5 and circularity >= CIRCLE_WEAK):
        return {**_fit_circle(cnt, xy), "info": info}
    if v == 4:
        box = cv2.boxPoints(cv2.minAreaRect(cnt))
        return {"kind": "rect", "pts": [tuple(p) for p in box], "info": info}
    return free


def _fit_circle(cnt, xy):
    # Tâm = trọng tâm vùng kín (moments) thay vì trung bình các điểm, vì điểm dày ở chỗ
    # vẽ chậm sẽ kéo lệch trung bình. Bán kính = khoảng cách trung bình từ tâm tới nét.
    m = cv2.moments(cnt)
    if m["m00"] != 0:
        center = np.array([m["m10"] / m["m00"], m["m01"] / m["m00"]], dtype=np.float32)
    else:
        center = xy.mean(axis=0)
    radius = float(np.mean(np.linalg.norm(xy - center, axis=1)))
    return {"kind": "circle", "pts": [], "center": (float(center[0]), float(center[1])), "radius": radius}


if __name__ == "__main__":
    rng = np.random.default_rng(0)

    def stroke(xy, noise=1.5):
        xy = np.asarray(xy, dtype=float) + rng.normal(0, noise, (len(xy), 2))
        return [(x, y, i / 30) for i, (x, y) in enumerate(xy)]

    def polygon(corners, per_side=20):
        corners = np.asarray(corners, dtype=float)
        out = []
        for a, b in zip(corners, np.roll(corners, -1, axis=0)):
            out += [a + (b - a) * k / per_side for k in range(per_side)]
        return out + [corners[0]]

    ang = np.linspace(0, 2 * np.pi, 80)
    circle = stroke(np.c_[300 + 100 * np.cos(ang), 300 + 100 * np.sin(ang)])
    r = recognize(circle)
    assert r["kind"] == "circle" and abs(r["radius"] - 100) < 5 and math.dist(r["center"], (300, 300)) < 5, r
    assert recognize(stroke(np.c_[np.linspace(0, 300, 40), np.linspace(0, 100, 40)]))["kind"] == "line"
    assert recognize(stroke(polygon([(100, 100), (400, 100), (400, 300), (100, 300)])))["kind"] == "rect"
    assert recognize(stroke(polygon([(100, 300), (400, 300), (250, 50)])))["kind"] == "triangle"
    assert recognize(stroke(np.c_[np.linspace(0, 300, 40), 100 * np.sin(np.linspace(0, 3, 40))]))["kind"] == "free"
    print("shapes OK")
