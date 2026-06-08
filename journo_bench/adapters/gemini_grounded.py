"""Gemini grounded-search runner — Google Search grounding, one generation.

The lighter comparison point: a single grounded answer, not a multi-step
research agent. Dormant without GOOGLE_API_KEY / GEMINI_API_KEY.

Gemini returns grounding sources as `vertexaisearch...` redirect links, not the
underlying article URLs, so we follow each redirect to its real URL before
appending — otherwise the report-text primary check can never match.
"""

from __future__ import annotations

import asyncio
import os

from ..metrics import record_metric
from ..pricing import gemini_grounded_cost

AVAILABLE = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.1-pro-preview"


def _key() -> str:
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""


async def run(seed: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_key())
    resp = await client.aio.models.generate_content(
        model=MODEL,
        contents=seed,
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
    )

    _record_cost(resp)

    report = resp.text or ""
    sources = await _grounded_sources(resp)
    if sources:
        report = f"{report}\n\nSources:\n" + "\n".join(f"- {u}" for u in sources)
    return report


def _record_cost(resp) -> None:
    um = getattr(resp, "usage_metadata", None)
    if um is None:
        return
    cand = (resp.candidates or [None])[0]
    gm = getattr(cand, "grounding_metadata", None)
    queries = getattr(gm, "web_search_queries", None) or []
    n_queries = len([q for q in queries if q])  # API returns empty strings; drop them
    record_metric(
        "cost_usd",
        gemini_grounded_cost(
            input_tokens=um.prompt_token_count or 0,
            output_tokens=um.candidates_token_count or 0,
            cached_tokens=getattr(um, "cached_content_token_count", 0) or 0,
            search_queries=n_queries,
        ),
    )


async def _grounded_sources(resp) -> list[str]:
    cand = (resp.candidates or [None])[0]
    gm = getattr(cand, "grounding_metadata", None)
    chunks = getattr(gm, "grounding_chunks", None) or []
    redirects = [
        c.web.uri for c in chunks if getattr(c, "web", None) and getattr(c.web, "uri", None)
    ]
    return await _resolve(redirects)


async def _resolve(urls: list[str]) -> list[str]:
    """Follow each grounding redirect to its real article URL."""
    import httpx

    async def one(client: "httpx.AsyncClient", u: str) -> str:
        try:
            r = await client.head(u, follow_redirects=True)
            return str(r.url)
        except httpx.HTTPError:
            return u

    if not urls:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        resolved = await asyncio.gather(*[one(client, u) for u in urls])
    return list(dict.fromkeys(resolved))
