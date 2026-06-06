"""Load one-file-per-case YAML into a stock pydantic-evals Dataset.

One case per file keeps each addition a clean, reviewable (eventually
contributable) unit. The answer key lives in `expected_output`, the
idiomatic pydantic-evals home for the correct answer.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic_evals import Case, Dataset

from .evaluators import Diagnostics

CASES_DIR = Path(__file__).parent / "cases"


def load_case(path: Path) -> Case:
    data = yaml.safe_load(path.read_text())
    return Case(
        name=data["name"],
        inputs=data["seed"],
        expected_output={
            "primary_url": data.get("primary_url"),
            "key_facts": data.get("key_facts") or [],
            "supporting_facts": data.get("supporting_facts") or [],
            "source": data.get("source"),
        },
        metadata={
            "event_date": str(data.get("event_date") or ""),
            "notes": data.get("notes"),
        },
    )


def load_dataset(case_filter: str | None = None) -> Dataset:
    paths = sorted(CASES_DIR.glob("*.yaml"))
    cases = [load_case(p) for p in paths]
    if case_filter:
        cases = [c for c in cases if c.name == case_filter]
        if not cases:
            raise ValueError(f"No case named '{case_filter}' in {CASES_DIR}")
    return Dataset(name="journo_research", cases=cases, evaluators=[Diagnostics()])
