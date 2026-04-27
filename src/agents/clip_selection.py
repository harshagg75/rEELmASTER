import json

from loguru import logger

from src.config import prompts as P
from src.config import settings as S
from src.memory.schema import SelectedClip, TypedProductionSpec
from src.tools.claude_client import call_claude, parse_json_response
from src.tools.vector_db import VectorDB


class ClipSelectionAgent:
    """
    Agent 05 — Clip Selection.
    Fetches candidates from Supabase using type-specific queries, then asks Claude
    to select and order 4-8 clips that match the brief.
    """

    def __init__(self) -> None:
        self.db = VectorDB()

    def run(self, spec: TypedProductionSpec) -> list[SelectedClip]:
        logger.info(f"[ClipSelection] Selecting clips for type={spec.reel_type}")

        candidates = self._fetch_candidates(spec)
        if not candidates:
            raise ValueError(
                f"[ClipSelection] No candidate clips found for type={spec.reel_type}. "
                "Ingest more clips first."
            )

        user_msg = self._build_prompt(spec, candidates)
        try:
            raw = call_claude(P.CLIP_SELECTION_PROMPT, user_msg, model=S.MODEL_AGENT)
            data = parse_json_response(raw)
        except Exception as e:
            logger.error(f"[ClipSelection] Claude call failed: {e}")
            raise

        clips = [SelectedClip(**c) for c in data["selected_clips"]]
        self._enforce_shot_type_variety(clips)
        logger.success(
            f"[ClipSelection] Selected {len(clips)} clips | "
            f"duration={data.get('total_duration_sec', '?')}s"
        )
        return clips

    # ── Candidate fetching ─────────────────────────────────────────────────────

    def _fetch_candidates(self, spec: TypedProductionSpec) -> list[dict]:
        brief = spec.reel_brief
        query_text = self._build_query_text(brief)

        if spec.reel_type == "fresh_drop":
            return self.db.similarity_search(
                query_text, limit=30,
                filters={"usage_count": 0, "quality_flag": "usable"},
            )

        if spec.reel_type == "best_of":
            return self.db.similarity_search(
                query_text, limit=20,
                filters={"performance_tier": "top_10_percent"},
            )

        if spec.reel_type == "concept_remix":
            return self._fetch_source_reel_clips(spec.source_reel_id)

        if spec.reel_type == "hybrid_mix":
            proven = self.db.similarity_search(
                query_text, limit=15,
                filters={"quality_flag": "usable"},
            )
            # Filter proven by performance_score in Python (RPC doesn't support range filters)
            proven = [c for c in proven if c.get("performance_score", 0) >= 75 and c.get("usage_count", 99) <= 2]
            fresh = self.db.similarity_search(
                query_text, limit=15,
                filters={"usage_count": 0},
            )
            return self._interleave(proven, fresh)

        if spec.reel_type == "trend_surfer":
            return self.db.similarity_search(
                query_text, limit=30,
                filters={"quality_flag": "usable"},
            )

        if spec.reel_type == "series":
            return self._fetch_series_candidates(spec, query_text)

        # Fallback: general search
        return self.db.similarity_search(query_text, limit=30)

    def _fetch_source_reel_clips(self, source_reel_id: str | None) -> list[dict]:
        if not source_reel_id:
            logger.warning("[ClipSelection] concept_remix has no source_reel_id — using general search")
            return self.db.similarity_search("motivational lifestyle", limit=20)
        try:
            from src.memory.stores import _get_client
            res = (
                _get_client()
                .table("post_log")
                .select("clip_ids")
                .eq("post_id", source_reel_id)
                .single()
                .execute()
            )
            clip_ids = res.data.get("clip_ids", []) if res.data else []
            if not clip_ids:
                return []
            client = _get_client()
            clips_res = client.table("clips").select("*").in_("clip_id", clip_ids).execute()
            return clips_res.data or []
        except Exception as e:
            logger.warning(f"[ClipSelection] Could not fetch source reel clips: {e}")
            return []

    def _fetch_series_candidates(self, spec: TypedProductionSpec, query_text: str) -> list[dict]:
        candidates = self.db.similarity_search(query_text, limit=30)
        if not spec.series_id:
            return candidates
        try:
            from src.memory.stores import _get_client
            res = (
                _get_client()
                .table("series_memory")
                .select("clip_ids_used")
                .eq("series_id", spec.series_id)
                .single()
                .execute()
            )
            used_ids = set(res.data.get("clip_ids_used", [])) if res.data else set()
            # Prefer unused clips; keep used ones as fallback
            unused = [c for c in candidates if c["clip_id"] not in used_ids]
            used = [c for c in candidates if c["clip_id"] in used_ids]
            return unused + used
        except Exception as e:
            logger.warning(f"[ClipSelection] Could not check series clip history: {e}")
            return candidates

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_query_text(self, brief) -> str:
        return (
            f"mood: {brief.clip_mood_preference}. "
            f"emotion: {brief.target_emotion}. "
            f"palette: {brief.color_palette}. "
            f"shot types: {', '.join(brief.preferred_shot_types)}."
        )

    @staticmethod
    def _interleave(proven: list[dict], fresh: list[dict]) -> list[dict]:
        """Alternate proven and fresh clips; never 2 proven in a row."""
        result = []
        pi, fi = 0, 0
        while pi < len(proven) or fi < len(fresh):
            if pi < len(proven):
                result.append(proven[pi]); pi += 1
            if fi < len(fresh):
                result.append(fresh[fi]); fi += 1
        return result

    @staticmethod
    def _enforce_shot_type_variety(clips: list[SelectedClip]) -> None:
        """Log a warning if two consecutive clips share the same shot_type."""
        for i in range(len(clips) - 1):
            if clips[i].shot_type == clips[i + 1].shot_type:
                logger.warning(
                    f"[ClipSelection] Consecutive same shot_type '{clips[i].shot_type}' "
                    f"at positions {i+1}-{i+2} — Claude should have avoided this."
                )

    def _build_prompt(self, spec: TypedProductionSpec, candidates: list[dict]) -> str:
        brief = spec.reel_brief
        candidates_summary = json.dumps(
            [
                {
                    "clip_id": c.get("clip_id"),
                    "shot_type": c.get("shot_type"),
                    "mood": c.get("mood"),
                    "emotion_tags": c.get("emotion_tags", []),
                    "scene_tags": c.get("scene_tags", []),
                    "quality_score": c.get("quality_score"),
                    "quality_flag": c.get("quality_flag"),
                    "performance_score": c.get("performance_score", 50),
                    "usage_count": c.get("usage_count", 0),
                    "performance_tier": c.get("performance_tier", "average"),
                    "usable_segments": c.get("usable_segments", []),
                    "file_path": c.get("file_path"),
                }
                for c in candidates[:40]  # cap at 40 to stay in context
            ],
            indent=2,
        )
        return (
            f"reel_type: {spec.reel_type}\n"
            f"production_notes: {spec.production_notes}\n\n"
            f"reel_brief:\n{brief.model_dump_json(indent=2)}\n\n"
            f"candidate_clips ({len(candidates)} available, showing up to 40):\n"
            f"{candidates_summary}\n\n"
            "Select 4-8 clips. Enforce: no two consecutive clips with the same shot_type. "
            "Match the energy_arc with movement_energy ordering. Return the JSON."
        )
