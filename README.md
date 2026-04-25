# ReelMind

Autonomous Instagram Reels production system

Drop raw clips into a folder. The system researches trends, selects clips, writes scripts, edits video, generates captions, publishes, tracks performance, and learns — all without manual input.

---

## What It Does

ReelMind runs a 13-agent AI pipeline that handles the full lifecycle of an Instagram Reel:

1. **Ingests** your raw video clips into a searchable library with quality scores and semantic embeddings
2. **Researches** trending audio and content formats in the Hindi-English motivational niche
3. **Plans** each reel using memory from all past performance data
4. **Selects** clips using vector similarity search against a strategy-specific brief
5. **Writes** a script and storyboard with proven hook formulas
6. **Edits** the video automatically via MoviePy
7. **Generates** captions and hashtags calibrated to real velocity data
8. **QA checks** against 6 criteria before publish
9. **Publishes** to Instagram via the Graph API
10. **Learns** from performance at T+1h, T+24h, T+7d, and T+30d checkpoints

Zero manual effort after the initial clip drop.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Agents | Anthropic API — `claude-sonnet-4-6` (agents), `claude-opus-4-6` (orchestrator) |
| Database | Supabase PostgreSQL + pgvector |
| Transcription | faster-whisper (local, free) |
| Video Analysis | FFmpeg + FFprobe |
| Video Editing | MoviePy |
| Agent Pipeline | LangGraph |
| Scheduling | APScheduler + SQLAlchemy jobstore |
| Video Storage | Cloudflare R2 (10 GB free tier) |
| Publishing | Instagram Graph API v21.0 |
| Hosting | Railway |
| Language | Python 3.11 |

---

## Project Structure

```
reelmind/
├── clips/                      ← drop raw .mp4 clips here
├── outputs/                    ← rendered reels land here
├── audio/                      ← reference audio files
├── skills/                     ← implementation guides per phase
│   ├── INGESTION.md
│   ├── MEMORY.md
│   ├── AGENTS.md
│   ├── PIPELINE.md
│   ├── INSTAGRAM.md
│   └── EDITOR.md
├── src/
│   ├── config/
│   │   ├── settings.py         ← all env vars and constants
│   │   └── prompts.py          ← all agent system prompts
│   ├── memory/
│   │   ├── schema.py           ← Pydantic models for every data structure
│   │   └── stores.py           ← 6 memory store classes (Supabase)
│   ├── agents/                 ← 13 agent files (one class each)
│   ├── tools/
│   │   ├── claude_client.py    ← Anthropic API wrapper
│   │   ├── video_analysis.py   ← FFprobe + scene detection
│   │   ├── transcription.py    ← faster-whisper local transcription
│   │   ├── vector_db.py        ← Supabase pgvector client
│   │   ├── instagram_api.py    ← publish + analytics + comments
│   │   ├── r2_storage.py       ← Cloudflare R2 upload/URL
│   │   └── auto_editor.py      ← MoviePy: EditManifest → .mp4
│   ├── pipeline/
│   │   ├── graph.py            ← LangGraph production DAG
│   │   ├── learning_loop.py    ← APScheduler checkpoint jobs
│   │   └── scheduler.py        ← daily cron entry point
│   └── scripts/
│       ├── ingest_clips.py     ← one-time library ingestion CLI
│       ├── run_reel.py         ← on-demand reel production
│       └── health.py           ← FastAPI /health for Railway
├── tests/
├── migrations/
│   └── 001_initial_schema.sql
├── Dockerfile
├── railway.toml
├── requirements.txt
└── .env.example
```

---

## Setup

### Prerequisites

- Python 3.11
- FFmpeg installed and on PATH
- Supabase project (free tier works)
- Cloudflare R2 bucket
- Instagram Business account + Graph API token
- Anthropic API key

### 1. Clone and install

```bash
git clone https://github.com/yourusername/reelmind.git
cd reelmind
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...
INSTAGRAM_ACCOUNT_ID=17841...
INSTAGRAM_ACCESS_TOKEN=EAAx...
CF_ACCOUNT_ID=abc123
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
```

### 3. Run database migrations

```bash
# Paste migrations/001_initial_schema.sql into Supabase SQL editor, or:
supabase db push
```

### 4. Ingest your clip library

Drop all your raw `.mp4` files into the `clips/` folder, then:

```bash
python src/scripts/ingest_clips.py --clips-dir ./clips
```

This analyzes every clip for quality, transcribes speech, generates embeddings, and stores everything in Supabase. Use `--resume` to continue an interrupted run. Use `--dry-run` to preview without writing.

### 5. Produce a reel

```bash
python src/scripts/run_reel.py
```

The full 10-agent pipeline runs and publishes to Instagram. Add `--dry-run` to stop before publish.

---

## The 13 Agents

| # | Agent | Model | Role |
|---|---|---|---|
| 01 | Clip Ingestion | Sonnet | Analyzes raw clips — quality score, mood, shot type, transcript summary, scene tags. Generates pgvector embedding for semantic search. |
| 02 | Trend Research | Sonnet + web_search | Scans current trends in Hindi-English motivational content. Flags trending audio with urgency: LOW / MEDIUM / HIGH. |
| 03 | Orchestrator | **Opus** | Reads all 6 memory stores and produces a specific, opinionated production brief. The brain of the system. |
| 04 | Type Selector | Sonnet | Chooses the reel strategy for this post, enforcing hard constraints (no 3 of same type in a row, series cap, trend_surfer gating). |
| 05 | Clip Selection | Sonnet | Runs vector search + strategy-specific SQL filters to find the best clips. Enforces shot-type diversity in the final ordering. |
| 06 | Script | Sonnet | Writes the full script and storyboard. Picks a proven hook formula from the library or invents a new experimental one (20% of posts). |
| 07 | Edit Spec | Sonnet | Produces the EditManifest: exact cut points, transitions, text overlays, color grade, and audio sync instructions. |
| 08 | Caption | Sonnet | Generates caption copy and hashtag sets calibrated to real hashtag velocity data. Outputs multiple variants. |
| 09 | QA | Sonnet | 6-check gate: policy → audio licensing → copyright → type consistency → caption energy → quality score. Triggers targeted revision loops. |
| 10 | Publisher | Sonnet + IG API | Uploads video to R2, creates Instagram media container, polls until ready, publishes, drops hashtags as first comment. |
| 11 | Analytics | Sonnet + IG API | Fetches post insights at each learning checkpoint. Computes engagement depth, hook score, save rate, discovery percent. |
| 12 | Audience | Sonnet | Runs NLP on post comments at T+7d and T+30d to extract topic preferences, sentiment, and audience signals. |
| 13 | Learning | Sonnet | The only agent that writes to memory stores. Updates all 6 stores using hardcoded math formulas, then uses Claude to write a delta report for the Orchestrator. |

---

## The 6 Reel Strategies

| Strategy | Clip Rule | Cadence | Key Constraint |
|---|---|---|---|
| `fresh_drop` | `usage_count = 0` only | 2–3x / week | Highest discovery potential; never reuse clips |
| `hybrid_mix` | 50% proven (score ≥ 75) + 50% fresh | 1–2x / week | Interleaved; no two proven clips consecutive |
| `concept_remix` | Clips from a specific past reel | 1x / week | Edit style must differ from the source reel |
| `series` | Any clips, narrative continuity | 1x / week | Max 2 active series at once |
| `trend_surfer` | Best audio-fit clips | When trends emerge | Only when Trend Agent returns urgency = HIGH |
| `best_of` | `performance_tier = 'top_10_percent'` only | Monthly | Only on milestones or 28+ days since last best_of |

**Hard rule:** never the same strategy 3 posts in a row.

---

## The Learning Loop

Every published reel triggers 4 scheduled checkpoints that run automatically:

```
Post published
    │
    ├── T+1h   → Agent 11 fetches early metrics → updates hook_library scores
    │
    ├── T+24h  → Agent 11 + Agent 13 → updates clip_performance, hashtag_velocity
    │
    ├── T+7d   → Agents 11 + 12 + 13 → full cycle → updates format_performance,
    │            audience_preference, comment NLP analysis
    │
    └── T+30d  → Agents 11 + 12 + 13 → monthly audit → updates optimal_timing,
                 re-normalizes all stores, writes Orchestrator delta report
```

The Orchestrator reads all 6 memory stores before every new reel brief. Over time the system learns:
- Which hook formulas retain viewers past 60%
- Which clips perform best in which reel types
- Which hashtag tiers actually drive discovery
- What day/hour gets the highest first-hour velocity
- What topics and emotions the audience responds to most

No human intervention needed after the initial setup.

---

## Deployment (Railway)

### One-click deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

### Manual deploy

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and link
railway login
railway init

# Set environment variables
railway vars set ANTHROPIC_API_KEY=sk-ant-... SUPABASE_URL=... # (all vars from .env)

# Deploy
railway up
```

The `railway.toml` configures:
- **Web service**: FastAPI `/health` endpoint (keeps the dyno alive)
- **Worker**: APScheduler process for learning loop checkpoints
- **Cron**: Daily reel production trigger

APScheduler uses a Supabase-backed SQLAlchemy jobstore so scheduled checkpoints survive Railway restarts and redeploys.

### Health check

```
GET https://your-app.railway.app/health
→ {"status": "ok", "pending_checkpoints": 3, "last_post": "2026-04-25T08:30:00Z"}
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service role key |
| `INSTAGRAM_ACCOUNT_ID` | Instagram Business account ID |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram Graph API long-lived token |
| `INSTAGRAM_APP_ID` | Meta app ID (for token refresh) |
| `INSTAGRAM_APP_SECRET` | Meta app secret (for token refresh) |
| `CF_ACCOUNT_ID` | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Cloudflare R2 access key |
| `R2_SECRET_ACCESS_KEY` | Cloudflare R2 secret key |
| `R2_BUCKET_NAME` | R2 bucket name (default: `ekfollowekchara-reelmind`) |
| `DATABASE_URL` | Supabase Postgres URL (for APScheduler jobstore) |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
