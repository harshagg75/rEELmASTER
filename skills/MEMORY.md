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
