"""Record a per-case metric onto the active pydantic-evals task run.

Each runner emits its own metrics as a side effect (cost for the paid
providers; external-call counts for Velora), so the value lands on the case
that produced it. A metric surfaces as an `AVG METRIC <name>` column in
Logfire's experiment list — the place to compare providers at a glance.

`record_metric` sets the value unconditionally. The public
`increment_eval_metric` helper skips a metric whose value stays 0, which would
silently drop a 0.0 case from the average; we never want that. No-op outside a
task context (e.g. a unit test calling an adapter directly).
"""

from __future__ import annotations

from pydantic_evals.dataset import _task_run


def record_metric(name: str, value: float) -> None:
    run = _task_run.CURRENT_TASK_RUN.get()
    if run is not None:
        run.record_metric(name, value)
