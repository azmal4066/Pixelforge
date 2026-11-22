"""Photo Editor: 500 filters / effects / templates, adjust, crop, text, undo/redo, Gemini AI."""
from __future__ import annotations

from typing import Optional

import streamlit as st

from pixelforge import catalog, gemini, photo
from pixelforge.edit_state import EditState
from pixelforge.models import TextLayer
from . import common as C

RATIOS = {"Original": None, "1:1": 1.0, "4:5": 4 / 5, "3:4": 3 / 4, "9:16": 9 / 16, "16:9": 16 / 9}
EXAMPLES = ["Sunset look-ku maathu", "Black and white aakku", "Brightness konjam kootu",
            '"Happy Birthday" text add pannu']
ACCENT = C.RED


# ------------------------------------------------------------------ session
def _init() -> dict:
    if "photo" not in st.session_state:
        st.session_state.photo = {
            "bytes": None, "work": None, "small": None, "state": EditState(),
            "undo": [], "redo": [], "ver": 0, "sel": 0, "reply": "", "caption": "",
            "src_id": None, "pv": None, "dl": None,
        }
    return st.session_state.photo


def set_image(ps: dict, data: bytes) -> None:
    ps["bytes"] = data
    ps["work"] = photo.load_image(data, 1100)
    ps["small"] = C.small_bytes(ps["work"])
    ps["pv"] = None
    ps["dl"] = None


def open_new(data: bytes) -> None:
    """Load `data` as a fresh photo (used by the AI Generate page too)."""
    ps = _init()
    if ps["bytes"] is not None:
        push_undo(ps)
    set_image(ps, data)
    ps["state"] = EditState()
    ps["ver"] += 1
    ps["sel"] = 0


def push_undo(ps: dict) -> None:
    ps["undo"].append((ps["bytes"], ps["state"].copy()))
    del ps["undo"][:-40]
    ps["redo"].clear()


def _restore(ps: dict, data: bytes, state: EditState) -> None:
    if data is not ps["bytes"]:
        set_image(ps, data)
    ps["state"] = state
    ps["ver"] += 1


def _change(ps: dict, fn) -> None:
    """Programmatic edit: checkpoint, mutate, reset widgets, rerun."""
    push_undo(ps)
    fn(ps["state"])
    ps["ver"] += 1
    st.rerun()


# ------------------------------------------------------------------ empty state
def _empty(ps: dict) -> None:
    C.hero("Photo Editor", "500 filters · 500 effects · 500 templates · Gemini AI", "🎞", ACCENT)
    c1, c2 = st.columns(2)
    with c1, C.card():
        C.step(1, "Pick a photo")
        up = st.file_uploader("Pick photo", type=["png", "jpg", "jpeg", "webp"], key="photo_up",
                              label_visibility="collapsed")
        with st.expander("📷 Use the camera"):
            cam = st.camera_input("Take a photo", key="photo_cam")
    with c2, C.card():
        generate_box(key="photo_gen")
    for f in (up, cam):
        if f is not None:
            set_image(ps, f.getvalue())
            ps["src_id"] = (f.name, f.size)
            ps["state"] = EditState()
            st.rerun()


def generate_box(key: str) -> None:
    C.step(2, "Or generate with AI")
    prompt = st.text_area("Describe the image", key=f"{key}_prompt", height=100,
                          placeholder="A neon-lit Chennai street at night, cinematic",
                          label_visibility="collapsed")
    if st.button("✨ Generate", key=f"{key}_go", type="primary", disabled=not prompt.strip(),
                 use_container_width=True):
        if not gemini.configured():
            st.error("GEMINI_API_KEY missing. Add it to `.streamlit/secrets.toml` (see README).")
            return
        slot = st.empty()
        slot.markdown(C.loader_html("GENERATING"), unsafe_allow_html=True)
        try:
            data = gemini.generate_image(prompt.strip())
            slot.empty()
            open_new(data)
            st.rerun()
        except Exception as e:
            slot.empty()
            st.error(str(e))


# ------------------------------------------------------------------ tabs
def _tab_adjust(ps: dict) -> None:
    s = ps["state"]

    def reset(st_: EditState) -> None:
        st_.reset_adjust()

    C.adjust_controls(s, ps["ver"], lambda: _change(ps, reset), "pa")


def _tab_crop(ps: dict) -> None:
    s = ps["state"]
    labels = list(RATIOS)
    idx = next((i for i, l in enumerate(labels)
                if (RATIOS[l] is None and s.aspect is None)
                or (RATIOS[l] is not None and s.aspect is not None and abs(RATIOS[l] - s.aspect) < 1e-3)), 0)
    pick = st.radio("Crop ratio", labels, index=idx, horizontal=True, key=f"pc_ratio{ps['ver']}")
    s.aspect = RATIOS[pick]
    C.rotate_flip(
        "pc",
        lambda: _change(ps, lambda x: setattr(x, "quarter_turns", (x.quarter_turns + 3) % 4)),
        lambda: _change(ps, lambda x: setattr(x, "quarter_turns", (x.quarter_turns + 1) % 4)),
        lambda: _change(ps, lambda x: setattr(x, "flip_h", not x.flip_h)),
    )


def _hex(c) -> str:
    return "#%02x%02x%02x" % tuple(c)


def _tab_text(ps: dict) -> None:
    s, v = ps["state"], ps["ver"]
    if st.button("➕ Add text", key="pt_add", type="primary"):
        def add(x: EditState) -> None:
            x.texts.append(TextLayer("Text"))
            ps["sel"] = len(x.texts) - 1
        _change(ps, add)
    if not s.texts:
        st.caption("Add a text layer, then set its position with the X / Y sliders.")
        return
    ps["sel"] = min(ps["sel"], len(s.texts) - 1)
    sel = st.selectbox("Layer", range(len(s.texts)), index=ps["sel"], key=f"pt_sel{v}",
                       format_func=lambda i: f"{i + 1}: {s.texts[i].text[:24]}")
    ps["sel"] = sel
    t = s.texts[sel]
    k = f"pt{v}_{sel}"
    t.text = st.text_input("Text", t.text, key=f"{k}_t")
    t.size = st.slider("Size", 12.0, 90.0, float(t.size), 1.0, key=f"{k}_s")
    c1, c2 = st.columns(2)
    t.dx = c1.slider("X", 0.0, 1.0, float(t.dx), 0.01, key=f"{k}_x")
    t.dy = c2.slider("Y", 0.0, 1.0, float(t.dy), 0.01, key=f"{k}_y")
    hexv = st.color_picker("Color", _hex(t.color), key=f"{k}_c").lstrip("#")
    t.color = tuple(int(hexv[i:i + 2], 16) for i in (0, 2, 4))
    if st.button("🗑 Delete layer", key="pt_del"):
        _change(ps, lambda x: x.texts.pop(sel))


def _gallery_tab(ps: dict, kind: str) -> None:
    def pick(name: str) -> None:
        def fn(x: EditState) -> None:
            if kind == C.FILTERS:
                x.preset = name
            elif kind == C.EFFECTS:
                x.effect = name
            else:
                t = next(t for t in catalog.templates() if t.name == name)
                x.preset, x.effect, x.aspect = t.filter, t.effect, t.aspect
                x.texts = [tl.copy() for tl in t.texts]
                ps["sel"] = 0
        _change(ps, fn)

    def clear() -> None:
        def fn(x: EditState) -> None:
            if kind == C.FILTERS:
                x.preset = "Original"
            elif kind == C.EFFECTS:
                x.effect = "None"
            else:
                x.preset, x.effect, x.aspect, x.texts = "Original", "None", None, []
        _change(ps, fn)

    C.gallery(kind, ps["state"], ps["small"], "photo", pick, clear)


def _tab_ai(ps: dict) -> None:
    if not gemini.configured():
        st.info("Add `GEMINI_API_KEY` to `.streamlit/secrets.toml` to use the AI box.")
    st.caption("Try: " + " · ".join(EXAMPLES))
    prompt = st.text_input("Tell Gemini what to do", key=f"ai_p{ps['ver']}",
                           placeholder="✨ Gemini-kitta sollunga… (Tamil / English)")
    if st.button("✨ Ask AI", key="ai_go", type="primary", use_container_width=True,
                 disabled=not prompt.strip() or not gemini.configured()):
        try:
            with st.spinner("Thinking…"):
                res = gemini.commands(prompt.strip(), ps["state"], video=False)
                new_bytes: Optional[bytes] = None
                if res.get("generative") is True and res.get("generativePrompt"):
                    new_bytes = gemini.edit_image(ps["bytes"], str(res["generativePrompt"]))
            push_undo(ps)
            s = ps["state"]
            if isinstance(res.get("set"), dict):
                s.apply_set(res["set"])
            if res.get("addText"):
                s.texts.append(TextLayer(str(res["addText"])))
                ps["sel"] = len(s.texts) - 1
            if new_bytes:
                set_image(ps, new_bytes)
            ps["reply"] = str(res.get("reply") or "")
            ps["ver"] += 1
            st.rerun()
        except Exception as e:
            st.error(str(e))
    if ps["reply"]:
        st.success(ps["reply"])
    st.divider()
    if st.button("#️⃣ Caption + hashtags", key="ai_cap", disabled=not gemini.configured(),
                 use_container_width=True):
        try:
            with st.spinner("Writing captions…"):
                img = photo.render(ps["work"], ps["state"])
                ps["caption"] = gemini.caption_and_tags(photo.to_bytes(img, "JPEG"))
        except Exception as e:
            st.error(str(e))
    if ps["caption"]:
        st.text_area("Caption", ps["caption"], height=220)
    with st.expander("✨ Generate a new image"):
        generate_box("photo_gen2")


# ------------------------------------------------------------------ page
def render_page() -> None:
    ps = _init()
    if ps["bytes"] is None:
        _empty(ps)
        return

    C.hero("Photo Editor", "500 filters · 500 effects · 500 templates · Gemini AI", "🎞", ACCENT)

    # ---- toolbar (undo / redo / export / new)
    t1, t2, t3, t4, _ = st.columns([1, 1, 2, 2, 4])
    if t1.button("↶ Undo", disabled=not ps["undo"], use_container_width=True):
        ps["redo"].append((ps["bytes"], ps["state"].copy()))
        d, s = ps["undo"].pop()
        _restore(ps, d, s)
        st.rerun()
    if t2.button("↷ Redo", disabled=not ps["redo"], use_container_width=True):
        ps["undo"].append((ps["bytes"], ps["state"].copy()))
        d, s = ps["redo"].pop()
        _restore(ps, d, s)
        st.rerun()
    if t3.button("💾 Prepare download", use_container_width=True):
        with st.spinner("Rendering full resolution…"):
            full = photo.render(photo.load_image(ps["bytes"]), ps["state"])
            ps["dl"] = photo.to_bytes(full, "PNG")
    if ps["dl"]:
        t4.download_button("⬇ Download PNG", ps["dl"], "pixelforge.png", "image/png", type="primary",
                           use_container_width=True)
    if st.sidebar.button("🆕 New photo", key="photo_new", use_container_width=True):
        del st.session_state["photo"]
        st.rerun()

    snap = (ps["bytes"], ps["state"].copy())
    left, right = st.columns([3, 2], gap="large")
    preview = left.container()
    with right:
        tabs = st.tabs(["🎞 Filters", "✨ Effects", "🧩 Templates", "🎚 Adjust", "✂ Crop", "🔤 Text", "🤖 AI"])
        with tabs[0]:
            _gallery_tab(ps, C.FILTERS)
        with tabs[1]:
            _gallery_tab(ps, C.EFFECTS)
        with tabs[2]:
            _gallery_tab(ps, C.TEMPLATES)
        with tabs[3]:
            _tab_adjust(ps)
        with tabs[4]:
            _tab_crop(ps)
        with tabs[5]:
            _tab_text(ps)
        with tabs[6]:
            _tab_ai(ps)

    # widget-driven edits (sliders, radio, text boxes) -> automatic undo checkpoint
    if ps["bytes"] is snap[0] and ps["state"].sig() != snap[1].sig():
        ps["undo"].append(snap)
        del ps["undo"][:-40]
        ps["redo"].clear()
        ps["dl"] = None

    key = (id(ps["bytes"]), ps["state"].sig())
    if ps["pv"] is None or ps["pv"][0] != key:
        ps["pv"] = (key, photo.render(ps["work"], ps["state"]))
    s = ps["state"]
    with preview:
        st.image(ps["pv"][1], use_container_width=True)
        names = [s.preset if s.preset != "Original" else "", s.effect if s.effect != "None" else ""]
        C.chips(*[f"🎞 {names[0]}" if names[0] else "", f"✨ {names[1]}" if names[1] else "",
                  f"▭ {s.aspect:.2f}" if s.aspect else "", f"🔤 {len(s.texts)} text" if s.texts else ""])
