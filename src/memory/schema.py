from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Agent 01 — Clip Ingestion
# ─────────────────────────────────────────────────────────────────────────────

class UsableSegment(BaseModel):
    start_sec: float
    end_sec: float
    note: str


class ClipMetadata(BaseModel):
    clip_id: str
    file_path: str
    quality_score: float
    quality_flag: Literal["usable", "borderline", "reject"]
    shot_type: Literal["close_up", "medium", "wide", "overhead", "selfie", "text_only"]
    movement_energy: int = Field(ge=1, le=10)
    scene_tags: list[str]
    emotion_tags: list[str]
    face_present: bool
    transcript_summary: str
    mood: Literal[
        "motivational", "aesthetic_calm", "energetic",
        "cultural", "aspirational", "contemplative"
    ]
    color_palette: Literal[
        "warm", "cool", "neutral", "vibrant",
        "muted", "golden_hour", "night"
    ]
    usable_segments: list[UsableSegment]
    embedding: list[float] | None = None
    usage_count: int = 0
    performance_score: float = 50.0
    performance_tier: Literal["top_10_percent", "good", "average", "below_average"] = "average"
    last_used_reel_id: str | None = None
    overused_flag: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Agent 02 — Trend Research
# ─────────────────────────────────────────────────────────────────────────────

class AudioTrend(BaseModel):
    audio_id: str
    title: str
    artist: str
    style: Literal["lo_fi", "bollywood", "indie", "motivational_speech", "ambient", "folk"]
    urgency: Literal["HIGH", "MEDIUM", "LOW"]
    reason: str
    estimated_days_trending: int


class TrendBrief(BaseModel):
    research_date: str  # YYYY-MM-DD
    trending_audios: list[AudioTrend]
    content_themes: list[str]
    cultural_moments: list[str]
    overall_urgency: Literal["HIGH", "MEDIUM", "LOW"]
    raw_notes: str


# ─────────────────────────────────────────────────────────────────────────────
# Agent 03 — Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class ReelBrief(BaseModel):
    target_emotion: str
    energy_arc: Literal["slow_build", "steady", "explosive", "melancholic_rise", "peak_to_resolve"]
    preferred_shot_types: list[str]
    hook_formula_id: str
    hook_formula_hint: str
    color_palette: Literal["warm", "cool", "neutral", "vibrant", "muted", "golden_hour", "night"]
    suggested_duration_sec: int = Field(ge=15, le=60)
    audio_hint: str
    opening_line_hint: str
    clip_mood_preference: str
    strategic_notes: str


# ─────────────────────────────────────────────────────────────────────────────
# Agent 04 — Type Selector
# ─────────────────────────────────────────────────────────────────────────────

class TypedProductionSpec(BaseModel):
    reel_type: Literal[
        "fresh_drop", "hybrid_mix", "concept_remix",
        "series", "trend_surfer", "best_of"
    ]
    reel_brief: ReelBrief
    selection_reason: str
    source_reel_id: str | None = None      # concept_remix only
    series_id: str | None = None            # series only
    episode_number: int | None = None       # series only
    audio_id: str | None = None             # trend_surfer only
    production_notes: str


# ─────────────────────────────────────────────────────────────────────────────
# Agent 05 — Clip Selection
# ─────────────────────────────────────────────────────────────────────────────

class SelectedClip(BaseModel):
    clip_id: str
    file_path: str
    segment_start: float
    segment_end: float
    selection_reason: str
    shot_type: str
    position: int  # 1-indexed order in the reel


# ─────────────────────────────────────────────────────────────────────────────
# Agent 06 — Script & Storyboard
# ─────────────────────────────────────────────────────────────────────────────

class ShotInstruction(BaseModel):
    shot_number: int
    clip_id: str
    segment_start: float
    segment_end: float
    duration_sec: float
    voiceover_text: str | None = None
    on_screen_text: str | None = None
    transition_out: Literal["cut", "fade", "slide", "zoom", "none"]
    shot_note: str


class ScriptStoryboard(BaseModel):
    hook_formula_id: str
    hook_formula_name: str
    hook_text: str
    is_experimental: bool = False
    shots: list[ShotInstruction]
    total_duration_sec: float
    audio_note: str
    emotional_arc_note: str
    series_continuity_note: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Agent 07 — Edit Spec
# ─────────────────────────────────────────────────────────────────────────────

class TimelineClip(BaseModel):
    clip_id: str
    file_path: str
    start_sec: float
    end_sec: float
    transition_in: Literal["none", "cut", "fade", "slide"]
    transition_out: Literal["cut", "fade", "slide"]
    speed_factor: float = 1.0
    on_screen_text: str | None = None
    text_position: Literal["center", "top_third", "bottom_third", "bottom_safe"] | None = None
    text_style: Literal["white_shadow", "white_outline", "yellow_bold", "minimal_white"] | None = None


class EditManifest(BaseModel):
    timeline: list[TimelineClip]
    audio_path: str | None = None
    audio_sync_offset_sec: float = 0.0
    target_duration_sec: float
    color_grade: Literal["warm", "golden_hour", "cool", "cinematic", "vibrant", "neutral"]
    aspect_ratio: str = "9:16"
    output_filename: str


# ─────────────────────────────────────────────────────────────────────────────
# Agent 08 — Caption
# ─────────────────────────────────────────────────────────────────────────────

class CaptionVariant(BaseModel):
    variant_id: Literal["A", "B", "C"]
    caption_text: str
    hashtag_tier1: list[str]
    hashtag_tier2: list[str]
    hashtag_tier3: list[str]
    language_mix_note: str


class CaptionPackage(BaseModel):
    variants: list[CaptionVariant]
    recommended_variant: Literal["A", "B", "C"]
    first_comment_hashtags: list[str]
    posting_time_suggestion: str


# ─────────────────────────────────────────────────────────────────────────────
# Agent 09 — QA
# ─────────────────────────────────────────────────────────────────────────────

class QAIssue(BaseModel):
    check_name: Literal[
        "policy", "audio_licensing", "copyright",
        "type_consistency", "caption_energy", "quality_score"
    ]
    passed: bool
    issue: str | None = None
    severity: Literal["low", "medium", "high"] | None = None


class QAReport(BaseModel):
    status: Literal["APPROVED", "REVISION_NEEDED", "HUMAN_REVIEW"]
    overall_score: int = Field(ge=0, le=100)
    checks: list[QAIssue]
    revision_target_agent: Literal[
        "clip_selection", "script", "edit_spec", "caption"
    ] | None = None
    revision_instruction: str | None = None
    revision_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Agent 10 — Notifier
# ─────────────────────────────────────────────────────────────────────────────

class PostMetadata(BaseModel):
    post_id: str                        # UUID generated by notifier
    reel_type: str
    hook_formula_id: str
    clip_ids: list[str]
    audio_id: str | None = None
    caption_variant_used: Literal["A", "B", "C"]
    caption_text: str
    first_comment_text: str
    hashtags_used: list[str]
    edit_style_class: str               # e.g. "warm_slow_build"
    series_id: str | None = None
    episode_number: int | None = None
    output_video_filename: str
    outputs_path: str
    recommended_post_time: str
    pre_post_checklist: list[str]
    agent_notes: str
    brief_text: str                     # written to posting_brief.txt and sent via Telegram
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Agent 11 — Analytics (manual metrics input)
# ─────────────────────────────────────────────────────────────────────────────

class ManualMetrics(BaseModel):
    post_id: str
    checkpoint: Literal["t1h", "t24h", "t7d", "t30d"]
    views: int
    likes: int
    saves: int
    shares: int
    comments_count: int
    follows_gained: int
    reach: int | None = None
    avg_watch_time_percent: float | None = None
    comments_text: str | None = None    # raw pasted comments, used at t7d/t30d


class PerformanceReport(BaseModel):
    post_id: str
    checkpoint: Literal["t1h", "t24h", "t7d", "t30d"]
    hook_score: float
    engagement_depth: float
    save_rate: float
    discovery_percent: float
    performance_tier: Literal["top_10_percent", "good", "average", "below_average"]
    raw_metrics: ManualMetrics
    performance_summary: str
    standout_metric: str
    computed_at: str                    # ISO datetime string


# ─────────────────────────────────────────────────────────────────────────────
# Agent 12 — Audience
# ─────────────────────────────────────────────────────────────────────────────

class AudienceInsights(BaseModel):
    post_id: str
    checkpoint: Literal["t7d", "t30d"]
    top_topics: list[str]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    audience_requests: list[str]
    language_observations: str
    save_share_mentions: int
    actionable_notes: list[str]
    comment_count_analyzed: int


# ─────────────────────────────────────────────────────────────────────────────
# Agent 13 — Learning
# ─────────────────────────────────────────────────────────────────────────────

class OrchestratorDeltaReport(BaseModel):
    post_id: str
    checkpoint: Literal["t1h", "t24h", "t7d", "t30d"]
    updates_applied: list[str]          # names of memory stores updated
    validation_flags: list[str]         # anomalies spotted, or empty
    performance_summary: str
    what_worked: list[str]
    what_didnt: list[str]
    recommended_adjustments: list[str]
    written_at: str                     # ISO datetime string
