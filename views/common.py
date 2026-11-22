"""Shared Streamlit widgets + the PixelForge neon theme (same palette as the Flutter v4 app):
starfield backdrop, glowing titles, reactor loader, gallery grid, adjust sliders, song picker."""
from __future__ import annotations

import io
import json
import math
import os
import tempfile
from typing import Callable, List, Optional, Sequence, Tuple

import streamlit as st
from PIL import Image

from pixelforge import audio, catalog, library, photo
from pixelforge.audio import BeatInfo
from pixelforge.config import MOODS
from pixelforge.edit_state import EditState, preset_names
from pixelforge.models import Track

PER_PAGE = 12
FILTERS, EFFECTS, TEMPLATES = "Filters", "Effects", "Templates"

# section accents (same as the Flutter hub cards)
RED, CYAN, GREEN, LILAC, VIOLET = "#FF2D55", "#00E5FF", "#00FF9C", "#B388FF", "#7C4DFF"
_GALLERY_META = {FILTERS: ("🎞", RED), EFFECTS: ("✨", GREEN), TEMPLATES: ("🧩", CYAN)}


# ------------------------------------------------------------------ theme
_CSS = """
:root{--acc:__ACC__;--acc-rgb:__RGB__;--bg:#07060F;--panel:#12102A;--panel2:#0E0B1F;--cyan:#00E5FF;--violet:#7C4DFF;}
.stApp{background:radial-gradient(1300px 760px at 50% -12%,#1B1140 0%,#07060F 62%) fixed;color:#F4F2FF;}
.stApp::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.6;
 background-image:
  radial-gradient(1.2px 1.2px at 22px 38px,#fff 50%,transparent 52%),
  radial-gradient(1px 1px at 96px 150px,#cfe9ff 50%,transparent 52%),
  radial-gradient(1.6px 1.6px at 170px 70px,#fff 50%,transparent 52%),
  radial-gradient(1px 1px at 210px 205px,#e9dcff 50%,transparent 52%),
  radial-gradient(1.3px 1.3px at 60px 215px,#fff 50%,transparent 52%);
 background-size:240px 240px;animation:pf-drift 60s linear infinite;}
@keyframes pf-drift{from{background-position:0 0}to{background-position:0 240px}}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stAppViewContainer"] .main,.block-container{position:relative;z-index:1;}
.block-container{padding-top:2.4rem;padding-bottom:4rem;max-width:1240px;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0E0B1F,#08071A);border-right:1px solid rgba(var(--acc-rgb),.25);}
hr{border-color:rgba(255,255,255,.08)!important;}

/* titles */
.pf-hero{margin:0 0 1.1rem 0;}
.pf-title{font-weight:900;letter-spacing:.32em;text-transform:uppercase;font-size:1.55rem;color:#fff;
 text-shadow:0 0 16px var(--acc),0 0 42px rgba(124,77,255,.45);}
.pf-sub{color:rgba(255,255,255,.55);letter-spacing:.14em;font-size:.76rem;margin-top:.35rem;text-transform:uppercase;}
.pf-stephead{display:flex;align-items:center;gap:.7rem;font-weight:800;letter-spacing:.2em;font-size:.82rem;
 text-transform:uppercase;color:#fff;margin:1.1rem 0 .5rem 0;}
.pf-num{display:inline-flex;align-items:center;justify-content:center;width:1.7rem;height:1.7rem;border-radius:50%;
 background:rgba(var(--acc-rgb),.18);border:1.5px solid var(--acc);color:var(--acc);font-size:.8rem;
 box-shadow:0 0 14px rgba(var(--acc-rgb),.55);}
.pf-chip{display:inline-block;padding:.22rem .7rem;border-radius:999px;font-size:.74rem;letter-spacing:.06em;
 background:rgba(var(--acc-rgb),.14);border:1px solid rgba(var(--acc-rgb),.55);color:#fff;margin:0 .35rem .35rem 0;}
.pf-warn{border-left:3px solid #FFB300;background:rgba(255,179,0,.09);padding:.5rem .8rem;border-radius:8px;
 font-size:.82rem;color:#FFD580;margin:.3rem 0;}
.pf-credit{font-size:.78rem;color:rgba(255,255,255,.6);}
.pf-empty{text-align:center;padding:2.2rem 1rem;color:rgba(255,255,255,.6);letter-spacing:.08em;}
.pf-pagebar{text-align:center;padding-top:.45rem;font-size:.8rem;letter-spacing:.1em;color:rgba(255,255,255,.65);}

/* cards (st.container(border=True)) */
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:18px!important;
 background:linear-gradient(135deg,rgba(var(--acc-rgb),.10),rgba(18,16,42,.92) 62%);
 border:1px solid rgba(var(--acc-rgb),.32)!important;box-shadow:0 0 26px -12px rgba(var(--acc-rgb),.8);}
[data-testid="stVerticalBlockBorderWrapper"]:has(.pf-sel){border:2px solid var(--acc)!important;
 box-shadow:0 0 18px rgba(var(--acc-rgb),.7);}

/* buttons */
.stButton>button,.stDownloadButton>button{border-radius:14px;border:1px solid rgba(255,255,255,.14);
 background:#171433;color:#fff;font-weight:600;transition:all .18s ease;}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--acc);
 box-shadow:0 0 16px rgba(var(--acc-rgb),.55);transform:translateY(-1px);color:#fff;}
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"],
.stDownloadButton>button[kind="primary"],.stDownloadButton>button[data-testid="stBaseButton-primary"]{
 background:linear-gradient(135deg,var(--acc),#7C4DFF);color:#07060F;border:none;font-weight:800;
 box-shadow:0 0 20px rgba(var(--acc-rgb),.55);}
.stButton>button:disabled{opacity:.35;}

/* tabs */
.stTabs [data-baseweb="tab-list"]{gap:4px;background:var(--panel2);border-radius:14px;padding:4px;
 border:1px solid rgba(255,255,255,.07);flex-wrap:wrap;}
.stTabs [data-baseweb="tab"]{border-radius:10px;padding:.35rem .8rem;height:auto;color:rgba(255,255,255,.7);}
.stTabs [aria-selected="true"]{background:rgba(var(--acc-rgb),.22);color:#fff;
 box-shadow:inset 0 0 0 1px var(--acc),0 0 14px rgba(var(--acc-rgb),.4);}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none;}

/* inputs */
.stTextInput input,.stTextArea textarea,[data-baseweb="select"]>div,.stNumberInput input{
 background:var(--panel2)!important;border-radius:12px!important;border-color:rgba(255,255,255,.12)!important;}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--acc)!important;
 box-shadow:0 0 0 1px var(--acc),0 0 14px rgba(var(--acc-rgb),.4)!important;}
[data-baseweb="slider"] div[role="slider"]{background:var(--acc)!important;box-shadow:0 0 12px var(--acc);}
[data-testid="stFileUploaderDropzone"]{background:var(--panel2);border:1.5px dashed rgba(var(--acc-rgb),.65);border-radius:16px;}
[data-testid="stProgress"] div[role="progressbar"]>div{background:linear-gradient(90deg,var(--acc),var(--cyan))!important;}
[data-testid="stAlert"]{border-radius:14px;}
[data-testid="stImage"] img{border-radius:14px;}
[data-testid="stVideo"] video,[data-testid="stVideo"]{border-radius:16px;}
[data-testid="stMetric"]{background:var(--panel2);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:.5rem .8rem;}

/* reactor loader */
.pf-loader{display:flex;flex-direction:column;align-items:center;gap:1rem;padding:2rem 0;}
.pf-ring{width:84px;height:84px;border-radius:50%;border:4px solid transparent;border-top-color:var(--cyan);
 border-right-color:var(--cyan);animation:pf-spin 1.2s linear infinite;position:relative;filter:drop-shadow(0 0 8px var(--cyan));}
.pf-ring::before{content:"";position:absolute;inset:10px;border-radius:50%;border:3px solid transparent;
 border-bottom-color:var(--acc);border-left-color:var(--acc);animation:pf-spin 1.8s linear infinite reverse;}
.pf-ring::after{content:"";position:absolute;inset:32px;border-radius:50%;background:var(--cyan);
 box-shadow:0 0 18px var(--cyan);animation:pf-pulse 1.6s ease-in-out infinite;}
.pf-lbl{letter-spacing:.45em;color:var(--cyan);font-weight:800;font-size:.8rem;}
@keyframes pf-spin{to{transform:rotate(360deg)}}
@keyframes pf-pulse{50%{transform:scale(.55);opacity:.6}}
"""


def _rgb(hex_: str) -> str:
    h = hex_.lstrip("#")
    return ",".join(str(int(h[i:i + 2], 16)) for i in (0, 2, 4))


def inject_theme(accent: str = VIOLET) -> None:
    """Idempotent: every page calls this, so no change to app.py is needed."""
    st.markdown(f"<style>{_CSS.replace('__ACC__', accent).replace('__RGB__', _rgb(accent))}</style>",
                unsafe_allow_html=True)


def hero(title: str, sub: str = "", icon: str = "", accent: str = VIOLET) -> None:
    inject_theme(accent)
    st.markdown(f'<div class="pf-hero"><div class="pf-title">{icon} {title}</div>'
                f'<div class="pf-sub">{sub}</div></div>', unsafe_allow_html=True)


def step(n: int, title: str) -> None:
    st.markdown(f'<div class="pf-stephead"><span class="pf-num">{n}</span><span>{title}</span></div>',
                unsafe_allow_html=True)


def chips(*labels: str) -> None:
    st.markdown("".join(f'<span class="pf-chip">{l}</span>' for l in labels if l), unsafe_allow_html=True)


def warn(text: str) -> None:
    st.markdown(f'<div class="pf-warn">⚠ {text}</div>', unsafe_allow_html=True)


def loader_html(label: str = "FORGING...") -> str:
    return f'<div class="pf-loader"><div class="pf-ring"></div><div class="pf-lbl">{label}</div></div>'


def card():
    """Neon card; falls back to a plain container on very old Streamlit."""
    try:
        return st.container(border=True)
    except TypeError:
        return st.container()


def mmss(sec: float) -> str:
    return f"{int(sec // 60)}:{sec % 60:04.1f}"


# ------------------------------------------------------------------ images
def small_bytes(img: Image.Image, side: int = 200) -> bytes:
    t = img.copy()
    t.thumbnail((side, side), Image.LANCZOS)
    return photo.to_bytes(t, "JPEG", 85)


def temp_dir() -> str:
    return tempfile.mkdtemp(prefix="pf_")


# ------------------------------------------------------------------ gallery
def _look_only(state: EditState) -> EditState:
    """Only the parts of the state that change how an *effect* thumbnail looks."""
    s = state.copy()
    s.effect, s.texts, s.aspect, s.quarter_turns, s.flip_h = "None", [], None, 0, False
    return s


@st.cache_data(show_spinner=False, max_entries=2000)
def _thumb(kind: str, name: str, base: bytes, cur_json: str) -> bytes:
    img = Image.open(io.BytesIO(base)).convert("RGB")
    if kind == FILTERS:
        s = EditState(preset=name)
    elif kind == EFFECTS:
        s = EditState.from_dict(json.loads(cur_json))
        s.effect = name
    else:
        t = next(x for x in catalog.templates() if x.name == name)
        s = EditState(preset=t.filter, effect=t.effect, texts=[x.copy() for x in t.texts])
    return photo.to_bytes(photo.render(img, s, crop=False), "JPEG", 82)


def _items(kind: str) -> List[Tuple[str, str]]:
    src = {FILTERS: catalog.filters, EFFECTS: catalog.effects, TEMPLATES: catalog.templates}[kind]()
    return [(x.name, x.group) for x in src]


def _is_selected(kind: str, state: EditState, name: str) -> bool:
    if kind == FILTERS:
        return state.preset == name
    if kind == EFFECTS:
        return state.effect == name
    return False


def _group_chips(options: Sequence[str], key: str) -> str:
    if hasattr(st, "pills"):  # Streamlit >= 1.40: wrapping chips, like the Flutter ChoiceChips
        v = st.pills("Group", list(options), selection_mode="single", default="All", key=key,
                     label_visibility="collapsed")
        return v or "All"
    return st.selectbox("Group", list(options), key=key, label_visibility="collapsed")


def gallery(kind: str, state: EditState, base_small: bytes, key: str,
            on_pick: Callable[[str], None], on_clear: Callable[[], None]) -> None:
    """500 items: group chips + search + paged thumbnail grid (neon cards, selected = glow)."""
    icon, accent = _GALLERY_META[kind]
    items = _items(kind)
    groups = ["All"] + list(dict.fromkeys(g for _, g in items))
    k = f"{key}_{kind}"

    st.markdown(f'<div class="pf-stephead" style="color:{accent};margin-top:.2rem">{icon} {kind.upper()}'
                f'<span style="color:rgba(255,255,255,.45);font-weight:500;letter-spacing:.1em">'
                f'&nbsp;{len(items)} looks</span></div>', unsafe_allow_html=True)
    group = _group_chips(groups, f"{k}_g")
    c2, c3 = st.columns([5, 1])
    q = c2.text_input("Search", key=f"{k}_q", placeholder=f"🔍 Search {len(items)} {kind.lower()}",
                      label_visibility="collapsed").strip().lower()
    if c3.button("Clear", key=f"{k}_clear", use_container_width=True):
        on_clear()

    shown = [n for n, g in items if (group == "All" or g == group) and q in n.lower()]
    pages = max(1, math.ceil(len(shown) / PER_PAGE))
    pk = f"{k}_page"
    sig = (group, q)
    if st.session_state.get(f"{k}_sig") != sig:  # new filter -> back to page 1
        st.session_state[f"{k}_sig"] = sig
        st.session_state[pk] = 1
    page = min(max(1, int(st.session_state.get(pk, 1))), pages)
    nb = st.columns([1, 3, 1])
    if nb[0].button("‹ Prev", key=f"{k}_prev", disabled=page <= 1, use_container_width=True):
        page -= 1
    if nb[2].button("Next ›", key=f"{k}_next", disabled=page >= pages, use_container_width=True):
        page += 1
    st.session_state[pk] = page
    nb[1].markdown(f'<div class="pf-pagebar">PAGE {page} / {pages} &nbsp;·&nbsp; {len(shown)} of {len(items)}</div>',
                   unsafe_allow_html=True)

    if not shown:
        st.markdown('<div class="pf-empty">No match. Try another word.</div>', unsafe_allow_html=True)
        return
    cur_json = json.dumps(_look_only(state).to_dict(), sort_keys=True) if kind == EFFECTS else ""
    chunk = shown[(page - 1) * PER_PAGE: page * PER_PAGE]
    for r in range(0, len(chunk), 3):
        cols = st.columns(3)
        for col, name in zip(cols, chunk[r:r + 3]):
            with col, card():
                sel = _is_selected(kind, state, name)
                if sel:
                    st.markdown('<span class="pf-sel"></span>', unsafe_allow_html=True)
                st.image(_thumb(kind, name, base_small, cur_json), use_container_width=True)
                if st.button(("✓ " if sel else "") + name, key=f"{k}_pick_{name}", use_container_width=True,
                             type="primary" if sel else "secondary"):
                    on_pick(name)


# ------------------------------------------------------------------ adjust
def adjust_controls(state: EditState, ver: int, on_reset: Callable[[], None], key: str) -> None:
    """Quick looks + brightness/contrast/saturation/warmth. Widget values are written
    straight into `state`; keys include `ver` so programmatic changes reset the widgets."""
    presets = preset_names()
    idx = presets.index(state.preset) + 1 if state.preset in presets else 0
    choice = st.selectbox("Quick look", ["— (gallery filter)"] + presets, index=idx, key=f"{key}_q{ver}")
    if choice in presets:
        state.preset = choice
    state.brightness = st.slider("☀ Brightness", -1.0, 1.0, float(state.brightness), 0.01, key=f"{key}_b{ver}")
    state.contrast = st.slider("◐ Contrast", 0.5, 1.5, float(state.contrast), 0.01, key=f"{key}_c{ver}")
    state.saturation = st.slider("🎨 Saturation", 0.0, 2.0, float(state.saturation), 0.01, key=f"{key}_s{ver}")
    state.warmth = st.slider("🔥 Warmth", -1.0, 1.0, float(state.warmth), 0.01, key=f"{key}_w{ver}")
    if st.button("↺ Reset adjustments", key=f"{key}_reset"):
        on_reset()


def rotate_flip(key: str, on_rotate_left: Callable[[], None], on_rotate_right: Callable[[], None],
                on_flip: Callable[[], None]) -> None:
    c1, c2, c3 = st.columns(3)
    if c1.button("⟲ Rotate left", key=f"{key}_rl", use_container_width=True):
        on_rotate_left()
    if c2.button("⟳ Rotate right", key=f"{key}_rr", use_container_width=True):
        on_rotate_right()
    if c3.button("⇋ Flip", key=f"{key}_fl", use_container_width=True):
        on_flip()


# ------------------------------------------------------------------ song picker
@st.cache_data(show_spinner=False, ttl=900)
def _search(query: str, mood: str):
    return library.search(query, None if mood == "Any" else mood)


@st.cache_data(show_spinner=False, max_entries=64)
def _beat(path: str) -> Optional[BeatInfo]:
    return audio.analyze(path)


def song_picker(prefix: str) -> Tuple[Optional[Track], Optional[BeatInfo]]:
    """Free library (Jamendo) or the user's own audio file. Returns (track, beat)."""
    key = f"{prefix}_track"
    track: Optional[Track] = st.session_state.get(key)
    if track is not None:
        with card():
            c1, c2, c3 = st.columns([1, 5, 2])
            if track.image_url:
                c1.image(track.image_url, use_container_width=True)
            else:
                c1.markdown("<div style='font-size:2.4rem;text-align:center'>🎵</div>", unsafe_allow_html=True)
            c2.markdown(f"**{track.title}**  \n{track.artist}")
            if track.local_path:
                c2.audio(track.local_path)
            if c3.button("Change / remove", key=f"{prefix}_rm", use_container_width=True):
                del st.session_state[key]
                st.rerun()
            with st.spinner("Detecting beats…"):
                beat = _beat(track.local_path) if track.local_path else None
            if beat:
                chips(f"🎚 ~{beat.bpm:.0f} BPM (estimated)")
            if track.non_commercial:
                warn("Non-commercial license (CC-NC): do not use in monetised content.")
        return track, beat

    tab_lib, tab_dev = st.tabs(["🎼 Free library", "📁 My songs"])
    with tab_lib:
        st.caption("Royalty-free tracks (Jamendo). Full export supported. Credit is shown with the result.")
        if not library.configured():
            st.info("Add `JAMENDO_CLIENT_ID` to `.streamlit/secrets.toml` to browse the free library.")
        else:
            c1, c2 = st.columns([3, 2])
            q = c1.text_input("Search free music", key=f"{prefix}_q", placeholder="🔍 Search songs").strip()
            mood = c2.selectbox("Mood", ["Any"] + list(MOODS), key=f"{prefix}_mood")
            try:
                results = _search(q, mood)
            except Exception as e:  # network / API error
                results = []
                st.error(str(e))
            for t in results[:12]:
                with card():
                    r1, r2, r3 = st.columns([1, 5, 2])
                    if t.image_url:
                        r1.image(t.image_url, use_container_width=True)
                    r2.markdown(f"**{t.title}** — {t.artist}" + ("  ⚠ CC-NC" if t.non_commercial else ""))
                    if t.audio_url:
                        r2.audio(t.audio_url)
                    if r3.button("Use", key=f"{prefix}_use_{t.id}", type="primary", use_container_width=True):
                        with st.spinner("Downloading song…"):
                            try:
                                library.download(t)
                                st.session_state[key] = t
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
    with tab_dev:
        st.caption("Use a song file from your device (your own recordings or music you have the rights to).")
        up = st.file_uploader("Pick audio file", type=["mp3", "wav", "m4a", "aac", "ogg", "flac"],
                              key=f"{prefix}_audio")
        if up is not None:
            path = os.path.join(temp_dir(), up.name)
            with open(path, "wb") as f:
                f.write(up.getbuffer())
            st.session_state[key] = Track(id=path, title=os.path.splitext(up.name)[0],
                                          artist="My device", source="device", local_path=path)
            st.rerun()
    return None, None
