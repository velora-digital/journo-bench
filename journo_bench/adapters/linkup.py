"""Linkup deep-search runner.

Linkup is a source-quality search engine (optimised for trusted, authoritative
sources), not an LLM deep-research agent — a useful contrast on this benchmark's
sourcing axis. We use deep search with a sourced answer:
`depth="deep"`, `output_type="sourcedAnswer"` → a synthesised answer plus the
sources behind it, with inline citations.

Dormant without LINKUP_API_KEY. Uses the `linkup` SDK (already a repo dep).
"""

from __future__ import annotations

import os

from ..metrics import record_metric
from ..pricing import linkup_cost
from ._task import TASK_INSTRUCTION

AVAILABLE = bool(os.getenv("LINKUP_API_KEY"))

DEPTH = "deep"
OUTPUT_TYPE = "sourcedAnswer"


async def run(seed: str) -> str:
    from linkup import LinkupClient

    # Linkup has no system-instruction field, only `query`, and in sourcedAnswer
    # mode that query is LLM-interpreted. So the shared task framing goes into
    # the query itself — same words every other provider gets, one field instead
    # of two.
    client = LinkupClient(api_key=os.environ["LINKUP_API_KEY"])
    resp = await client.async_search(
        query=f"{TASK_INSTRUCTION}\n\n{seed}",
        depth=DEPTH,
        output_type=OUTPUT_TYPE,
        include_inline_citations=True,
    )

    record_metric("cost_usd", linkup_cost(DEPTH, OUTPUT_TYPE))

    report = resp.answer or ""
    urls = [s.url for s in (resp.sources or []) if getattr(s, "url", None)]
    if urls:
        report = f"{report}\n\nSources:\n" + "\n".join(f"- {u}" for u in urls)
    return report
