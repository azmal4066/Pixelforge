"""AI Generate: text -> image with Gemini, then open it in the Photo Editor."""
from __future__ import annotations

import streamlit as st

from pixelforge import gemini
from . import common as C
from . import photo_page

EXAMPLES = [
    "A neon-lit Chennai street at night, cinematic",
    "Pongal festival kolam at sunrise, golden light",
    "Cyberpunk Marina Beach, rain, reflections",
    "Minimal poster of a lone hero on a mountain",
]


def _open_in_editor() -> None:
    photo_page.open_new(st.session_state["gen_image"])
    st.session_state["page"] = "Photo Editor"


def _use_example(text: str) -> None:
    st.session_state["gen_prompt"] = text


def render_page() -> None:
    C.hero("AI Generate", "Text to image with Gemini, then edit it in place", "✨", C.LILAC)
    if not gemini.configured():
        st.info("Add `GEMINI_API_KEY` to `.streamlit/secrets.toml` to generate images.")

    with C.card():
        C.step(1, "Describe the image")
        prompt = st.text_area("Describe the image", key="gen_prompt", height=120,
                              placeholder="A neon-lit Chennai street at night, cinematic",
                              label_visibility="collapsed")
        st.caption("Ideas — tap one to fill the box")
        cols = st.columns(2)
        for i, ex in enumerate(EXAMPLES):
            cols[i % 2].button(ex, key=f"gen_ex{i}", on_click=_use_example, args=(ex,), use_container_width=True)
        go = st.button("✨ Generate", type="primary", disabled=not prompt.strip(), use_container_width=True)

    if go:
        if not gemini.configured():
            st.error("GEMINI_API_KEY missing. Add it to `.streamlit/secrets.toml` (see README).")
        else:
            slot = st.empty()
            slot.markdown(C.loader_html("GENERATING"), unsafe_allow_html=True)
            try:
                st.session_state["gen_image"] = gemini.generate_image(prompt.strip())
            except Exception as e:
                st.error(str(e))
            slot.empty()

    img = st.session_state.get("gen_image")
    if img:
        C.step(2, "Result")
        st.image(img, use_container_width=True)
        c1, c2 = st.columns(2)
        c1.button("🎨 Open in Photo Editor", on_click=_open_in_editor, type="primary", use_container_width=True)
        c2.download_button("⬇ Download", img, "pixelforge_ai.png", "image/png", use_container_width=True)
