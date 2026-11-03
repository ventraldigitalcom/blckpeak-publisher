"""Lossless-composition portrait finishing for explicitly approved BLCKPEAK stills.

Only crop a few edge pixels to exact 9:16 and resample. Never pad with black.
This cannot fix source SKU geometry or embedded black borders; human QC remains required.
"""
import json
import subprocess
from pathlib import Path


def run(*args):
    subprocess.run(args, check=True, timeout=300)


def probe_dimensions(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=30)
    streams = json.loads(result.stdout).get("streams") or []
    if not streams:
        raise ValueError("Missing decodable video/image stream")
    return int(streams[0]["width"]), int(streams[0]["height"])


def portrait_crop(width, height):
    if min(width, height) < 200:
        raise ValueError("Source resolution too small")
    unit = min(width // 9, height // 16)
    cw, ch = 9 * unit, 16 * unit
    if unit == 0 or max((width - cw) / width, (height - ch) / height) > .025:
        raise ValueError("Source is not sufficiently close to portrait 9:16; manual review")
    return cw, ch, (width - cw) // 2, (height - ch) // 2


def export_media(source, mp4, instagram_jpg, tiktok_jpg):
    """Create 8s silent YouTube mp4, 4:5 Instagram JPG and true 9:16 TikTok JPG."""
    width, height = probe_dimensions(source)
    cw, ch, left, top = portrait_crop(width, height)
    crop = f"crop={cw}:{ch}:{left}:{top}"
    fit = f"{crop},scale=1080:1920:flags=lanczos,setsar=1"
    for path in (mp4, instagram_jpg, tiktok_jpg):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-framerate", "30", "-i", str(source), "-t", "8",
        "-vf", fit + ",format=yuv420p", "-r", "30", "-c:v", "libx264",
        "-preset", "veryfast", "-crf", "22", "-an", "-movflags", "+faststart",
        str(mp4))
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-vf", fit, "-frames:v", "1", "-q:v", "2",
        str(tiktok_jpg))
    # Keep all source artwork for 4:5 IG feed; sides filled from blurred
    # source imagery, not uniform black bars. Manual QC still required.
    filt = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]{crop},scale=1080:1350:force_original_aspect_ratio=increase,"
        f"crop=1080:1350,boxblur=20:1[blur];"
        f"[fg]{crop},scale=1080:1350:force_original_aspect_ratio=decrease[sharp];"
        f"[blur][sharp]overlay=(W-w)/2:(H-h)/2,format=yuvj420p"
    )
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(source), "-filter_complex", filt, "-frames:v", "1",
        "-q:v", "2", str(instagram_jpg))
    expected = [(mp4, (1080, 1920)), (tiktok_jpg, (1080, 1920)),
                (instagram_jpg, (1080, 1350))]
    for path, dims in expected:
        actual = probe_dimensions(path)
        if actual != dims:
            raise RuntimeError(f"Bad export dimensions {path}: {actual}, expected {dims}")
    return {"source": (width, height), "crop": (cw, ch, left, top),
            "youtube": (1080, 1920), "tiktok": (1080, 1920),
            "instagram": (1080, 1350)}
