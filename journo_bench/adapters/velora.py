"""Velora research agent runner.

The one runner that reaches into this repo's `src/`. Behind a soft import so
the benchmark still runs for anyone without the Velora backend — it just drops
out of the lineup.

Runs the agent the way it ships for NEWS. Production's article pipeline injects
two generic editorial-news skills into a research run (it does not come from
`site_id`): `editorial_news/research_orch.md`, the research-orchestration
guidance (chase the primary source, follow the attributed quote), wrapped in
`<research_guidance>` in the brief; and `editorial_news/research.md`, the news
synthesis template, passed as `research_template`. We replicate exactly that,
with `site_id=None` so NO customer/site-specific (e.g. cycling) skills load —
keeping it a fair cross-domain test while giving the agent its real news brain.

The type is hard-coded to `editorial_news` (every benchmark case is a news
tip), rather than running the live skill-selection agent.
"""

from __future__ import annotations

from datetime import datetime

from ..metrics import record_metric
from ..pricing import velora_external_cost

try:
    from src.ai.skills.type_registry import load_type_pool
    from src.ai.workflows.research.graph import run_research_graph
    from src.core.api_call_meter import count_api_calls

    AVAILABLE = True
except ImportError:
    AVAILABLE = False

NEWS_TYPE = "editorial_news"

# Standard tier: the agent exactly as it ships. Pro tier: identical pipeline,
# one variable changed — the researcher and synthesizer each move up a model
# size. Thinking levels, prompts, skills, and every other agent stay the same,
# so a score delta is attributable to model tier alone.
RESEARCHER_MODEL = "gpt-5.4-nano"
SYNTHESIZER_MODEL = "gpt-5.4-mini"
PRO_RESEARCHER_MODEL = "gpt-5.4-mini"
PRO_SYNTHESIZER_MODEL = "gpt-5.4"


def _pin_models(researcher_model: str, synthesizer_model: str) -> None:
    """Point the shared agent factory at this tier's models.

    run.py evaluates providers sequentially, so tiers cannot interleave; within
    one provider every case pins the same pair, and the model_name check makes
    the already-pinned case a no-op.
    """
    from src.ai.agents.factory import get_agent_factory
    from src.ai.agents.research.agents import (
        build_researcher_agent,
        build_synthesizer_agent,
    )

    factory = get_agent_factory()
    if factory.researcher_agent.model_name != researcher_model:
        factory.researcher_agent = build_researcher_agent(researcher_model)
    if factory.synthesizer_agent.model_name != synthesizer_model:
        factory.synthesizer_agent = build_synthesizer_agent(synthesizer_model)


def _news_skills() -> tuple[str, str]:
    """(research-orchestration guidance, news synthesis template) for editorial news."""
    pool = load_type_pool()
    orch = pool.stage_skills.get(f"{NEWS_TYPE}/research_orch")
    synth = pool.stage_skills.get(f"{NEWS_TYPE}/research")
    return (orch.content if orch else ""), (synth.content if synth else "")


def _build_brief(seed: str, research_orch: str) -> str:
    """The seed as the brief body, plus the research guidance and date — as the
    article pipeline assembles it, minus the article-specific source sections."""
    today = datetime.now().strftime("%Y-%m-%d")
    guidance = ""
    if research_orch:
        guidance = f"\n<research_guidance>\n{research_orch}\n</research_guidance>\n"
    return f"{seed}\n{guidance}\nToday's date: {today}\n"


async def run(seed: str) -> str:
    return await _run(seed, RESEARCHER_MODEL, SYNTHESIZER_MODEL)


async def run_pro(seed: str) -> str:
    return await _run(seed, PRO_RESEARCHER_MODEL, PRO_SYNTHESIZER_MODEL)


async def _run(seed: str, researcher_model: str, synthesizer_model: str) -> str:
    _pin_models(researcher_model, synthesizer_model)
    research_orch, research_synth = _news_skills()
    brief = _build_brief(seed, research_orch)
    with count_api_calls() as calls:
        result = await run_research_graph(
            brief, site_id=None, research_template=research_synth or None
        )
    record_metric("serper_calls", calls["serper"])
    record_metric("scrapecreators_calls", calls["scrapecreators"])
    record_metric("linkup_calls", calls["linkup"])
    record_metric(
        "external_cost_usd",
        velora_external_cost(calls["serper"], calls["scrapecreators"], calls["linkup"]),
    )
    return result.report or ""
