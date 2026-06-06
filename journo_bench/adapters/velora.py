"""Velora research agent runner.

The one runner that reaches into this repo's `src/`. Behind a soft import so
the benchmark still runs for anyone without the Velora backend — it just
drops out of the lineup. `site_id=None` runs the generic agent with no
site-specific skills, the fair cross-domain configuration.

Returns the synthesised report verbatim: whatever sources it declares in
that report are what get scored.
"""

from __future__ import annotations

try:
    from src.ai.workflows.research.graph import run_research_graph

    AVAILABLE = True
except ImportError:
    AVAILABLE = False


async def run(seed: str) -> str:
    result = await run_research_graph(brief=seed, site_id=None)
    return result.report or ""
