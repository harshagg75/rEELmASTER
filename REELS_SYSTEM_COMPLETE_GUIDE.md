# @ekfollowekchara — Complete A2A Reels System
## From Zero to Deployed: Free Stack, Claude Code, Step-by-Step

---

## What You're Building

A fully autonomous multi-agent Instagram Reels machine that:
- Watches your raw clip folder, auto-ingests new footage
- Reads Instagram trends daily (audio, formats, hooks)
- Decides what kind of reel to make (fresh / hybrid / remix / series / trend / best-of)
- Selects the best clips semantically (understands content, not just filenames)
- Writes script, storyboard, edit spec, caption, hashtags
- QA checks everything before posting
- Posts at optimal time via Instagram API
- Measures performance at 1h / 24h / 7d / 30d
- Updates 6 memory stores (hooks, clips, hashtags, formats, audience, timing)
- Gets measurably smarter with every single post

**Fully free to host. ~$5–15/month total running cost (only Anthropic API usage).**

---

## The Complete Free Stack

| Layer | Tool | Why Free | Alternative |
|-------|------|----------|-------------|
| **AI Agents** | Anthropic API (Sonnet 4.6) | Pay-per-use, ~$0.003/reel | — |
| **Orchestrator** | Anthropic API (Opus 4.6) | 1 call per reel | — |
| **Transcription** | Faster-Whisper (local) | Runs on your machine, free | OpenAI Whisper API |
| **Vector DB** | Supabase pgvector | Free tier (500MB) | Pinecone free tier |
| **Database** | Supabase PostgreSQL | Free tier (500MB) | SQLite (local only) |
| **Video Processing** | FFmpeg (local) | Open source | — |
| **Hosting** | Railway or Render | Free tier (750 hrs/month) | Fly.io free |
| **Scheduler** | APScheduler + Railway Cron | Free | GitHub Actions |
| **File Storage** | Cloudflare R2 | 10GB free forever | Backblaze B2 |
| **Code** | Claude Code (local) | Your Anthropic subscription | — |
| **Version Control** | GitHub | Free | — |
| **Monitoring** | Grafana Cloud | Free tier | Uptime Kuma |

**Estimated monthly cost: $5–15 (Anthropic API only, scales with posting frequency)**

---

## Phase Map — The Full Journey

```
PHASE 0 — Setup (1 day)
   Install tools, accounts, API keys

PHASE 1 — Foundation (2–3 days with Claude Code)
   Project structure, config, data schemas, memory stores

PHASE 2 — Ingestion Engine (1–2 days)
   FFmpeg analysis, Whisper transcription, vector indexing

PHASE 3 — Agent Layer (3–4 days)
   All 13 agents: prompts, tool calls, JSON contracts

PHASE 4 — Pipeline Wiring (1–2 days)
   LangGraph DAG, QA revision loop, state management

PHASE 5 — Instagram Integration (1 day)
   Graph API: publish, analytics, comments

PHASE 6 — Learning Loop (1–2 days)
   4-checkpoint scheduler, 6 memory store updates

PHASE 7 — Local Testing (2–3 days)
   Dry runs, mock Instagram, tune prompts

PHASE 8 — Deploy to Railway (1 day)
   Dockerfile, env vars, cron schedule

PHASE 9 — Monitor & Iterate (ongoing)
   Watch the system learn, tune prompts
```

---

## PHASE 0 — Environment Setup

### What to install on your machine

```bash
# 1. Python 3.11+
pyenv install 3.11.9
pyenv global 3.11.9

# 2. FFmpeg (video analysis)
# macOS:
brew install ffmpeg
# Ubuntu/WSL:
sudo apt install ffmpeg

# 3. Claude Code
npm install -g @anthropic-ai/claude-code

# 4. Git
git init reelmind
cd reelmind
```

### Accounts to create (all free)

1. **Anthropic Console** — console.anthropic.com → get API key
2. **Supabase** — supabase.com → create project → get DB URL + anon key
3. **Railway** — railway.app → connect GitHub account
4. **Cloudflare** — cloudflare.com → R2 storage (10GB free)
5. **Instagram Developer** — developers.facebook.com → create app → get long-lived token for @ekfollowekchara
6. **GitHub** — create private repo `reelmind`

### Instagram API Setup (most complex step)
```
1. Go to developers.facebook.com
2. Create App → Business → Add Instagram product
3. Connect your @ekfollowekchara business account
4. Get User Access Token → exchange for Long-Lived Token (60 days)
5. Permissions needed:
   - instagram_basic
   - instagram_content_publish
   - instagram_manage_insights
   - pages_read_engagement
6. Set up a weekly cron job to refresh the token before it expires
```

---

## PHASE 1 — Project Foundation with Claude Code

### How to use Claude Code for this project

Claude Code is a terminal-based AI coding agent. You give it tasks in natural language and it writes, edits, and runs code. The key to using it well for this project is:

1. **Always start a session by pointing it to your CLAUDE.md** — this is the project bible
2. **Give it one phase at a time** — don't say "build everything", say "build Phase 2: ingestion engine"
3. **Use skill files** — pre-written instructions for specific tasks (templates below)
4. **Review every file it creates** before moving to the next task

### Starting Claude Code

```bash
cd reelmind
claude  # opens Claude Code in this directory
```

Claude Code will automatically read `CLAUDE.md` from your project root if it exists.

---

### File: `CLAUDE.md` (put this in your project root)

This is the single most important file. Claude Code reads this at the start of every session.

```markdown
# @ekfollowekchara — Multi-Agent Reels System

## Project Purpose
Autonomous Instagram Reels production system for @ekfollowekchara.
13 AI agents, 6 reel strategies, self-learning loop.
Account niche: motivational/lifestyle/cultural, Hindi-English mix, North Indian audience.

## Stack
- Python 3.11
- Anthropic API (claude-sonnet-4-6 for agents, claude-opus-4-6 for orchestrator)
- Supabase (PostgreSQL + pgvector)
- FFmpeg + faster-whisper (local video analysis)
- LangGraph (agent pipeline)
- APScheduler (checkpoint scheduling)
- Instagram Graph API v21.0
- Railway (hosting)
- Cloudflare R2 (video storage)

## Project Structure
reelmind/
├── CLAUDE.md               ← you are here
├── skills/                 ← Claude Code skill files (read before coding each phase)
│   ├── INGESTION.md
│   ├── AGENTS.md
│   ├── PIPELINE.md
│   ├── MEMORY.md
│   └── INSTAGRAM.md
├── src/
│   ├── config/             ← settings, prompts, constants
│   ├── memory/             ← 6 memory stores + schemas
│   ├── agents/             ← all 13 agents
│   ├── tools/              ← ffmpeg, whisper, vector_db, instagram
│   ├── pipeline/           ← langgraph DAG + learning loop
│   └── scripts/            ← ingest_clips.py, run_reel.py
├── tests/
├── Dockerfile
├── railway.toml
├── requirements.txt
└── .env.example

## Key Rules for Claude Code
1. Every agent returns typed Pydantic models — no raw dicts across agent boundaries
2. All prompts live in src/config/prompts.py — not inline in agent files
3. Memory stores are append-only from agents — only Learning Agent (13) writes to memory
4. All Instagram API calls go through src/tools/instagram_api.py — nowhere else
5. Use loguru for all logging — never print()
6. All config comes from environment variables via src/config/settings.py
7. Never hardcode API keys anywhere

## The 13 Agents
01 Clip Ingestion & Analysis     — runs once on library
02 Trend Research                — runs daily, uses web search
03 Orchestrator                  — OPUS model, reads all memory, issues brief
04 Reel Type Selector            — picks from 6 strategies
05 Clip Selection                — semantic search + type rules
06 Script & Storyboard           — hook formula system
07 Edit Specification            — CapCut-compatible manifest
08 Caption & Hashtag             — brand voice + velocity DB
09 QA & Review                   — 6-dimension check
10 Scheduler & Publisher         — IG Graph API
11 Performance Analytics         — 4 checkpoints
12 Audience Intelligence         — NLP + segment profiles
13 Learning & Memory             — updates all 6 stores

## The 6 Memory Stores
1. Hook Library              — hook formulas ranked by watch-time %
2. Clip Performance DB       — composite score per clip
3. Hashtag Velocity DB       — discovery % with weekly decay
4. Format Performance Matrix — reel_type × duration × energy vs engagement
5. Audience Preference Model — topics/emotions your audience acts on
6. Optimal Timing Model      — posting time → first-hour velocity

## The 6 Reel Strategies
1. fresh_drop    — 100% never-used clips
2. hybrid_mix    — 40-60% proven + fresh
3. concept_remix — same clips, new music + concept
4. series        — narrative continuation
5. trend_surfer  — locked to trending audio
6. best_of       — top 10% performance clips only

## Learning Checkpoints
T+1h  → Hook quality (watch-time %)
T+24h → Discovery, saves, hashtag attribution
T+7d  → Audience NLP, follower quality
T+30d → Long-tail, full pattern audit

## When writing agents, always:
- Accept typed Pydantic inputs
- Call Claude via src/tools/claude_client.py
- Parse JSON response with parse_json_response()
- Return typed Pydantic output
- Log with loguru at INFO and SUCCESS levels
- Handle errors with try/except and log WARNING

## Current Status
[ ] Phase 1 — Foundation
[ ] Phase 2 — Ingestion Engine
[ ] Phase 3 — Agent Layer
[ ] Phase 4 — Pipeline Wiring
[ ] Phase 5 — Instagram Integration
[ ] Phase 6 — Learning Loop
[ ] Phase 7 — Local Testing
[ ] Phase 8 — Deploy
```

---

## Skill Files for Claude Code

Create a `skills/` folder in your project. Each skill file is a focused instruction document. Before starting each phase, tell Claude Code: **"Read skills/AGENTS.md then build Agent 05."**

---

### `skills/INGESTION.md`

```markdown
# Skill: Clip Ingestion Engine

## Goal
Build the one-time clip library processor.
Every raw video clip → analyzed → stored in Supabase + pgvector.

## What to build
1. src/tools/video_analysis.py
   - extract_quality_metrics(path) → Dict
     Uses: ffprobe subprocess call
     Returns: {duration, resolution_score, fps_score, bitrate_score,
               audio_clarity_score, technical_quality_raw, is_vertical}
   - detect_scene_changes(path) → List[{timestamp_sec, confidence}]
     Uses: ffmpeg with select filter
   - extract_usable_segments(path) → List[{start_sec, end_sec, note}]
     Uses: scene changes to identify natural cut points
     Cap segments at 15s, return max 8 per clip

2. src/tools/transcription.py
   - transcribe_video(path) → str
     Uses: faster-whisper (local, free) NOT OpenAI API
     Model: medium (good balance of speed/accuracy for Hindi-English)
     Handle: no audio, music-only clips (return empty string)

3. src/agents/ingestion_agent.py
   - ClipIngestionAgent.run(clip_path, ffprobe_data, transcript) → ClipMetadata
     Calls Claude Sonnet to analyze visual content + transcript
     Returns full ClipMetadata Pydantic model
     Stores to: Supabase clips table + pgvector embedding

## Supabase schema for clips table
clips:
  id UUID PRIMARY KEY
  clip_id TEXT UNIQUE  (filename without extension)
  file_path TEXT
  quality_score FLOAT
  quality_flag TEXT  (excellent/good/acceptable/last_resort)
  shot_type TEXT
  movement_energy INT
  scene_tags TEXT[]
  emotion_tags TEXT[]
  face_present BOOL
  transcript_summary TEXT
  mood TEXT
  color_palette TEXT
  usable_segments JSONB
  embedding vector(1536)  -- pgvector
  usage_count INT DEFAULT 0
  performance_score FLOAT DEFAULT 50
  performance_tier TEXT DEFAULT 'average'
  created_at TIMESTAMPTZ DEFAULT NOW()

## faster-whisper setup
pip install faster-whisper
Model download happens on first run (~1.5GB for medium)
Use: WhisperModel("medium", device="cpu", compute_type="int8")

## Test command
python scripts/ingest_clips.py --clips-dir ./test_clips --dry-run
Should print: clip_id, quality_score, mood, transcript_summary for each clip
```

---

### `skills/AGENTS.md`

```markdown
# Skill: Agent Layer

## Goal
Build all 13 agents as clean, testable Python classes.
Each agent: typed input → Claude API call → typed output.

## Universal Agent Pattern
Every agent follows this exact structure:

class XAgent:
    def run(self, input: InputModel) -> OutputModel:
        user_msg = self._build_prompt(input)
        raw = call_claude(SYSTEM_PROMPT, user_msg, model=MODEL)
        data = parse_json_response(raw)
        return OutputModel(**data)
    
    def _build_prompt(self, input) -> str:
        # Build the user message with all context
        ...

## Model Assignment
- Agent 03 (Orchestrator): claude-opus-4-6
- All others: claude-sonnet-4-6
- Agent 02 (Trend Research): claude-sonnet-4-6 WITH web_search tool enabled

## Agent-Specific Notes

AGENT 02 — Trend Research:
Enable web search tool in the API call.
Search for: "Instagram Reels trending [niche] [current month year]"
Search for: "trending Instagram audio [month year]"
Return TrendBrief with urgency flags.

AGENT 03 — Orchestrator:
Read ALL 6 memory stores before building the brief.
Call memory.get_orchestrator_context() to get full summary.
This is the ONLY agent that reads everything.
Output: ReelBrief with specific concept, not vague direction.

AGENT 04 — Type Selector:
Enforce these hard rules in the prompt:
- No same type 3 posts in a row
- trend_surfer only if urgency=HIGH
- best_of only if milestone or 28+ days since last one
- max 2 active series simultaneously

AGENT 05 — Clip Selection:
Type-specific query filters:
fresh_drop → WHERE usage_count = 0
hybrid_mix → MIX proven (score≥75, usage≤2) + fresh
concept_remix → clips FROM specific past reel ID
series → any clips matching brief
trend_surfer → best audio-energy match (quality secondary)
best_of → WHERE performance_tier = 'top_10_percent'

AGENT 06 — Script:
Hook Library top-10 is passed as context.
20% of posts: hook_test_mode=True → invent new formula.
For concept_remix: "Find a completely different story these clips can tell."
For series: reference previous episode, plant next episode setup.

AGENT 09 — QA:
Returns APPROVED or REVISION_NEEDED.
REVISION_NEEDED must include:
  - revision_target_agent (which agent to re-run)
  - revision_instruction (specific, actionable)
Max 3 revision loops before human escalation.

AGENT 13 — Learning:
ONLY agent with write access to all 6 memory stores.
Performs math updates directly (no Claude needed for arithmetic).
Claude synthesizes the delta report for Orchestrator after math is done.

## Testing Each Agent
Each agent should have a standalone test:
python -m pytest tests/test_agent_02.py -v
Use mock Claude responses for speed.
Test edge cases: empty clip library, no trending audio found, QA failure.
```

---

### `skills/MEMORY.md`

```markdown
# Skill: Memory Store System

## Goal
6 persistent stores in Supabase PostgreSQL that drive learning.
Only Learning Agent (13) writes. All other agents read.

## Supabase Tables to Create

### 1. hook_library
formula_id TEXT PRIMARY KEY
formula_name TEXT
formula_pattern TEXT
example TEXT
score FLOAT DEFAULT 50      -- 0-100, updated every post
times_used INT DEFAULT 0
avg_watch_time_percent FLOAT DEFAULT 0
last_tested TIMESTAMPTZ
trend_delta FLOAT DEFAULT 0  -- positive=improving, negative=decaying
is_experimental BOOL DEFAULT FALSE

Seed with 10 default hooks on first run (see CLAUDE.md for formulas).

### 2. clip_performance
(extends clips table — update in place)
performance_score FLOAT DEFAULT 50
performance_tier TEXT  -- top_10_percent / top_25_percent / average / below_average
usage_count INT DEFAULT 0
last_used_reel_id TEXT
overused_flag BOOL DEFAULT FALSE

### 3. hashtag_velocity
tag TEXT PRIMARY KEY
tier INT  (1/2/3)
velocity FLOAT DEFAULT 0     -- discovery impression %
times_used INT DEFAULT 0
last_used TIMESTAMPTZ
avg_discovery_percent FLOAT DEFAULT 0
is_dead BOOL DEFAULT FALSE

### 4. format_performance
UNIQUE(reel_type, duration_bucket, energy_level)
avg_engagement_depth FLOAT DEFAULT 0
avg_save_rate FLOAT DEFAULT 0
avg_hook_score FLOAT DEFAULT 0
data_points INT DEFAULT 0
decay_flag BOOL DEFAULT FALSE

### 5. audience_preference
preference_key TEXT PRIMARY KEY  (e.g. "topic:hustle", "emotion:pride")
category TEXT  (topic/emotion/format)
weight FLOAT DEFAULT 0.5
data_points INT DEFAULT 0

### 6. optimal_timing
PRIMARY KEY (day_of_week, hour)
avg_first_hour_velocity FLOAT DEFAULT 0
data_points INT DEFAULT 0

### 7. post_log (backbone of learning loop)
post_id TEXT PRIMARY KEY  (IG post ID)
ig_post_url TEXT
reel_type TEXT
hook_formula_id TEXT
clip_ids TEXT[]
audio_id TEXT
caption_variant TEXT  (a/b/c)
hashtags_used TEXT[]
edit_style_class TEXT
series_id TEXT
episode_number INT
post_timestamp TIMESTAMPTZ
quality_score INT
checkpoints_completed TEXT[] DEFAULT '{}'
latest_performance JSONB

## Update Rules (enforced in Learning Agent)

Hook Library update:
  if watch_time_pct >= 0.60: score += 10
  if watch_time_pct <= 0.30: score -= 5
  else: score += linear_interpolation

Clip Performance update:
  new_score = (old_score * 0.7) + (engagement_depth * 100 * 0.3)
  if new_score >= 80: tier = 'top_10_percent'
  if new_score >= 65: tier = 'top_25_percent'

Hashtag Velocity update:
  Set velocity = this_post_attribution_pct
  Every Monday: velocity *= 0.98 (decay)
  If velocity < 0.01: is_dead = True

Optimal Timing update:
  Record: (post_day, post_hour) → first_hour_view_count/60 (views/min)
  Rolling average per (day, hour) bucket
```

---

### `skills/PIPELINE.md`

```markdown
# Skill: LangGraph Pipeline

## Goal
Wire all 13 agents into a LangGraph state machine.
Two graphs: Production Pipeline (Agents 1-10) + Learning Graph (Agents 11-13).

## Production Pipeline Flow
trend_research → orchestrate → type_selector → clip_selection 
→ script → edit_spec → caption → qa → [branch] → publish → END
                                               ↓ (if failed)
                                      revision_router → back to correct agent

## State Schema (TypedDict)
ReelPipelineState:
  # inputs
  account_niche: str
  last_30_days_stats: Dict
  last_10_reel_types: List[str]
  video_url: str          # pre-signed R2 URL of rendered video
  
  # intermediate (each agent writes one of these)
  trend_brief: Optional[Dict]
  reel_brief: Optional[Dict]
  typed_spec: Optional[Dict]
  selected_clips: Optional[List[Dict]]
  storyboard: Optional[Dict]
  edit_manifest: Optional[Dict]
  caption_package: Optional[Dict]
  qa_report: Optional[Dict]
  
  # control flow
  post_metadata: Optional[Dict]
  pipeline_status: str
  qa_revision_count: int    # max 3
  error: Optional[str]

## QA Revision Routing
After QA failure, revision_router reads qa_report.issues[0].revision_target_agent
Maps to: script | edit_spec | caption | clip_selection
Max 3 revisions then → END with human_review flag

## Learning Graph (separate, runs async after publish)
Triggered by: post published event
Nodes: analytics_checkpoint → audience_intelligence → learning_update
Runs 4 times: T+1h, T+24h, T+7d, T+30d
T+1h and T+24h: only analytics_checkpoint runs
T+7d and T+30d: all three nodes run (full learning cycle)

## Scheduling
Use APScheduler with SQLAlchemy jobstore (persists to Supabase).
After each publish: schedule 4 jobs with future run_dates.
Jobs survive server restarts because they're persisted in DB.

## Running the pipeline
run_production_pipeline(stats, last_10_types, video_url) → final_state
dry_run=True: skips publish node, returns full state for inspection
```

---

### `skills/INSTAGRAM.md`

```markdown
# Skill: Instagram Graph API Integration

## Base URL
https://graph.facebook.com/v21.0

## Publishing Flow (2 steps)

Step 1: Create container
POST /{account_id}/media
  media_type: REELS
  video_url: <pre-signed R2 URL — must be publicly accessible>
  caption: <full caption text>
→ returns: {id: container_id}

Step 2: Wait for processing (poll every 15s, up to 5 min)
GET /{container_id}?fields=status_code
  status_code: IN_PROGRESS | FINISHED | ERROR | EXPIRED
→ wait until FINISHED

Step 3: Publish
POST /{account_id}/media_publish
  creation_id: container_id
→ returns: {id: post_id}

Step 4: Post hashtags as first comment
POST /{post_id}/comments
  message: "#tag1 #tag2 #tag3..."

## Reading Analytics
GET /{post_id}/insights
  metric: plays,reach,saved,shares,comments,follows,impressions
→ returns metric values

## Checkpoint Timing
T+1h:  collect views, avg_watch_time (if available via reels_plays)
T+24h: collect reach, saves, shares, hashtag_impressions, comments
T+7d:  collect full insights + read all comments for NLP
T+30d: collect final reach, profile_visits, follows

## Token Management
Long-lived tokens expire in 60 days.
Build a weekly cron job to refresh:
GET /oauth/access_token
  grant_type: fb_exchange_token
  client_id: APP_ID
  client_secret: APP_SECRET
  fb_exchange_token: CURRENT_TOKEN
Store new token back to Supabase secrets table.

## Rate Limits
200 calls/hour per token
Publishing: max 50 reels/day (you'll never hit this)
Insights: 200 calls/hour

## Video Requirements for Reels
Format: MP4 (H.264 video, AAC audio)
Aspect ratio: 9:16 (vertical)
Resolution: 1080x1920 recommended minimum
Duration: 3s to 90s
File size: max 1GB
Must be uploaded to a public URL (use Cloudflare R2 with public access)
```

---

## PHASE 2 — Claude Code Session Guide

### How to structure each coding session

**Start every session:**
```bash
cd reelmind
claude
```

Claude Code will read CLAUDE.md automatically. Then say:

```
Read skills/INGESTION.md then build the clip ingestion engine.
Start with src/tools/video_analysis.py.
Follow the patterns in CLAUDE.md exactly.
```

**One phase per session. Never skip ahead.**

### Session 1 — Foundation (Phase 1)
Tell Claude Code:
```
Build the project foundation:
1. Create the full directory structure from CLAUDE.md
2. Create src/config/settings.py with all env vars (never hardcode keys)
3. Create src/config/prompts.py with placeholder prompts for all 13 agents
4. Create src/memory/schema.py with all Pydantic models
5. Create requirements.txt
6. Create .env.example
Don't build any agents yet — just the skeleton.
```

### Session 2 — Ingestion Engine (Phase 2)
Tell Claude Code:
```
Read skills/INGESTION.md
Build the complete ingestion engine:
1. src/tools/video_analysis.py (FFmpeg quality + scene detection)
2. src/tools/transcription.py (faster-whisper, local, free)
3. src/agents/ingestion_agent.py (ClipIngestionAgent)
4. src/scripts/ingest_clips.py (CLI with progress bar)
5. Supabase schema SQL for the clips table + pgvector index
Then create tests/test_ingestion.py with 3 test cases.
```

### Session 3 — Memory Stores (Phase 1 continued)
Tell Claude Code:
```
Read skills/MEMORY.md
Build the complete memory store system:
1. SQL migration file for all 7 Supabase tables
2. src/memory/stores.py — all 6 store classes with read/write methods
3. Seed script for default hook formulas
4. Test that reads/writes work with a local Supabase connection
```

### Session 4 — Agents 1–6 (Phase 3)
Tell Claude Code:
```
Read skills/AGENTS.md
Build Agents 01 through 06.
For each: the agent class, the prompt in prompts.py, a unit test.
Use mock Claude responses in tests (don't call the real API in tests).
Strictly follow the Universal Agent Pattern from AGENTS.md.
```

### Session 5 — Agents 7–13 (Phase 3 continued)
Tell Claude Code:
```
Read skills/AGENTS.md
Build Agents 07 through 13.
Agent 13 (Learning) is the most important — it writes to all 6 memory stores.
Ensure Agent 13 performs the math updates directly (hardcoded formulas)
and only calls Claude to synthesize the delta report text.
```

### Session 6 — Pipeline (Phase 4)
Tell Claude Code:
```
Read skills/PIPELINE.md
Build the LangGraph pipeline:
1. src/pipeline/graph.py — production DAG with QA revision loop
2. src/pipeline/learning_loop.py — async checkpoint scheduler
3. Connect all agents via typed state
4. Test with dry_run=True end-to-end
```

### Session 7 — Instagram Integration (Phase 5)
Tell Claude Code:
```
Read skills/INSTAGRAM.md
Build src/tools/instagram_api.py:
1. Full publish flow (container → wait → publish)
2. Post hashtags as first comment
3. All analytics endpoints for each checkpoint
4. Token refresh mechanism
5. Rate limit handling with tenacity retry
```

### Session 8 — Deploy Setup (Phase 8)
Tell Claude Code:
```
Set up deployment:
1. Dockerfile (Python 3.11-slim, install FFmpeg)
2. railway.toml (service config, cron for daily reel)
3. Health check endpoint (FastAPI, single /health route)
4. Startup script that checks all env vars before starting
5. .github/workflows/deploy.yml for auto-deploy on push to main
```

---

## PHASE 8 — Deployment on Railway (Free)

### Railway Setup

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Create project
railway init

# 4. Link GitHub repo
railway link

# 5. Set all environment variables
railway variables set ANTHROPIC_API_KEY=...
railway variables set SUPABASE_URL=...
railway variables set SUPABASE_ANON_KEY=...
railway variables set INSTAGRAM_ACCESS_TOKEN=...
railway variables set INSTAGRAM_ACCOUNT_ID=...
railway variables set CLOUDFLARE_R2_BUCKET=...
railway variables set CLOUDFLARE_R2_ACCESS_KEY=...
railway variables set CLOUDFLARE_R2_SECRET_KEY=...
railway variables set IG_TIMEZONE=Asia/Kolkata

# 6. Deploy
railway up
```

### `railway.toml` (put in project root)
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "./Dockerfile"

[deploy]
startCommand = "python src/scripts/run_scheduler.py"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[[services]]
name = "reelmind"

[[services.cron]]
schedule = "0 14 * * *"  # 2pm UTC = 7:30pm IST daily
command = "python src/scripts/run_reel.py"
```

### `Dockerfile` (minimal, production-grade)
```dockerfile
FROM python:3.11-slim

# Install FFmpeg (essential for video analysis)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download Whisper model at build time (saves startup time)
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"

# Copy source
COPY src/ ./src/
COPY CLAUDE.md .

# Health check
EXPOSE 8000

CMD ["python", "src/scripts/run_scheduler.py"]
```

---

## PHASE 9 — Free Cloudflare R2 for Video Storage

Your rendered videos need a public URL for the Instagram API. Cloudflare R2 gives you 10GB free forever.

```bash
# 1. Go to cloudflare.com → R2 → Create bucket: ekfollowekchara-reelmind
# 2. Make bucket public (required for Instagram API video_url)
# 3. Get Access Key + Secret Key from R2 API tokens
# 4. In your code:

import boto3
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

# Upload rendered video
s3.upload_file("rendered_reel.mp4", "ekfollowekchara-reelmind", "reel_20240422.mp4",
               ExtraArgs={"ContentType": "video/mp4"})

# Get public URL
video_url = f"https://pub-{ACCOUNT_ID}.r2.dev/reel_20240422.mp4"
```

---

## The Edit Problem — Where to Render the Video

The system produces an **edit manifest JSON** (what to cut, when, what music, what text overlay). You need something to turn that into an actual .mp4. Options ranked by cost:

| Option | Cost | Quality | Setup |
|--------|------|---------|-------|
| **CapCut API** | Free (limited) | Excellent | Medium |
| **FFmpeg scripted edit** | Free | Good enough | Claude Code builds it |
| **MoviePy** | Free | Good | Claude Code builds it |
| **Hand off to you** | Free | Your choice | System outputs manifest, you edit |
| **Remotion** (code-to-video) | Free self-host | Excellent | Complex |

**Recommended for personal use:** Let the system produce the edit manifest + script, then use CapCut on your phone with the manifest as instructions. Or tell Claude Code to build an FFmpeg-based auto-editor using MoviePy. This takes 1 extra session.

Tell Claude Code:
```
Build src/tools/auto_editor.py using MoviePy.
Input: EditManifest JSON from Agent 07.
Output: rendered .mp4 at 1080x1920, uploaded to Cloudflare R2.
Return the public R2 URL.
```

---

## Monitoring for Free

### Option A — Grafana Cloud (free tier)
```bash
# Set up Prometheus metrics in your FastAPI health endpoint
# Connect to Grafana Cloud free tier
# Dashboard: posts published, agent errors, learning checkpoint status
```

### Option B — Supabase + simple dashboard
Query your post_log table directly. Add a simple FastAPI endpoint:
```
GET /dashboard → returns last 10 posts with performance metrics
```

### Option C — Telegram bot notifications (easiest)
```python
# Send yourself a Telegram message after each post
import httpx
httpx.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
          params={"chat_id": YOUR_CHAT_ID, 
                  "text": f"✅ Posted! {ig_url}\nQA: {qa_score}/100\nType: {reel_type}"})
```

---

## Total Cost Summary

| Service | Monthly Cost |
|---------|-------------|
| Anthropic API (1 reel/day, ~15 agent calls/reel) | ~$8–12 |
| Supabase (free tier) | $0 |
| Railway (free tier, 500 hrs/month) | $0 |
| Cloudflare R2 (10GB free) | $0 |
| Instagram API | $0 |
| GitHub | $0 |
| **Total** | **~$8–12/month** |

If you post 2x/day: ~$15–25/month. Still very low.

---

## The Prompt Tuning Cycle (Most Important Part)

After your first 10 real posts, the system's quality depends on how well-tuned the prompts are. Spend time here.

**Week 1–2:** Run with defaults. Watch output quality.

**Week 3:** Open Claude Code and say:
```
Read the last 10 posts from our Supabase post_log table.
Read the performance metrics for each.
Compare the hook_formula_id to hook_score for each post.
Tell me which hooks are underperforming and suggest improved
versions of those formulas in src/config/prompts.py SCRIPT_PROMPT.
```

**Month 1:** Say:
```
Read all 30 posts and their performance.
Read the audience_preference table in Supabase.
Rewrite the ORCHESTRATOR_PROMPT in prompts.py to be
more specific about what @ekfollowekchara's audience
actually responds to, based on the real data we now have.
```

This is the compounding advantage — the prompts get better as the data accumulates.

---

## Quick Reference: Claude Code Commands for Each Phase

```bash
# Phase 1 — Foundation
"Build the project skeleton from CLAUDE.md"

# Phase 2 — Ingestion
"Read skills/INGESTION.md — build the ingestion engine"

# Phase 3 — Memory
"Read skills/MEMORY.md — build all 6 memory store classes"

# Phase 4 — Agents
"Read skills/AGENTS.md — build Agents 01 through 06"
"Read skills/AGENTS.md — build Agents 07 through 13"

# Phase 5 — Pipeline
"Read skills/PIPELINE.md — build the LangGraph production DAG"

# Phase 6 — Instagram
"Read skills/INSTAGRAM.md — build the Instagram API client"

# Phase 7 — Auto Editor
"Build src/tools/auto_editor.py using MoviePy. Input: EditManifest. Output: .mp4 on R2."

# Phase 8 — Deploy
"Build Dockerfile, railway.toml, and GitHub Actions deploy workflow"

# Phase 9 — Tune
"Read post_log and hook_library from Supabase. Tune prompts based on real performance data."
```

---

## Files Checklist for Claude Code Sessions

Before each session, make sure these exist:
- [ ] `CLAUDE.md` in project root (always)
- [ ] `skills/INGESTION.md` before Session 2
- [ ] `skills/MEMORY.md` before Session 3
- [ ] `skills/AGENTS.md` before Sessions 4 and 5
- [ ] `skills/PIPELINE.md` before Session 6
- [ ] `skills/INSTAGRAM.md` before Session 7

These files are what make Claude Code build things correctly the first time. Without them, it guesses. With them, it executes.

---

## Final Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  YOUR MACHINE (one-time)                                        │
│  Raw clips → ingest_clips.py → Supabase clips table + pgvector │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ↓ (daily, Railway cron)
┌─────────────────────────────────────────────────────────────────┐
│  RAILWAY (hosted, free tier)                                    │
│                                                                 │
│  [02 Trend] → [03 Orchestrator*] → [04 Type Selector]          │
│                     ↑                       ↓                  │
│               6 Memory Stores        [05 Clip Select]          │
│                 (Supabase)                  ↓                  │
│  [13 Learning] ← [12 Audience] ←     [06 Script]              │
│       ↑          [11 Analytics]           ↓                   │
│       │               ↑             [07 Edit Spec]            │
│       │               │                   ↓                   │
│       │         [10 Publisher]       [08 Caption]             │
│       │               ↑                   ↓                   │
│       │         Cloudflare R2        [09 QA] ←──────────┐    │
│       │         (video storage)            ↓             │    │
│       │                            APPROVED / REVISION───┘    │
│       │                                    ↓                  │
│       └─────── T+1h/24h/7d/30d ←── Instagram Graph API        │
│                                                                 │
│  * Orchestrator reads all 6 memory stores before each brief    │
└─────────────────────────────────────────────────────────────────┘
```

**This system, once running, requires zero daily input from you.**
Drop clips into the folder. The agents do the rest.
