"""Secrets: Streamlit secrets first, environment variables as fallback."""
from __future__ import annotations

import os

MOODS = {
    "Happy": "happy", "Chill": "chillout", "Energetic": "energetic", "Party": "party",
    "Romantic": "romantic", "Sad": "sad", "Epic": "epic", "Lofi": "lofi",
}


def secret(name: str, default: str = "") -> str:
    try:
        import streamlit as st

        v = st.secrets.get(name)  # raises if no secrets file exists
        if v:
            return str(v)
    except Exception:
        pass
    return os.environ.get(name, default)
