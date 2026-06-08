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

AVAILABLE = bool(os.getenv("LINKUP_API_KEY"))


async def run(seed: str) -> str:
    from linkup import LinkupClient

    client = LinkupClient(api_key=os.environ["LINKUP_API_KEY"])
    resp = await client.async_search(
        query=seed,
        depth="deep",
        output_type="sourcedAnswer",
        include_inline_citations=True,
    )

    report = resp.answer or ""
    urls = [s.url for s in (resp.sources or []) if getattr(s, "url", None)]
    if urls:
        report = f"{report}\n\nSources:\n" + "\n".join(f"- {u}" for u in urls)
    return report
