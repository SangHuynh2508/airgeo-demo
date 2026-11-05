"""Lệnh `airgeo` / `python -m airgeo`: đọc tham số dòng lệnh rồi chạy app."""
import argparse

from airgeo.config import Config


def parse_args(argv=None) -> Config:
    d = Config()
    ap = argparse.ArgumentParser(prog="airgeo", description="Bang ve hinh hoc khong cham bang cu chi tay")
    ap.add_argument("--camera", type=int, default=d.camera, help="chi so camera (thu 1, 2 neu thay logo OBS)")
    ap.add_argument("--width", type=int, default=d.width)
    ap.add_argument("--height", type=int, default=d.height)
    ap.add_argument("--model", type=int, default=d.model_complexity, choices=[0, 1],
                    help="model_complexity cua MediaPipe")
    ap.add_argument("--gesture", default=d.gesture, choices=["two_finger", "pinch"],
                    help="cu chi bam: ap ngon giua sat ngon tro, hoac chum ngon cai + tro")
    a = ap.parse_args(argv)
    return Config(camera=a.camera, width=a.width, height=a.height, model_complexity=a.model,
                  gesture=a.gesture)


def main(argv=None):
    from airgeo.app import run  # import trễ: `airgeo --help` không phải nạp MediaPipe
    try:
        run(parse_args(argv))
    except KeyboardInterrupt:
        pass  # Ctrl+C trong terminal: khối finally trong run() đã đóng camera / CSV
