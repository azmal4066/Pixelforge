"""Pillow / numpy versions of the 10 catalog effect kinds (same look as the Flutter painters)."""
from __future__ import annotations

import random
import zlib

import numpy as np
from PIL import Image, ImageDraw

from . import catalog

CYAN_ACCENT = (0x18, 0xFF, 0xFF)


def _grid(w: int, h: int):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx, yy


def _over(base: np.ndarray, col, alpha: np.ndarray) -> np.ndarray:
    a = alpha[..., None]
    return base * (1 - a) + np.array(col, dtype=np.float32) * a


def _composite(img: Image.Image, overlay: Image.Image) -> Image.Image:
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def apply_effect(img: Image.Image, name: str) -> Image.Image:
    e = catalog.effect(name)
    if e is None:
        return img
    img = img.convert("RGB")
    w, h = img.size
    rnd = random.Random(zlib.crc32(e.name.encode()))
    k, col, kind = e.k, e.color, e.kind
    sc = max(1.0, min(w, h) / 360.0)  # sizes in the Flutter painters are logical px on a ~360px canvas

    if kind in ("grain", "dust", "bokeh", "glitch", "frame"):
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        if kind == "grain":
            n = int(min(30000, 700 * (w * h) / (360 * 480)))
            fill = (*col, int(255 * .35 * k))
            for _ in range(n):
                x, y, r = rnd.random() * w, rnd.random() * h, (.5 + rnd.random() * k) * sc
                d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
        elif kind == "dust":
            fill = (*col, int(255 * .55))
            for _ in range(40 + round(k * 80)):
                x, y, r = rnd.random() * w, rnd.random() * h, (.6 + rnd.random() * 1.8) * sc
                d.ellipse([x - r, y - r, x + r, y + r], fill=fill)
        elif kind == "bokeh":
            for _ in range(8 + round(k * 14)):
                rad = min(w, h) * (.03 + rnd.random() * .08)
                x, y = rnd.random() * w, rnd.random() * h
                a = .1 + .22 * k * rnd.random()
                d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(*col, int(255 * a)))
        elif kind == "glitch":
            for i in range(4 + round(k * 8)):
                y = rnd.random() * h
                bh = (2 + rnd.random() * 10 * k) * sc
                x = (rnd.random() - .5) * 24 * k * sc
                c = col if i % 2 == 0 else CYAN_ACCENT
                d.rectangle([x, y, x + w, y + bh], fill=(*c, int(255 * (.22 * k + .08))))
        else:  # frame
            sw = min(w, h) * (.02 + .05 * k)
            d.rectangle([sw / 2, sw / 2, w - sw / 2, h - sw / 2], outline=(*col, int(255 * .9)),
                        width=max(1, int(sw)))
        return _composite(img, ov)

    base = np.asarray(img, dtype=np.float32)
    xx, yy = _grid(w, h)
    colf = np.array(col, dtype=np.float32)

    if kind == "vignette":
        dist = np.hypot(xx - w / 2, yy - h / 2) / min(w, h)
        t = np.clip((dist - .45) / (1 - .45), 0, 1)
        out = _over(base, col, t * k * .85)
    elif kind == "leak":
        bx = (-1 + rnd.random() + 1) / 2 * w
        by = 0.0
        ex, ey = float(w), float(h)
        vx, vy = ex - bx, ey - by
        t = np.clip(((xx - bx) * vx + (yy - by) * vy) / (vx * vx + vy * vy), 0, 1)
        a = np.where(t <= .55, k * .7 * (1 - t / .55), k * .3 * ((t - .55) / .45))
        src = colf * a[..., None]
        out = 255 - (255 - base) * (255 - src) / 255  # screen blend
    elif kind == "scan":
        period = max(2, round(4 * sc))
        thick = max(1, round(1.4 * sc))
        rows = (np.arange(h) % period) < thick
        a = np.zeros((h, w), dtype=np.float32)
        a[rows, :] = .25 * k
        out = _over(base, col, a)
    elif kind == "glow":
        cx, cy = w * .65, h * .3
        rad = .9 * min(w, h)
        a = np.clip(1 - np.hypot(xx - cx, yy - cy) / rad, 0, 1) * k * .6
        out = base + colf * a[..., None]  # plus blend
    elif kind == "duo":
        gray = (base * np.array([.299, .587, .114], dtype=np.float32)).sum(axis=2, keepdims=True)
        lum = max(.2, float((colf * np.array([.299, .587, .114])).sum() / 255))
        tinted = np.clip(gray * (colf / 255.0) / lum, 0, 255)
        a = k * .45
        out = base * (1 - a) + tinted * a
    else:
        return img
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
