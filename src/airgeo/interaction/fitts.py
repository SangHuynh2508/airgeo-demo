"""Bài đo bấm mục tiêu kiểu ISO 9241-9 (multi-directional tapping) – phím K trong app.

n mục tiêu tròn đường kính W trên vòng tròn đường kính D, bấm lần lượt theo thứ tự đối diện (0, 6, 1, 7, ...).
Mỗi khối (D, W): lần bấm đầu chỉ để bắt đầu, n lần sau được tính. Trượt (ngoài mục tiêu) vẫn sang mục tiêu kế.

Mỗi khối (Soukoreff & MacKenzie 2004):
  dx  = độ lệch điểm bấm so với tâm mục tiêu, chiếu lên hướng di chuyển (từ mục tiêu trước tới mục tiêu này)
  We  = 4.133 · SD(dx)        (SD = 0 thì dùng W)
  De  = trung bình quãng di chuyển thật (giữa 2 điểm bấm liên tiếp, chiếu lên hướng di chuyển)
  IDe = log2(De / We + 1);  MT = thời gian trung bình giữa 2 lần bấm;  throughput TP = IDe / MT (bit/s)
Cột stabilize ghi ổn định điểm bấm (phím S) đang bật hay tắt để so sánh.
"""
import csv
import math
import os
import statistics
from datetime import datetime

N = 11
BLOCKS = [(300, 50), (300, 90), (500, 50), (500, 90)]      # (D, W) px
HEADER = 90                                                # px dải tiêu đề phía trên


class FittsTask:
    def __init__(self, width, height, blocks=BLOCKS, n=N):
        self.center = (width / 2, (height + HEADER) / 2)       # chừa dải tiêu đề phía trên
        # khung hình thấp: thu nhỏ cả D lẫn W cho vòng mục tiêu lọt khung (số ghi ra là cỡ thật đã dùng)
        k = min(1.0, (min(width, height - HEADER) / 2 - 20) / max(D / 2 + W / 2 for D, W in blocks))
        self.blocks, self.n = [(D * k, W * k) for D, W in blocks], n
        self.order = [(j * ((n + 1) // 2)) % n for j in range(n + 1)]
        self.block = self.step = 0          # khối hiện tại / lần bấm thứ mấy trong khối (0 = lần bắt đầu)
        self.records, self.done = [], False
        self.gesture = "two_finger"         # bấm bằng áp 2 ngón như nút; phím B đổi sang chụm
        self._prev = None                   # (t, điểm bấm) lần trước

    @property
    def current(self):
        return self.order[self.step]

    def targets(self):
        D = self.blocks[self.block][0]
        cx, cy = self.center
        return [(cx + D / 2 * math.sin(2 * math.pi * i / self.n), cy - D / 2 * math.cos(2 * math.pi * i / self.n))
                for i in range(self.n)]

    def on_event(self, ev, stabilize):
        if self.done or ev.kind != "down":
            return
        D, W = self.blocks[self.block]
        tg = self.targets()
        b = tg[self.current]
        if self.step > 0:
            a = tg[self.order[self.step - 1]]
            d = math.dist(a, b)
            u = ((b[0] - a[0]) / d, (b[1] - a[1]) / d)
            (t0, p0), p = self._prev, ev.pos
            self.records.append(dict(
                block=self.block, D=D, W=W, trial=self.step, t=round(ev.t, 4), mt=ev.t - t0,
                x=round(p[0], 1), y=round(p[1], 1), tx=round(b[0], 1), ty=round(b[1], 1),
                hit=int(math.dist(p, b) <= W / 2),
                dx=(p[0] - b[0]) * u[0] + (p[1] - b[1]) * u[1],
                ae=(p[0] - p0[0]) * u[0] + (p[1] - p0[1]) * u[1],
                stabilize=int(stabilize), gesture=self.gesture))
        self._prev = (ev.t, ev.pos)
        self.step += 1
        if self.step > self.n:              # hết khối
            self.block, self.step, self._prev = self.block + 1, 0, None
            self.done = self.block >= len(self.blocks)
            if self.done:
                self.block -= 1

    def summary(self):
        out = []
        for k, (D, W) in enumerate(self.blocks):
            r = [x for x in self.records if x["block"] == k]
            if not r:
                continue
            sd = statistics.stdev([x["dx"] for x in r]) if len(r) > 1 else 0.0
            we = 4.133 * sd if sd > 0 else W
            de = statistics.mean(x["ae"] for x in r)
            mt = statistics.mean(x["mt"] for x in r)
            ide = math.log2(max(de, 0.0) / we + 1)
            out.append(dict(D=D, W=W, n=len(r), mt_ms=mt * 1000, we=we, ide=ide, tp=ide / mt if mt > 0 else 0.0,
                            error_rate=1 - sum(x["hit"] for x in r) / len(r),
                            stabilize=r[-1]["stabilize"], gesture=r[-1]["gesture"]))
        return out

    def save(self, folder="data"):
        """Ghi data/fitts_<thời gian>.csv (từng lần bấm) và ..._summary.csv (từng khối). Trả về 2 đường dẫn."""
        os.makedirs(folder, exist_ok=True)
        base = os.path.join(folder, f"fitts_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        paths = []
        for path, rows in ((base + ".csv", self.records), (base + "_summary.csv", self.summary())):
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["empty"])
                w.writeheader()
                w.writerows(rows)
            paths.append(path)
        return paths
