-- ReelMind — full database schema
-- Run this once in the Supabase SQL editor for your project.
-- Embedding dimension: 384 (paraphrase-multilingual-MiniLM-L12-v2)

-- ─────────────────────────────────────────────────────────────────────────────
-- Extensions
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. clips — video library + pgvector embeddings
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clips (
  id               UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
  clip_id          TEXT    UNIQUE NOT NULL,
  file_path        TEXT    NOT NULL,
  quality_score    FLOAT   NOT NULL,
  quality_flag     TEXT    NOT NULL CHECK (quality_flag IN ('usable','borderline','reject')),
  shot_type        TEXT,
  movement_energy  INT,
  scene_tags       TEXT[],
  emotion_tags     TEXT[],
  face_present     BOOL    DEFAULT FALSE,
  transcript_summary TEXT,
  mood             TEXT,
  color_palette    TEXT,
  usable_segments  JSONB,
  embedding        vector(384),   -- paraphrase-multilingual-MiniLM-L12-v2
  usage_count      INT     DEFAULT 0,
  performance_score FLOAT  DEFAULT 50,
  performance_tier TEXT    DEFAULT 'average',
  last_used_reel_id TEXT,
  overused_flag    BOOL    DEFAULT FALSE,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS clips_embedding_idx    ON clips USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS clips_usage_idx        ON clips (usage_count);
CREATE INDEX IF NOT EXISTS clips_performance_idx  ON clips (performance_score DESC);
CREATE INDEX IF NOT EXISTS clips_quality_idx      ON clips (quality_flag);
CREATE INDEX IF NOT EXISTS clips_mood_idx         ON clips (mood);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. hook_library — hook formula scores (Memory Store 1)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hook_library (
  formula_id              TEXT PRIMARY KEY,
  formula_name            TEXT NOT NULL,
  formula_pattern         TEXT NOT NULL,
  example                 TEXT,
  score                   FLOAT   DEFAULT 50,
  times_used              INT     DEFAULT 0,
  avg_watch_time_percent  FLOAT   DEFAULT 0,
  last_tested             TIMESTAMPTZ,
  trend_delta             FLOAT   DEFAULT 0,
  is_experimental         BOOL    DEFAULT FALSE,
  created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. hashtag_velocity — hashtag performance (Memory Store 3)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS hashtag_velocity (
  tag                     TEXT PRIMARY KEY,
  tier                    INT  NOT NULL CHECK (tier IN (1,2,3)),
  velocity                FLOAT   DEFAULT 0,
  times_used              INT     DEFAULT 0,
  last_used               TIMESTAMPTZ,
  avg_discovery_percent   FLOAT   DEFAULT 0,
  is_dead                 BOOL    DEFAULT FALSE,
  from_trend_research     BOOL    DEFAULT FALSE,
  created_at              TIMESTAMPTZ DEFAULT NOW(),
  updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. format_performance — reel type × duration × energy (Memory Store 4)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS format_performance (
  id                      BIGSERIAL PRIMARY KEY,
  reel_type               TEXT NOT NULL,
  duration_bucket         TEXT NOT NULL,  -- e.g. '15-25s', '25-40s', '40-60s'
  energy_level            TEXT NOT NULL,  -- slow_build | steady | explosive | etc.
  avg_engagement_depth    FLOAT   DEFAULT 0,
  avg_save_rate           FLOAT   DEFAULT 0,
  avg_hook_score          FLOAT   DEFAULT 0,
  data_points             INT     DEFAULT 0,
  decay_flag              BOOL    DEFAULT FALSE,
  updated_at              TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (reel_type, duration_bucket, energy_level)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. audience_preference — topic/content weights (Memory Store 5)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audience_preference (
  preference_key  TEXT PRIMARY KEY,
  category        TEXT NOT NULL,
  weight          FLOAT   DEFAULT 0.5,
  data_points     INT     DEFAULT 0,
  last_updated    TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. optimal_timing — best posting slots (Memory Store 6)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS optimal_timing (
  day_of_week             INT  NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),  -- 0=Mon
  hour                    INT  NOT NULL CHECK (hour BETWEEN 0 AND 23),
  avg_first_hour_velocity FLOAT   DEFAULT 0,
  data_points             INT     DEFAULT 0,
  updated_at              TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (day_of_week, hour)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. post_log — learning loop backbone
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS post_log (
  post_id                 TEXT PRIMARY KEY,
  reel_type               TEXT,
  hook_formula_id         TEXT REFERENCES hook_library (formula_id) ON DELETE SET NULL,
  clip_ids                TEXT[],
  audio_id                TEXT,
  caption_variant         TEXT,
  hashtags_used           TEXT[],
  edit_style_class        TEXT,
  series_id               TEXT,
  episode_number          INT,
  output_video_filename   TEXT,
  recommended_post_time   TEXT,
  post_timestamp          TIMESTAMPTZ,         -- set when user confirms post is live
  checkpoints_completed   TEXT[]  DEFAULT '{}',
  latest_performance      JSONB,
  delta_report            JSONB,
  created_at              TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS post_log_reel_type_idx ON post_log (reel_type);
CREATE INDEX IF NOT EXISTS post_log_hook_idx      ON post_log (hook_formula_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. series_memory — active series tracking
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS series_memory (
  series_id               TEXT PRIMARY KEY,
  series_name             TEXT,
  episode_count           INT     DEFAULT 0,
  last_episode_summary    TEXT,
  next_episode_setup      TEXT,
  clip_ids_used           TEXT[]  DEFAULT '{}',
  status                  TEXT    DEFAULT 'active' CHECK (status IN ('active','completed','paused')),
  created_at              TIMESTAMPTZ DEFAULT NOW(),
  updated_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. orchestrator_deltas — learning reports for next brief
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orchestrator_deltas (
  id                      BIGSERIAL PRIMARY KEY,
  post_id                 TEXT REFERENCES post_log (post_id) ON DELETE CASCADE,
  checkpoint              TEXT NOT NULL,
  updates_applied         TEXT[],
  validation_flags        TEXT[],
  performance_summary     TEXT,
  what_worked             TEXT[],
  what_didnt              TEXT[],
  recommended_adjustments TEXT[],
  written_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Vector similarity search RPC (called by VectorDB.similarity_search)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION search_clips(query_embedding vector(384), match_count int)
RETURNS TABLE (
  clip_id          TEXT,
  file_path        TEXT,
  quality_score    FLOAT,
  quality_flag     TEXT,
  shot_type        TEXT,
  movement_energy  INT,
  scene_tags       TEXT[],
  emotion_tags     TEXT[],
  face_present     BOOL,
  transcript_summary TEXT,
  mood             TEXT,
  color_palette    TEXT,
  usable_segments  JSONB,
  usage_count      INT,
  performance_score FLOAT,
  performance_tier TEXT,
  similarity       FLOAT
)
LANGUAGE sql STABLE AS $$
  SELECT
    clip_id, file_path, quality_score, quality_flag, shot_type, movement_energy,
    scene_tags, emotion_tags, face_present, transcript_summary, mood, color_palette,
    usable_segments, usage_count, performance_score, performance_tier,
    1 - (embedding <=> query_embedding) AS similarity
  FROM clips
  ORDER BY embedding <=> query_embedding
  LIMIT match_count;
$$;

-- ─────────────────────────────────────────────────────────────────────────────
-- Seed: 10 default hook formulas for @ekfollowekchara
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO hook_library (formula_id, formula_name, formula_pattern, example, score)
VALUES
  ('H001', 'Limiting Belief Challenge',
   'Open with a sharp question that challenges a common limiting belief',
   'Kya sach mein tune apne aap ko rok rakha hai?',  50),
  ('H002', 'Nobody Talks About This',
   'Start with "koi nahi bolta" + uncomfortable truth',
   'Koi nahi bolta — mehnat ke saath direction bhi chahiye.',  50),
  ('H003', 'Soft Hindi Poetry Opener',
   'Open with a poetic Hindi line that lands like a quiet revelation',
   'Kuch raste woh hote hain jo dikhte nahi — feel hote hain.',  50),
  ('H004', 'POV Hook',
   'POV: something has just changed. Drop the viewer into a moment.',
   'POV: tune kal se rehna band kar diya.',  50),
  ('H005', 'Uncomfortable Stat',
   'Open with a real/relatable statistic about Indian 20-somethings',
   'India mein 68% 20-somethings apne passion se door hain.',  50),
  ('H006', 'The Reframe',
   'Take something the viewer thinks is bad and reframe it as strength',
   'Slow progress is still progress. Ruk jaana alag baat hai.',  50),
  ('H007', 'Time Contrast',
   'Contrast where you were vs where you are / could be',
   'Ek saal pehle aur aaj — dono same insaan? Ya kuch badla?',  50),
  ('H008', 'Direct Address',
   'Speak directly to one person who feels stuck or behind',
   'Yeh wali reel uss insaan ke liye hai jo thak gaya hai.',  50),
  ('H009', 'Permission Slip',
   'Give the viewer permission to feel something they have been suppressing',
   'It is okay to not have it all figured out. Seriously.',  50),
  ('H010', 'Silent Truth',
   'State something everyone knows but nobody says out loud',
   'Sab jaante hain, koi nahi bolega — growth mein dard hota hai.',  50)
ON CONFLICT (formula_id) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- updated_at trigger for clips
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER clips_updated_at
  BEFORE UPDATE ON clips
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
