"""Gemini = the editing brain.
  commands()          natural language -> JSON edit commands (cheap text model)
  edit_image()        generative edits (background change, remove object, ...)
  generate_image()    text -> image
  caption_and_tags()  caption + hashtags for a photo
The key stays on the Streamlit server (st.secrets), never in the browser."""
from __future__ import annotations

import base64
import json
import re
from typing import Any, Dict, List

import requests

from .config import secret
from .edit_state import EditState

BASE = "https://generativelanguage.googleapis.com/v1beta/models"

SYSTEM = """You are the editing brain of a photo and video editor. Convert the user's request into JSON only.
Schema:
{
 "reply": "short friendly reply in the user's language (Tamil / Tanglish / English)",
 "set": { only the keys that should change:
   "brightness": -1..1, "contrast": 0.5..1.5, "saturation": 0..2, "warmth": -1..1,
   "preset": one of [Original, Vivid, Warm, Cool, B&W, Sepia, Fade, Dramatic, Vintage],
   "rotateQuarterTurns": 0..3 (absolute), "flipH": true/false,
   "speed": 0.25..4 (video only), "mute": true/false (video only) },
 "addText": string or null,
 "generative": true ONLY if the request needs pixel-level AI editing (change background, remove or add objects, restyle, outfit change, sky replace),
 "generativePrompt": precise English instruction for the image model when generative is true
}
Be moderate with values. Never include keys outside the schema."""


def _models():
    return (
        secret("GEMINI_TEXT_MODEL", "gemini-2.5-flash"),
        secret("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image"),
    )


def configured() -> bool:
    return bool(secret("GEMINI_API_KEY"))


def _generate(model: str, body: Dict[str, Any]) -> Dict[str, Any]:
    key = secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing. Add it to .streamlit/secrets.toml (see README).")
    r = requests.post(
        f"{BASE}/{model}:generateContent",
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        data=json.dumps(body), timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:240]}")
    return r.json()


def _parts(j: Dict[str, Any]) -> List[Dict[str, Any]]:
    c = j.get("candidates") or []
    if not c:
        return []
    return (c[0].get("content") or {}).get("parts") or []


def _text(j: Dict[str, Any]) -> str:
    return "".join(p.get("text", "") for p in _parts(j)).strip()


def _mime(b: bytes) -> str:
    return "image/png" if b[:2] == b"\x89P" else "image/jpeg"


def commands(prompt: str, state: EditState, video: bool) -> Dict[str, Any]:
    text_model, _ = _models()
    j = _generate(text_model, {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": (
            f"Media: {'video' if video else 'photo'}\n"
            f"Current state: {json.dumps(state.to_gemini_json())}\nRequest: {prompt}")}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    })
    raw = re.sub(r"^```json|```$", "", _text(j), flags=re.M).strip()
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else {"reply": raw}
    except Exception:
        return {"reply": raw or "Sorry, I could not understand that."}


def _first_image(j: Dict[str, Any]) -> bytes:
    for p in _parts(j):
        d = p.get("inlineData") or p.get("inline_data")
        if d and d.get("data"):
            return base64.b64decode(d["data"])
    t = _text(j)
    raise RuntimeError("Gemini returned no image." if not t else f"Gemini: {t}")


def edit_image(image: bytes, instruction: str) -> bytes:
    _, image_model = _models()
    j = _generate(image_model, {
        "contents": [{"parts": [
            {"text": f"{instruction}\nKeep the person identity, framing and image quality. Return only the edited image."},
            {"inlineData": {"mimeType": _mime(image), "data": base64.b64encode(image).decode()}},
        ]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    })
    return _first_image(j)


def generate_image(prompt: str) -> bytes:
    _, image_model = _models()
    j = _generate(image_model, {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    })
    return _first_image(j)


def caption_and_tags(image: bytes) -> str:
    text_model, _ = _models()
    j = _generate(text_model, {"contents": [{"parts": [
        {"text": "Write 3 short social media captions (1 Tamil, 1 English, 1 Tanglish) and 10 hashtags for this photo."},
        {"inlineData": {"mimeType": _mime(image), "data": base64.b64encode(image).decode()}},
    ]}]})
    return _text(j)
