import json
import random

from loguru import logger

from src.config import prompts as P
from src.config import settings as S
from src.memory.schema import ReelBrief, TrendBrief
from src.tools.claude_client import call_claude, parse_json_response


class OrchestratorAgent:
    """
    Agent 03 — Orchestrator.
    Uses claude-opus-4-6. Reads ALL 6 memory stores before building the brief.
    Reads the latest orchestrator_delta for continuity.
    Determines hook_test_mode (20% probability) and injects it into ReelBrief.
    """

    def run(self, trend_brief: TrendBrief) -> ReelBrief:
        logger.info("[Orchestrator] Building reel brief...")

        from src.memory.stores import memory
        mem_context = memory.get_orchestrator_context()
        latest_delta = self._get_latest_delta()

        hook_test_mode = random.random() < 0.20
        user_msg = self._build_prompt(trend_brief, mem_context, latest_delta, hook_test_mode)

        try:
            raw = call_claude(P.ORCHESTRATOR_PROMPT, user_msg, model=S.MODEL_ORCHESTRATOR)
            data = parse_json_response(raw)
        except Exception as e:
            logger.error(f"[Orchestrator] Claude call failed: {e}")
            raise

        data["hook_test_mode"] = hook_test_mode
        brief = ReelBrief(**data)
        logger.success(
            f"[Orchestrator] Brief ready | emotion={brief.target_emotion} | "
            f"arc={brief.energy_arc} | hook_test_mode={hook_test_mode}"
        )
        return brief

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_latest_delta(self) -> dict | None:
        try:
            from src.memory.stores import _get_client
            res = (
                _get_client()
                .table("orchestrator_deltas")
                .select("*")
                .order("written_at", desc=True)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception as e:
            logger.warning(f"[Orchestrator] Could not fetch delta report: {e}")
            return None

    def _build_prompt(
        self,
        trend_brief: TrendBrief,
        mem_context: dict,
        latest_delta: dict | None,
        hook_test_mode: bool,
    ) -> str:
        delta_text = (
            json.dumps(latest_delta, indent=2)
            if latest_delta
            else "(no previous delta — this is the first reel)"
        )
        return (
            f"trend_brief:\n{trend_brief.model_dump_json(indent=2)}\n\n"
            f"memory_context:\n{json.dumps(mem_context, indent=2)}\n\n"
            f"latest_delta_report:\n{delta_text}\n\n"
            f"hook_test_mode: {hook_test_mode} "
            f"{'— invent a new experimental hook formula' if hook_test_mode else ''}\n\n"
            "Produce a specific, opinionated ReelBrief as JSON. "
            "The hook_formula_id should be an existing ID from hook_library_top10 or 'new' "
            "if hook_test_mode is True."
        )
