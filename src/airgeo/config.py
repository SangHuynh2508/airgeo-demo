"""Mọi giá trị mặc định của app ở một chỗ (trước đây nằm rải rác trong app.py)."""
from dataclasses import dataclass


@dataclass
class Config:
    # Camera + MediaPipe
    camera: int = 0
    width: int = 1280
    height: int = 720
    model_complexity: int = 1          # 0 nhanh hơn, 1 chính xác hơn
    # Chụm (xem gesture/pinch.py); ngưỡng còn chỉnh được bằng phím , . khi chạy
    pinch_on: float = 0.20
    pinch_off: float = 0.35
    pinch_grace: float = 0.2           # giây giữ nét khi mất tay / tỉ lệ nhảy vọt
    pinch_mode: str = "2d"             # "2d" hoặc "3d" (phím P)
    # Bộ lọc
    ma_window: int = 5
    one_euro_mincutoff: float = 1.0
    one_euro_beta: float = 0.007
    one_euro_dcutoff: float = 1.0
    # Khác
    data_dir: str = "data"             # nơi lưu CSV, tính từ thư mục đang đứng khi chạy lệnh
    trail_len: int = 60                # số điểm vết ở chế độ so sánh (phím M)
