"""Video Editor: trim, speed 0.25x-4x, filters/effects/templates/adjust, rotate/flip,
original sound mix, add song, Gemini AI box, one-pass FFmpeg export."""
from __future__ import annotations

import io
import os
import shutil
from typing import List, Optional

import streamlit as st
from PIL import Image, ImageEnhance

from pixelforge import catalog, export, gemini, photo
from pixelforge.edit_state import EditState
from . import common as C

EXAMPLES = ["Slow motion-la maathu", "Cinematic warm look kudu", "Video-va 2x speed aakku",
            "Original sound mute pannu"]
ACCENT = C.CYAN
STRIP_FRAMES = 6


def _init() -> dict:
    if "video" not in st.session_state:
        st.session_state.video = {
            "path": None, "name": None, "dur": 0.0, "fid": None, "state": EditState(),
            "trim": (0.0, 0.0), "speed": 1.0, "keep": True, "reply": "", "ver": 0,
            "opts": export.ExportOptions(), "result": None, "frame_t": 0.0,
        }
    return st.session_state.video


@st.cache_data(show_spinner=False, max_entries=256)
def _frame(path: str, t: float) -> Optional[bytes]:
    return export.extract_frame(path, t)


@st.cache_data(show_spinner=False, max_entries=512)
def _strip_thumb(path: str, t: float) -> Optional[bytes]:
    raw = export.extract_frame(path, t)
    if not raw:
        return None
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return C.small_bytes(img, 240)


def _bump(vs: dict) -> None:
    vs["ver"] += 1
    vs["result"] = None
    st.rerun()


def _load(vs: dict, up) -> None:
    path = os.path.join(C.temp_dir(), up.name)
    with open(path, "wb") as f:
        f.write(up.getbuffer())
    dur, _ = export.probe(path)
    if not dur:
        st.error("Could not read this video. Try an MP4 / MOV file.")
        return
    vs.update(path=path, name=up.name, dur=dur, fid=(up.name, up.size), state=EditState(),
              trim=(0.0, float(dur)), speed=1.0, keep=True, reply="", result=None,
              opts=export.ExportOptions(), frame_t=0.0)
    vs["ver"] += 1
    st.session_state.pop("video_track", None)
    st.rerun()


# ------------------------------------------------------------------ tabs
def _tab_trim(vs: dict) -> None:
    dur, v = vs["dur"], vs["ver"]
    lo, hi = vs["trim"]
    a, b = st.slider("✂ Trim (seconds)", 0.0, float(dur), (float(lo), float(hi)), 0.1, key=f"v_trim{v}")
    if b - a < 0.5:  # keep at least 0.5 s
        b = min(float(dur), a + 0.5)
        a = max(0.0, b - 0.5)
    vs["trim"] = (a, b)
    vs["speed"] = st.slider("⏩ Speed", 0.25, 4.0, float(vs["speed"]), 0.25, format="%.2fx", key=f"v_speed{v}")
    out_len = (b - a) / vs["speed"]
    c1, c2, c3 = st.columns(3)
    c1.metric("In → Out", f"{C.mmss(a)} → {C.mmss(b)}")
    c2.metric("Output", f"{out_len:.1f}s")
    c3.metric("Speed", f"{vs['speed']:.2f}x")
    vs["frame_t"] = st.slider("🎞 Preview frame at (seconds)", 0.0, float(dur),
                              float(min(max(vs["frame_t"], 0.0), dur)), 0.1, key=f"v_ft{v}")


def _tab_adjust(vs: dict) -> None:
    s = vs["state"]

    def reset() -> None:
        s.reset_adjust()
        _bump(vs)

    C.adjust_controls(s, vs["ver"], reset, "va")

    def rot(d: int):
        def f():
            s.quarter_turns = (s.quarter_turns + d) % 4
            _bump(vs)
        return f

    def flip() -> None:
        s.flip_h = not s.flip_h
        _bump(vs)

    C.rotate_flip("va", rot(3), rot(1), flip)


def _gallery_tab(vs: dict, kind: str, small: bytes) -> None:
    s = vs["state"]

    def pick(name: str) -> None:
        if kind == C.FILTERS:
            s.preset = name
        elif kind == C.EFFECTS:
            s.effect = name
        else:  # video: look + effect (text layers are photo-only)
            t = next(t for t in catalog.templates() if t.name == name)
            s.preset, s.effect = t.filter, t.effect
        _bump(vs)

    def clear() -> None:
        s.preset = "Original"
        if kind != C.FILTERS:
            s.effect = "None"
        _bump(vs)

    C.gallery(kind, s, small, "video", pick, clear)
    if kind != C.FILTERS:
        st.caption("Preview shows every effect. Export applies Vignette, Film Grain and Duotone; "
                   "the other effects are photo / preview only.")


def _tab_music(vs: dict):
    o: export.ExportOptions = vs["opts"]
    track, _beat = C.song_picker("video")
    vs["keep"] = st.toggle("🔊 Keep original sound", vs["keep"], key=f"v_keep{vs['ver']}")
    if track is not None:
        o.music_volume = st.slider("Song volume", 0.0, 1.5, float(o.music_volume), 0.05, key=f"v_mv{vs['ver']}")
        o.original_volume = st.slider("Original sound", 0.0, 1.0, float(o.original_volume), 0.05,
                                      key=f"v_ov{vs['ver']}")
        o.music_start = float(st.slider("Start song at (sec)", 0, 120, int(o.music_start), 1,
                                        key=f"v_ms{vs['ver']}"))
    return track


def _tab_ai(vs: dict) -> None:
    if not gemini.configured():
        st.info("Add `GEMINI_API_KEY` to `.streamlit/secrets.toml` to use the AI box.")
    st.caption("Try: " + " · ".join(EXAMPLES))
    prompt = st.text_input("Tell Gemini what to do", key=f"v_ai{vs['ver']}",
                           placeholder="✨ Gemini-kitta sollunga… (Tamil / English)")
    if st.button("✨ Ask AI", key="v_ai_go", type="primary", use_container_width=True,
                 disabled=not prompt.strip() or not gemini.configured()):
        try:
            with st.spinner("Thinking…"):
                res = gemini.commands(prompt.strip(), vs["state"], video=True)
            sset = res.get("set")
            if isinstance(sset, dict):
                vs["state"].apply_set(sset)
                sp = sset.get("speed")
                if isinstance(sp, (int, float)) and not isinstance(sp, bool):
                    vs["speed"] = max(0.25, min(4.0, float(sp)))
                if isinstance(sset.get("mute"), bool):
                    vs["keep"] = not sset["mute"]
            vs["reply"] = str(res.get("reply") or "")
            _bump(vs)
        except Exception as e:
            st.error(str(e))
    if vs["reply"]:
        st.success(vs["reply"])


# ------------------------------------------------------------------ preview + export
def _filmstrip(vs: dict) -> None:
    """Frames across the whole clip with the current look; frames outside the trim are dimmed."""
    dur, path = vs["dur"], vs["path"]
    a, b = vs["trim"]
    times: List[float] = [round(dur * (i + .5) / STRIP_FRAMES, 1) for i in range(STRIP_FRAMES)]
    cols = st.columns(STRIP_FRAMES)
    for col, t in zip(cols, times):
        raw = _strip_thumb(path, t)
        if not raw:
            continue
        img = photo.render(Image.open(io.BytesIO(raw)).convert("RGB"), vs["state"], texts=False, crop=False)
        if not (a <= t <= b):
            img = ImageEnhance.Brightness(img).enhance(0.3)
        col.image(img, use_container_width=True, caption=C.mmss(t))


def _export(vs: dict, track) -> None:
    a, b = vs["trim"]
    bar = st.progress(0.0, text="Exporting…")
    try:
        out = export.render_video(
            vs["path"], a, b, vs["speed"], vs["keep"], vs["state"].ffmpeg_filters(), vs["opts"],
            audio=track.local_path if track is not None else None,
            on_progress=lambda f: bar.progress(min(1.0, f), text=f"Exporting… {int(f * 100)}%"),
        )
        with open(out, "rb") as f:
            vs["result"] = (f.read(), track.credit if track is not None else "")
        bar.empty()
    except Exception as e:
        bar.empty()
        st.error(str(e))


def render_page() -> None:
    C.hero("Video Editor", "Trim · speed · looks · songs · Gemini AI · one-pass export", "🎬", ACCENT)
    if shutil.which("ffmpeg") is None:
        st.error("FFmpeg not found on this server. Add `ffmpeg` to packages.txt (see README).")
        return
    vs = _init()
    with C.card():
        if vs["path"] is None:
            C.step(1, "Pick a video")
        up = st.file_uploader("Pick video", type=["mp4", "mov", "m4v", "mkv", "webm", "avi"], key="video_up",
                              label_visibility="visible" if vs["path"] else "collapsed")
    if up is not None and vs["fid"] != (up.name, up.size):
        _load(vs, up)
    if vs["path"] is None:
        return

    frame = _frame(vs["path"], round(vs["frame_t"], 1))
    base = Image.open(io.BytesIO(frame)).convert("RGB") if frame else None
    small = C.small_bytes(base) if base is not None else None

    left, right = st.columns([3, 2], gap="large")
    preview = left.container()
    track = None
    with right:
        tabs = st.tabs(["✂ Trim", "🎞 Filters", "✨ Effects", "🧩 Templates", "🎚 Adjust", "🎵 Music", "🤖 AI"])
        with tabs[0]:
            _tab_trim(vs)
        with tabs[1]:
            if small:
                _gallery_tab(vs, C.FILTERS, small)
        with tabs[2]:
            if small:
                _gallery_tab(vs, C.EFFECTS, small)
        with tabs[3]:
            if small:
                _gallery_tab(vs, C.TEMPLATES, small)
        with tabs[4]:
            _tab_adjust(vs)
        with tabs[5]:
            track = _tab_music(vs)
        with tabs[6]:
            _tab_ai(vs)

    s = vs["state"]
    a, b = vs["trim"]
    with preview:
        if base is not None:
            st.image(photo.render(base, s, texts=False, crop=False), use_container_width=True,
                     caption=f"Look preview at {vs['frame_t']:.1f}s")
        C.chips(f"🎞 {s.preset}" if s.preset != "Original" else "",
                f"✨ {s.effect}" if s.effect != "None" else "",
                f"⏩ {vs['speed']:.2f}x" if vs["speed"] != 1 else "",
                f"⏱ {(b - a) / vs['speed']:.1f}s out",
                f"🎵 {track.title}" if track is not None else "")
        with st.spinner("Building timeline…"):
            _filmstrip(vs)
        with st.expander("▶ Play original video"):
            st.video(vs["path"])
        if st.button("🎬 Export video", type="primary", use_container_width=True):
            _export(vs, track)
        if vs["result"]:
            data, credit = vs["result"]
            st.video(data)
            st.download_button("⬇ Download MP4", data, "pixelforge_video.mp4", "video/mp4",
                               type="primary", use_container_width=True)
            if credit:
                st.markdown(f'<div class="pf-credit">Music credit: {credit}</div>', unsafe_allow_html=True)
