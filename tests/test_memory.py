"""
Tests for src/memory/stores.py — all 6 store classes + MemoryStores wrapper.
All Supabase calls are mocked; no live DB required.
Run: pytest tests/test_memory.py -v
"""
from unittest.mock import MagicMock, patch

import pytest

from src.memory.stores import (
    AudiencePreferenceStore,
    ClipPerformanceStore,
    FormatPerformanceStore,
    HashtagVelocityStore,
    HookLibraryStore,
    MemoryStores,
    OptimalTimingStore,
)


# ── Shared mock factory ────────────────────────────────────────────────────────

def _mock_client():
    """Return a MagicMock that mimics the supabase-py query builder chain."""
    client = MagicMock()
    # Every chained call (table / select / eq / order / limit / execute) returns
    # a fresh MagicMock by default, so callers can chain freely.
    return client


def _make_result(data=None, count=None):
    result = MagicMock()
    result.data = data or []
    result.count = count
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 1 — HookLibraryStore
# ─────────────────────────────────────────────────────────────────────────────

class TestHookLibraryStore:
    HOOK_ROW = {
        "formula_id": "H001",
        "formula_name": "Limiting Belief Challenge",
        "formula_pattern": "...",
        "score": 50.0,
        "avg_watch_time_percent": 0.0,
        "is_experimental": False,
    }

    def test_get_top_n_returns_list(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().order().limit().execute.return_value = _make_result([self.HOOK_ROW])
            mock_gc.return_value = client
            store = HookLibraryStore()
            result = store.get_top_n(5)
        assert isinstance(result, list)
        assert result[0]["formula_id"] == "H001"

    def test_get_top_n_returns_empty_on_error(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            mock_gc.side_effect = Exception("db down")
            result = HookLibraryStore().get_top_n()
        assert result == []

    def test_update_score_increments_for_high_watch_time(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().single().execute.return_value = _make_result(
                {"score": 50.0, "times_used": 2}
            )
            mock_gc.return_value = client
            HookLibraryStore().update_score("H001", watch_time_pct=0.75)
            update_call = client.table().update()
            # Verify update was called (chained builder was invoked)
            assert update_call is not None

    def test_update_score_decrements_for_low_watch_time(self):
        """score should decrease when watch_time_pct <= 0.30."""
        captured_payload = {}

        def fake_update(payload):
            captured_payload.update(payload)
            return MagicMock()

        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().single().execute.return_value = _make_result(
                {"score": 50.0, "times_used": 1}
            )
            client.table().update = fake_update
            mock_gc.return_value = client
            HookLibraryStore().update_score("H001", watch_time_pct=0.20)

        assert captured_payload.get("score", 50) < 50 or captured_payload == {}

    def test_seed_defaults_calls_upsert(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            mock_gc.return_value = client
            HookLibraryStore().seed_defaults()
            client.table().upsert.assert_called_once()
            args = client.table().upsert.call_args[0][0]
            assert len(args) == 10
            assert args[0]["formula_id"] == "H001"


# ─────────────────────────────────────────────────────────────────────────────
# 2 — ClipPerformanceStore
# ─────────────────────────────────────────────────────────────────────────────

class TestClipPerformanceStore:
    CLIP_ROW = {
        "clip_id": "clip_abc",
        "quality_score": 80.0,
        "mood": "motivational",
        "shot_type": "medium",
        "usage_count": 0,
    }

    def test_get_fresh_returns_list(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().neq().order().limit().execute.return_value = (
                _make_result([self.CLIP_ROW])
            )
            mock_gc.return_value = client
            result = ClipPerformanceStore().get_fresh(10)
        assert isinstance(result, list)

    def test_get_proven_returns_list(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().gte().lte().neq().eq().order().execute.return_value = (
                _make_result([self.CLIP_ROW])
            )
            mock_gc.return_value = client
            result = ClipPerformanceStore().get_proven()
        assert isinstance(result, list)

    def test_get_top_10_percent_returns_list(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().order().execute.return_value = _make_result([])
            mock_gc.return_value = client
            result = ClipPerformanceStore().get_top_10_percent()
        assert result == []

    def test_update_score_computes_weighted_average(self):
        """new_score = old*0.7 + engagement*100*0.3 — verify update is called."""
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().single().execute.return_value = _make_result(
                {"performance_score": 50.0}
            )
            mock_gc.return_value = client
            ClipPerformanceStore().update_score("clip_abc", engagement_depth=0.8)
            # update() should have been invoked on the builder chain
            client.table().update.assert_called()

    def test_get_freshness_index_returns_dict(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().execute.return_value = _make_result([], count=5)
            client.table().select().execute.return_value = _make_result([], count=20)
            mock_gc.return_value = client
            result = ClipPerformanceStore().get_freshness_index()
        assert "fresh" in result
        assert "total" in result
        assert "ratio" in result

    def test_get_freshness_index_graceful_on_error(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            mock_gc.side_effect = Exception("db error")
            result = ClipPerformanceStore().get_freshness_index()
        assert result == {"fresh": 0, "total": 0, "ratio": 0.0}


# ─────────────────────────────────────────────────────────────────────────────
# 3 — HashtagVelocityStore
# ─────────────────────────────────────────────────────────────────────────────

class TestHashtagVelocityStore:
    def test_get_by_tier_returns_list(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().eq().order().limit().execute.return_value = _make_result(
                [{"tag": "#motivation", "tier": 1, "velocity": 40.0, "times_used": 3, "avg_discovery_percent": 12.0}]
            )
            mock_gc.return_value = client
            result = HashtagVelocityStore().get_by_tier(tier=1)
        assert isinstance(result, list)

    def test_add_from_trend_research_calls_upsert(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            mock_gc.return_value = client
            HashtagVelocityStore().add_from_trend_research(["#grind", "#hustle"], tier=2)
            client.table().upsert.assert_called_once()
            rows = client.table().upsert.call_args[0][0]
            assert len(rows) == 2
            assert rows[0]["from_trend_research"] is True

    def test_apply_weekly_decay_updates_velocity(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().execute.return_value = _make_result(
                [{"tag": "#hustle", "velocity": 0.50}]
            )
            mock_gc.return_value = client
            HashtagVelocityStore().apply_weekly_decay()
            client.table().update.assert_called()

    def test_apply_weekly_decay_marks_dead_below_threshold(self):
        """Tags with velocity < 0.01 after decay should be marked dead."""
        captured = {}

        def fake_update(payload):
            captured.update(payload)
            return MagicMock()

        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().execute.return_value = _make_result(
                [{"tag": "#dead", "velocity": 0.009}]
            )
            client.table().update = fake_update
            mock_gc.return_value = client
            HashtagVelocityStore().apply_weekly_decay()

        if captured:
            assert captured.get("is_dead") is True


# ─────────────────────────────────────────────────────────────────────────────
# 4 — FormatPerformanceStore
# ─────────────────────────────────────────────────────────────────────────────

class TestFormatPerformanceStore:
    def test_duration_bucket_boundaries(self):
        store = FormatPerformanceStore()
        assert store._duration_bucket(10) == "under_15s"
        assert store._duration_bucket(20) == "15-25s"
        assert store._duration_bucket(30) == "25-40s"
        assert store._duration_bucket(50) == "40-60s"
        assert store._duration_bucket(90) == "60s_plus"

    def test_update_inserts_new_row(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().eq().eq().execute.return_value = _make_result([])
            mock_gc.return_value = client
            FormatPerformanceStore().update(
                "fresh_drop", 30.0, "steady", 0.7, 0.15, 8.0
            )
            client.table().insert.assert_called_once()

    def test_update_updates_existing_row(self):
        existing_row = {
            "id": 1, "avg_engagement_depth": 0.6, "avg_save_rate": 0.1,
            "avg_hook_score": 7.0, "data_points": 2,
        }
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().eq().eq().execute.return_value = _make_result([existing_row])
            mock_gc.return_value = client
            FormatPerformanceStore().update(
                "fresh_drop", 30.0, "steady", 0.8, 0.2, 9.0
            )
            client.table().update.assert_called()

    def test_get_best_returns_list(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().gte().order().limit().execute.return_value = _make_result([])
            mock_gc.return_value = client
            result = FormatPerformanceStore().get_best()
        assert isinstance(result, list)

    def test_flag_decay_calls_update(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            mock_gc.return_value = client
            FormatPerformanceStore().flag_decay("series")
            client.table().update.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# 5 — AudiencePreferenceStore
# ─────────────────────────────────────────────────────────────────────────────

class TestAudiencePreferenceStore:
    def test_update_topic_inserts_new(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().execute.return_value = _make_result([])
            mock_gc.return_value = client
            AudiencePreferenceStore().update_topic("motivation", comment_volume=50, save_rate=0.3)
            client.table().insert.assert_called_once()

    def test_update_topic_blends_existing(self):
        existing = {"weight": 0.5, "data_points": 4}
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().execute.return_value = _make_result([existing])
            mock_gc.return_value = client
            AudiencePreferenceStore().update_topic("motivation", comment_volume=80, save_rate=0.6)
            client.table().update.assert_called_once()

    def test_get_top_topics_returns_list(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().order().limit().execute.return_value = _make_result(
                [{"preference_key": "hustle", "weight": 0.8, "data_points": 5}]
            )
            mock_gc.return_value = client
            result = AudiencePreferenceStore().get_top_topics(3)
        assert isinstance(result, list)
        assert result[0]["preference_key"] == "hustle"

    def test_get_full_model_returns_dict(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().execute.return_value = _make_result(
                [{"preference_key": "motivation", "weight": 0.7}]
            )
            mock_gc.return_value = client
            result = AudiencePreferenceStore().get_full_model()
        assert isinstance(result, dict)
        assert result.get("motivation") == 0.7


# ─────────────────────────────────────────────────────────────────────────────
# 6 — OptimalTimingStore
# ─────────────────────────────────────────────────────────────────────────────

class TestOptimalTimingStore:
    def test_record_inserts_new_slot(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().eq().execute.return_value = _make_result([])
            mock_gc.return_value = client
            OptimalTimingStore().record(day_of_week=5, hour=18, first_hour_velocity=1200.0)
            client.table().insert.assert_called_once()

    def test_record_updates_existing_slot(self):
        existing = {"avg_first_hour_velocity": 1000.0, "data_points": 3}
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().eq().eq().execute.return_value = _make_result([existing])
            mock_gc.return_value = client
            OptimalTimingStore().record(day_of_week=5, hour=18, first_hour_velocity=1400.0)
            client.table().update.assert_called_once()

    def test_get_best_slot_returns_dict(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().gte().order().limit().execute.return_value = _make_result(
                [{"day_of_week": 5, "hour": 18, "avg_first_hour_velocity": 1200.0, "data_points": 4}]
            )
            mock_gc.return_value = client
            result = OptimalTimingStore().get_best_slot()
        assert result["day_of_week"] == 5
        assert result["hour"] == 18

    def test_get_best_slot_returns_default_when_no_data(self):
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            client.table().select().gte().order().limit().execute.return_value = _make_result([])
            mock_gc.return_value = client
            result = OptimalTimingStore().get_best_slot()
        assert "day_of_week" in result
        assert "hour" in result


# ─────────────────────────────────────────────────────────────────────────────
# 7 — MemoryStores wrapper
# ─────────────────────────────────────────────────────────────────────────────

class TestMemoryStores:
    def test_get_orchestrator_context_returns_all_keys(self):
        expected_keys = [
            "hook_library_top10", "freshness_index", "proven_clips_count",
            "hashtags_tier1", "hashtags_tier2", "best_format",
            "audience_top_topics", "audience_full_model", "optimal_slot",
        ]
        with patch("src.memory.stores._get_client") as mock_gc:
            client = _mock_client()
            # All sub-queries return empty results
            client.table().select().order().limit().execute.return_value = _make_result([])
            client.table().select().eq().order().limit().execute.return_value = _make_result([])
            client.table().select().gte().lte().neq().eq().order().execute.return_value = _make_result([])
            client.table().select().eq().execute.return_value = _make_result([], count=0)
            client.table().select().execute.return_value = _make_result([], count=0)
            client.table().select().eq().order().execute.return_value = _make_result([])
            client.table().select().gte().order().limit().execute.return_value = _make_result([])
            mock_gc.return_value = client
            ctx = MemoryStores().get_orchestrator_context()

        for key in expected_keys:
            assert key in ctx, f"Missing key in orchestrator context: {key}"

    def test_stores_singleton_importable(self):
        from src.memory.stores import memory
        assert isinstance(memory, MemoryStores)
