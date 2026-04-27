import json

from loguru import logger

from src.config import prompts as P
from src.config import settings as S
from src.memory.schema import ReelBrief, TrendBrief, TypedProductionSpec
from src.tools.claude_client import call_claude, parse_json_response


class TypeSelectorAgent:
    """
    Agent 04 — Type Selector.
    Enforces all 6 hard rules before handing off to Claude for the final selection.
    """

    def run(
        self,
        reel_brief: ReelBrief,
        trend_brief: TrendBrief,
        last_10_reel_types: list[str],
        milestone_trigger: bool = False,
        days_since_last_best_of: int = 999,
        active_series_count: int = 0,
        past_reels_available_for_remix: bool = True,
    ) -> TypedProductionSpec:
        logger.info("[TypeSelector] Selecting reel type...")

        constraints = self._evaluate_constraints(
            trend_brief=trend_brief,
            last_10_reel_types=last_10_reel_types,
            milestone_trigger=milestone_trigger,
            days_since_last_best_of=days_since_last_best_of,
            active_series_count=active_series_count,
            past_reels_available_for_remix=past_reels_available_for_remix,
        )
        user_msg = self._build_prompt(
            reel_brief, trend_brief, last_10_reel_types, constraints
        )

        try:
            raw = call_claude(P.TYPE_SELECTOR_PROMPT, user_msg, model=S.MODEL_AGENT)
            data = parse_json_response(raw)
        except Exception as e:
            logger.error(f"[TypeSelector] Claude call failed: {e}")
            raise

        data["reel_brief"] = reel_brief.model_dump()
        spec = TypedProductionSpec(**data)
        logger.success(f"[TypeSelector] Selected type={spec.reel_type} | {spec.selection_reason}")
        return spec

    # ── Private helpers ────────────────────────────────────────────────────────

    def _evaluate_constraints(
        self,
        trend_brief: TrendBrief,
        last_10_reel_types: list[str],
        milestone_trigger: bool,
        days_since_last_best_of: int,
        active_series_count: int,
        past_reels_available_for_remix: bool,
    ) -> dict:
        """Compute which types are currently allowed per the hard rules."""
        last_3 = last_10_reel_types[-3:] if len(last_10_reel_types) >= 3 else []
        return {
            "trend_surfer_allowed": trend_brief.overall_urgency == "HIGH",
            "best_of_allowed": milestone_trigger or days_since_last_best_of >= 28,
            "series_allowed": active_series_count < 2,
            "concept_remix_allowed": past_reels_available_for_remix,
            "same_type_3_in_row": len(last_3) == 3 and len(set(last_3)) == 1,
            "blocked_type": last_3[-1] if (len(last_3) == 3 and len(set(last_3)) == 1) else None,
            "last_3_types": last_3,
            "overall_urgency": trend_brief.overall_urgency,
            "high_urgency_audio": [
                a.audio_id for a in trend_brief.trending_audios if a.urgency == "HIGH"
            ],
        }

    def _build_prompt(
        self,
        reel_brief: ReelBrief,
        trend_brief: TrendBrief,
        last_10_reel_types: list[str],
        constraints: dict,
    ) -> str:
        c = constraints
        return (
            f"reel_brief:\n{reel_brief.model_dump_json(indent=2)}\n\n"
            f"trend_brief_summary:\n"
            f"  overall_urgency: {trend_brief.overall_urgency}\n"
            f"  high_urgency_audios: {c['high_urgency_audio']}\n"
            f"  content_themes: {trend_brief.content_themes}\n\n"
            f"last_10_reel_types: {json.dumps(last_10_reel_types)}\n\n"
            f"constraint_evaluation:\n{json.dumps(c, indent=2)}\n\n"
            f"HARD RULES REMINDER:\n"
            f"- trend_surfer_allowed: {c['trend_surfer_allowed']} (requires urgency=HIGH)\n"
            f"- best_of_allowed: {c['best_of_allowed']} (requires milestone OR 28+ days)\n"
            f"- series_allowed: {c['series_allowed']} (requires active_series_count < 2)\n"
            f"- concept_remix_allowed: {c['concept_remix_allowed']}\n"
            f"- If same_type_3_in_row=True: DO NOT select '{c['blocked_type']}'\n\n"
            "Select the best reel type and return the JSON TypedProductionSpec."
        )
