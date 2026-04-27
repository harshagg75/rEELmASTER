import os
import subprocess
import tempfile

from loguru import logger

try:
    from faster_whisper import WhisperModel
    _WHISPER_AVAILABLE = True
except ImportError:
    _WHISPER_AVAILABLE = False
    logger.warning("[Transcription] faster-whisper not installed. Transcription unavailable.")

_model: "WhisperModel | None" = None


def _get_model() -> "WhisperModel":
    global _model
    if not _WHISPER_AVAILABLE:
        raise ImportError("faster-whisper is not installed. Run: pip install faster-whisper")
    if _model is None:
        logger.info("[Transcription] Loading faster-whisper medium model (cpu, int8) …")
        _model = WhisperModel("medium", device="cpu", compute_type="int8")
        logger.success("[Transcription] Model loaded.")
    return _model


def transcribe_video(video_path: str) -> str:
    """
    Extract audio from video, transcribe with faster-whisper, return transcript string.
    Returns empty string for music-only clips or on any failure.
    Always cleans up the temp WAV file.
    """
    tmp_wav: str | None = None
    try:
        # Extract audio: 16kHz mono WAV (optimal for Whisper)
        tmp_wav = tempfile.mktemp(suffix=".wav")
        extract_cmd = [
            "ffmpeg", "-i", video_path,
            "-ar", "16000", "-ac", "1",
            "-f", "wav", tmp_wav,
            "-y", "-loglevel", "error",
        ]
        subprocess.run(extract_cmd, check=True, capture_output=True, timeout=60)

        model = _get_model()
        segments, info = model.transcribe(tmp_wav, beam_size=5)

        text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        transcript = " ".join(text_parts).strip()

        # Empty transcript with low language confidence → music-only clip
        if not transcript and info.language_probability < 0.5:
            logger.debug(
                f"[Transcription] Music-only clip detected: {video_path} "
                f"(lang_prob={info.language_probability:.2f})"
            )
            return ""

        logger.debug(
            f"[Transcription] {video_path} → {len(transcript)} chars "
            f"(lang={info.language}, prob={info.language_probability:.2f})"
        )
        return transcript

    except subprocess.CalledProcessError as e:
        logger.warning(
            f"[Transcription] Audio extraction failed for {video_path}: "
            f"{e.stderr.decode(errors='replace')[:200] if e.stderr else str(e)}"
        )
        return ""
    except subprocess.TimeoutExpired:
        logger.warning(f"[Transcription] Audio extraction timed out for {video_path}")
        return ""
    except ImportError:
        logger.warning("[Transcription] faster-whisper unavailable — skipping transcription.")
        return ""
    except Exception as e:
        logger.warning(f"[Transcription] Unexpected error for {video_path}: {e}")
        return ""
    finally:
        if tmp_wav and os.path.exists(tmp_wav):
            try:
                os.remove(tmp_wav)
            except OSError:
                pass
