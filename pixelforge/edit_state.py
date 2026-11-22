"""ONE edit description -> colour matrix (photo) AND FFmpeg filters (video)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import catalog
from .models import Look, TextLayer

PRESETS: Dict[str, Look] = {
    "Original": Look(0, 1, 1, 0),
    "Vivid": Look(0, 1.15, 1.4, 0.05),
    "Warm": Look(0, 1.0, 1.1, 0.5),
    "Cool": Look(0, 1.0, 1.05, -0.5),
    "B&W": Look(0, 1.1, 0, 0),
    "Sepia": Look(0, 1.0, 1, 0, sepia=True),
    "Fade": Look(0.08, 0.85, 0.8, 0),
    "Dramatic": Look(-0.05, 1.35, 0.85, 0),
    "Vintage": Look(0.05, 0.9, 0.7, 0.3),
}


def preset_names() -> List[str]:
    return list(PRESETS.keys())


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _then(a: List[float], b: List[float]) -> List[float]:
    r = [0.0] * 20
    for i in range(4):
        for j in range(5):
            s = 0.0
            for k in range(4):
                s += b[i * 5 + k] * a[k * 5 + j]
            if j == 4:
                s += b[i * 5 + 4]
            r[i * 5 + j] = s
    return r


@dataclass
class EditState:
    brightness: float = 0.0  # -1..1
    contrast: float = 1.0  # 0.5..1.5
    saturation: float = 1.0  # 0..2
    warmth: float = 0.0  # -1..1
    preset: str = "Original"
    effect: str = "None"  # catalog effect name, 'None' = off
    quarter_turns: int = 0  # 0..3 (clockwise)
    flip_h: bool = False
    aspect: Optional[float] = None  # None = original
    texts: List[TextLayer] = field(default_factory=list)

    # ------------------------------------------------------------ helpers
    def copy(self) -> "EditState":
        return EditState(
            self.brightness, self.contrast, self.saturation, self.warmth,
            self.preset, self.effect, self.quarter_turns, self.flip_h,
            self.aspect, [t.copy() for t in self.texts],
        )

    def reset_adjust(self) -> None:
        self.brightness, self.contrast, self.saturation, self.warmth = 0.0, 1.0, 1.0, 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Full, hashable-friendly description (cache keys, undo comparison)."""
        return {
            "brightness": self.brightness, "contrast": self.contrast,
            "saturation": self.saturation, "warmth": self.warmth,
            "preset": self.preset, "effect": self.effect,
            "quarter_turns": self.quarter_turns, "flip_h": self.flip_h,
            "aspect": self.aspect,
            "texts": [[t.text, t.dx, t.dy, t.size, list(t.color)] for t in self.texts],
        }

    def sig(self) -> str:
        import json
        return json.dumps(self.to_dict(), sort_keys=True)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "EditState":
        return EditState(
            d["brightness"], d["contrast"], d["saturation"], d["warmth"],
            d["preset"], d["effect"], d["quarter_turns"], d["flip_h"], d["aspect"],
            [TextLayer(t[0], t[1], t[2], t[3], tuple(t[4])) for t in d["texts"]],
        )

    def to_gemini_json(self) -> Dict[str, Any]:
        return {
            "brightness": self.brightness, "contrast": self.contrast,
            "saturation": self.saturation, "warmth": self.warmth,
            "preset": self.preset, "effect": self.effect,
            "rotateQuarterTurns": self.quarter_turns, "flipH": self.flip_h,
        }

    # ------------------------------------------------------------ effective look
    @property
    def _p(self) -> Look:
        return PRESETS.get(self.preset) or catalog.look(self.preset) or PRESETS["Original"]

    @property
    def _eb(self) -> float:
        return _clamp(self.brightness + self._p.b, -1.0, 1.0)

    @property
    def _ec(self) -> float:
        return _clamp(self.contrast * self._p.c, 0.3, 2.0)

    @property
    def _es(self) -> float:
        return _clamp(self.saturation * self._p.s, 0.0, 3.0)

    @property
    def _ew(self) -> float:
        return _clamp(self.warmth + self._p.w, -1.0, 1.0)

    # ------------------------------------------------------------ colour matrix (4x5, offsets 0..255)
    @property
    def matrix(self) -> List[float]:
        m = [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0]
        m = [float(x) for x in m]
        s = self._es
        m = _then(m, [
            .213 + .787 * s, .715 - .715 * s, .072 - .072 * s, 0, 0,
            .213 - .213 * s, .715 + .285 * s, .072 - .072 * s, 0, 0,
            .213 - .213 * s, .715 - .715 * s, .072 + .928 * s, 0, 0,
            0, 0, 0, 1, 0,
        ])
        c = self._ec
        o = 128 * (1 - c)
        m = _then(m, [c, 0, 0, 0, o, 0, c, 0, 0, o, 0, 0, c, 0, o, 0, 0, 0, 1, 0])
        b = self._eb * 127.5
        m = _then(m, [1, 0, 0, 0, b, 0, 1, 0, 0, b, 0, 0, 1, 0, b, 0, 0, 0, 1, 0])
        p = self._p
        if p.hue != 0:
            a = p.hue * 3.14159265 / 180
            co, si = math.cos(a), math.sin(a)
            m = _then(m, [
                .213 + co * .787 - si * .213, .715 - co * .715 - si * .715, .072 - co * .072 + si * .928, 0, 0,
                .213 - co * .213 + si * .143, .715 + co * .285 + si * .140, .072 - co * .072 - si * .283, 0, 0,
                .213 - co * .213 - si * .787, .715 - co * .715 + si * .715, .072 + co * .928 + si * .072, 0, 0,
                0, 0, 0, 1, 0,
            ])
        w = self._ew
        if w != 0:
            m = _then(m, [1, 0, 0, 0, w * 35, 0, 1, 0, 0, w * 8, 0, 0, 1, 0, -w * 35, 0, 0, 0, 1, 0])
        if p.sepia:
            m = _then(m, [
                .393, .769, .189, 0, 0,
                .349, .686, .168, 0, 0,
                .272, .534, .131, 0, 0,
                0, 0, 0, 1, 0,
            ])
        return m

    # ------------------------------------------------------------ FFmpeg filter chain
    def ffmpeg_filters(self) -> str:
        f: List[str] = []
        b, c, s = self._eb * 0.5, self._ec, self._es
        if self._eb != 0 or self._ec != 1 or self._es != 1:
            f.append(f"eq=brightness={b:.3f}:contrast={c:.3f}:saturation={s:.3f}")
        if self._ew != 0:
            f.append(f"colorbalance=rm={self._ew * 0.25:.3f}:bm={-self._ew * 0.25:.3f}")
        p = self._p
        if p.hue != 0:
            f.append(f"hue=h={p.hue:.1f}")
        fx = catalog.effect_ffmpeg(self.effect)
        if fx:
            f.append(fx)
        if p.sepia:
            f.append("colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131")
        q = self.quarter_turns % 4
        if q == 1:
            f.append("transpose=1")
        elif q == 2:
            f.append("hflip,vflip")
        elif q == 3:
            f.append("transpose=2")
        if self.flip_h:
            f.append("hflip")
        return ",".join(f)

    # ------------------------------------------------------------ Gemini "set" object
    def apply_set(self, s: Dict[str, Any]) -> None:
        def d(k: str) -> Optional[float]:
            v = s.get(k)
            return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

        b, c, sa, w = d("brightness"), d("contrast"), d("saturation"), d("warmth")
        if b is not None:
            self.brightness = _clamp(b, -1.0, 1.0)
        if c is not None:
            self.contrast = _clamp(c, 0.5, 1.5)
        if sa is not None:
            self.saturation = _clamp(sa, 0.0, 2.0)
        if w is not None:
            self.warmth = _clamp(w, -1.0, 1.0)
        p = s.get("preset")
        if isinstance(p, str) and (p in PRESETS or catalog.look(p) is not None):
            self.preset = p
        ef = s.get("effect")
        if isinstance(ef, str) and (ef == "None" or catalog.effect(ef) is not None):
            self.effect = ef
        q = s.get("rotateQuarterTurns")
        if isinstance(q, (int, float)) and not isinstance(q, bool):
            self.quarter_turns = int(q) % 4
        fl = s.get("flipH")
        if isinstance(fl, bool):
            self.flip_h = fl
