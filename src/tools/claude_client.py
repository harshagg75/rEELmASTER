import json
import re
from typing import Any

import anthropic
from loguru import logger

from src.config import settings

_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def call_claude(system: str, user: str, model: str | None = None) -> str:
    model = model or settings.MODEL_AGENT
    logger.debug(f"[ClaudeClient] Calling {model} | prompt chars: {len(user)}")
    try:
        response = _client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text
    except anthropic.APIStatusError as e:
        logger.error(f"[ClaudeClient] API status error {e.status_code}: {e.message}")
        raise
    except anthropic.APIConnectionError as e:
        logger.error(f"[ClaudeClient] Connection error: {e}")
        raise


def call_claude_with_search(system: str, user: str) -> str:
    """Call claude-sonnet with the server-side web_search tool enabled."""
    logger.debug(f"[ClaudeClient] Calling {settings.MODEL_AGENT} with web_search")
    try:
        response = _client.messages.create(
            model=settings.MODEL_AGENT,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
        )
        # Server-side tool — extract only TextBlock items from the response
        text_blocks = [
            block.text
            for block in response.content
            if block.type == "text"
        ]
        return "\n".join(text_blocks)
    except anthropic.APIStatusError as e:
        logger.error(f"[ClaudeClient] Search API error {e.status_code}: {e.message}")
        raise
    except anthropic.APIConnectionError as e:
        logger.error(f"[ClaudeClient] Connection error: {e}")
        raise


def parse_json_response(raw: str) -> dict[str, Any]:
    """Strip markdown code fences then parse JSON. Raises ValueError on failure."""
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(
            f"[ClaudeClient] JSON parse failed at char {e.pos}. "
            f"Raw preview: {raw[:300]!r}"
        )
        raise ValueError(f"Agent returned invalid JSON: {e}") from e
