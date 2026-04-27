from datetime import date

from loguru import logger

from src.config import prompts as P
from src.memory.schema import TrendBrief
from src.tools.claude_client import call_claude_with_search, parse_json_response


class TrendResearchAgent:
    """
    Agent 02 — Trend Research.
    Uses web_search to find what is trending RIGHT NOW in the Hindi-English niche.
    Always includes today's date in the prompt.
    """

    def run(self) -> TrendBrief:
        logger.info("[TrendResearch] Searching for current trends...")
        user_msg = self._build_prompt()
        try:
            raw = call_claude_with_search(P.TREND_RESEARCH_PROMPT, user_msg)
            data = parse_json_response(raw)
        except Exception as e:
            logger.error(f"[TrendResearch] Failed: {e}")
            raise
        trend = TrendBrief(**data)
        logger.success(
            f"[TrendResearch] Done | urgency={trend.overall_urgency} | "
            f"{len(trend.trending_audios)} audios | {len(trend.content_themes)} themes"
        )
        return trend

    def _build_prompt(self) -> str:
        return (
            f"Today's date: {date.today().isoformat()}\n\n"
            "Search for what is trending RIGHT NOW in the Instagram Reels space for the "
            "motivational/lifestyle Hindi-English niche targeting North Indian millennials and Gen Z.\n\n"
            "Search specifically for:\n"
            "1. Trending Reels audio/songs in India right now (Bollywood, indie, lo-fi, motivational speech)\n"
            "2. Trending Reels formats in Hindi motivational niche\n"
            "3. Trending hashtags in #motivation #hinglish #northindia #desilifestyle clusters\n"
            "4. Upcoming cultural moments or festivals in next 7-14 days relevant to North India\n"
            "5. Viral Hinglish phrases appearing in trending reels\n\n"
            "Make multiple searches. Return the complete JSON TrendBrief."
        )
