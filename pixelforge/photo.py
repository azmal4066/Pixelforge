"""Photo render pipeline: colour matrix -> flip -> rotate -> aspect crop -> effect -> text."""
from __future__ import annotations

import io
import os
from functools import lru_cache
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .edit_state import EditState
from .effects import apply_effect

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansTamil-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "DejaVuSans-Bold.ttf",
]


@lru_cache(maxsize=64)
def get_font(size_px: int):
    size_px = max(6, int(size_px))
    for path in _FONT_CANDIDATES:
        try:
            if os.path.isabs(path) and not os.path.exists(path):
                continue
            return ImageFont.truetype(path, size_px)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size_px)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def load_image(data: bytes, max_side: Optional[int] = None) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    if max_side and max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    return img


def apply_matrix(img: Image.Image, m) -> Image.Image:
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    out = np.empty_like(a)
    for i in range(3):
        out[..., i] = m[i * 5] * r + m[i * 5 + 1] * g + m[i * 5 + 2] * b + m[i * 5 + 4]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def _cover_crop(img: Image.Image, aspect: float) -> Image.Image:
    w, h = img.size
    cur = w / h
    if abs(cur - aspect) < 1e-3:
        return img
    if cur > aspect:  # too wide
        nw = int(round(h * aspect))
        x0 = (w - nw) // 2
        return img.crop((x0, 0, x0 + nw, h))
    nh = int(round(w / aspect))
    y0 = (h - nh) // 2
    return img.crop((0, y0, w, y0 + nh))


def draw_texts(img: Image.Image, state: EditState) -> Image.Image:
    if not state.texts:
        return img
    w, h = img.size
    out = img.convert("RGBA")
    for t in state.texts:
        if not t.text:
            continue
        font = get_font(t.size * (w / 360))
        pos = (t.dx * w, t.dy * h)
        shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).text(pos, t.text, font=font, fill=(0, 0, 0, 140))
        shadow = shadow.filter(ImageFilter.GaussianBlur(max(1.0, 2 * w / 360)))
        out = Image.alpha_composite(out, shadow)
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text(pos, t.text, font=font, fill=(*t.color, 255))
        out = Image.alpha_composite(out, layer)
    return out.convert("RGB")


def render(img: Image.Image, state: EditState, texts: bool = True, crop: bool = True) -> Image.Image:
    out = apply_matrix(img, state.matrix)
    if state.flip_h:
        out = ImageOps.mirror(out)
    q = state.quarter_turns % 4
    if q == 1:
        out = out.transpose(Image.ROTATE_270)  # 90 deg clockwise
    elif q == 2:
        out = out.transpose(Image.ROTATE_180)
    elif q == 3:
        out = out.transpose(Image.ROTATE_90)
    if crop and state.aspect:
        out = _cover_crop(out, state.aspect)
    if state.effect != "None":
        out = apply_effect(out, state.effect)
    if texts:
        out = draw_texts(out, state)
    return out


def to_bytes(img: Image.Image, fmt: str = "PNG", quality: int = 92) -> bytes:
    buf = io.BytesIO()
    if fmt.upper() in ("JPEG", "JPG"):
        img.convert("RGB").save(buf, "JPEG", quality=quality)
    else:
        img.save(buf, "PNG")
    return buf.getvalue()
