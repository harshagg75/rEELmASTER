"""
src/memory/stores.py — 6 Supabase-backed memory stores.
Read by any agent; written ONLY by Agent 13 (Learning).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger

try:
    from supabase import Client, create_client
    _supabase_available = True
except ImportError:
    _supabase_available = False
    logger.warning("[Memory] supabase-py not installed; stores will be unavailable.")


def _get_client() -> "Client":
    from src.config import settings
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


class HookLibraryStore:
    """Memory Store 1 — Hook formula effectiveness scores."""

    def get_top_n(self, n: int = 10) -> list[dict]:
        try:
            res = (
                _get_client()
                .table("hook_library")
                .select("formula_id,formula_name,formula_pattern,score,avg_watch_time_percent,is_experimental")
                .order("score", desc=True)
                .limit(n)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"[HookLibrary] get_top_n failed: {e}")
            return []

    def update_score(self, formula_id: str, watch_time_pct: float) -> None:
        """score += 10 if watch >= 0.60, -= 5 if watch <= 0.30 (from MEMORY.md)"""
        try:
            client = _get_client()
            existing = (
                client.table("hook_library")
                .select("score,times_used")
                .eq("formula_id", formula_id)
                .single()
                .execute()
            )
            row = existing.data
            if not row:
                logger.warning(f"[HookLibrary] formula_id {formula_id} not found")
                return
            score = row["score"]
            if watch_time_pct >= 0.60:
                score += 10
            elif watch_time_pct <= 0.30:
                score -= 5
            score = max(0.0, min(100.0, score))
            client.table("hook_library").update({
                "score": score,
                "times_used": row["times_used"] + 1,
                "avg_watch_time_percent": watch_time_pct,
                "last_tested": datetime.now(timezone.utc).isoformat(),
            }).eq("formula_id", formula_id).execute()
        except Exception as e:
            logger.error(f"[HookLibrary] update_score failed for {formula_id}: {e}")

    def seed_defaults(self) -> None:
        """Insert 10 default hook formulas; skip if already present."""
        defaults = [
            ("H001", "Limiting Belief Challenge",
             "Open with a sharp question that challenges a common limiting belief",
             "Kya sach mein tune apne aap ko rok rakha hai?"),
            ("H002", "Nobody Talks About This",
             "Start with 'koi nahi bolta' + uncomfortable truth",
             "Koi nahi bolta — mehnat ke saath direction bhi chahiye."),
            ("H003", "Soft Hindi Poetry Opener",
             "Open with a poetic Hindi line that lands like a quiet revelation",
             "Kuch raste woh hote hain jo dikhte nahi — feel hote hain."),
            ("H004", "POV Hook",
             "POV: something has just changed. Drop the viewer into a moment.",
             "POV: tune kal se rehna band kar diya."),
            ("H005", "Uncomfortable Stat",
             "Open with a real/relatable statistic about Indian 20-somethings",
             "India mein 68% 20-somethings apne passion se door hain."),
            ("H006", "The Reframe",
             "Take something the viewer thinks is bad and reframe it as strength",
             "Slow progress is still progress. Ruk jaana alag baat hai."),
            ("H007", "Time Contrast",
             "Contrast where you were vs where you are / could be",
             "Ek saal pehle aur aaj — dono same insaan? Ya kuch badla?"),
            ("H008", "Direct Address",
             "Speak directly to one person who feels stuck or behind",
             "Yeh wali reel uss insaan ke liye hai jo thak gaya hai."),
            ("H009", "Permission Slip",
             "Give the viewer permission to feel something they have been suppressing",
             "It is okay to not have it all figured out. Seriously."),
            ("H010", "Silent Truth",
             "State something everyone knows but nobody says out loud",
             "Sab jaante hain, koi nahi bolega — growth mein dard hota hai."),
        ]
        rows = [
            {
                "formula_id": fid, "formula_name": fname,
                "formula_pattern": fpat, "example": fex, "score": 50.0,
            }
            for fid, fname, fpat, fex in defaults
        ]
        try:
            _get_client().table("hook_library").upsert(rows, on_conflict="formula_id").execute()
            logger.success(f"[HookLibrary] Seeded {len(rows)} hook formulas.")
        except Exception as e:
            logger.error(f"[HookLibrary] seed_defaults failed: {e}")


class ClipPerformanceStore:
    """Memory Store 2 — Clip usage and performance (reads/writes clips table)."""

    def get_fresh(self, limit: int = 20) -> list[dict]:
        """Unused clips (usage_count = 0), best quality first."""
        try:
            res = (
                _get_client()
                .table("clips")
                .select("clip_id,file_path,quality_score,mood,shot_type,scene_tags,emotion_tags,usage_count")
                .eq("usage_count", 0)
                .neq("quality_flag", "reject")
                .order("quality_score", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"[ClipPerformance] get_fresh failed: {e}")
            return []

    def get_proven(self, min_score: float = 75.0, max_usage: int = 5) -> list[dict]:
        """Clips with good performance score and not yet overused."""
        try:
            res = (
                _get_client()
                .table("clips")
                .select("clip_id,file_path,quality_score,performance_score,mood,shot_type,usage_count")
                .gte("performance_score", min_score)
                .lte("usage_count", max_usage)
                .neq("quality_flag", "reject")
                .eq("overused_flag", False)
                .order("performance_score", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"[ClipPerformance] get_proven failed: {e}")
            return []

    def get_top_10_percent(self) -> list[dict]:
        """Clips with performance_tier = 'top_10_percent' (used by best_of reel type)."""
        try:
            res = (
                _get_client()
                .table("clips")
                .select("clip_id,file_path,quality_score,performance_score,mood,shot_type")
                .eq("performance_tier", "top_10_percent")
                .order("performance_score", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"[ClipPerformance] get_top_10_percent failed: {e}")
            return []

    def update_score(self, clip_id: str, engagement_depth: float) -> None:
        """new_score = old_score * 0.7 + engagement_depth * 100 * 0.3 (from MEMORY.md)"""
        try:
            client = _get_client()
            existing = (
                client.table("clips")
                .select("performance_score")
                .eq("clip_id", clip_id)
                .single()
                .execute()
            )
            row = existing.data
            if not row:
                logger.warning(f"[ClipPerformance] clip_id {clip_id} not found")
                return
            new_score = row["performance_score"] * 0.7 + engagement_depth * 100 * 0.3
            new_score = round(max(0.0, min(100.0, new_score)), 2)
            tier = (
                "top_10_percent" if new_score >= 90
                else ("average" if new_score >= 50 else "underperformer")
            )
            client.table("clips").update({
                "performance_score": new_score,
                "performance_tier": tier,
            }).eq("clip_id", clip_id).execute()
        except Exception as e:
            logger.error(f"[ClipPerformance] update_score failed for {clip_id}: {e}")

    def increment_usage(self, clip_id: str, reel_id: str) -> None:
        """Increment usage_count; set overused_flag when count reaches 10."""
        try:
            client = _get_client()
            existing = (
                client.table("clips")
                .select("usage_count")
                .eq("clip_id", clip_id)
                .single()
                .execute()
            )
            row = existing.data
            if not row:
                return
            new_count = row["usage_count"] + 1
            client.table("clips").update({
                "usage_count": new_count,
                "last_used_reel_id": reel_id,
                "overused_flag": new_count >= 10,
            }).eq("clip_id", clip_id).execute()
        except Exception as e:
            logger.error(f"[ClipPerformance] increment_usage failed for {clip_id}: {e}")

    def get_freshness_index(self) -> dict:
        """Return {fresh, total, ratio} of unused vs all clips."""
        try:
            fresh_res = (
                _get_client()
                .table("clips")
                .select("clip_id", count="exact")
                .eq("usage_count", 0)
                .execute()
            )
            total_res = (
                _get_client()
                .table("clips")
                .select("clip_id", count="exact")
                .execute()
            )
            fresh = fresh_res.count or 0
            total = total_res.count or 0
            return {
                "fresh": fresh,
                "total": total,
                "ratio": round(fresh / total, 2) if total else 0.0,
            }
        except Exception as e:
            logger.warning(f"[ClipPerformance] get_freshness_index failed: {e}")
            return {"fresh": 0, "total": 0, "ratio": 0.0}


class HashtagVelocityStore:
    """Memory Store 3 — Hashtag performance and weekly decay."""

    def get_by_tier(self, tier: int, limit: int = 30) -> list[dict]:
        try:
            res = (
                _get_client()
                .table("hashtag_velocity")
                .select("tag,tier,velocity,times_used,avg_discovery_percent")
                .eq("tier", tier)
                .eq("is_dead", False)
                .order("velocity", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"[HashtagVelocity] get_by_tier failed: {e}")
            return []

    def update_velocity(self, tag: str, discovery_pct: float) -> None:
        """Set velocity = discovery_pct and bump times_used."""
        try:
            client = _get_client()
            existing = (
                client.table("hashtag_velocity")
                .select("times_used")
                .eq("tag", tag)
                .single()
                .execute()
            )
            row = existing.data
            if not row:
                logger.warning(f"[HashtagVelocity] tag '{tag}' not found")
                return
            client.table("hashtag_velocity").update({
                "velocity": discovery_pct,
                "avg_discovery_percent": discovery_pct,
                "times_used": row["times_used"] + 1,
                "last_used": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("tag", tag).execute()
        except Exception as e:
            logger.warning(f"[HashtagVelocity] update_velocity failed for {tag}: {e}")

    def apply_weekly_decay(self) -> None:
        """velocity *= 0.98; mark dead if velocity < 0.01 (from MEMORY.md)."""
        try:
            client = _get_client()
            all_tags = (
                client.table("hashtag_velocity")
                .select("tag,velocity")
                .eq("is_dead", False)
                .execute()
                .data or []
            )
            now = datetime.now(timezone.utc).isoformat()
            for row in all_tags:
                new_vel = round(row["velocity"] * 0.98, 4)
                client.table("hashtag_velocity").update({
                    "velocity": new_vel,
                    "is_dead": new_vel < 0.01,
                    "updated_at": now,
                }).eq("tag", row["tag"]).execute()
            logger.info(f"[HashtagVelocity] Weekly decay applied to {len(all_tags)} tags.")
        except Exception as e:
            logger.error(f"[HashtagVelocity] apply_weekly_decay failed: {e}")

    def add_from_trend_research(self, tags: list[str], tier: int) -> None:
        """Insert new hashtags discovered by Agent 02 (Trend Research)."""
        rows = [
            {
                "tag": t, "tier": tier, "from_trend_research": True,
                "velocity": 50.0, "avg_discovery_percent": 0.0,
            }
            for t in tags
        ]
        try:
            _get_client().table("hashtag_velocity").upsert(rows, on_conflict="tag").execute()
        except Exception as e:
            logger.error(f"[HashtagVelocity] add_from_trend_research failed: {e}")


class FormatPerformanceStore:
    """Memory Store 4 — Reel format effectiveness by (type x duration_bucket x energy)."""

    def update(
        self,
        reel_type: str,
        duration_sec: float,
        energy: str,
        engagement_depth: float,
        save_rate: float,
        hook_score: float,
    ) -> None:
        """Rolling average per (reel_type, bucket, energy) combo."""
        bucket = self._duration_bucket(duration_sec)
        try:
            client = _get_client()
            existing = (
                client.table("format_performance")
                .select("id,avg_engagement_depth,avg_save_rate,avg_hook_score,data_points")
                .eq("reel_type", reel_type)
                .eq("duration_bucket", bucket)
                .eq("energy_level", energy)
                .execute()
            )
            rows = existing.data or []
            now = datetime.now(timezone.utc).isoformat()
            if rows:
                r = rows[0]
                n = r["data_points"]
                new_n = n + 1

                def rolling(old: float, new: float) -> float:
                    return round((old * n + new) / new_n, 4)

                client.table("format_performance").update({
                    "avg_engagement_depth": rolling(r["avg_engagement_depth"], engagement_depth),
                    "avg_save_rate": rolling(r["avg_save_rate"], save_rate),
                    "avg_hook_score": rolling(r["avg_hook_score"], hook_score),
                    "data_points": new_n,
                    "decay_flag": False,
                    "updated_at": now,
                }).eq("id", r["id"]).execute()
            else:
                client.table("format_performance").insert({
                    "reel_type": reel_type,
                    "duration_bucket": bucket,
                    "energy_level": energy,
                    "avg_engagement_depth": engagement_depth,
                    "avg_save_rate": save_rate,
                    "avg_hook_score": hook_score,
                    "data_points": 1,
                    "updated_at": now,
                }).execute()
        except Exception as e:
            logger.error(f"[FormatPerformance] update failed: {e}")

    def get_best(self) -> list[dict]:
        """Top 5 non-decayed format combos by engagement depth (min 2 data points)."""
        try:
            res = (
                _get_client()
                .table("format_performance")
                .select("reel_type,duration_bucket,energy_level,avg_engagement_depth,avg_save_rate,data_points")
                .eq("decay_flag", False)
                .gte("data_points", 2)
                .order("avg_engagement_depth", desc=True)
                .limit(5)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"[FormatPerformance] get_best failed: {e}")
            return []

    def flag_decay(self, reel_type: str) -> None:
        """Mark all combos for a reel_type as decaying."""
        try:
            _get_client().table("format_performance").update({
                "decay_flag": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("reel_type", reel_type).execute()
        except Exception as e:
            logger.error(f"[FormatPerformance] flag_decay failed: {e}")

    @staticmethod
    def _duration_bucket(duration_sec: float) -> str:
        if duration_sec < 15:
            return "under_15s"
        elif duration_sec < 25:
            return "15-25s"
        elif duration_sec < 40:
            return "25-40s"
        elif duration_sec < 60:
            return "40-60s"
        return "60s_plus"


class AudiencePreferenceStore:
    """Memory Store 5 — Topic and content preference weights."""

    def update_topic(self, topic: str, comment_volume: int, save_rate: float) -> None:
        """Blended weight = (comment_volume/100)*0.4 + save_rate*0.6."""
        new_weight = round(
            min(1.0, max(0.0, (comment_volume / 100) * 0.4 + save_rate * 0.6)), 4
        )
        try:
            client = _get_client()
            existing = (
                client.table("audience_preference")
                .select("weight,data_points")
                .eq("preference_key", topic)
                .execute()
            )
            rows = existing.data or []
            now = datetime.now(timezone.utc).isoformat()
            if rows:
                r = rows[0]
                n = r["data_points"]
                blended = round((r["weight"] * n + new_weight) / (n + 1), 4)
                client.table("audience_preference").update({
                    "weight": blended,
                    "data_points": n + 1,
                    "last_updated": now,
                }).eq("preference_key", topic).execute()
            else:
                client.table("audience_preference").insert({
                    "preference_key": topic,
                    "category": "topic",
                    "weight": new_weight,
                    "data_points": 1,
                    "last_updated": now,
                }).execute()
        except Exception as e:
            logger.error(f"[AudiencePreference] update_topic failed for {topic}: {e}")

    def get_top_topics(self, n: int = 5) -> list[dict]:
        try:
            res = (
                _get_client()
                .table("audience_preference")
                .select("preference_key,weight,data_points")
                .eq("category", "topic")
                .order("weight", desc=True)
                .limit(n)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.warning(f"[AudiencePreference] get_top_topics failed: {e}")
            return []

    def get_full_model(self) -> dict[str, float]:
        """Return all preference weights as {key: weight}."""
        try:
            res = _get_client().table("audience_preference").select("preference_key,weight").execute()
            return {r["preference_key"]: r["weight"] for r in (res.data or [])}
        except Exception as e:
            logger.warning(f"[AudiencePreference] get_full_model failed: {e}")
            return {}


class OptimalTimingStore:
    """Memory Store 6 — Best posting day/hour slots."""

    def record(self, day_of_week: int, hour: int, first_hour_velocity: float) -> None:
        """Rolling average of first_hour_velocity per (day, hour) slot."""
        try:
            client = _get_client()
            existing = (
                client.table("optimal_timing")
                .select("avg_first_hour_velocity,data_points")
                .eq("day_of_week", day_of_week)
                .eq("hour", hour)
                .execute()
            )
            rows = existing.data or []
            now = datetime.now(timezone.utc).isoformat()
            if rows:
                r = rows[0]
                n = r["data_points"]
                new_avg = round(
                    (r["avg_first_hour_velocity"] * n + first_hour_velocity) / (n + 1), 4
                )
                client.table("optimal_timing").update({
                    "avg_first_hour_velocity": new_avg,
                    "data_points": n + 1,
                    "updated_at": now,
                }).eq("day_of_week", day_of_week).eq("hour", hour).execute()
            else:
                client.table("optimal_timing").insert({
                    "day_of_week": day_of_week,
                    "hour": hour,
                    "avg_first_hour_velocity": first_hour_velocity,
                    "data_points": 1,
                    "updated_at": now,
                }).execute()
        except Exception as e:
            logger.error(f"[OptimalTiming] record failed: {e}")

    def get_best_slot(self) -> dict:
        """Return (day, hour) with highest avg first-hour velocity (min 2 data points)."""
        try:
            res = (
                _get_client()
                .table("optimal_timing")
                .select("day_of_week,hour,avg_first_hour_velocity,data_points")
                .gte("data_points", 2)
                .order("avg_first_hour_velocity", desc=True)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            if rows:
                return rows[0]
            return {"day_of_week": 5, "hour": 18, "avg_first_hour_velocity": 0.0, "data_points": 0}
        except Exception as e:
            logger.warning(f"[OptimalTiming] get_best_slot failed: {e}")
            return {"day_of_week": 5, "hour": 18, "avg_first_hour_velocity": 0.0, "data_points": 0}


class MemoryStores:
    """Aggregator for all 6 memory stores. Passed as context to Agent 03 (Orchestrator)."""

    def __init__(self) -> None:
        self.hooks = HookLibraryStore()
        self.clips = ClipPerformanceStore()
        self.hashtags = HashtagVelocityStore()
        self.formats = FormatPerformanceStore()
        self.audience = AudiencePreferenceStore()
        self.timing = OptimalTimingStore()

    def get_orchestrator_context(self) -> dict[str, Any]:
        """Read all 6 stores and return a compact summary for Agent 03."""
        return {
            "hook_library_top10": self.hooks.get_top_n(10),
            "freshness_index": self.clips.get_freshness_index(),
            "proven_clips_count": len(self.clips.get_proven()),
            "hashtags_tier1": self.hashtags.get_by_tier(tier=1, limit=20),
            "hashtags_tier2": self.hashtags.get_by_tier(tier=2, limit=10),
            "best_format": self.formats.get_best(),
            "audience_top_topics": self.audience.get_top_topics(n=8),
            "audience_full_model": self.audience.get_full_model(),
            "optimal_slot": self.timing.get_best_slot(),
        }


memory = MemoryStores()
