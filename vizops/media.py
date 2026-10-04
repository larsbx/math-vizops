"""Normalize finished renderer media and check the bytes a browser will receive."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

from .sources import SourceError


class MediaUnavailable(RuntimeError):
    """The environment cannot reach a playback verdict."""


def prepare(movie: Path, target: Path, poster: Path) -> dict:
    """Produce verified H.264/yuv420p MP4 and its first-frame poster in scratch."""
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise MediaUnavailable("ffmpeg/ffprobe are required to verify browser media")
    subprocess.run([
        ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(movie),
        "-map", "0:v:0", "-an", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(target),
    ], check=True, capture_output=True, timeout=900)
    info = json.loads(subprocess.check_output([
        ffprobe, "-v", "error", "-select_streams", "v:0", "-show_streams",
        "-show_format", "-of", "json", str(target),
    ], timeout=60))
    try:
        streams = info["streams"]
        stream, = streams
        duration = float(info["format"]["duration"])
        width, height = stream["width"], stream["height"]
        valid = (stream["codec_name"] == "h264" and stream["pix_fmt"] == "yuv420p"
                 and math.isfinite(duration) and duration > 0
                 and type(width) is int and width > 0 and type(height) is int and height > 0)
    except (KeyError, TypeError, ValueError) as error:
        raise SourceError("invalid playback metadata") from error
    if not valid:
        raise SourceError("rendered media is not a playable H.264/yuv420p video")
    subprocess.run([
        ffmpeg, "-nostdin", "-v", "error", "-y", "-i", str(target),
        "-frames:v", "1", str(poster),
    ], check=True, capture_output=True, timeout=60)
    if not poster.is_file() or poster.is_symlink() or not poster.stat().st_size:
        raise SourceError("poster was not produced")
    return {"codec": "h264", "pixel_format": "yuv420p", "duration_seconds": duration,
            "width": width, "height": height}
