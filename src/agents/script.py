import json

from loguru import logger

from src.config import prompts as P
from src.config import settings as S
from src.memory.schema import ScriptStoryboard, SelectedClip, TypedProductionSpec
from src.tools.claude_client import call_claude, parse_json_response


class ScriptAgent:
    """
    Agent 06 — Script & Storyboard.
    Reads hook library top-10. Handles concept_remix and series special cases.
    If hook_test_mode=True, instructs Claude to invent a new experimental formula.
    """

    def run(self, spec: TypedProductionSpec, selected_clips: list[SelectedClip]) -> ScriptStoryboard:
        logger.info(f"[Script] Writing script | type={spec.reel_type} | clips={len(selected_clips)}")

        hook_library = self._get_hook_library()
        user_msg = self._build_prompt(spec, selected_clips, hook_library)

        try:
            raw = call_claude(P.SCRIPT_PROMPT, user_msg, model=S.MODEL_AGENT)
            data = parse_json_response(raw)
        except Exception as e:
            logger.error(f"[Script] Claude call failed: {e}")
            raise

        storyboard = ScriptStoryboard(**data)
        logger.success(
            f"[Script] Script ready | hook={storyboard.hook_formula_id} | "
            f"shots={len(storyboard.shots)} | duration={storyboard.total_duration_sec}s | "
            f"experimental={storyboard.is_experimental}"
        )
        return storyboard

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_hook_library(self) -> list[dict]:
        try:
            from src.memory.stores import memory
            return memory.hooks.get_top_n(10)
        except Exception as e:
            logger.warning(f"[Script] Could not fetch hook library: {e}")
            return []

    def _build_prompt(
        self,
        spec: TypedProductionSpec,
        selected_clips: list[SelectedClip],
        hook_library: list[dict],
    ) -> str:
        brief = spec.reel_brief
        hook_test_mode = brief.hook_test_mode

        clips_json = json.dumps([c.model_dump() for c in selected_clips], indent=2)
        hooks_json = json.dumps(hook_library, indent=2) if hook_library else "[]"

        # Base prompt
        parts = [
            f"reel_type: {spec.reel_type}",
            f"production_notes: {spec.production_notes}",
            f"reel_brief:\n{brief.model_dump_json(indent=2)}",
            f"selected_clips:\n{clips_json}",
            f"hook_library_top10:\n{hooks_json}",
            f"hook_test_mode: {hook_test_mode}",
        ]

        # hook_test_mode special instruction
        if hook_test_mode:
            parts.append(
                "\nHOOK TEST MODE IS ACTIVE: Do NOT use an existing hook formula. "
                "Invent a completely new formula. Give it a descriptive name. "
                "Set hook_formula_id = 'new' and is_experimental = true. "
                "The new formula should be a pattern not seen in the hook_library above."
            )
        else:
            parts.append(
                f"\nUse the hook_formula_id specified in reel_brief: {brief.hook_formula_id}. "
                "Cite which formula you used and why it fits this brief."
            )

        # concept_remix special instruction
        if spec.reel_type == "concept_remix":
            parts.append(
                "\nCONCEPT REMIX RULES: These clips appeared in a previous reel. "
                "Find a COMPLETELY DIFFERENT story they can tell. "
                "The hook MUST reframe what the viewer thinks they're watching — surprise them. "
                "The edit energy must differ from the source reel's edit style."
            )

        # series special instruction
        if spec.reel_type == "series" and spec.episode_number:
            ep = spec.episode_number
            parts.append(
                f"\nSERIES RULES: This is episode {ep}. "
                f"Reference episode {ep-1} summary in the opening 5 seconds. "
                f"Plant a setup for episode {ep+1} in the final 10 seconds. "
                "Fill series_continuity_note with what was referenced and what was planted."
            )

        parts.append("\nReturn the complete JSON ScriptStoryboard.")
        return "\n\n".join(parts)
