# skills/AGENTS.md

## Goal
13 agents as clean Python classes. Typed input → Claude → typed output.

## Universal Pattern (enforce for all 13)
```python
from src.tools.claude_client import call_claude, parse_json_response
from src.config import prompts as P, settings as S
from src.memory.schema import InputModel, OutputModel

class XAgent:
    def run(self, input: InputModel) -> OutputModel:
        user_msg = self._build_prompt(input)
        raw = call_claude(P.X_AGENT_PROMPT, user_msg, model=S.MODEL_AGENT)
        data = parse_json_response(raw)
        return OutputModel(**data)
    
    def _build_prompt(self, input: InputModel) -> str:
        return f"""
{input.field1}
{input.field2.model_dump_json(indent=2)}
Return complete JSON matching the schema.
"""
```

## claude_client.py must implement
```python
def call_claude(system: str, user: str, model: str = None) -> str:
    # Standard Anthropic API call
    # Returns response text

def call_claude_with_search(system: str, user: str) -> str:
    # Same but with web_search_20250305 tool enabled
    # Extracts text blocks from response

def parse_json_response(raw: str) -> Dict:
    # Strips ```json fences, parses JSON
    # Raises ValueError with helpful message if parsing fails
```

## Per-Agent Special Instructions

**Agent 02 — Trend Research**
Use `call_claude_with_search()`. Always include today's date in the prompt.
Search for trending content in the motivational/lifestyle Hindi-English niche.
Output includes urgency flag per audio: LOW / MEDIUM / HIGH.
HIGH = trend is 0-5 days old and accelerating.

**Agent 03 — Orchestrator (Opus)**
Reads ALL 6 memory stores via `memory.get_orchestrator_context()` before building brief.
Must produce a specific, opinionated brief — not generic direction.
Bad: "make something motivational"
Good: "30-second cinematic reel, hook formula H007, target emotion: quiet determination, warm palette, energy arc: slow-build, audio ID X, prefer 5-8s close-up clips"
Model: S.MODEL_ORCHESTRATOR (claude-opus-4-6)

**Agent 04 — Type Selector**
Hard constraints in prompt:
- Never same type 3 consecutive posts
- trend_surfer ONLY if TrendBrief.overall_urgency = "HIGH"  
- best_of ONLY if milestone_trigger=True OR 28+ days since last best_of
- Max 2 active series (check series_memory table for status='active')

**Agent 05 — Clip Selection**
Build query string from ReelBrief fields for vector similarity search.
Type-specific Supabase filters:
- fresh_drop: `WHERE usage_count = 0 AND quality_score >= 40`
- best_of: `WHERE performance_tier = 'top_10_percent'`
- hybrid_mix: fetch proven + fresh separately, interleave in Python
- concept_remix: fetch clip_ids from post_log for source_reel_id
Enforce: no two consecutive clips with same shot_type in the ordered selection.

**Agent 06 — Script**
Pass Hook Library top-10 as context. Cite which formula is being used.
hook_test_mode=True (20% of posts): invent new formula, flag as is_experimental.
concept_remix prompt addition: "These clips appeared in a previous reel. Find a completely different story they can tell. The hook must reframe what the viewer thinks they're watching."
series prompt addition: "Reference episode {N-1} summary in first 5 seconds. Plant setup for episode {N+1} in final 10 seconds."

**Agent 09 — QA**
6 checks in order: policy → audio licensing → copyright → type_consistency → caption_energy → quality_score.
REVISION_NEEDED must include: revision_target_agent AND revision_instruction (specific, not "improve quality").
Quality score >= 70 required for APPROVED.
Max 3 revisions in pipeline before human_review flag.

**Agent 13 — Learning (most critical)**
Performs all math updates DIRECTLY in Python (no Claude for arithmetic).
Only calls Claude to generate the delta_report text for Orchestrator.
Write to ALL 6 stores in sequence. Log each store update at INFO level.
Write completed delta_report to orchestrator_deltas table AND update post_log.
