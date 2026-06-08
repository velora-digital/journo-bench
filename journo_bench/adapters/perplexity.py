"""Perplexity Sonar runners — two tiers as separate entries.

`run_pro` uses sonar-pro (the flagship grounded model, peer to Gemini Grounded);
`run_deep_research` uses sonar-deep-research (the agentic multi-step model, peer
to Gemini Deep Research, slow and pricey). Both share one core.

Dormant without PERPLEXITY_API_KEY. The report keeps Perplexity's inline [n]
markers and appends a numbered source list that matches them, so each cited
claim stays traceable. Cost comes from the API's own usage.cost.total_cost.
"""

from __future__ import annotations

import os

from ..metrics import record_metric
from ..pricing import perplexity_cost
from ._task import TASK_INSTRUCTION

AVAILABLE = bool(os.getenv("PERPLEXITY_API_KEY"))

BASE_URL = "https://api.perplexity.ai"


async def _run(model: str, seed: str) -> str:
    import httpx

    headers = {"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": TASK_INSTRUCTION},
            {"role": "user", "content": seed},
        ],
    }

    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if usage := data.get("usage"):
        record_metric("cost_usd", perplexity_cost(usage))

    report = data["choices"][0]["message"]["content"]
    # Perplexity inlines [n] markers in the content; number the sources to match
    # so each cited claim stays traceable. Newer API returns search_results;
    # older returns a flat citations list.
    results = data.get("search_results") or []
    urls = [r.get("url") for r in results if r.get("url")] or (data.get("citations") or [])
    if not urls:
        return report
    sources = "\n".join(f"[{i}] {u}" for i, u in enumerate(urls, 1))
    return f"{report}\n\nSources:\n{sources}"


async def run_pro(seed: str) -> str:
    return await _run("sonar-pro", seed)


async def run_deep_research(seed: str) -> str:
    return await _run("sonar-deep-research", seed)
