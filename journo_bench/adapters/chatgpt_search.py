"""ChatGPT-with-search runner — OpenAI Responses API + the hosted web_search tool.

The closest headless equivalent of asking the ChatGPT app: the same GPT-5.x model
with the same web search the app runs on, given the shared task instruction. It
is not the desktop product (the app's hidden system prompt and scaffolding can't
be replicated), so it is labelled as the model + web search. Two entries:
gpt-5.4 and gpt-5.5. Dormant without OPENAI_API_KEY.

The Responses API returns url_citation annotations on the output text; we render
them inline as [n] markers tied to a numbered source list, so citation scoring
measures the model and not our rendering.
"""

from __future__ import annotations

import os

from ..metrics import record_metric
from ..pricing import openai_websearch_cost
from ._task import TASK_INSTRUCTION

AVAILABLE = bool(os.getenv("OPENAI_API_KEY"))

# Pin reasoning effort so 5.4 and 5.5 are comparable. Unset, each model uses a
# different default and the search loop runs away (5.5 fired 30+ searches, 127s,
# $0.64). Medium = a thorough-but-bounded search, like the other providers.
REASONING_EFFORT = "medium"


async def _run(model: str, seed: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = await client.responses.create(
        model=model,
        instructions=TASK_INSTRUCTION,
        input=seed,
        tools=[{"type": "web_search"}],
        reasoning={"effort": REASONING_EFFORT},
    )
    _record_cost(resp, model)
    return _inline_cited(resp)


async def run_54(seed: str) -> str:
    return await _run("gpt-5.4", seed)


async def run_55(seed: str) -> str:
    return await _run("gpt-5.5", seed)


def _record_cost(resp, model: str) -> None:
    u = getattr(resp, "usage", None)
    if u is None:
        return
    searches = sum(1 for it in (resp.output or []) if getattr(it, "type", "") == "web_search_call")
    record_metric(
        "cost_usd",
        openai_websearch_cost(
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            search_calls=searches,
            model=model,
        ),
    )


def _inline_cited(resp) -> str:
    """Inline the output text's url_citation annotations as [n], with a source list."""
    text, annotations = "", []
    for item in resp.output or []:
        if getattr(item, "type", "") != "message":
            continue
        for block in getattr(item, "content", None) or []:
            if getattr(block, "type", "") == "output_text":
                text = block.text or ""
                annotations = getattr(block, "annotations", None) or []
                break
    if not text:
        text = getattr(resp, "output_text", "") or ""

    cites = [
        (getattr(a, "end_index", None), a.url)
        for a in annotations
        if getattr(a, "type", "") == "url_citation" and getattr(a, "url", None)
    ]
    cites = [c for c in cites if c[0] is not None]
    if not cites:
        return text

    num_of_url: dict[str, int] = {}
    numbered: list[str] = []
    for _, url in sorted(cites, key=lambda c: c[0]):
        if url not in num_of_url:
            num_of_url[url] = len(numbered) + 1
            numbered.append(url)
    for end, url in sorted(cites, key=lambda c: c[0], reverse=True):
        text = text[:end] + f"[{num_of_url[url]}]" + text[end:]
    text += "\n\nSources:\n" + "\n".join(f"[{n}] {u}" for n, u in enumerate(numbered, 1))
    return text
