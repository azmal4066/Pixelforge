"""Local BPM + beat-phase estimation (no server, no Spotify audio-features).
FFmpeg decodes to 11 kHz mono PCM, then an onset envelope + autocorrelation finds
the tempo and a phase search finds where the beats land."""
from __future__ import annotations

import math
import subprocess
from dataclasses import dataclass
from typing import Optional

import numpy as np

SR = 11025
HOP = 256
FPS = SR / HOP


@dataclass(frozen=True)
class BeatInfo:
    bpm: float
    first_beat: float  # seconds
    interval: float  # seconds per beat


def analyze(audio_path: str) -> Optional[BeatInfo]:
    try:
        p = subprocess.run(
            ["ffmpeg", "-v", "error", "-nostdin", "-i", audio_path, "-t", "90", "-ac", "1",
             "-ar", str(SR), "-f", "s16le", "-"],
            capture_output=True, timeout=120,
        )
    except Exception:
        return None
    if p.returncode != 0 or not p.stdout:
        return None
    return detect(np.frombuffer(p.stdout, dtype="<i2"))


def detect(samples: np.ndarray) -> Optional[BeatInfo]:
    frames = len(samples) // HOP
    if frames < FPS * 8:
        return None
    x = samples[: frames * HOP].astype(np.float32).reshape(frames, HOP) / 32768.0
    env = np.sqrt((x * x).mean(axis=1))

    onset = np.zeros(frames, dtype=np.float32)
    onset[1:] = np.maximum(env[1:] - env[:-1], 0)
    onset = np.maximum(0, onset - onset.mean())

    min_lag = round(60 * FPS / 180)
    max_lag = round(60 * FPS / 70)
    best_lag, best = min_lag, -1.0
    acf = {}
    for lag in range(min_lag - 1, max_lag + 2):
        acf[lag] = float(np.dot(onset[lag:], onset[:-lag])) / (frames - lag)
    for lag in range(min_lag, max_lag + 1):
        if acf[lag] > best:
            best, best_lag = acf[lag], lag
    # parabolic interpolation: integer lags are too coarse at 43 frames/s (+-3 BPM)
    y0, y1, y2 = acf[best_lag - 1], acf[best_lag], acf[best_lag + 1]
    denom = y0 - 2 * y1 + y2
    lag_est = best_lag + (0.5 * (y0 - y2) / denom if denom != 0 else 0.0)
    bpm = 60 * FPS / lag_est
    while bpm < 80:
        bpm *= 2
    while bpm > 160:
        bpm /= 2
    lag_f = 60 * FPS / bpm

    best_phase, best_score = 0.0, -1.0
    ph = 0.0
    while ph < lag_f:
        idx = np.round(np.arange(ph, frames, lag_f)).astype(int)
        idx = idx[idx < frames]
        score = float(onset[idx].sum())
        if score > best_score:
            best_score, best_phase = score, ph
        ph += 1
    return BeatInfo(bpm, best_phase / FPS, 60 / bpm)
