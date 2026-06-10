"""Run the benchmark: each available agent over every case, scored identically.

    uv run -m evals_public.journo_research.run --agent all
    uv run -m evals_public.journo_research.run --agent velora --case _example-template

pydantic-evals evaluates one task at a time, so "compare N agents" is just
a loop of `dataset.evaluate(agent)` per agent — no custom harness.

Scoring happens inside the task wrapper (`_scored`), not a pydantic-evals
evaluator, so the composite lands as a metric (see `metrics.record_metric`).
Each runner also emits its own metrics — `cost_usd` for the paid providers,
`serper_calls`/`scrapecreators_calls` for Velora. A metric surfaces as an
`AVG METRIC <name>` column in Logfire's experiment list (and the terminal
table); an evaluator score only shows per-run.

The Velora runner needs this repo's bootstrap (Logfire so prompts resolve;
DB pool for any skill access). External runners need only their API key.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from . import export
from .adapters import (
    chatgpt_search,
    claude_search,
    gemini_deep_research,
    gemini_grounded,
    linkup,
    perplexity,
    velora,
)
from .adapters.base import Agent
from .dataset import load_dataset
from .metrics import record_metric
from .scoring import score_report

REGISTRY: dict[str, tuple[Agent, bool]] = {
    "velora": (velora.run, velora.AVAILABLE),
    "velora_pro": (velora.run_pro, velora.AVAILABLE),
    "gemini_deep_research": (gemini_deep_research.run, gemini_deep_research.AVAILABLE),
    "gemini_grounded_pro": (gemini_grounded.run_pro, gemini_grounded.AVAILABLE),
    "gemini_grounded_flash": (gemini_grounded.run_flash, gemini_grounded.AVAILABLE),
    "linkup": (linkup.run, linkup.AVAILABLE),
    "perplexity_pro": (perplexity.run_pro, perplexity.AVAILABLE),
    "perplexity_deep_research": (perplexity.run_deep_research, perplexity.AVAILABLE),
    "chatgpt_5_4": (chatgpt_search.run_54, chatgpt_search.AVAILABLE),
    "chatgpt_5_5": (chatgpt_search.run_55, chatgpt_search.AVAILABLE),
    "claude_sonnet_4_6": (claude_search.run_sonnet, claude_search.AVAILABLE),
    "claude_opus_4_8": (claude_search.run_opus, claude_search.AVAILABLE),
}

# Model label recorded with each result row, so a later re-run is a new, pinned
# measurement rather than a silent overwrite.
MODELS: dict[str, str] = {
    "velora": "velora-research",
    "velora_pro": "velora-research-pro",
    "gemini_deep_research": gemini_deep_research.AGENT,
    "gemini_grounded_pro": gemini_grounded.MODEL_PRO,
    "gemini_grounded_flash": gemini_grounded.MODEL_FLASH,
    "linkup": f"linkup-{linkup.DEPTH}-{linkup.OUTPUT_TYPE}",
    "perplexity_pro": "sonar-pro",
    "perplexity_deep_research": "sonar-deep-research",
    "chatgpt_5_4": "gpt-5.4",
    "chatgpt_5_5": "gpt-5.5",
    "claude_sonnet_4_6": "claude-sonnet-4-6",
    "claude_opus_4_8": "claude-opus-4-8",
}

# Cap fan-out where 30 concurrent cases would strain a shared resource: the
# agentic deep-research tiers (slow, rate-limited) and Velora (DB pool + its own
# Serper/LLM fan-out per case). The simple grounded APIs run unbounded.
CONCURRENCY: dict[str, int] = {
    "velora": 10,
    "velora_pro": 10,
    "linkup": 4,
    "perplexity_pro": 6,
    "gemini_deep_research": 4,
    "perplexity_deep_research": 4,
    "chatgpt_5_4": 8,
    "chatgpt_5_5": 8,
    "claude_sonnet_4_6": 6,
    "claude_opus_4_8": 6,
}


def _scored(agent: Agent, answers: dict[str, dict]) -> Callable[[str], Awaitable[dict]]:
    """Wrap a runner: produce the report, then score it and record the metric.

    Runs inside the task context, so `increment_eval_metric` lands on the
    case. Returns the report unchanged as the task output.
    """

    async def task(seed: str) -> dict:
        report = await agent(seed)
        res = await score_report(report, answers.get(seed) or {})
        if res is None:
            return {"report": report}
        record_metric("score", res.score)
        return {"report": report, "result": res}

    return task


def _configure_logfire() -> None:
    """Configure Logfire for every run when the Velora repo is importable; a
    standalone run (no `src/`) skips it. The results file does not depend on it."""
    try:
        from src.core.observability import configure_logfire
    except ImportError:
        return
    configure_logfire("velora-journo-eval")


async def _init_velora_pool() -> None:
    from src.core.services import factory

    await factory.data.get_neon_connection().init_pool()


async def main(agent: str, case_filter: str | None) -> None:
    wanted = list(REGISTRY) if agent == "all" else [a.strip() for a in agent.split(",")]

    selected: dict[str, Agent] = {}
    for name in wanted:
        fn, available = REGISTRY[name]
        if available:
            selected[name] = fn
        else:
            print(f"skip {name}: adapter unavailable (missing key or import)")

    if not selected:
        print("No available agents to run.")
        return

    _configure_logfire()
    if "velora" in selected:
        await _init_velora_pool()

    dataset = load_dataset(case_filter)
    answers = {c.inputs: c.expected_output for c in dataset.cases}

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_at = datetime.now(UTC).isoformat()

    for name, adapter in selected.items():
        print(f"\n{'#' * 70}\n# {name}\n{'#' * 70}")
        report = await dataset.evaluate(
            _scored(adapter, answers), name=name, max_concurrency=CONCURRENCY.get(name)
        )
        report.print(include_input=False, include_output=False)
        n = export.append_results(run_id, run_at, name, MODELS.get(name, name), report)
        print(f"  wrote {n} rows to {export.RESULTS}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="all", help="all | " + " | ".join(REGISTRY))
    parser.add_argument("--case", default=None, help="case name(s), comma-separated")
    args = parser.parse_args()
    asyncio.run(main(args.agent, args.case))
