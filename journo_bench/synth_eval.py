"""Synthesizer-only sub-eval — generate-and-dump for human (me) review.

Replays the frozen real synthesizer inputs (synth_fixtures/*.yaml: brief +
findings captured from production traces) through one synthesis call with a
candidate system prompt (synth_fixtures/prompts/<name>.md), and writes each
output report to synth_fixtures/out/<prompt>/ with the expected facts in a
header. No LLM judge — read the outputs and judge the whole picture. No research
run, no Logfire-managed prompt, nothing touches production.

    uv run -m evals_public.journo_research.synth_eval --prompt v3 --case naesen
    uv run -m evals_public.journo_research.synth_eval --prompt v3 --split train --runs 2
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import yaml

from src.core.observability import configure_logfire

configure_logfire("velora-synth-eval")

from src.ai.base.llm_config import LLMProvider, ThinkingLevel  # noqa: E402
from src.ai.base.pydantic_base_agent import PydanticBaseAgent  # noqa: E402
from src.ai.skills.type_registry import load_type_pool  # noqa: E402

HERE = Path(__file__).parent
FIX = HERE / "synth_fixtures"
PROMPTS = FIX / "prompts"
OUT = FIX / "out"


def _content_template() -> str:
    pool = load_type_pool()
    skill = pool.stage_skills.get("editorial_news/research")
    return skill.content if skill else ""


def _user_message(fx: dict, template: str) -> str:
    section = f"\n\n<content_template>\n{template}\n</content_template>" if template else ""
    return f"Research Brief: {fx['brief']}{section}\n\nFindings:\n{fx['findings']}"


def _header(fx: dict) -> str:
    lines = [f"# {fx['name']}  ({fx['split']})", "", "## Expected KEY facts"]
    lines += [f"- {k}" for k in fx.get("key_facts") or []]
    lines += ["", "## Expected SECONDARY facts (the gap we're chasing)"]
    lines += [f"- {s}" for s in fx.get("secondary_facts") or []]
    lines += ["", "---", "## Synthesizer output", ""]
    return "\n".join(lines)


async def _gen(synth, prompt: str, template: str, fx: dict) -> str:
    return str(await synth.run(_user_message(fx, template), prompt))


async def main(
    prompt_name: str, split: str, case: str | None, runs: int, model: str, thinking: str
) -> None:
    prompt = (PROMPTS / f"{prompt_name}.md").read_text()
    template = _content_template()
    synth = PydanticBaseAgent(
        name="Synthesizer",
        model_name=model,
        provider=LLMProvider.AZURE,
        thinking_level=ThinkingLevel(thinking),
        output_type=str,
    )
    fixtures = [yaml.safe_load(p.read_text()) for p in sorted(FIX.glob("*.yaml"))]
    if case:
        fixtures = [f for f in fixtures if case in f["name"]]
    elif split != "all":
        fixtures = [f for f in fixtures if f["split"] == split]

    out_dir = OUT / f"{prompt_name}__{model}__{thinking}"
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = [
        (fx, r, asyncio.create_task(_gen(synth, prompt, template, fx)))
        for fx in fixtures
        for r in range(1, runs + 1)
    ]

    print(
        f"prompt={prompt_name} model={model} thinking={thinking}  cases={[f['name'] for f in fixtures]}  runs={runs}\n"
    )
    for fx, r, task in jobs:
        report = await task
        path = out_dir / f"{fx['name']}__r{r}.md"
        path.write_text(_header(fx) + report)
        # quick deterministic hint: distinctive secondary terms present?
        terms = []
        for s in fx.get("secondary_facts") or []:
            terms += [
                w.strip(",.\"'()")
                for w in str(s).split()
                if len(w) > 6 or any(c.isdigit() for c in w)
            ]
        hits = [t for t in terms if t.lower() in report.lower()]
        print(
            f"  {path.relative_to(HERE)}  ({len(report)} chars)  sec-terms {len(hits)}/{len(terms)} present"
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="baseline")
    ap.add_argument("--split", default="all", choices=["train", "test", "all"])
    ap.add_argument("--case", default=None, help="substring of a case name to run just that one")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--model", default="gpt-5.4-mini")
    ap.add_argument("--thinking", default="low", choices=[t.value for t in ThinkingLevel])
    args = ap.parse_args()
    asyncio.run(main(args.prompt, args.split, args.case, args.runs, args.model, args.thinking))
