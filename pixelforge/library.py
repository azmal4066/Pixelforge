"""Royalty-free library (Jamendo, Creative Commons).
IMPORTANT: many Jamendo tracks are CC "-NC" (non-commercial). The UI warns about this."""
from __future__ import annotations

import hashlib
import os
import tempfile
from typing import List, Optional

import requests

from .config import MOODS, secret
from .models import Track

_CACHE = os.path.join(tempfile.gettempdir(), "pixelforge_audio")


def configured() -> bool:
    return bool(secret("JAMENDO_CLIENT_ID"))


def search(query: str = "", mood: Optional[str] = None) -> List[Track]:
    cid = secret("JAMENDO_CLIENT_ID")
    if not cid:
        raise RuntimeError("JAMENDO_CLIENT_ID missing. See README.")
    params = {
        "client_id": cid, "format": "json", "limit": "30", "audioformat": "mp32",
        "audiodownload_allowed": "true", "include": "licenses", "imagesize": "200",
        "order": "popularity_week" if not query else "relevance",
    }
    if query:
        params["search"] = query
    if mood:
        params["fuzzytags"] = MOODS.get(mood, mood)
    r = requests.get("https://api.jamendo.com/v3.0/tracks/", params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Library error {r.status_code}")
    out: List[Track] = []
    for t in r.json().get("results", []):
        dl = t.get("audiodownload")
        out.append(Track(
            id=str(t.get("id")), title=t.get("name") or "", artist=t.get("artist_name") or "",
            source="library", image_url=t.get("image"), audio_url=t.get("audio"),
            download_url=dl if dl else t.get("audio"), external_url=t.get("shareurl"),
            license_url=t.get("license_ccurl"), duration_sec=t.get("duration"),
        ))
    return out


def download(track: Track) -> str:
    """Download the full file once, return the local path."""
    if track.local_path and os.path.exists(track.local_path):
        return track.local_path
    url = track.download_url or track.audio_url
    if not url:
        raise RuntimeError("This track has no downloadable audio.")
    os.makedirs(_CACHE, exist_ok=True)
    path = os.path.join(_CACHE, hashlib.sha1(url.encode()).hexdigest() + ".mp3")
    if not os.path.exists(path):
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(path + ".part", "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        os.replace(path + ".part", path)
    track.local_path = path
    return path
