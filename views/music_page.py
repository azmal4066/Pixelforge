"""Music Studio: photos -> beat-synced slideshow with a song, or add a song to a video."""
from __future__ import annotations

import os
import shutil

import streamlit as st
from PIL import Image, ImageOps

from pixelforge import export
from . import common as C

ACCENT = C.GREEN


def _save_photos(files) -> list:
    """Normalise EXIF rotation and save as JPEG so FFmpeg sees upright images."""
    sig = tuple((f.name, f.size) for f in files)
    cached = st.session_state.get("ms_photo_cache")
    if cached and cached[0] == sig:
        return cached[1]
    d = C.temp_dir()
    paths = []
    for i, f in enumerate(files):
        img = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        p = os.path.join(d, f"{i:03d}.jpg")
        img.save(p, "JPEG", quality=92)
        paths.append(p)
    st.session_state["ms_photo_cache"] = (sig, paths)
    return paths


def render_page() -> None:
    C.hero("Music Studio", "Beat-synced slideshow · add a song to your video", "🎵", ACCENT)
    if shutil.which("ffmpeg") is None:
        st.error("FFmpeg not found on this server. Add `ffmpeg` to packages.txt (see README).")
        return

    mode = st.radio("Media", ["Video", "Photos"], horizontal=True, key="ms_mode", label_visibility="collapsed")
    is_video = mode == "Video"

    # 1. media ----------------------------------------------------------------
    C.step(1, "Media")
    video_path, photo_paths = None, []
    with C.card():
        if is_video:
            up = st.file_uploader("Pick video", type=["mp4", "mov", "m4v", "mkv", "webm", "avi"], key="ms_video")
            if up is not None:
                cached = st.session_state.get("ms_video_cache")
                if not cached or cached[0] != (up.name, up.size):
                    p = os.path.join(C.temp_dir(), up.name)
                    with open(p, "wb") as f:
                        f.write(up.getbuffer())
                    st.session_state["ms_video_cache"] = ((up.name, up.size), p)
                video_path = st.session_state["ms_video_cache"][1]
        else:
            ups = st.file_uploader("Pick photos (order = slideshow order)", type=["png", "jpg", "jpeg", "webp"],
                                   accept_multiple_files=True, key="ms_photos")
            if ups:
                photo_paths = _save_photos(ups)
                C.chips(f"🖼 {len(photo_paths)} photos selected")
                cols = st.columns(min(6, len(photo_paths)))
                for col, p in zip(cols, photo_paths):
                    col.image(p, use_container_width=True)

    # 2. song -----------------------------------------------------------------
    C.step(2, "Song")
    track, beat = C.song_picker("ms")

    # 3. mix ------------------------------------------------------------------
    C.step(3, "Mix")
    o = export.ExportOptions()
    target = 30.0
    with C.card():
        c1, c2 = st.columns(2)
        o.music_volume = c1.slider("🔊 Song volume", 0.0, 1.5, 1.0, 0.05)
        if is_video:
            o.original_volume = c2.slider("🎤 Original sound", 0.0, 1.0, 0.35, 0.05)
        o.music_start = float(c1.slider("⏭ Start song at (sec)", 0, 120, 0, 1))
        o.fade_out = c2.slider("🌅 Fade out (sec)", 0.0, 5.0, 1.5, 0.1)
        if not is_video:
            target = float(st.slider("⏱ Video length (sec)", 10, 60, 30, 1))
            if beat is not None and photo_paths:
                per = max(1, round(target / len(photo_paths) / beat.interval)) * beat.interval
                C.chips(f"🥁 cut every {per:.2f}s", f"🎚 ~{beat.bpm:.0f} BPM",
                        f"⏱ {per * len(photo_paths):.1f}s total")
            st.caption("Photo cuts snap to the song beats automatically.")

    # 4. export ---------------------------------------------------------------
    C.step(4, "Export")
    ready = track is not None and track.exportable and (video_path if is_video else photo_paths)
    if st.button("🎬 Create video", type="primary", disabled=not ready, use_container_width=True):
        bar = st.progress(0.0, text="Preparing…")
        cb = lambda f: bar.progress(min(1.0, f), text=f"Exporting… {int(f * 100)}%")
        try:
            if is_video:
                out = export.add_music_to_video(video_path, track.local_path, o, cb)
            else:
                out = export.photos_to_video(photo_paths, track.local_path, o, target, beat, on_progress=cb)
            with open(out, "rb") as f:
                st.session_state["ms_result"] = (f.read(), track.credit)
        except Exception as e:
            st.error(str(e))
        bar.empty()
    if not ready:
        st.caption("Pick " + ("a video" if is_video else "photos") + " and a song to enable export.")

    res = st.session_state.get("ms_result")
    if res:
        data, credit = res
        st.video(data)
        st.download_button("⬇ Download MP4", data, "pixelforge_music_video.mp4", "video/mp4",
                           type="primary", use_container_width=True)
        if credit:
            st.markdown(f'<div class="pf-credit">Music credit: {credit}</div>', unsafe_allow_html=True)
