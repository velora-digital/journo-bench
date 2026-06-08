"""Per-case diagnostic breakdown for Logfire's run-detail view.

The composite `score` is recorded as a metric in the task wrapper (so it shows
in the experiment LIST). This evaluator is the other half: it reads the typed
`ScoreResult` the judge already produced (passed through on the task output, so
no second judge call) and emits each of the five checks as a pass/fail
assertion, each with the judge's one-sentence reason attached — so you can see
WHAT failed and WHY, per case.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_evals.evaluators import EvaluationReason, Evaluator, EvaluatorContext

from .scoring import ScoreResult


@dataclass
class Diagnostics(Evaluator[str, dict]):
    """Render the four checks as separate, reasoned pass/fail results."""

    def evaluate(self, ctx: EvaluatorContext[str, dict]) -> dict:
        out = ctx.output
        res = out.get("result") if isinstance(out, dict) else None
        if not isinstance(res, ScoreResult):
            return {}

        err_bits = []
        if res.errors:
            err_bits.append("flagged: " + "; ".join(res.errors))
        if res.error_reason:
            err_bits.append(res.error_reason)
        err_reason = " | ".join(err_bits) or "no contradictions"

        return {
            "primary_reached": EvaluationReason(
                value=bool(res.primary), reason=res.primary_reason or "—"
            ),
            "key_facts_present": EvaluationReason(
                value=bool(res.key_facts_present), reason=res.present_reason or "—"
            ),
            "secondary_facts_present": EvaluationReason(
                value=bool(res.secondary_facts_present), reason=res.secondary_reason or "—"
            ),
            "citation": EvaluationReason(
                value=bool(res.citation), reason=res.citation_reason or "—"
            ),
            "no_factual_error": EvaluationReason(
                value=not res.has_factual_error, reason=err_reason
            ),
        }
