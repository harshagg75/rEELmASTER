"""
Tests for Agents 01-06 — all Claude calls and DB calls are mocked.
Run: pytest tests/test_agents.py -v
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.memory.schema import (
    AudioTrend,
    ReelBrief,
    ScriptStoryboard,
    SelectedClip,
    TrendBrief,
    TypedProductionSpec,
)


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def sample_trend_brief() -> TrendBrief:
    return TrendBrief(
        research_date="2026-04-27",
        trending_audios=[
            AudioTrend(
                audio_id="tum-kya-mile-indie",
                title="Tum Kya Mile",
                artist="Lucky Ali",
                style="indie",
                urgency="HIGH",
                reason="Trending on Reels for 3 days, fits reflective mood",
                estimated_days_trending=3,
            )
        ],
        content_themes=["late_night_hustle", "chai_and_dreams", "first_salary"],
        cultural_moments=["Eid in 10 days"],
        overall_urgency="HIGH",
        raw_notes="Short motivational POV formats dominating North India feed",
    )


@pytest.fixture
def sample_reel_brief() -> ReelBrief:
    return ReelBrief(
        target_emotion="pre-leap quiet courage",
        energy_arc="slow_build",
        preferred_shot_types=["close_up", "medium"],
        hook_formula_id="H003",
        hook_formula_hint="Open with a poetic Hindi line about unseen paths",
        color_palette="warm",
        suggested_duration_sec=27,
        audio_hint="soft lo-fi with rising energy, no lyrics",
        opening_line_hint="Kuch raste woh hote hain jo dikhte nahi...",
        clip_mood_preference="contemplative",
        strategic_notes="H003 had highest watch-time last 30 days. Warm palette clips performing well.",
        hook_test_mode=False,
    )


@pytest.fixture
def sample_spec(sample_reel_brief) -> TypedProductionSpec:
    return TypedProductionSpec(
        reel_type="fresh_drop",
        reel_brief=sample_reel_brief,
        selection_reason="2 fresh_drop posts this week, variety needed",
        production_notes="Use only usage_count=0 clips, prefer close_up for first shot",
    )


@pytest.fixture
def sample_selected_clips() -> list[SelectedClip]:
    return [
        SelectedClip(
            clip_id="clip_001",
            file_path="/clips/clip_001.mp4",
            segment_start=0.0,
            segment_end=5.0,
            selection_reason="Close-up with warm light, matches hook mood",
            shot_type="close_up",
            position=1,
        ),
        SelectedClip(
            clip_id="clip_002",
            file_path="/clips/clip_002.mp4",
            segment_start=1.5,
            segment_end=7.5,
            selection_reason="Medium shot, city aesthetic, energy builds",
            shot_type="medium",
            position=2,
        ),
        SelectedClip(
            clip_id="clip_003",
            file_path="/clips/clip_003.mp4",
            segment_start=0.0,
            segment_end=6.0,
            selection_reason="Wide establishing shot, high movement energy",
            shot_type="wide",
            position=3,
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Agent 02 — TrendResearchAgent
# ─────────────────────────────────────────────────────────────────────────────

class TestTrendResearchAgent:
    SAMPLE_RESPONSE = {
        "research_date": "2026-04-27",
        "trending_audios": [
            {
                "audio_id": "tum-kya-mile-indie",
                "title": "Tum Kya Mile",
                "artist": "Lucky Ali",
                "style": "indie",
                "urgency": "HIGH",
                "reason": "Trending for 3 days, fits reflective mood",
                "estimated_days_trending": 3,
            }
        ],
        "content_themes": ["chai_and_dreams", "first_salary", "late_night_study"],
        "cultural_moments": ["Eid in 10 days"],
        "overall_urgency": "HIGH",
        "raw_notes": "POV formats dominating North India feed",
    }

    def test_returns_trend_brief(self):
        with patch("src.agents.trend_research.call_claude_with_search",
                   return_value=json.dumps(self.SAMPLE_RESPONSE)):
            from src.agents.trend_research import TrendResearchAgent
            brief = TrendResearchAgent().run()
        assert isinstance(brief, TrendBrief)
        assert brief.overall_urgency == "HIGH"
        assert len(brief.trending_audios) == 1
        assert brief.trending_audios[0].audio_id == "tum-kya-mile-indie"

    def test_uses_call_claude_with_search(self):
        """Must call call_claude_with_search (web_search tool), not bare call_claude."""
        with patch("src.agents.trend_research.call_claude_with_search",
                   return_value=json.dumps(self.SAMPLE_RESPONSE)) as mock_search:
            from src.agents.trend_research import TrendResearchAgent
            TrendResearchAgent().run()
        mock_search.assert_called_once()

    def test_prompt_includes_today_date(self):
        from datetime import date
        captured = {}

        def fake_search(system, user):
            captured["user"] = user
            return json.dumps(self.SAMPLE_RESPONSE)

        with patch("src.agents.trend_research.call_claude_with_search", side_effect=fake_search):
            from src.agents.trend_research import TrendResearchAgent
            TrendResearchAgent().run()

        assert date.today().isoformat() in captured["user"]

    def test_content_themes_returned(self):
        with patch("src.agents.trend_research.call_claude_with_search",
                   return_value=json.dumps(self.SAMPLE_RESPONSE)):
            from src.agents.trend_research import TrendResearchAgent
            brief = TrendResearchAgent().run()
        assert "chai_and_dreams" in brief.content_themes


# ─────────────────────────────────────────────────────────────────────────────
# Agent 03 — OrchestratorAgent
# ─────────────────────────────────────────────────────────────────────────────

class TestOrchestratorAgent:
    SAMPLE_RESPONSE = {
        "target_emotion": "pre-leap quiet courage",
        "energy_arc": "slow_build",
        "preferred_shot_types": ["close_up", "medium"],
        "hook_formula_id": "H003",
        "hook_formula_hint": "Open with a poetic Hindi line about unseen paths",
        "color_palette": "warm",
        "suggested_duration_sec": 27,
        "audio_hint": "soft lo-fi, no lyrics",
        "opening_line_hint": "Kuch raste woh hote hain jo dikhte nahi...",
        "clip_mood_preference": "contemplative",
        "strategic_notes": "H003 had highest watch-time last 30 days.",
    }

    def _run_agent(self, trend_brief, mock_response=None):
        response = mock_response or self.SAMPLE_RESPONSE
        mem_ctx = {"hook_library_top10": [], "freshness_index": {"fresh": 5, "total": 10, "ratio": 0.5}}

        with patch("src.agents.orchestrator.call_claude", return_value=json.dumps(response)):
            with patch("src.memory.stores.MemoryStores.get_orchestrator_context", return_value=mem_ctx):
                with patch("src.agents.orchestrator.OrchestratorAgent._get_latest_delta", return_value=None):
                    from src.agents.orchestrator import OrchestratorAgent
                    return OrchestratorAgent().run(trend_brief)

    def test_returns_reel_brief(self, sample_trend_brief):
        brief = self._run_agent(sample_trend_brief)
        assert isinstance(brief, ReelBrief)
        assert brief.target_emotion == "pre-leap quiet courage"
        assert brief.energy_arc == "slow_build"

    def test_uses_orchestrator_model(self, sample_trend_brief):
        from src.config import settings as S
        captured = {}

        def fake_claude(system, user, model=None):
            captured["model"] = model
            return json.dumps(self.SAMPLE_RESPONSE)

        mem_ctx = {"hook_library_top10": []}
        with patch("src.agents.orchestrator.call_claude", side_effect=fake_claude):
            with patch("src.memory.stores.MemoryStores.get_orchestrator_context", return_value=mem_ctx):
                with patch("src.agents.orchestrator.OrchestratorAgent._get_latest_delta", return_value=None):
                    from src.agents.orchestrator import OrchestratorAgent
                    OrchestratorAgent().run(sample_trend_brief)

        assert captured["model"] == S.MODEL_ORCHESTRATOR

    def test_hook_test_mode_is_bool(self, sample_trend_brief):
        brief = self._run_agent(sample_trend_brief)
        assert isinstance(brief.hook_test_mode, bool)

    def test_reads_memory_context(self, sample_trend_brief):
        """Verify get_orchestrator_context() is called."""
        mem_ctx = {"hook_library_top10": [], "freshness_index": {"fresh": 3, "total": 10, "ratio": 0.3}}
        with patch("src.agents.orchestrator.call_claude", return_value=json.dumps(self.SAMPLE_RESPONSE)):
            with patch("src.memory.stores.MemoryStores.get_orchestrator_context",
                       return_value=mem_ctx) as mock_ctx:
                with patch("src.agents.orchestrator.OrchestratorAgent._get_latest_delta", return_value=None):
                    from src.agents.orchestrator import OrchestratorAgent
                    OrchestratorAgent().run(sample_trend_brief)
        mock_ctx.assert_called_once()

    def test_delta_included_in_prompt(self, sample_trend_brief):
        delta = {"post_id": "test_post", "performance_summary": "Strong save rate"}
        captured = {}

        def fake_claude(system, user, model=None):
            captured["user"] = user
            return json.dumps(self.SAMPLE_RESPONSE)

        mem_ctx = {"hook_library_top10": []}
        with patch("src.agents.orchestrator.call_claude", side_effect=fake_claude):
            with patch("src.memory.stores.MemoryStores.get_orchestrator_context", return_value=mem_ctx):
                with patch("src.agents.orchestrator.OrchestratorAgent._get_latest_delta", return_value=delta):
                    from src.agents.orchestrator import OrchestratorAgent
                    OrchestratorAgent().run(sample_trend_brief)

        assert "Strong save rate" in captured["user"]


# ─────────────────────────────────────────────────────────────────────────────
# Agent 04 — TypeSelectorAgent
# ─────────────────────────────────────────────────────────────────────────────

class TestTypeSelectorAgent:
    SAMPLE_RESPONSE = {
        "reel_type": "fresh_drop",
        "selection_reason": "Strong fresh clip inventory and no fresh_drop in last 3 posts",
        "source_reel_id": None,
        "series_id": None,
        "episode_number": None,
        "audio_id": None,
        "production_notes": "Use only usage_count=0 clips. Prefer close_up for first shot.",
    }

    def _run_agent(self, reel_brief, trend_brief, last_10=None, **kwargs):
        last_10 = last_10 or ["hybrid_mix", "series", "concept_remix"]
        with patch("src.agents.type_selector.call_claude", return_value=json.dumps(self.SAMPLE_RESPONSE)):
            from src.agents.type_selector import TypeSelectorAgent
            return TypeSelectorAgent().run(
                reel_brief, trend_brief, last_10, **kwargs
            )

    def test_returns_typed_production_spec(self, sample_reel_brief, sample_trend_brief):
        spec = self._run_agent(sample_reel_brief, sample_trend_brief)
        assert isinstance(spec, TypedProductionSpec)
        assert spec.reel_type == "fresh_drop"

    def test_reel_brief_embedded_in_spec(self, sample_reel_brief, sample_trend_brief):
        spec = self._run_agent(sample_reel_brief, sample_trend_brief)
        assert spec.reel_brief.hook_formula_id == sample_reel_brief.hook_formula_id

    def test_trend_surfer_blocked_when_not_high_urgency(self, sample_reel_brief):
        """trend_surfer_allowed should be False when urgency is MEDIUM."""
        from src.agents.type_selector import TypeSelectorAgent
        low_urgency_trend = TrendBrief(
            research_date="2026-04-27",
            trending_audios=[
                AudioTrend(
                    audio_id="old-track",
                    title="Old Track",
                    artist="Various",
                    style="bollywood",
                    urgency="MEDIUM",
                    reason="stable but not urgent",
                    estimated_days_trending=10,
                )
            ],
            content_themes=["generic"],
            cultural_moments=[],
            overall_urgency="MEDIUM",
            raw_notes="",
        )
        agent = TypeSelectorAgent()
        constraints = agent._evaluate_constraints(
            trend_brief=low_urgency_trend,
            last_10_reel_types=[],
            milestone_trigger=False,
            days_since_last_best_of=10,
            active_series_count=0,
            past_reels_available_for_remix=True,
        )
        assert constraints["trend_surfer_allowed"] is False

    def test_best_of_blocked_without_milestone_or_days(self, sample_reel_brief, sample_trend_brief):
        from src.agents.type_selector import TypeSelectorAgent
        agent = TypeSelectorAgent()
        constraints = agent._evaluate_constraints(
            trend_brief=sample_trend_brief,
            last_10_reel_types=[],
            milestone_trigger=False,
            days_since_last_best_of=10,  # less than 28
            active_series_count=0,
            past_reels_available_for_remix=True,
        )
        assert constraints["best_of_allowed"] is False

    def test_best_of_allowed_with_milestone(self, sample_reel_brief, sample_trend_brief):
        from src.agents.type_selector import TypeSelectorAgent
        agent = TypeSelectorAgent()
        constraints = agent._evaluate_constraints(
            trend_brief=sample_trend_brief,
            last_10_reel_types=[],
            milestone_trigger=True,
            days_since_last_best_of=5,
            active_series_count=0,
            past_reels_available_for_remix=True,
        )
        assert constraints["best_of_allowed"] is True

    def test_same_type_3_in_row_detected(self, sample_reel_brief, sample_trend_brief):
        from src.agents.type_selector import TypeSelectorAgent
        agent = TypeSelectorAgent()
        constraints = agent._evaluate_constraints(
            trend_brief=sample_trend_brief,
            last_10_reel_types=["hybrid_mix", "hybrid_mix", "hybrid_mix"],
            milestone_trigger=False,
            days_since_last_best_of=99,
            active_series_count=0,
            past_reels_available_for_remix=True,
        )
        assert constraints["same_type_3_in_row"] is True
        assert constraints["blocked_type"] == "hybrid_mix"

    def test_series_blocked_when_2_active(self, sample_reel_brief, sample_trend_brief):
        from src.agents.type_selector import TypeSelectorAgent
        agent = TypeSelectorAgent()
        constraints = agent._evaluate_constraints(
            trend_brief=sample_trend_brief,
            last_10_reel_types=[],
            milestone_trigger=False,
            days_since_last_best_of=99,
            active_series_count=2,
            past_reels_available_for_remix=True,
        )
        assert constraints["series_allowed"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Agent 05 — ClipSelectionAgent
# ─────────────────────────────────────────────────────────────────────────────

class TestClipSelectionAgent:
    SAMPLE_CLIPS_RESPONSE = {
        "selected_clips": [
            {
                "clip_id": "clip_001",
                "file_path": "/clips/clip_001.mp4",
                "segment_start": 0.0,
                "segment_end": 5.0,
                "selection_reason": "Perfect warm close-up for hook",
                "shot_type": "close_up",
                "position": 1,
            },
            {
                "clip_id": "clip_002",
                "file_path": "/clips/clip_002.mp4",
                "segment_start": 1.5,
                "segment_end": 7.0,
                "selection_reason": "Medium shot, energy builds",
                "shot_type": "medium",
                "position": 2,
            },
            {
                "clip_id": "clip_003",
                "file_path": "/clips/clip_003.mp4",
                "segment_start": 0.0,
                "segment_end": 6.0,
                "selection_reason": "Wide, strong energy arc endpoint",
                "shot_type": "wide",
                "position": 3,
            },
        ],
        "total_duration_sec": 17.5,
        "selection_notes": "All fresh clips, energy arc ascending as briefed",
    }

    CANDIDATE_CLIPS = [
        {
            "clip_id": "clip_001", "shot_type": "close_up", "mood": "contemplative",
            "emotion_tags": ["reflective", "determined"], "scene_tags": ["window_light"],
            "quality_score": 82.0, "quality_flag": "usable", "performance_score": 50.0,
            "usage_count": 0, "performance_tier": "average",
            "usable_segments": [{"start_sec": 0.0, "end_sec": 5.0}],
            "file_path": "/clips/clip_001.mp4",
        },
        {
            "clip_id": "clip_002", "shot_type": "medium", "mood": "motivational",
            "emotion_tags": ["ambitious"], "scene_tags": ["city_walk"],
            "quality_score": 75.0, "quality_flag": "usable", "performance_score": 50.0,
            "usage_count": 0, "performance_tier": "average",
            "usable_segments": [{"start_sec": 1.5, "end_sec": 7.0}],
            "file_path": "/clips/clip_002.mp4",
        },
        {
            "clip_id": "clip_003", "shot_type": "wide", "mood": "aspirational",
            "emotion_tags": ["inspired"], "scene_tags": ["rooftop"],
            "quality_score": 78.0, "quality_flag": "usable", "performance_score": 50.0,
            "usage_count": 0, "performance_tier": "average",
            "usable_segments": [{"start_sec": 0.0, "end_sec": 6.0}],
            "file_path": "/clips/clip_003.mp4",
        },
    ]

    def test_returns_list_of_selected_clips(self, sample_spec):
        with patch("src.agents.clip_selection.call_claude",
                   return_value=json.dumps(self.SAMPLE_CLIPS_RESPONSE)):
            with patch("src.tools.vector_db.VectorDB.similarity_search",
                       return_value=self.CANDIDATE_CLIPS):
                from src.agents.clip_selection import ClipSelectionAgent
                clips = ClipSelectionAgent().run(sample_spec)
        assert isinstance(clips, list)
        assert len(clips) == 3
        assert all(isinstance(c, SelectedClip) for c in clips)

    def test_clips_have_correct_positions(self, sample_spec):
        with patch("src.agents.clip_selection.call_claude",
                   return_value=json.dumps(self.SAMPLE_CLIPS_RESPONSE)):
            with patch("src.tools.vector_db.VectorDB.similarity_search",
                       return_value=self.CANDIDATE_CLIPS):
                from src.agents.clip_selection import ClipSelectionAgent
                clips = ClipSelectionAgent().run(sample_spec)
        positions = [c.position for c in clips]
        assert positions == [1, 2, 3]

    def test_raises_when_no_candidates(self, sample_spec):
        with patch("src.tools.vector_db.VectorDB.similarity_search", return_value=[]):
            from src.agents.clip_selection import ClipSelectionAgent
            with pytest.raises(ValueError, match="No candidate clips"):
                ClipSelectionAgent().run(sample_spec)

    def test_interleave_alternates_proven_fresh(self):
        from src.agents.clip_selection import ClipSelectionAgent
        proven = [{"clip_id": f"proven_{i}"} for i in range(3)]
        fresh = [{"clip_id": f"fresh_{i}"} for i in range(3)]
        result = ClipSelectionAgent._interleave(proven, fresh)
        assert result[0]["clip_id"] == "proven_0"
        assert result[1]["clip_id"] == "fresh_0"
        assert result[2]["clip_id"] == "proven_1"
        assert result[3]["clip_id"] == "fresh_1"

    def test_fresh_drop_queries_usage_count_zero(self, sample_spec):
        captured = {}

        def fake_search(query_text, limit=20, filters=None):
            captured["filters"] = filters
            return self.CANDIDATE_CLIPS

        with patch("src.tools.vector_db.VectorDB.similarity_search", side_effect=fake_search):
            with patch("src.agents.clip_selection.call_claude",
                       return_value=json.dumps(self.SAMPLE_CLIPS_RESPONSE)):
                from src.agents.clip_selection import ClipSelectionAgent
                ClipSelectionAgent().run(sample_spec)

        assert captured.get("filters", {}).get("usage_count") == 0


# ─────────────────────────────────────────────────────────────────────────────
# Agent 06 — ScriptAgent
# ─────────────────────────────────────────────────────────────────────────────

class TestScriptAgent:
    SAMPLE_STORYBOARD = {
        "hook_formula_id": "H003",
        "hook_formula_name": "Soft Hindi Poetry Opener",
        "hook_text": "Kuch raste woh hote hain jo dikhte nahi — feel hote hain.",
        "is_experimental": False,
        "shots": [
            {
                "shot_number": 1,
                "clip_id": "clip_001",
                "segment_start": 0.0,
                "segment_end": 4.0,
                "duration_sec": 4.0,
                "voiceover_text": "Kuch raste woh hote hain jo dikhte nahi...",
                "on_screen_text": "Kuch raste feel hote hain",
                "transition_out": "fade",
                "shot_note": "Hook delivery on close-up with warm light",
            },
            {
                "shot_number": 2,
                "clip_id": "clip_002",
                "segment_start": 1.5,
                "segment_end": 7.0,
                "duration_sec": 5.5,
                "voiceover_text": "Tune apne aap ko rok ke rakha hai.",
                "on_screen_text": None,
                "transition_out": "cut",
                "shot_note": "Energy builds — medium shot city walk",
            },
            {
                "shot_number": 3,
                "clip_id": "clip_003",
                "segment_start": 0.0,
                "segment_end": 6.0,
                "duration_sec": 6.0,
                "voiceover_text": "Ab kuch alag karne ka waqt hai.",
                "on_screen_text": "You are not behind.",
                "transition_out": "none",
                "shot_note": "Resolution — wide rooftop shot, high energy",
            },
        ],
        "total_duration_sec": 15.5,
        "audio_note": "Soft lo-fi, no lyrics, rising energy in final 5s",
        "emotional_arc_note": "Quiet reflection → challenge → resolution",
        "series_continuity_note": None,
    }

    SAMPLE_STORYBOARD_EXPERIMENTAL = {
        **SAMPLE_STORYBOARD,
        "hook_formula_id": "new",
        "hook_formula_name": "The Midnight Confession",
        "hook_text": "2 baje sochte hain woh jo 8 baje bolne ki himmat nahi hoti.",
        "is_experimental": True,
    }

    def test_returns_script_storyboard(self, sample_spec, sample_selected_clips):
        with patch("src.agents.script.call_claude",
                   return_value=json.dumps(self.SAMPLE_STORYBOARD)):
            with patch("src.memory.stores.HookLibraryStore.get_top_n", return_value=[]):
                from src.agents.script import ScriptAgent
                storyboard = ScriptAgent().run(sample_spec, sample_selected_clips)
        assert isinstance(storyboard, ScriptStoryboard)
        assert storyboard.hook_formula_id == "H003"
        assert len(storyboard.shots) == 3

    def test_hook_text_not_empty(self, sample_spec, sample_selected_clips):
        with patch("src.agents.script.call_claude",
                   return_value=json.dumps(self.SAMPLE_STORYBOARD)):
            with patch("src.memory.stores.HookLibraryStore.get_top_n", return_value=[]):
                from src.agents.script import ScriptAgent
                storyboard = ScriptAgent().run(sample_spec, sample_selected_clips)
        assert len(storyboard.hook_text) > 10

    def test_hook_test_mode_sets_experimental_flag(self, sample_spec, sample_selected_clips):
        """When hook_test_mode=True, is_experimental must be True in the output."""
        spec_with_test = TypedProductionSpec(
            reel_type="fresh_drop",
            reel_brief=ReelBrief(
                **{**sample_spec.reel_brief.model_dump(), "hook_test_mode": True}
            ),
            selection_reason="test",
            production_notes="test",
        )
        with patch("src.agents.script.call_claude",
                   return_value=json.dumps(self.SAMPLE_STORYBOARD_EXPERIMENTAL)):
            with patch("src.memory.stores.HookLibraryStore.get_top_n", return_value=[]):
                from src.agents.script import ScriptAgent
                storyboard = ScriptAgent().run(spec_with_test, sample_selected_clips)
        assert storyboard.is_experimental is True
        assert storyboard.hook_formula_id == "new"

    def test_hook_test_mode_prompt_mentions_invention(self, sample_spec, sample_selected_clips):
        """When hook_test_mode=True, the prompt must tell Claude to invent a new formula."""
        spec_with_test = TypedProductionSpec(
            reel_type="fresh_drop",
            reel_brief=ReelBrief(
                **{**sample_spec.reel_brief.model_dump(), "hook_test_mode": True}
            ),
            selection_reason="test",
            production_notes="test",
        )
        captured = {}

        def fake_claude(system, user, model=None):
            captured["user"] = user
            return json.dumps(self.SAMPLE_STORYBOARD_EXPERIMENTAL)

        with patch("src.agents.script.call_claude", side_effect=fake_claude):
            with patch("src.memory.stores.HookLibraryStore.get_top_n", return_value=[]):
                from src.agents.script import ScriptAgent
                ScriptAgent().run(spec_with_test, sample_selected_clips)

        assert "HOOK TEST MODE IS ACTIVE" in captured["user"]
        assert "is_experimental = true" in captured["user"]

    def test_concept_remix_prompt_mentions_reframe(self, sample_selected_clips, sample_reel_brief):
        """concept_remix reel type should include the reframe instruction in the prompt."""
        remix_spec = TypedProductionSpec(
            reel_type="concept_remix",
            reel_brief=sample_reel_brief,
            selection_reason="remix test",
            source_reel_id="prev_reel_001",
            production_notes="Edit style must differ from source",
        )
        captured = {}

        def fake_claude(system, user, model=None):
            captured["user"] = user
            return json.dumps(self.SAMPLE_STORYBOARD)

        with patch("src.agents.script.call_claude", side_effect=fake_claude):
            with patch("src.memory.stores.HookLibraryStore.get_top_n", return_value=[]):
                from src.agents.script import ScriptAgent
                ScriptAgent().run(remix_spec, sample_selected_clips)

        assert "CONCEPT REMIX RULES" in captured["user"]
        assert "COMPLETELY DIFFERENT story" in captured["user"]

    def test_series_prompt_references_episodes(self, sample_selected_clips, sample_reel_brief):
        """Series reel should include episode N-1 and N+1 references in the prompt."""
        series_storyboard = {**self.SAMPLE_STORYBOARD, "series_continuity_note": "Referenced ep 2, planted ep 4"}
        series_spec = TypedProductionSpec(
            reel_type="series",
            reel_brief=sample_reel_brief,
            selection_reason="series episode 3",
            series_id="series_ambition_001",
            episode_number=3,
            production_notes="Episode 3 of Ambition series",
        )
        captured = {}

        def fake_claude(system, user, model=None):
            captured["user"] = user
            return json.dumps(series_storyboard)

        with patch("src.agents.script.call_claude", side_effect=fake_claude):
            with patch("src.memory.stores.HookLibraryStore.get_top_n", return_value=[]):
                from src.agents.script import ScriptAgent
                storyboard = ScriptAgent().run(series_spec, sample_selected_clips)

        assert "SERIES RULES" in captured["user"]
        assert "episode 2" in captured["user"]
        assert "episode 4" in captured["user"]
        assert storyboard.series_continuity_note is not None

    def test_reads_hook_library(self, sample_spec, sample_selected_clips):
        """get_top_n(10) must be called to fetch hook library context."""
        with patch("src.agents.script.call_claude",
                   return_value=json.dumps(self.SAMPLE_STORYBOARD)):
            with patch("src.memory.stores.HookLibraryStore.get_top_n",
                       return_value=[]) as mock_hooks:
                from src.agents.script import ScriptAgent
                ScriptAgent().run(sample_spec, sample_selected_clips)
        mock_hooks.assert_called_once_with(10)
