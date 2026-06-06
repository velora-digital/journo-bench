"""OpenAI Deep Research runner (o4-mini-deep-research via the Responses API).

Dormant without OPENAI_API_KEY. Best-effort against the documented Responses
API shape — verify against the live API before publishing a run.

Returns the report text. The Responses API carries citations as inline
annotations rather than printed URLs, so we append the declared sources as a
list — that's faithful to the document a user is shown, and it lets the
report-text scoring see the sources the agent actually cited.
"""

from __future__ import annotations

import os

AVAILABLE = bool(os.getenv("OPENAI_API_KEY"))

MODEL = "o4-mini-deep-research"


async def run(seed: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI()
    resp = await client.responses.create(
        model=MODEL,
        input=seed,
        tools=[{"type": "web_search_preview"}],
    )

    report = resp.output_text or ""

    urls: list[str] = []
    for item in resp.output or []:
        for content in getattr(item, "content", None) or []:
            for ann in getattr(content, "annotations", None) or []:
                url = getattr(ann, "url", None)
                if url:
                    urls.append(url)

    sources = "\n".join(f"- {u}" for u in dict.fromkeys(urls))
    return f"{report}\n\nSources:\n{sources}" if sources else report
