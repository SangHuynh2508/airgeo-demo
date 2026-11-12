import numpy as np

from airgeo.ui import text


def test_put_text_draws_vietnamese_and_symbols():
    img = np.zeros((200, 400, 3), np.uint8)
    w, h = text.put_text(img, ["Diện tích", "S = ½ · AB · h = 6 cm²"], (10, 10), 20, (0, 255, 255))
    assert w > 100 and h > 40 and img[10:10 + h, 10:10 + w].any() and not img[150:, :].any()


def test_render_is_cached_and_clipped_at_edges():
    img = np.zeros((50, 50, 3), np.uint8)
    text.put_text(img, ["cache me"], (40, 40), 20)        # tràn ra ngoài ảnh: chỉ vẽ phần trong ảnh
    hits = text._render.cache_info().hits
    text.put_text(img, ["cache me"], (-30, -5), 20)
    assert text._render.cache_info().hits == hits + 1
    assert text.text_size(["cache me"], 20) == text.put_text(img, ["cache me"], (0, 0), 20)
