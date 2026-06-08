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
from ._task import TASK_INSTRUCTION

AVAILABLE = bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))

# deep-research-max-preview-04-2026 is the more comprehensive (slower) variant.
AGENT = "deep-research-preview-04-2026"
POLL_S = 15
MAX_WAIT_S = 1800


def _key() -> str:
    return os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""


async def run(seed: str) -> str:
    from google import genai

    # The deep-research agent has no system_instruction channel, so the shared
    # task framing goes into the input ahead of the seed — same words every other
    # provider gets, as with Linkup.
    client = genai.Client(api_key=_key())
    interaction = await client.aio.interactions.create(
        agent=AGENT, input=f"{TASK_INSTRUCTION}\n\n{seed}", background=True
    )

    waited = 0
    while waited < MAX_WAIT_S:
        result = await client.aio.interactions.get(interaction.id)
        if result.status == "completed":
            _record_cost(result)
            return _report_text(result)
        if result.status == "failed":
            return ""
        await asyncio.sleep(POLL_S)
        waited += POLL_S
    return ""


def _report_text(result) -> str:
    """Render the text blocks in `outputs` with their URLCitation annotations
    inlined as [n] markers tied to a numbered source list, so each cited claim is
    traceable to its source. Annotation indices are byte offsets into the block."""
    blocks = [
        c for c in (result.outputs or []) if getattr(c, "type", None) == "text" and (c.text or "")
    ]

    def _anns(content) -> list:
        return [
            a
            for a in (getattr(content, "annotations", None) or [])
            if getattr(a, "type", None) == "url_citation"
            and getattr(a, "url", None)
            and getattr(a, "end_index", None) is not None
        ]

    num_of_url: dict[str, int] = {}
    numbered: list[str] = []
    for content in blocks:  # reading order assigns source numbers
        for a in sorted(_anns(content), key=lambda a: (a.end_index, a.start_index or 0)):
            if a.url not in num_of_url:
                num_of_url[a.url] = len(numbered) + 1
                numbered.append(a.url)

    parts: list[str] = []
    for content in blocks:
        data = content.text.encode("utf-8")
        for a in sorted(_anns(content), key=lambda a: a.end_index, reverse=True):
            marker = f"[{num_of_url[a.url]}]".encode()
            data = data[: a.end_index] + marker + data[a.end_index :]
        parts.append(data.decode("utf-8", errors="ignore"))

    report = "\n".join(parts)
    if numbered:
        report += "\n\nSources:\n" + "\n".join(f"[{n}] {u}" for n, u in enumerate(numbered, 1))
    return report


def _record_cost(result) -> None:
    u = getattr(result, "usage", None)
    if u is None:
        return
    # grounding_tool_count is a list of per-tool counts, not a scalar.
    searches = sum(
        (getattr(g, "count", 0) or 0) for g in (getattr(u, "grounding_tool_count", None) or [])
    )
    # total_thought_tokens is separate from total_output_tokens and bills at the
    # output rate, so fold it in.
    output_tokens = (getattr(u, "total_output_tokens", 0) or 0) + (
        getattr(u, "total_thought_tokens", 0) or 0
    )
    record_metric(
        "cost_usd",
        gemini_deep_research_cost(
            input_tokens=getattr(u, "total_input_tokens", 0) or 0,
            output_tokens=output_tokens,
            cached_tokens=getattr(u, "total_cached_tokens", 0) or 0,
            search_queries=searches,
        ),
    )
