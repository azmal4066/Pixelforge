"""PixelForge (Streamlit): photo editor, video editor, music studio, AI generate."""
import time

import streamlit as st

st.set_page_config(page_title="PixelForge", page_icon="🎞", layout="wide", initial_sidebar_state="collapsed")

from views import common as C, generate_page, music_page, photo_page, video_page  # noqa: E402

PAGES = {
    "Photo Editor": ("🎞", "Filters, effects, templates, Gemini AI", C.RED, photo_page),
    "Video Editor": ("🎬", "Trim, filters, effects, songs, AI", C.CYAN, video_page),
    "Music Studio": ("🎵", "Beat-synced slideshow + add song", C.GREEN, music_page),
    "AI Generate": ("✨", "Text to image, then edit in place", C.LILAC, generate_page),
}
HOME = "Home"


def _go(name: str) -> None:
    st.session_state["page"] = name


def _splash() -> None:
    C.inject_theme(C.CYAN)
    slot = st.empty()
    slot.markdown('<div style="height:70vh;display:flex;flex-direction:column;align-items:center;justify-content:center">'
                  '<div class="pf-title" style="font-size:2.2rem">PIXELFORGE</div>'
                  f'{C.loader_html("POWERING UP")}</div>', unsafe_allow_html=True)
    time.sleep(1.6)
    slot.empty()


def _hub() -> None:
    C.hero("PixelForge", "500 Filters • 500 Effects • 500 Templates", "", C.CYAN)
    cols = st.columns(2)
    for i, (name, (icon, sub, accent, _)) in enumerate(PAGES.items()):
        with cols[i % 2]:
            st.markdown(f'<div style="border:1.4px solid {accent}b3;border-radius:22px;padding:22px 16px 6px;'
                        f'background:linear-gradient(135deg,{accent}47,#12102A);box-shadow:0 0 24px -6px {accent}80;'
                        f'text-align:center;margin-bottom:-8px"><div style="font-size:2.6rem;'
                        f'text-shadow:0 0 18px {accent}">{icon}</div>'
                        f'<div style="font-weight:900;letter-spacing:.25em;font-size:.9rem;margin-top:.5rem">'
                        f'{name.upper()}</div><div style="font-size:.75rem;color:#fff9;margin:.3rem 0 .8rem">{sub}</div></div>',
                        unsafe_allow_html=True)
            st.button("Open", key=f"hub_{name}", on_click=_go, args=(name,), use_container_width=True, type="primary")


def main() -> None:
    if "splashed" not in st.session_state:
        st.session_state["splashed"] = True
        _splash()
    st.session_state.setdefault("page", HOME)
    options = [HOME] + list(PAGES)
    if st.session_state["page"] not in options:
        st.session_state["page"] = HOME
    st.sidebar.markdown("### PIXELFORGE")
    st.sidebar.radio("Go to", options, key="page", label_visibility="collapsed")
    page = st.session_state["page"]
    if page == HOME:
        _hub()
    else:
        PAGES[page][3].render_page()


main()
