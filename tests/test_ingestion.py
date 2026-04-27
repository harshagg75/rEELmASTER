"""
Tests for the ingestion engine — video_analysis, transcription helpers, and ClipIngestionAgent.
Run: pytest tests/test_ingestion.py -v
"""
import json
from unittest.mock import patch

import pytest

from src.tools.video_analysis import (
    extract_quality_metrics,
    extract_usable_segments,
    _fallback_metrics,
)
from src.agents.ingestion import ClipIngestionAgent


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 — extract_quality_metrics
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractQualityMetrics:
    REQUIRED_KEYS = [
        "duration", "width", "height", "fps", "bit_rate",
        "resolution_score", "fps_score", "bitrate_score",
        "audio_clarity_score", "is_vertical", "technical_quality_raw", "has_audio",
    ]

    def test_returns_all_required_keys(self, test_clip):
        metrics = extract_quality_metrics(test_clip)
        for key in self.REQUIRED_KEYS:
            assert key in metrics, f"Missing key: {key}"

    def test_scores_within_valid_ranges(self, test_clip):
        metrics = extract_quality_metrics(test_clip)
        assert 0 <= metrics["technical_quality_raw"] <= 100, "technical_quality_raw out of range"
        for score_key in ("resolution_score", "fps_score", "bitrate_score", "audio_clarity_score"):
            assert 0 <= metrics[score_key] <= 10, f"{score_key} out of [0,10]"

    def test_vertical_clip_is_detected(self, test_clip_vertical):
        metrics = extract_quality_metrics(test_clip_vertical)
        assert metrics["is_vertical"] is True

    def test_horizontal_clip_not_vertical(self, test_clip_horizontal):
        metrics = extract_quality_metrics(test_clip_horizontal)
        assert metrics["is_vertical"] is False

    def test_fallback_metrics_all_zero(self):
        fb = _fallback_metrics()
        assert fb["technical_quality_raw"] == 0.0
        assert fb["has_audio"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — extract_usable_segments
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractUsableSegments:
    def test_single_segment_when_no_scene_changes(self, test_clip):
        """Uniform black clip → no scene changes → exactly 1 fallback segment."""
        with patch("src.tools.video_analysis.detect_scene_changes", return_value=[]):
            segments = extract_usable_segments(test_clip)
        assert len(segments) == 1
        assert segments[0]["start_sec"] == 0.0
        assert "note" in segments[0]

    def test_each_segment_max_15s(self, test_clip):
        """No segment should exceed 15 seconds."""
        with patch("src.tools.video_analysis.detect_scene_changes", return_value=[]):
            segments = extract_usable_segments(test_clip)
        for seg in segments:
            duration = seg["end_sec"] - seg["start_sec"]
            assert duration <= 15.0 + 0.05, f"Segment exceeds 15s: {duration:.2f}s"

    def test_max_8_segments_enforced(self, test_clip):
        """Even with many scene changes, cap at 8 segments."""
        many_changes = [{"timestamp_sec": float(i * 1.5)} for i in range(1, 25)]
        with patch("src.tools.video_analysis.detect_scene_changes", return_value=many_changes):
            segments = extract_usable_segments(test_clip)
        assert len(segments) <= 8

    def test_segments_are_ordered(self, test_clip):
        """Segments must be in chronological order."""
        changes = [{"timestamp_sec": 1.5}, {"timestamp_sec": 3.0}, {"timestamp_sec": 4.5}]
        with patch("src.tools.video_analysis.detect_scene_changes", return_value=changes):
            segments = extract_usable_segments(test_clip)
        for i in range(len(segments) - 1):
            assert segments[i]["end_sec"] <= segments[i + 1]["start_sec"] + 0.05

    def test_pre_computed_metrics_avoids_double_ffprobe(self, test_clip):
        """Passing quality_metrics should not trigger a second ffprobe call."""
        metrics = extract_quality_metrics(test_clip)
        with patch("src.tools.video_analysis.extract_quality_metrics") as mock_qm:
            with patch("src.tools.video_analysis.detect_scene_changes", return_value=[]):
                extract_usable_segments(test_clip, quality_metrics=metrics)
            mock_qm.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 — ClipIngestionAgent (dry_run, no real API call)
# ─────────────────────────────────────────────────────────────────────────────

class TestClipIngestionAgent:
    SAMPLE_RESPONSE = {
        "clip_id": "test_clip",
        "file_path": "/tmp/test_clip.mp4",
        "quality_score": 74.5,
        "quality_flag": "usable",
        "shot_type": "medium",
        "movement_energy": 4,
        "scene_tags": ["nature", "solitude", "window_light"],
        "emotion_tags": ["peaceful", "reflective"],
        "face_present": False,
        "transcript_summary": "No speech detected.",
        "mood": "aesthetic_calm",
        "color_palette": "warm",
        "usable_segments": [{"start_sec": 0.0, "end_sec": 5.0, "note": "Full clip (5.0s)"}],
    }

    def test_dry_run_returns_clip_metadata(self, test_clip):
        ffprobe_data = extract_quality_metrics(test_clip)
        ffprobe_data["usable_segments"] = [
            {"start_sec": 0.0, "end_sec": 5.0, "note": "Full clip"}
        ]
        response = dict(self.SAMPLE_RESPONSE)
        response["file_path"] = test_clip
        response["clip_id"] = "test_clip"

        with patch("src.agents.ingestion.call_claude", return_value=json.dumps(response)):
            agent = ClipIngestionAgent(dry_run=True)
            metadata = agent.run(test_clip, ffprobe_data, transcript="")

        from src.memory.schema import ClipMetadata
        assert isinstance(metadata, ClipMetadata)
        assert metadata.clip_id == "test_clip"
        assert metadata.quality_score == 74.5
        assert metadata.mood == "aesthetic_calm"
        assert metadata.quality_flag == "usable"

    def test_python_segments_override_claude_segments(self, test_clip):
        """Python-computed usable_segments must override whatever Claude returns."""
        python_segments = [{"start_sec": 1.0, "end_sec": 4.0, "note": "Python computed"}]
        ffprobe_data = extract_quality_metrics(test_clip)
        ffprobe_data["usable_segments"] = python_segments

        response = dict(self.SAMPLE_RESPONSE)
        response["file_path"] = test_clip
        # Claude returns different segments
        response["usable_segments"] = [{"start_sec": 0.0, "end_sec": 2.0, "note": "Claude computed"}]

        with patch("src.agents.ingestion.call_claude", return_value=json.dumps(response)):
            agent = ClipIngestionAgent(dry_run=True)
            metadata = agent.run(test_clip, ffprobe_data, transcript="")

        assert metadata.usable_segments[0].start_sec == 1.0
        assert metadata.usable_segments[0].note == "Python computed"

    def test_dry_run_does_not_call_vector_db(self, test_clip):
        """In dry_run mode, VectorDB must never be instantiated or called."""
        ffprobe_data = extract_quality_metrics(test_clip)
        ffprobe_data["usable_segments"] = [{"start_sec": 0.0, "end_sec": 5.0, "note": "x"}]
        response = dict(self.SAMPLE_RESPONSE)
        response["file_path"] = test_clip

        with patch("src.agents.ingestion.call_claude", return_value=json.dumps(response)):
            with patch("src.agents.ingestion.VectorDB") as mock_db_cls:
                agent = ClipIngestionAgent(dry_run=True)
                agent.run(test_clip, ffprobe_data, transcript="")
                mock_db_cls.assert_not_called()
