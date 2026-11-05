"""Interface chung cho bộ lọc điểm 2D. Bộ lọc tự cài sau này chỉ cần có đúng các thành phần này."""
from typing import Protocol


class PointFilter(Protocol):
    name: str  # ghi vào cột filter_name của CSV

    def filter(self, x: float, y: float, t: float) -> tuple[float, float]:
        """t: giây, lấy từ time.perf_counter()."""

    def reset(self) -> None:
        """Gọi khi mất tay / đổi bộ lọc, để không bị kéo từ vị trí cũ."""

    def describe(self) -> str:
        """Tham số hiện tại, hiển thị lên HUD."""
