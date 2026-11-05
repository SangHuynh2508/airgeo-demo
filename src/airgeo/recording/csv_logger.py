"""Ghi dữ liệu thô từng frame ra CSV trong thư mục data/.

Luôn lưu tọa độ THÔ (chưa lọc) để sau này chạy lại các bộ lọc trên cùng một bộ dữ liệu.
"""
import csv
import os
from datetime import datetime

COLUMNS = ["t", "x8_raw", "y8_raw", "x4_raw", "y4_raw", "pinch",
           "filter_name", "x_filt", "y_filt", "mode", "session_id"]


class CsvLogger:
    def __init__(self, folder="data"):
        self.folder = folder
        self.file = None
        self.session_id = None

    @property
    def active(self):
        return self.file is not None

    def start(self):
        os.makedirs(self.folder, exist_ok=True)
        base = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id, n = base, 1
        # Bật/tắt ghi 2 lần trong cùng 1 giây không được ghi đè file của phiên trước
        while os.path.exists(self._path()):
            n += 1
            self.session_id = f"{base}_{n}"
        path = self._path()
        self.file = open(path, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(COLUMNS)
        return path

    def _path(self):
        return os.path.join(self.folder, f"session_{self.session_id}.csv")

    def log(self, **row):
        """Thiếu cột nào (ví dụ không thấy tay) thì để trống."""
        if self.file:
            row["session_id"] = self.session_id
            self.writer.writerow(["" if row.get(c) is None else row[c] for c in COLUMNS])

    def stop(self):
        if self.file:
            self.file.close()
            self.file = None
