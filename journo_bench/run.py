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

from .adapters import gemini_deep_research, gemini_grounded, linkup, perplexity, velora
from .adapters.base import Agent
from .dataset import load_dataset
from .metrics import record_metric
from .scoring import score_report

REGISTRY: dict[str, tuple[Agent, bool]] = {
    "velora": (velora.run, velora.AVAILABLE),
    "gemini_deep_research": (gemini_deep_research.run, gemini_deep_research.AVAILABLE),
    "gemini_grounded": (gemini_grounded.run, gemini_grounded.AVAILABLE),
    "linkup": (linkup.run, linkup.AVAILABLE),
    "perplexity": (perplexity.run, perplexity.AVAILABLE),
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


async def _bootstrap_for_velora() -> None:
    from src.core.observability import configure_logfire
    from src.core.services import factory

    configure_logfire("velora-journo-eval")
    await factory.data.get_neon_connection().init_pool()


async def main(agent: str, case_filter: str | None) -> None:
    wanted = list(REGISTRY) if agent == "all" else [agent]

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

    if "velora" in selected:
        await _bootstrap_for_velora()

    dataset = load_dataset(case_filter)
    answers = {c.inputs: c.expected_output for c in dataset.cases}

    for name, adapter in selected.items():
        print(f"\n{'#' * 70}\n# {name}\n{'#' * 70}")
        report = await dataset.evaluate(_scored(adapter, answers), name=name)
        report.print(include_input=False, include_output=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", default="all", help="all | " + " | ".join(REGISTRY))
    parser.add_argument("--case", default=None, help="run a single case by name")
    args = parser.parse_args()
    asyncio.run(main(args.agent, args.case))
