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
