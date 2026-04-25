# skills/INGESTION.md

## Goal
Build the one-time clip library processor.
Every raw video clip → analyzed → stored in Supabase + pgvector.

## Files to Build
1. `src/tools/video_analysis.py`
   - `extract_quality_metrics(path) → Dict`
     FFprobe subprocess. Returns: duration, resolution_score (1-10), fps_score, bitrate_score, audio_clarity_score, is_vertical, technical_quality_raw (weighted avg).
   - `detect_scene_changes(path, threshold=0.4) → List[{timestamp_sec}]`
     FFmpeg select filter. Parse pts_time from stderr output.
   - `extract_usable_segments(path) → List[{start_sec, end_sec, note}]`
     Build segments from scene changes. Cap each segment at 15s. Max 8 per clip.

2. `src/tools/transcription.py`
   - `transcribe_video(path) → str`
     Use faster-whisper (local, free). Model: "medium". device="cpu", compute_type="int8".
     Extract audio to temp WAV (16kHz mono) first via FFmpeg. Return "" for music-only clips.

3. `src/agents/ingestion.py`
   - `ClipIngestionAgent.run(clip_path, ffprobe_data, transcript) → ClipMetadata`
     Calls Claude Sonnet with INGESTION_AGENT_PROMPT from prompts.py.
     Returns typed ClipMetadata. Stores to Supabase + upserts pgvector embedding.

4. `src/scripts/ingest_clips.py`
   - CLI with --clips-dir and --resume flags
   - Rich progress bar showing clip name + quality score
   - Summary table at end: ingested / failed / skipped counts

## Supabase clips table schema
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE clips (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_id TEXT UNIQUE NOT NULL,
  file_path TEXT NOT NULL,
  quality_score FLOAT NOT NULL,
  quality_flag TEXT NOT NULL,
  shot_type TEXT,
  movement_energy INT,
  scene_tags TEXT[],
  emotion_tags TEXT[],
  face_present BOOL DEFAULT FALSE,
  transcript_summary TEXT,
  mood TEXT,
  color_palette TEXT,
  usable_segments JSONB,
  embedding vector(1536),
  usage_count INT DEFAULT 0,
  performance_score FLOAT DEFAULT 50,
  performance_tier TEXT DEFAULT 'average',
  last_used_reel_id TEXT,
  overused_flag BOOL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX clips_embedding_idx ON clips USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX clips_usage_idx ON clips(usage_count);
CREATE INDEX clips_performance_idx ON clips(performance_score DESC);
```

## Test command
```bash
python src/scripts/ingest_clips.py --clips-dir ./test_clips --dry-run
```
Should print: clip_id, quality_score, mood, transcript_summary for 3 test clips.

---

# skills/MEMORY.md

## Goal
6 persistent Supabase tables. Only Agent 13 writes. All others read.

## All 7 Supabase Tables

```sql
-- Memory Store 1: Hook Library
CREATE TABLE hook_library (
  formula_id TEXT PRIMARY KEY,
  formula_name TEXT NOT NULL,
  formula_pattern TEXT NOT NULL,
  example TEXT,
  score FLOAT DEFAULT 50,
  times_used INT DEFAULT 0,
  avg_watch_time_percent FLOAT DEFAULT 0,
  last_tested TIMESTAMPTZ,
  trend_delta FLOAT DEFAULT 0,
  is_experimental BOOL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory Store 3: Hashtag Velocity
CREATE TABLE hashtag_velocity (
  tag TEXT PRIMARY KEY,
  tier INT NOT NULL,
  velocity FLOAT DEFAULT 0,
  times_used INT DEFAULT 0,
  last_used TIMESTAMPTZ,
  avg_discovery_percent FLOAT DEFAULT 0,
  is_dead BOOL DEFAULT FALSE,
  from_trend_research BOOL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Memory Store 4: Format Performance
CREATE TABLE format_performance (
  id BIGSERIAL PRIMARY KEY,
  reel_type TEXT NOT NULL,
  duration_bucket TEXT NOT NULL,
  energy_level TEXT NOT NULL,
  avg_engagement_depth FLOAT DEFAULT 0,
  avg_save_rate FLOAT DEFAULT 0,
  avg_hook_score FLOAT DEFAULT 0,
  data_points INT DEFAULT 0,
  decay_flag BOOL DEFAULT FALSE,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(reel_type, duration_bucket, energy_level)
);

-- Memory Store 5: Audience Preference
CREATE TABLE audience_preference (
  preference_key TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  weight FLOAT DEFAULT 0.5,
  data_points INT DEFAULT 0,
  last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Memory Store 6: Optimal Timing
CREATE TABLE optimal_timing (
  day_of_week INT NOT NULL,
  hour INT NOT NULL,
  avg_first_hour_velocity FLOAT DEFAULT 0,
  data_points INT DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (day_of_week, hour)
);

-- Post Log (learning loop backbone)
CREATE TABLE post_log (
  post_id TEXT PRIMARY KEY,
  ig_post_url TEXT,
  reel_type TEXT,
  hook_formula_id TEXT,
  clip_ids TEXT[],
  audio_id TEXT,
  caption_variant TEXT,
  hashtags_used TEXT[],
  edit_style_class TEXT,
  series_id TEXT,
  episode_number INT,
  post_timestamp TIMESTAMPTZ,
  quality_score INT,
  checkpoints_completed TEXT[] DEFAULT '{}',
  latest_performance JSONB,
  delta_report JSONB
);

-- Series Memory
CREATE TABLE series_memory (
  series_id TEXT PRIMARY KEY,
  series_name TEXT,
  episode_count INT DEFAULT 0,
  last_episode_summary TEXT,
  next_episode_setup TEXT,
  clip_ids_used TEXT[] DEFAULT '{}',
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## MemoryStores class structure
```python
class MemoryStores:
    def get_orchestrator_context(self) -> Dict:
        # Returns all 6 stores summarized for Agent 03
        return {
            "hook_library_top10": self.hooks.get_top_n(10),
            "freshness_index": ...,
            "proven_clips_count": ...,
            "hashtags_tier1": ...,
            "best_format": ...,
            "audience_top_topics": ...,
            "optimal_slot": ...,
        }
```

## Update formulas (hardcoded in Agent 13, no Claude needed)
- Hook: score += 10 if watch_time >= 0.60, -= 5 if <= 0.30
- Clip: new_score = old_score*0.7 + engagement_depth*100*0.3
- Hashtag: velocity = this_post_attribution; weekly *= 0.98; if < 0.01 mark dead
- Format: rolling average of last 5 posts per (type, duration, energy) tuple
- Timing: rolling average of (post_hour, post_day) → first_hour_velocity

## Seed defaults on first run
Insert 10 hook formulas into hook_library with score=50.
See CLAUDE.md for the 10 default hook patterns.

---

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

---

# skills/PIPELINE.md

## Goal
LangGraph state machine. Production pipeline (Agents 1-10) + Learning loop (Agents 11-13).

## Production Graph Structure
```python
StateGraph(ReelPipelineState)
  entry: trend_research
  edges (linear): trend_research → orchestrate → type_selector → clip_selection
               → script → edit_spec → caption → qa
  conditional after qa:
    if approved → publish → END
    if failed and revision_count < 3 → qa_revision_router
    if failed and revision_count >= 3 → END (with human_review=True flag)
  qa_revision_router → routes to: script | edit_spec | caption | clip_selection
```

## ReelPipelineState (TypedDict)
Required fields:
- account_niche, last_30_days_stats, last_10_reel_types, video_url (inputs)
- trend_brief, reel_brief, typed_spec, selected_clips, storyboard, edit_manifest, caption_package, qa_report (intermediate — each agent writes one)
- post_metadata, pipeline_status, qa_revision_count, error (control flow)

## Learning Loop (separate, async)
```python
# Called AFTER successful publish
def schedule_learning_checkpoints(post_id: str, post_time: datetime):
    for checkpoint, delta in [("T+1h", 1h), ("T+24h", 24h), ("T+7d", 7d), ("T+30d", 30d)]:
        scheduler.add_job(
            func=run_checkpoint,
            trigger="date",
            run_date=post_time + delta,
            args=[post_id, checkpoint],
            id=f"{post_id}_{checkpoint}",
        )
```

APScheduler uses SQLAlchemy jobstore backed by Supabase — jobs survive Railway restarts.

## run_checkpoint(post_id, checkpoint)
- T+1h: Agent 11 only → update hook_library
- T+24h: Agent 11 + Agent 13 → update clip_performance, hashtag_velocity
- T+7d: Agent 11 + 12 + 13 → full learning cycle
- T+30d: Agent 11 + 12 + 13 → full learning cycle + monthly audit

## Entry Point
```python
# src/scripts/run_reel.py
def main(dry_run=False):
    graph = build_production_graph()
    state = graph.invoke(initial_state)
    if state["pipeline_status"] == "published" and not dry_run:
        schedule_learning_checkpoints(state["post_metadata"]["post_id"], datetime.utcnow())
```

---

# skills/INSTAGRAM.md

## Goal
Full Instagram Graph API integration. Publish + analytics + comment NLP.

## Base Setup
```python
BASE = "https://graph.facebook.com/v21.0"
ACCOUNT_ID = settings.INSTAGRAM_ACCOUNT_ID
TOKEN = settings.INSTAGRAM_ACCESS_TOKEN
```

## Publish Flow (3 steps + 1 comment)
```python
# Step 1: Container
POST {BASE}/{ACCOUNT_ID}/media
  {media_type: "REELS", video_url: R2_PUBLIC_URL, caption: CAPTION_TEXT, access_token: TOKEN}
→ {id: container_id}

# Step 2: Poll until ready
GET {BASE}/{container_id}?fields=status_code&access_token={TOKEN}
Poll every 15s. Status: IN_PROGRESS → FINISHED (or ERROR/EXPIRED)
Timeout after 5 minutes.

# Step 3: Publish
POST {BASE}/{ACCOUNT_ID}/media_publish
  {creation_id: container_id, access_token: TOKEN}
→ {id: post_id}

# Step 4: Hashtags as first comment
POST {BASE}/{post_id}/comments
  {message: "#tag1 #tag2 ...", access_token: TOKEN}
```

## Analytics Endpoints
```python
# Insights for a post
GET {BASE}/{post_id}/insights
  ?metric=plays,reach,saved,shares,comments,follows,impressions
  &access_token={TOKEN}

# Comments (for NLP at T+7d)
GET {BASE}/{post_id}/comments
  ?fields=text,timestamp,like_count&limit=100&access_token={TOKEN}
```

## Token Refresh (weekly cron job)
```python
GET {BASE}/oauth/access_token
  ?grant_type=fb_exchange_token
  &client_id={APP_ID}
  &client_secret={APP_SECRET}
  &fb_exchange_token={CURRENT_TOKEN}
→ {access_token: NEW_TOKEN, expires_in: 5183944}
# Store new token to Supabase secrets table
# Schedule next refresh for 50 days from now
```

## Video Requirements for R2 Upload
Format: MP4 (H.264 + AAC)  |  Aspect: 9:16  |  Min: 1080x1920  |  Max: 1GB  |  Duration: 3-90s

## Cloudflare R2 Upload
```python
import boto3
s3 = boto3.client("s3",
    endpoint_url=f"https://{CF_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_KEY, aws_secret_access_key=R2_SECRET)
s3.upload_file(local_path, "ekfollowekchara-reelmind", filename,
               ExtraArgs={"ContentType": "video/mp4"})
public_url = f"https://pub-{CF_ACCOUNT_ID}.r2.dev/{filename}"
```

## Rate Limits
200 API calls/hour per token. Publishing: 50 reels/day max.
Use tenacity for retries: stop_after_attempt(3), wait_exponential(min=4, max=30).
