from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

RGB = Tuple[int, int, int]


@dataclass(frozen=True)
class Look:
    b: float
    c: float
    s: float
    w: float
    hue: float = 0.0
    sepia: bool = False


@dataclass
class TextLayer:
    text: str
    dx: float = 0.1  # 0..1 of canvas width (top-left)
    dy: float = 0.4  # 0..1 of canvas height
    size: float = 28.0
    color: RGB = (255, 255, 255)

    def copy(self) -> "TextLayer":
        return TextLayer(self.text, self.dx, self.dy, self.size, self.color)


@dataclass(frozen=True)
class FilterDef:
    name: str
    group: str
    look: Look


@dataclass(frozen=True)
class EffectDef:
    name: str
    group: str
    kind: str  # vignette grain leak scan glow duo glitch dust bokeh frame
    k: float  # strength 0.2 .. 1.0
    color: RGB


@dataclass(frozen=True)
class TemplateDef:
    name: str
    group: str
    filter: str
    effect: str
    aspect: Optional[float]
    texts: Tuple[TextLayer, ...] = field(default_factory=tuple)


@dataclass
class Track:
    id: str
    title: str
    artist: str
    source: str = "library"  # library | device
    image_url: Optional[str] = None
    audio_url: Optional[str] = None  # stream url (preview)
    download_url: Optional[str] = None  # full file url
    local_path: Optional[str] = None
    external_url: Optional[str] = None
    license_url: Optional[str] = None
    duration_sec: Optional[int] = None

    @property
    def exportable(self) -> bool:
        return self.source in ("library", "device")

    @property
    def non_commercial(self) -> bool:
        return "-nc" in (self.license_url or "")

    @property
    def credit(self) -> str:
        if self.source != "library":
            return ""
        return f'"{self.title}" by {self.artist} - {self.license_url or "see Jamendo"} (via Jamendo)'
