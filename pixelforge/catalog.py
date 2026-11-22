"""500 filters + 500 effects + 500 templates, generated from compact
parameter families (20 x 25, 10 x 10 x 5, 20 x 25) - same as the Flutter app."""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional

from .models import EffectDef, FilterDef, Look, TemplateDef, TextLayer

# name, brightness, contrast, saturation, warmth, hue, sepia
_BASES = [
    ("Noir", -.05, 1.35, 0.0, 0.0, 0.0, False),
    ("Golden Hour", .04, 1.08, 1.25, .7, 0.0, False),
    ("Neon Night", -.08, 1.3, 1.7, -.3, 18.0, False),
    ("Teal Orange", 0.0, 1.2, 1.2, .35, -14.0, False),
    ("Kodak Gold", .05, 1.05, 1.15, .55, 0.0, False),
    ("Cyberpunk", -.06, 1.35, 1.6, -.5, 38.0, False),
    ("Matte Fade", .1, .8, .75, .05, 0.0, False),
    ("Retro 70s", .06, .95, .8, .6, 0.0, True),
    ("Ice Blue", .03, 1.1, 1.0, -.8, 0.0, False),
    ("Emerald", 0.0, 1.15, 1.3, -.1, 70.0, False),
    ("Rose Pink", .05, 1.0, 1.2, .2, -32.0, False),
    ("Moody", -.12, 1.4, .8, -.15, 0.0, False),
    ("Pop Vivid", .02, 1.18, 1.9, .1, 0.0, False),
    ("Pastel Dream", .12, .85, .7, .15, 0.0, False),
    ("Sunset Burn", -.02, 1.25, 1.4, .9, -10.0, False),
    ("Midnight", -.18, 1.3, .9, -.6, 0.0, False),
    ("Desert", .04, 1.1, .9, .75, 0.0, True),
    ("Forest", -.03, 1.2, 1.1, -.2, 45.0, False),
    ("Chrome", .02, 1.4, .6, -.1, 0.0, False),
    ("Dream Violet", .0, 1.1, 1.3, -.2, -60.0, False),
]

_FX_KINDS = [
    ("Vignette", "vignette"), ("Film Grain", "grain"), ("Light Leak", "leak"),
    ("Scanlines", "scan"), ("Glow", "glow"), ("Duotone", "duo"),
    ("Glitch", "glitch"), ("Dust", "dust"), ("Bokeh", "bokeh"), ("Frame", "frame"),
]

_FX_COLORS = [
    ("Crimson", (0xFF, 0x17, 0x44)), ("Amber", (0xFF, 0x91, 0x00)),
    ("Gold", (0xFF, 0xD7, 0x40)), ("Lime", (0xC6, 0xFF, 0x00)),
    ("Emerald", (0x00, 0xE6, 0x76)), ("Cyan", (0x00, 0xE5, 0xFF)),
    ("Azure", (0x29, 0x79, 0xFF)), ("Violet", (0x7C, 0x4D, 0xFF)),
    ("Magenta", (0xF5, 0x00, 0x57)), ("Snow", (0xFF, 0xFF, 0xFF)),
]

# title, headline, subtitle
_TPL_BASES = [
    ("Birthday", "Happy Birthday", "Inniki unga naal!"),
    ("Wedding", "Just Married", "Forever starts today"),
    ("Pongal", "Pongal Vazhthukkal", "Pongalo Pongal"),
    ("Deepavali", "Happy Deepavali", "Light up the night"),
    ("Travel", "Wanderlust", "Oor suthalam"),
    ("Reel Hype", "ON FIRE", "Mass loading..."),
    ("Movie Poster", "THE LEGEND", "Coming soon"),
    ("Love", "My Everything", "Un ninaivu"),
    ("Gym", "NO PAIN NO GAIN", "Beast mode"),
    ("Foodie", "Yummy Time", "Saapadu ready"),
    ("Fashion", "STYLE FILES", "Own the look"),
    ("Friends", "Squad Goals", "Nanbenda"),
    ("Graduation", "Class of 2026", "Dreams unlocked"),
    ("Baby", "Welcome Baby", "Chella kutty"),
    ("Music", "ON REPEAT", "Vibe with me"),
    ("Gaming", "GAME ON", "Level up"),
    ("Sunset", "Golden Moments", "Evening feels"),
    ("Retro", "Throwback", "Old is gold"),
    ("Minimal", "Less is more", "Simple. Clean."),
    ("Hero", "RISE", "Be your own hero"),
]

_ROMAN = ["I", "II", "III", "IV", "V"]
WHITE = (255, 255, 255)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@lru_cache(maxsize=1)
def filters() -> List[FilterDef]:
    out: List[FilterDef] = []
    for name, b, c, s, w, hue, sepia in _BASES:
        for i in range(5):
            f = .4 + .3 * i  # intensity
            for t in range(5):
                hue_shift = (t - 2) * 12.0
                out.append(FilterDef(
                    f"{name} {_ROMAN[i]}{chr(65 + t)}",
                    name,
                    Look(
                        b * f,
                        1 + (c - 1) * f,
                        _clamp(1 + (s - 1) * f, 0.0, 2.0),
                        _clamp(w * f + (t - 2) * .12, -1.0, 1.0),
                        hue=hue * f + hue_shift,
                        sepia=sepia and i >= 2,
                    ),
                ))
    return out


@lru_cache(maxsize=1)
def effects() -> List[EffectDef]:
    out: List[EffectDef] = []
    for kname, kind in _FX_KINDS:
        for cname, col in _FX_COLORS:
            for i in range(5):
                out.append(EffectDef(f"{kname} {cname} {_ROMAN[i]}", kname, kind, .2 + .2 * i, col))
    return out


@lru_cache(maxsize=1)
def templates() -> List[TemplateDef]:
    fl, ef = filters(), effects()
    palette = [WHITE, (0xFF, 0xEB, 0x3B), (0x18, 0xFF, 0xFF), (0xFF, 0x40, 0x81), (0x69, 0xF0, 0xAE)]
    aspects = [None, 1, 4 / 5, 9 / 16, 16 / 9]
    out: List[TemplateDef] = []
    n = 0
    for group, head, sub_text in _TPL_BASES:
        for v in range(25):
            layout, style = v % 5, v // 5
            col = palette[style]
            big = 30.0 + style * 4
            if layout == 0:
                title = TextLayer(head, .08, .08, big, col)
                sub = TextLayer(sub_text, .08, .2, 16, WHITE)
            elif layout == 1:
                title = TextLayer(head, .12, .42, big + 4, col)
                sub = TextLayer(sub_text, .25, .56, 16, WHITE)
            elif layout == 2:
                title = TextLayer(head, .08, .72, big, col)
                sub = TextLayer(sub_text, .08, .85, 16, WHITE)
            elif layout == 3:
                title = TextLayer(head, .06, .06, big - 4, col)
                sub = TextLayer(sub_text, .06, .88, 18, col)
            else:
                title = TextLayer(head.upper(), .04, .45, big + 8, col)
                sub = TextLayer(sub_text, .04, .62, 14, WHITE)
            out.append(TemplateDef(
                f"{group} {v + 1}", group,
                fl[(n * 37 + 11) % len(fl)].name,
                ef[(n * 53 + 7) % len(ef)].name,
                aspects[(v + style) % 5],
                (title, sub),
            ))
            n += 1
    return out


@lru_cache(maxsize=1)
def _filter_map() -> Dict[str, FilterDef]:
    return {f.name: f for f in filters()}


@lru_cache(maxsize=1)
def _effect_map() -> Dict[str, "EffectDef"]:
    return {e.name: e for e in effects()}


def look(name: str) -> Optional[Look]:
    f = _filter_map().get(name)
    return f.look if f else None


def effect(name: str) -> Optional[EffectDef]:
    return _effect_map().get(name)


def effect_ffmpeg(name: str) -> Optional[str]:
    """FFmpeg equivalent for the effects that have one (others are preview/photo only)."""
    e = effect(name)
    if e is None:
        return None
    if e.kind == "vignette":
        return f"vignette=angle={0.25 + e.k * 0.6:.2f}"
    if e.kind == "grain":
        return f"noise=alls={round(e.k * 30)}:allf=t"
    if e.kind == "duo":
        r = (e.color[0] / 255 - .5) * e.k * .5
        b = (e.color[2] / 255 - .5) * e.k * .5
        return f"colorbalance=rs={r:.2f}:bs={b:.2f}"
    return None
