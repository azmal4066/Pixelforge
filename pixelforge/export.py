"""FFmpeg export: renderVideo(), slideshow, add music. Same filter graphs as the Flutter app,
run through the system `ffmpeg` binary (list args - no shell quoting)."""
from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .audio import BeatInfo

Progress = Optional[Callable[[float], None]]


@dataclass
class ExportOptions:
    music_volume: float = 1.0
    original_volume: float = 0.35
    music_start: float = 0.0  # seconds into the song
    fade_in: float = 0.5
    fade_out: float = 1.5


def _f(v: float) -> str:
    return f"{v:.3f}"


def _out_path() -> str:
    d = os.path.join(tempfile.gettempdir(), "pixelforge_out")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"pixelforge_{int(time.time() * 1000)}.mp4")


def _run(args: List[str], total: Optional[float], on_progress: Progress) -> None:
    cmd = ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
           "-progress", "pipe:1", "-nostats"] + args
    with tempfile.TemporaryFile() as err:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, text=True)
        assert p.stdout is not None
        for line in p.stdout:
            if on_progress and total and total > 0 and line.startswith("out_time_us="):
                try:
                    sec = int(line.split("=", 1)[1]) / 1e6
                    on_progress(max(0.0, min(1.0, sec / total)))
                except ValueError:
                    pass
        rc = p.wait()
        if rc != 0:
            err.seek(0)
            tail = err.read().decode(errors="ignore")[-600:]
            raise RuntimeError(f"FFmpeg failed: {tail}")
    if on_progress:
        on_progress(1.0)


def probe(path: str) -> Tuple[Optional[float], bool]:
    """(duration seconds, has audio stream)"""
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
             "-of", "json", path], capture_output=True, text=True, timeout=60)
        j = json.loads(p.stdout or "{}")
    except Exception:
        return None, False
    try:
        dur = float(j.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        dur = None
    has_audio = any(s.get("codec_type") == "audio" for s in j.get("streams", []))
    return dur, has_audio


def extract_frame(path: str, t: float) -> Optional[bytes]:
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-nostdin", "-ss", _f(max(0.0, t)), "-i", path,
         "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, timeout=60)
    return p.stdout if p.returncode == 0 and p.stdout else None


def add_music_to_video(video: str, audio: str, o: ExportOptions, on_progress: Progress = None) -> str:
    out = _out_path()
    d, has_audio = probe(video)
    fade_start = 0.0 if d is None else max(0.0, d - o.fade_out)
    music = (f"[1:a]atrim=start={_f(o.music_start)},asetpts=PTS-STARTPTS,"
             f"volume={_f(o.music_volume)},afade=t=in:st=0:d={_f(o.fade_in)}"
             f"{',afade=t=out:st=%s:d=%s' % (_f(fade_start), _f(o.fade_out)) if d is not None else ''},apad")
    if has_audio:
        filt = (f"{music}[m];[0:a]volume={_f(o.original_volume)}[o];"
                f"[o][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
        amap = "[a]"
    else:
        filt, amap = f"{music}[m]", "[m]"
    args = ["-i", video, "-i", audio, "-filter_complex", filt, "-map", "0:v", "-map", amap,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
    args += ["-t", _f(d)] if d is not None else ["-shortest"]
    args += ["-movflags", "+faststart", out]
    _run(args, d, on_progress)
    return out


def photos_to_video(images: List[str], audio: str, o: ExportOptions, target_seconds: float,
                    beat: Optional[BeatInfo] = None, width: int = 1080, height: int = 1920,
                    on_progress: Progress = None) -> str:
    """Photos -> slideshow video, cuts snapped to the song's beats."""
    if not images:
        raise RuntimeError("Pick at least one photo.")
    n = len(images)
    audio_start = o.music_start
    if beat is not None:
        beats_per_cut = max(1, round(target_seconds / n / beat.interval))
        per_photo = beats_per_cut * beat.interval
        k = math.ceil((o.music_start - beat.first_beat) / beat.interval)
        audio_start = beat.first_beat + k * beat.interval
        while audio_start < 0:
            audio_start += beat.interval
    else:
        per_photo = target_seconds / n
    total = per_photo * n

    list_path = os.path.join(tempfile.gettempdir(), f"slides_{int(time.time() * 1000)}.txt")
    esc = lambda s: s.replace("'", "'\\''")
    with open(list_path, "w") as fh:
        for img in images:
            fh.write(f"file '{esc(img)}'\nduration {_f(per_photo)}\n")
        fh.write(f"file '{esc(images[-1])}'\n")  # concat demuxer quirk

    out = _out_path()
    fade_start = max(0.0, total - o.fade_out)
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p")
    af = (f"volume={_f(o.music_volume)},afade=t=in:st=0:d={_f(o.fade_in)},"
          f"afade=t=out:st={_f(fade_start)}:d={_f(o.fade_out)},apad")
    args = ["-f", "concat", "-safe", "0", "-i", list_path, "-ss", _f(audio_start), "-i", audio,
            "-vf", vf, "-af", af, "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k", "-t", _f(total), "-movflags", "+faststart", out]
    try:
        _run(args, total, on_progress)
    finally:
        try:
            os.remove(list_path)
        except OSError:
            pass
    return out


def _atempo(speed: float) -> str:
    if abs(speed - 1) < 0.001:
        return ""
    parts, sp = [], speed
    while sp > 2.0:
        parts.append("atempo=2.0")
        sp /= 2.0
    while sp < 0.5:
        parts.append("atempo=0.5")
        sp /= 0.5
    parts.append(f"atempo={_f(sp)}")
    return ",".join(parts) + ","


def render_video(video: str, start: float, end: float, speed: float, keep_original_audio: bool,
                 v_filters: str, o: ExportOptions, audio: Optional[str] = None,
                 on_progress: Progress = None) -> str:
    """Full video editor render: trim + speed + colour/rotate/flip + original sound
    + optional song, in a single FFmpeg pass."""
    out = _out_path()
    _, has_audio = probe(video)
    out_len = (end - start) / speed

    v = f"[0:v]trim=start={_f(start)}:end={_f(end)},setpts=(PTS-STARTPTS)/{_f(speed)}"
    if v_filters:
        v += f",{v_filters}"
    v += ",format=yuv420p[v]"
    parts = [v]

    use_orig = has_audio and keep_original_audio
    use_music = audio is not None
    ov = o.original_volume if use_music else 1.0

    if use_orig:
        parts.append(f"[0:a]atrim=start={_f(start)}:end={_f(end)},asetpts=PTS-STARTPTS,"
                     f"{_atempo(speed)}volume={_f(ov)}[o]")
    if use_music:
        fo = min(o.fade_out, out_len)
        parts.append(f"[1:a]atrim=start={_f(o.music_start)},asetpts=PTS-STARTPTS,"
                     f"volume={_f(o.music_volume)},afade=t=in:st=0:d={_f(o.fade_in)},"
                     f"afade=t=out:st={_f(max(0.0, out_len - fo))}:d={_f(fo)},apad[m]")
    amap = None
    if use_orig and use_music:
        parts.append("[o][m]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]")
        amap = "[a]"
    elif use_music:
        amap = "[m]"
    elif use_orig:
        amap = "[o]"

    args = ["-i", video] + (["-i", audio] if use_music else [])
    args += ["-filter_complex", ";".join(parts), "-map", "[v]"]
    if amap:
        args += ["-map", amap, "-c:a", "aac", "-b:a", "192k"]
    args += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-t", _f(out_len),
             "-movflags", "+faststart", out]
    _run(args, out_len, on_progress)
    return out
