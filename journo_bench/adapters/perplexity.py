"""Perplexity Sonar Deep Research runner.

Dormant without PERPLEXITY_API_KEY. Returns the report text with its declared
sources appended, so report-text scoring sees the URLs Perplexity cited.
Verify the response shape against the live API before publishing a run.
"""

from __future__ import annotations

import os

from ..metrics import record_metric
from ..pricing import perplexity_cost
from ._task import TASK_INSTRUCTION

AVAILABLE = bool(os.getenv("PERPLEXITY_API_KEY"))

MODEL = "sonar-deep-research"
BASE_URL = "https://api.perplexity.ai"


async def run(seed: str) -> str:
    import httpx

    headers = {"Authorization": f"Bearer {os.environ['PERPLEXITY_API_KEY']}"}
    payload = {
        "model": MODEL,
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
    urls = data.get("citations", []) or []

    sources = "\n".join(f"- {u}" for u in urls)
    return f"{report}\n\nSources:\n{sources}" if sources else report
