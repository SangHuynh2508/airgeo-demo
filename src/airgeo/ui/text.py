"""Chữ Unicode (có dấu, ½ π ² ·) bằng Pillow – cv2.putText chỉ vẽ được ASCII.
Ảnh chữ (mặt nạ xám) lưu đệm theo (nội dung, cỡ chữ) nên frame không đổi chữ không phải vẽ lại."""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@lru_cache(maxsize=16)
def _font(size, bold=False):
    try:
        # font Windows, có tiếng Việt và ½ π ²
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


@lru_cache(maxsize=128)
def _render(lines, size, bold=False):
    font, lh = _font(size, bold), round(size * 1.3)
    w = max(1, *(round(font.getlength(s)) + 2 for s in lines))
    mask = Image.new("L", (w, lh * len(lines) + 4), 0)
    draw = ImageDraw.Draw(mask)
    for i, s in enumerate(lines):
        draw.text((1, i * lh), s, fill=255, font=font)
    return np.asarray(mask, np.float32) / 255


def text_size(lines, size, bold=False):
    h, w = _render(tuple(lines), size, bold).shape
    return w, h


def put_text(img, lines, org, size=20, color=(255, 255, 255), bold=False):
    """Vẽ nhiều dòng, góc trên trái tại org, màu BGR; phần ra ngoài ảnh bị cắt. Trả về (w, h) của khối chữ."""
    a = _render(tuple(lines), size, bold)
    h, w = a.shape
    x, y = org
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, img.shape[1]), min(y + h, img.shape[0])
    if x0 < x1 and y0 < y1:
        a = a[y0 - y:y1 - y, x0 - x:x1 - x, None]
        roi = img[y0:y1, x0:x1]
        roi[:] = (roi * (1 - a) + np.array(color, np.float32) * a).astype(np.uint8)
    return w, h
