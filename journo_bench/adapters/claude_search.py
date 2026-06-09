"""Claude-with-search runner — Anthropic Messages API + the hosted web_search tool.

The closest headless equivalent of asking the Claude app: the same Claude 4.x
model with the same web search, given the shared task instruction. Not the
desktop product (its hidden system prompt and scaffolding can't be replicated),
so labelled as the model + web search. Two entries: Sonnet 4.6 and Opus 4.8.
Dormant without ANTHROPIC_API_KEY.

Claude interleaves text blocks with citations to the web results; we render those
as inline [n] markers tied to a numbered source list, so citation scoring
measures the model and not our rendering.
"""

from __future__ import annotations

import os

from ..metrics import record_metric
from ..pricing import anthropic_websearch_cost
from ._task import TASK_INSTRUCTION

AVAILABLE = bool(os.getenv("ANTHROPIC_API_KEY"))
MAX_TOKENS = 4096
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 8}


async def _run(model: str, seed: str) -> str:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = await client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=TASK_INSTRUCTION,
        messages=[{"role": "user", "content": seed}],
        tools=[WEB_SEARCH_TOOL],
    )
    _record_cost(resp, model)
    return _inline_cited(resp)


async def run_sonnet(seed: str) -> str:
    return await _run("claude-sonnet-4-6", seed)


async def run_opus(seed: str) -> str:
    return await _run("claude-opus-4-8", seed)


def _record_cost(resp, model: str) -> None:
    u = getattr(resp, "usage", None)
    if u is None:
        return
    stu = getattr(u, "server_tool_use", None)
    searches = (getattr(stu, "web_search_requests", 0) or 0) if stu else 0
    record_metric(
        "cost_usd",
        anthropic_websearch_cost(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            searches=searches,
            model=model,
        ),
    )


def _inline_cited(resp) -> str:
    """Concatenate text blocks, appending [n] markers for each block's citations."""
    num_of_url: dict[str, int] = {}
    numbered: list[str] = []
    parts: list[str] = []
    for block in resp.content or []:
        if getattr(block, "type", "") != "text":
            continue
        parts.append(block.text or "")
        cited: list[int] = []
        for c in getattr(block, "citations", None) or []:
            url = getattr(c, "url", None)
            if not url:
                continue
            if url not in num_of_url:
                num_of_url[url] = len(numbered) + 1
                numbered.append(url)
            cited.append(num_of_url[url])
        if cited:
            parts.append("".join(f"[{n}]" for n in dict.fromkeys(cited)))
    report = "".join(parts)
    if numbered:
        report += "\n\nSources:\n" + "\n".join(f"[{n}] {u}" for n, u in enumerate(numbered, 1))
    return report
