# @ekfollowekchara — Multi-Agent Reels System
> Drop this file in your project root. Claude Code reads it automatically every session.

## Project Purpose
Autonomous Instagram Reels production system for @ekfollowekchara.
13 AI agents, 6 reel strategies, self-learning loop.
Account niche: motivational/lifestyle/cultural, Hindi-English mix, North Indian audience.
Goal: zero manual effort after dropping clips into the folder.

## Stack
- Python 3.11
- Anthropic API (claude-sonnet-4-6 for agents, claude-opus-4-6 for orchestrator only)
- Supabase PostgreSQL + pgvector (vector search for clips)
- faster-whisper LOCAL (free transcription, no OpenAI API needed)
- FFmpeg (video quality analysis + scene detection)
- LangGraph (agent pipeline state machine)
- APScheduler + SQLAlchemy jobstore (persistent checkpoint scheduling)
- Instagram Graph API v21.0
- Railway (hosting, free tier)
- Cloudflare R2 (video storage, 10GB free forever)
- MoviePy (auto video editing from edit manifest)

## Project Structure
```
reelmind/
├── CLAUDE.md                   ← project bible (this file)
├── skills/                     ← read before each coding phase
│   ├── INGESTION.md
│   ├── AGENTS.md
│   ├── PIPELINE.md
│   ├── MEMORY.md
│   └── INSTAGRAM.md
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py         ← all env vars, constants, model names
│   │   └── prompts.py          ← ALL agent system prompts (never inline)
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── schema.py           ← Pydantic models for every data structure
│   │   └── stores.py           ← 6 memory store classes (Supabase)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── ingestion.py        ← Agent 01
│   │   ├── trend_research.py   ← Agent 02
│   │   ├── orchestrator.py     ← Agent 03 (Opus)
│   │   ├── type_selector.py    ← Agent 04
│   │   ├── clip_selection.py   ← Agent 05
│   │   ├── script.py           ← Agent 06
│   │   ├── edit_spec.py        ← Agent 07
│   │   ├── caption.py          ← Agent 08
│   │   ├── qa.py               ← Agent 09
│   │   ├── publisher.py        ← Agent 10
│   │   ├── analytics.py        ← Agent 11
│   │   ├── audience.py         ← Agent 12
│   │   └── learning.py         ← Agent 13 (only writer to memory stores)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── claude_client.py    ← base Claude API call + parse_json_response()
│   │   ├── video_analysis.py   ← FFprobe + scene detection
│   │   ├── transcription.py    ← faster-whisper local transcription
│   │   ├── vector_db.py        ← Supabase pgvector client
│   │   ├── instagram_api.py    ← publish + analytics + comments
│   │   ├── r2_storage.py       ← Cloudflare R2 upload/URL
│   │   └── auto_editor.py      ← MoviePy: EditManifest → .mp4
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── graph.py            ← LangGraph production DAG
│   │   ├── learning_loop.py    ← APScheduler checkpoint jobs
│   │   └── scheduler.py        ← daily cron entry point
│   └── scripts/
│       ├── ingest_clips.py     ← one-time library ingestion CLI
│       ├── run_reel.py         ← on-demand or scheduled production
│       └── health.py           ← FastAPI /health endpoint for Railway
├── tests/
│   ├── test_ingestion.py
│   ├── test_agents.py
│   ├── test_memory.py
│   └── test_pipeline.py
├── migrations/
│   └── 001_initial_schema.sql  ← all Supabase tables
├── Dockerfile
├── railway.toml
├── requirements.txt
└── .env.example
```

## Coding Rules — Enforce These Always

### 1. Agent structure (Universal Pattern)
Every agent is a class with a single `.run()` method:
```python
class XAgent:
    def run(self, input: InputModel) -> OutputModel:
        user_msg = self._build_prompt(input)
        raw = call_claude(PROMPTS.X_AGENT, user_msg, model=SETTINGS.MODEL_AGENT)
        data = parse_json_response(raw)
        return OutputModel(**data)
```

### 2. No raw dicts across agent boundaries
All agent inputs and outputs are typed Pydantic models defined in `src/memory/schema.py`.
Never pass a raw dict between agents.

### 3. All prompts in one file
`src/config/prompts.py` — one constant per agent, all CAPS.
Never write a prompt string inside an agent file.

### 4. Memory store access
- Reads: any agent can call `memory.stores.X.get_*()`
- Writes: ONLY `src/agents/learning.py` (Agent 13)
- No agent except 13 calls any `.update_*()` or `.upsert_*()` method

### 5. Instagram API isolation
ALL Instagram calls go through `src/tools/instagram_api.py`.
No other file imports httpx and calls Instagram directly.

### 6. Logging
Use loguru everywhere. Import: `from loguru import logger`
```python
logger.info("[AgentName] Starting task...")
logger.success("[AgentName] Task complete: {detail}")
logger.warning("[AgentName] Issue: {detail}")
logger.error("[AgentName] Failed: {detail}")
```
Never use `print()`.

### 7. Config from environment only
All values from `src/config/settings.py` which reads from `.env`.
No hardcoded values in any other file. Not even model names.

### 8. Error handling
Wrap Claude API calls in try/except. Log warnings, don't crash the pipeline.
QA failures trigger revision loops — they are expected, not errors.

## The 13 Agents — Quick Reference

| # | Name | Model | Key Input | Key Output |
|---|------|-------|-----------|------------|
| 01 | Clip Ingestion | Sonnet | clip_path, ffprobe_data, transcript | ClipMetadata |
| 02 | Trend Research | Sonnet + web_search | account_niche | TrendBrief |
| 03 | Orchestrator | **Opus** | trend_brief + ALL memory stores | ReelBrief |
| 04 | Type Selector | Sonnet | reel_brief + last_10_types | TypedProductionSpec |
| 05 | Clip Selection | Sonnet | typed_spec | List[SelectedClip] |
| 06 | Script | Sonnet | typed_spec + clips + hook_library | ScriptStoryboard |
| 07 | Edit Spec | Sonnet | typed_spec + storyboard | EditManifest |
| 08 | Caption | Sonnet | typed_spec + manifest + hashtag_db | CaptionPackage |
| 09 | QA | Sonnet | typed_spec + manifest + caption | QAReport |
| 10 | Publisher | Sonnet + IG API | typed_spec + manifest + caption | PostMetadata |
| 11 | Analytics | Sonnet + IG API | post_metadata + checkpoint | PerformanceReport |
| 12 | Audience | Sonnet | post_metadata + perf_reports + comments | AudienceInsights |
| 13 | Learning | Sonnet | post_metadata + all_reports + insights | OrchestratorDeltaReport |

## The 6 Reel Strategies

| Type | Clip Rule | Frequency | Key Constraint |
|------|-----------|-----------|----------------|
| fresh_drop | usage_count = 0 only | 2-3x/week | highest discovery potential |
| hybrid_mix | 50% proven (score≥75) + 50% fresh | 1-2x/week | interleave, no 2 proven consecutive |
| concept_remix | clips FROM specific past reel | 1x/week | edit style MUST differ from source |
| series | any clips, narrative continuity | 1x/week | max 2 active series simultaneously |
| trend_surfer | best audio-fit clips | as trends emerge | only when urgency=HIGH |
| best_of | performance_tier='top_10_percent' only | monthly | only milestone or 28+ days since last |

Hard rule: never same type 3 posts in a row.

## The 6 Memory Stores

| Store | Updated When | Read By |
|-------|-------------|---------|
| hook_library | T+1h checkpoint | Agent 06 (Script) |
| clip_performance | T+24h checkpoint | Agent 05 (Clip Selection) |
| hashtag_velocity | T+24h + weekly decay | Agent 08 (Caption) |
| format_performance | T+7d checkpoint | Agent 03 (Orchestrator) |
| audience_preference | T+7d checkpoint | Agent 03 (Orchestrator) |
| optimal_timing | T+30d checkpoint | Agent 10 (Publisher) |

All stores are read by Agent 03 (Orchestrator) via `memory.get_orchestrator_context()`.

## Learning Checkpoint Schedule

| Checkpoint | When | Agents Run | Memory Updated |
|------------|------|------------|----------------|
| T+1h | 1 hour after post | 11 (Analytics) | hook_library |
| T+24h | 24 hours after post | 11 (Analytics) + 13 (Learning) | clip_performance, hashtag_velocity |
| T+7d | 7 days after post | 11 + 12 + 13 (full cycle) | format_performance, audience_preference |
| T+30d | 30 days after post | 11 + 12 + 13 (full cycle) | optimal_timing, all stores re-normalized |

## Supabase Tables Needed
1. clips (video metadata + pgvector embedding)
2. hook_library
3. hashtag_velocity
4. format_performance
5. audience_preference
6. optimal_timing
7. post_log (backbone of learning loop)
8. series_memory
9. orchestrator_deltas

All tables defined in `migrations/001_initial_schema.sql`.

## Phase Status — Update This As You Build
- [ ] Phase 1 — Foundation (skeleton, config, schemas)
- [ ] Phase 2 — Ingestion Engine
- [ ] Phase 3a — Memory Stores
- [ ] Phase 3b — Agents 01-06
- [ ] Phase 3c — Agents 07-13
- [ ] Phase 4 — LangGraph Pipeline
- [ ] Phase 5 — Instagram API
- [ ] Phase 6 — Auto Editor (MoviePy)
- [ ] Phase 7 — Local Testing
- [ ] Phase 8 — Deploy to Railway
- [ ] Phase 9 — Prompt Tuning (after 10 real posts)
