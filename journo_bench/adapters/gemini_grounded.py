"""Gemini grounded-search runner — Google Search grounding, one generation.

The lighter comparison point: a single grounded answer, not a multi-step
research agent. Two tiers run as separate entries: `run_pro` (gemini-3.1-pro)
and `run_flash` (gemini-3.5-flash). Dormant without GOOGLE_API_KEY / GEMINI_API_KEY.

Gemini returns grounding sources as `vertexaisearch...` redirect links, not the
underlying article URLs, so we follow each redirect to its real URL before
inlining — otherwise the report-text primary check can never match.
"""

from __future__ import annotations

import asyncio
import os

from ..metrics import record_metric
from ..pricing import gemini_grounded_cost
from ._task import TASK_INSTRUCTION

AVAILABLE = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

MODEL_PRO = "gemini-3.1-pro-preview"
MODEL_FLASH = "gemini-3.5-flash"


def _key() -> str:
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""


async def _run(model: str, seed: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=_key())
    resp = await client.aio.models.generate_content(
        model=model,
        contents=seed,
        config=types.GenerateContentConfig(
            system_instruction=TASK_INSTRUCTION,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    _record_cost(resp, model)
    return await _inline_cited(resp)


async def run_pro(seed: str) -> str:
    return await _run(MODEL_PRO, seed)


async def run_flash(seed: str) -> str:
    return await _run(MODEL_FLASH, seed)


def _record_cost(resp, model: str) -> None:
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
            model=model,
        ),
    )


async def _inline_cited(resp) -> str:
    """Render Gemini's grounding as inline [n] citations tied to a numbered source
    list, following Google's documented pattern (sort supports by segment end,
    insert a marker at each), so each grounded claim is traceable to its source.
    Falls back to a flat source list when the grounding lacks segment supports."""
    text = resp.text or ""
    cand = (resp.candidates or [None])[0]
    gm = getattr(cand, "grounding_metadata", None)
    chunks = getattr(gm, "grounding_chunks", None) or []
    supports = getattr(gm, "grounding_supports", None) or []

    raw = [
        c.web.uri if getattr(c, "web", None) and getattr(c.web, "uri", None) else None
        for c in chunks
    ]
    resolved = await _resolve(raw)  # index-aligned with chunks; None where missing

    if not (text and supports and any(resolved)):
        urls = list(dict.fromkeys(u for u in resolved if u))
        tail = "\n\nSources:\n" + "\n".join(f"- {u}" for u in urls) if urls else ""
        return text + tail

    # Number each cited chunk in reading order (where its support segment ends).
    num_of_chunk: dict[int, int] = {}
    numbered: list[str] = []
    for s in sorted(supports, key=lambda s: _seg_end(s) or 0):
        for ci in getattr(s, "grounding_chunk_indices", None) or []:
            if 0 <= ci < len(resolved) and resolved[ci] and ci not in num_of_chunk:
                num_of_chunk[ci] = len(numbered) + 1
                numbered.append(resolved[ci])

    # Segment indices are UTF-8 byte offsets; insert on bytes, descending so
    # earlier offsets stay valid as we go.
    data = text.encode("utf-8")
    edits: list[tuple[int, str]] = []
    for s in supports:
        end = _seg_end(s)
        cis = [
            ci for ci in (getattr(s, "grounding_chunk_indices", None) or []) if ci in num_of_chunk
        ]
        if end is None or not cis:
            continue
        marker = "".join(f"[{num_of_chunk[ci]}]" for ci in dict.fromkeys(cis))
        edits.append((end, marker))
    for end, marker in sorted(edits, key=lambda e: e[0], reverse=True):
        data = data[:end] + marker.encode("utf-8") + data[end:]
    text = data.decode("utf-8", errors="ignore")

    text += "\n\nSources:\n" + "\n".join(f"[{n}] {u}" for n, u in enumerate(numbered, 1))
    return text


def _seg_end(support) -> int | None:
    seg = getattr(support, "segment", None)
    return getattr(seg, "end_index", None) if seg else None


async def _resolve(urls: list[str | None]) -> list[str | None]:
    """Follow each grounding redirect to its real URL, preserving index and length."""
    import httpx

    async def one(client: "httpx.AsyncClient", u: str | None) -> str | None:
        if not u:
            return None
        try:
            r = await client.head(u, follow_redirects=True)
            return str(r.url)
        except httpx.HTTPError:
            return u

    if not urls:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        return await asyncio.gather(*[one(client, u) for u in urls])
