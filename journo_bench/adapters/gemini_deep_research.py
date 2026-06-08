"""Gemini Deep Research runner — the agentic `interactions` API.

One submit + poll: `interactions.create(agent=..., input=..., background=True)`
returns immediately, then we poll `interactions.get(id)` until `completed`.
The report is `output_text`. Dormant without GOOGLE_API_KEY / GEMINI_API_KEY.

NOTE: confirm on the first live run whether `output_text` carries the source
URLs inline (it should, via citations). If sources come back in a separate
field instead, append them here so the report-text primary check can see them.
"""

from __future__ import annotations

import asyncio
import os

from ..metrics import record_metric
from ..pricing import gemini_deep_research_cost

AVAILABLE = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

# deep-research-max-preview-04-2026 is the more comprehensive (slower) variant.
AGENT = "deep-research-preview-04-2026"
POLL_S = 15
MAX_WAIT_S = 1800


def _key() -> str:
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""


async def run(seed: str) -> str:
    from google import genai

    client = genai.Client(api_key=_key())
    interaction = await client.aio.interactions.create(agent=AGENT, input=seed, background=True)

    waited = 0
    while waited < MAX_WAIT_S:
        result = await client.aio.interactions.get(interaction.id)
        if result.status == "completed":
            _record_cost(result)
            return result.output_text or ""
        if result.status == "failed":
            return ""
        await asyncio.sleep(POLL_S)
        waited += POLL_S
    return ""


def _record_cost(result) -> None:
    u = getattr(result, "usage", None)
    if u is None:
        return
    record_metric(
        "cost_usd",
        gemini_deep_research_cost(
            input_tokens=getattr(u, "total_input_tokens", 0) or 0,
            output_tokens=getattr(u, "total_output_tokens", 0) or 0,
            cached_tokens=getattr(u, "total_cached_tokens", 0) or 0,
            search_queries=getattr(u, "grounding_tool_count", 0) or 0,
        ),
    )
