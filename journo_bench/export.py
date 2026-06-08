"""Append one JSON row per case to results.jsonl — the report's durable source.

Logfire holds the rich traces (judge reasoning, full agent runs) when the Velora
repo is present; this file is the self-contained record the report's tables read
from and that gets committed alongside it, with no Logfire dependency. One row
per (run, provider, case): the composite, the five checks and their reasons,
cost, call counts, the Logfire trace id, and the full brief.

Append-only: re-runs accumulate, each tagged with run_id, so the report selects
the latest N runs per provider rather than overwriting history.
"""

from __future__ import annotations

import json
from pathlib import Path

RESULTS = Path(__file__).parent / "results" / "results.jsonl"


def _flag(res, attr: str) -> bool | None:
    if res is None:
        return None
    v = getattr(res, attr, None)
    return bool(v) if v is not None else None


def append_results(run_id: str, run_at: str, provider: str, model: str, report) -> int:
    """Write a row per case from a finished `dataset.evaluate` report. Returns count."""
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in report.cases:
        out = case.output or {}
        res = out.get("result")
        m = case.metrics or {}
        rows.append(
            {
                "run_id": run_id,
                "run_at": run_at,
                "provider": provider,
                "model": model,
                "case": case.name,
                "score": getattr(res, "score", None),
                "primary_reached": _flag(res, "primary"),
                "key_facts": _flag(res, "key_facts_present"),
                "secondary_facts": _flag(res, "secondary_facts_present"),
                "cited_to_primary": _flag(res, "citation"),
                "factual_error": getattr(res, "has_factual_error", None),
                "errors": getattr(res, "errors", None) or [],
                "reasons": {
                    "primary": getattr(res, "primary_reason", ""),
                    "key": getattr(res, "present_reason", ""),
                    "secondary": getattr(res, "secondary_reason", ""),
                    "citation": getattr(res, "citation_reason", ""),
                    "error": getattr(res, "error_reason", ""),
                }
                if res
                else {},
                "cost_usd": m.get("cost_usd"),
                "llm_cost_usd": m.get("cost"),
                "external_cost_usd": m.get("external_cost_usd"),
                "serper_calls": m.get("serper_calls"),
                "scrapecreators_calls": m.get("scrapecreators_calls"),
                "linkup_calls": m.get("linkup_calls"),
                "duration_s": case.task_duration,
                "trace_id": case.trace_id,
                "report": out.get("report"),
            }
        )
    with RESULTS.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)
