import json
import re
import subprocess
from loguru import logger

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except ImportError:
    pass  # relies on system ffmpeg/ffprobe being on PATH


def extract_quality_metrics(file_path: str) -> dict:
    """Run ffprobe on a clip and return scored quality metrics (0-100 overall)."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", file_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        data = json.loads(result.stdout)
    except FileNotFoundError:
        logger.error("[VideoAnalysis] ffprobe not found — install FFmpeg and add to PATH.")
        raise
    except subprocess.CalledProcessError as e:
        logger.warning(f"[VideoAnalysis] ffprobe failed for {file_path}: {e.stderr[:200]}")
        return _fallback_metrics()
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        logger.warning(f"[VideoAnalysis] ffprobe parse error for {file_path}: {e}")
        return _fallback_metrics()

    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(fmt.get("duration", 0.0))

    # ── Resolution score (0-10) ───────────────────────────────────────────────
    if video:
        width = int(video.get("width", 0))
        height = int(video.get("height", 0))
        max_dim = max(width, height)
        is_vertical = height > width
        if max_dim >= 1920:
            resolution_score = 10.0
        elif max_dim >= 1280:
            resolution_score = 8.0
        elif max_dim >= 854:
            resolution_score = 6.0
        elif max_dim >= 640:
            resolution_score = 4.0
        else:
            resolution_score = 2.0
    else:
        width = height = 0
        is_vertical = False
        resolution_score = 0.0

    # ── FPS score (0-10) ─────────────────────────────────────────────────────
    fps = 0.0
    fps_score = 0.0
    if video:
        fps_str = video.get("r_frame_rate", "0/1")
        try:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) > 0 else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0
        if fps >= 30:
            fps_score = 10.0
        elif fps >= 24:
            fps_score = 8.0
        elif fps >= 15:
            fps_score = 5.0
        elif fps > 0:
            fps_score = 2.0

    # ── Bitrate score (0-10) ─────────────────────────────────────────────────
    try:
        # Prefer stream-level bitrate, fall back to container bitrate
        if video and video.get("bit_rate"):
            bit_rate = int(video["bit_rate"])
        else:
            bit_rate = int(fmt.get("bit_rate", 0))
    except (ValueError, TypeError):
        bit_rate = 0

    if bit_rate >= 5_000_000:
        bitrate_score = 10.0
    elif bit_rate >= 2_000_000:
        bitrate_score = 8.0
    elif bit_rate >= 1_000_000:
        bitrate_score = 6.0
    elif bit_rate >= 500_000:
        bitrate_score = 4.0
    else:
        bitrate_score = 2.0

    # ── Audio clarity score (0-10) ───────────────────────────────────────────
    audio_clarity_score = 0.0
    if audio:
        try:
            sample_rate = int(audio.get("sample_rate", 0))
        except (ValueError, TypeError):
            sample_rate = 0
        if sample_rate >= 44100:
            audio_clarity_score = 10.0
        elif sample_rate >= 22050:
            audio_clarity_score = 7.0
        elif sample_rate > 0:
            audio_clarity_score = 4.0

    # ── Weighted total (0-100) ────────────────────────────────────────────────
    technical_quality_raw = round(
        (resolution_score * 0.35
         + fps_score * 0.25
         + bitrate_score * 0.25
         + audio_clarity_score * 0.15) * 10,
        2,
    )

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": round(fps, 2),
        "bit_rate": bit_rate,
        "resolution_score": resolution_score,
        "fps_score": fps_score,
        "bitrate_score": bitrate_score,
        "audio_clarity_score": audio_clarity_score,
        "is_vertical": is_vertical,
        "technical_quality_raw": technical_quality_raw,
        "has_audio": audio is not None,
    }


def detect_scene_changes(file_path: str, threshold: float = 0.4) -> list[dict]:
    """Return timestamps (sec) where scene changes exceed threshold using ffmpeg select filter."""
    cmd = [
        "ffmpeg", "-i", file_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        timestamps = []
        for match in re.finditer(r"pts_time:([\d.]+)", result.stderr):
            ts = float(match.group(1))
            if ts > 0.1:  # skip frame 0 — not a scene change
                timestamps.append({"timestamp_sec": round(ts, 3)})
        return sorted(timestamps, key=lambda x: x["timestamp_sec"])
    except FileNotFoundError:
        logger.error("[VideoAnalysis] ffmpeg not found — install FFmpeg and add to PATH.")
        raise
    except subprocess.TimeoutExpired:
        logger.warning(f"[VideoAnalysis] Scene detection timed out for {file_path}")
        return []
    except subprocess.SubprocessError as e:
        logger.warning(f"[VideoAnalysis] Scene detection failed for {file_path}: {e}")
        return []


def extract_usable_segments(
    file_path: str,
    quality_metrics: dict | None = None,
) -> list[dict]:
    """
    Build usable clip segments from scene boundaries.
    Each segment capped at 15s, max 8 returned.
    Falls back to a single full-clip segment when no scene changes are detected.
    """
    if quality_metrics is None:
        quality_metrics = extract_quality_metrics(file_path)

    duration = quality_metrics.get("duration", 0.0)
    if duration <= 0:
        logger.warning(f"[VideoAnalysis] Could not determine duration for {file_path}")
        return [{"start_sec": 0.0, "end_sec": 0.0, "note": "Unknown duration"}]

    scene_changes = detect_scene_changes(file_path)
    boundaries = [0.0] + [sc["timestamp_sec"] for sc in scene_changes] + [duration]

    segments = []
    for i in range(len(boundaries) - 1):
        raw_start = boundaries[i]
        raw_end = boundaries[i + 1]
        start = round(raw_start, 2)
        end = round(min(raw_end, raw_start + 15.0), 2)  # cap at 15s
        seg_dur = round(end - start, 2)

        if seg_dur < 1.0:  # skip fragments shorter than 1 second
            continue

        extras = []
        if quality_metrics.get("is_vertical"):
            extras.append("vertical")
        if seg_dur >= 8.0:
            extras.append("long")

        note = f"Segment {len(segments) + 1} ({seg_dur:.1f}s)"
        if extras:
            note += f" — {', '.join(extras)}"

        segments.append({"start_sec": start, "end_sec": end, "note": note})

        if len(segments) >= 8:
            break

    if not segments:
        end = round(min(duration, 15.0), 2)
        segments = [{
            "start_sec": 0.0,
            "end_sec": end,
            "note": f"Full clip ({end:.1f}s) — no scene changes detected",
        }]

    return segments


def _fallback_metrics() -> dict:
    return {
        "duration": 0.0, "width": 0, "height": 0, "fps": 0.0, "bit_rate": 0,
        "resolution_score": 0.0, "fps_score": 0.0, "bitrate_score": 0.0,
        "audio_clarity_score": 0.0, "is_vertical": False,
        "technical_quality_raw": 0.0, "has_audio": False,
    }
