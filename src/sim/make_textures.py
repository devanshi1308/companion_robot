"""
Generate the floor and rug textures for the apartment (procedural, nothing downloaded).

Output: models/textures/{hardwood,laminate,carpet,rug}.png

Run:  python src/sim/make_textures.py
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "models", "textures")


def _planks(size, planks, base, tone_var, grain_amp, seed, seam=0.55):
    """Tileable wood planks running along x (grain uses whole numbers of periods, so it tiles)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size, 3), np.float32)
    ph = size // planks
    xs = np.arange(size)[None, :]
    for p in range(planks):
        tone = rng.uniform(-tone_var, tone_var)
        rows = np.arange(ph)[:, None]
        grain = np.zeros((ph, size), np.float32)
        for _ in range(4):
            k = int(rng.integers(2, 14))
            grain += np.sin(2 * np.pi * k * xs / size + rows * rng.uniform(0.1, 0.6) + rng.uniform(0, 6.28))
        grain /= 4
        block = np.array(base, np.float32)[None, None, :] + tone + grain[..., None] * grain_amp
        block += rng.normal(0, 2.0, (ph, 1, 3))                      # streaks along the plank
        block[:2] *= seam                                              # seam between planks
        jx = int(rng.integers(0, size))
        block[:, jx:jx + 2] *= seam + 0.1                              # end joint
        img[p * ph:(p + 1) * ph] = block
    return np.clip(img, 0, 255).astype(np.uint8)


def hardwood():
    return _planks(512, 8, (166, 112, 70), 14, 9, seed=1)


def laminate():
    return _planks(512, 5, (196, 178, 150), 9, 5, seed=2, seam=0.7)


def carpet():
    rng = np.random.default_rng(3)
    size = 256
    base = np.array([158, 146, 132], np.float32)
    noise = rng.normal(0, 7, (size, size, 1))
    blotch = np.zeros((size, size, 1), np.float32)
    xs = np.arange(size)[None, :, None]
    ys = np.arange(size)[:, None, None]
    for k in range(3):
        blotch += np.sin(2 * np.pi * (k + 1) * xs / size + k) * np.sin(2 * np.pi * (k + 2) * ys / size) * 4
    return np.clip(base + noise + blotch, 0, 255).astype(np.uint8)


def rug():
    """Burgundy rug with a cream border and a diamond pattern (map once over the whole rug)."""
    w, h = 520, 380
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = x / w, y / h
    img = np.zeros((h, w, 3), np.float32)
    img[:] = (120, 36, 44)
    edge = np.minimum.reduce([u, 1 - u, v, 1 - v])
    img[(edge > 0.03) & (edge < 0.05)] = (214, 196, 160)               # inner line
    img[edge <= 0.03] = (44, 52, 84)                                    # outer band
    inner = (edge > 0.07)
    d = np.abs(u - 0.5) * (w / h) + np.abs(v - 0.5)                     # diamond distance
    for r, col in ((0.50, (160, 70, 60)), (0.36, (214, 196, 160)), (0.22, (44, 52, 84)), (0.10, (170, 120, 70))):
        img[inner & (d < r)] = col
    tile = ((x // 20 + y // 20) % 2)[..., None]
    img *= (0.96 + 0.04 * tile)
    img += np.random.default_rng(4).normal(0, 4, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("hardwood", hardwood), ("laminate", laminate), ("carpet", carpet), ("rug", rug)):
        Image.fromarray(fn()).save(os.path.join(OUT, f"{name}.png"))
    print("textures ->", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
