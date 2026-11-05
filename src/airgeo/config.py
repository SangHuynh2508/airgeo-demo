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
    # Tương tác (giai đoạn 2) – chỉnh sau khi thử webcam
    toolbar_height: int = 70           # thanh nút trên không ở mép trên
    key_size: int = 80                 # cạnh phím số trên không (px); tự thu nhỏ nếu khung hình thấp
    hit_radius: float = 15.0           # con trỏ cách nét <= bao nhiêu px thì trúng hình
    label_radius: float = 25.0         # bán kính vùng bấm nhãn cạnh
    drag_threshold: float = 10.0       # đi quá bao nhiêu px thì tính là kéo
    min_side_px: float = 10.0          # cạnh / bán kính nhỏ nhất khi dựng lại hình
    history_limit: int = 50            # số bước Undo
    confirm_window: float = 2.0        # giây để bấm "Xoa het" lần 2
