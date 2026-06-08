"""Score one report against a case's answer key. One composite float per case.

    score = primary_reached + key_facts_present + secondary_facts_present
            + citation - 2*factual_error
    each check is 0 or 1; range -2 .. +4

Three tiers of fact, distinct roles:
- key_facts:      the spine — the story doesn't exist without them.
- secondary_facts: the flesh — a desk editor would call the article thin
                  without them. Reaching them shows the agent read the primary.
- incidental_facts: background the story touches but isn't about (team, ticker,
                  age). Never required; just must not be got wrong.

- primary_reached:        LLM judge — did the report reach the primary source's
                          own publication of this story, citing it in ANY official
                          URL form. Grounded by a deterministic check on the known
                          canonical URLs (a verbatim match is strong evidence), so
                          it is robust to which form the agent happens to cite.
- key_facts_present:      LLM judge — does the report convey the key facts (all
                          the essential ones), in any form. Paraphrase counts.
- secondary_facts_present: LLM judge — does it also convey the secondary facts.
- citation:               LLM judge — are the key facts cited to the primary
                          source (the laundering check). Tolerant of naming.
- factual_error:          LLM judge — does the report contradict any fact in
                          any tier. The "first, do no harm" penalty (-2).

`score_report` is called from the task runner (not a pydantic-evals
evaluator) so the result can be recorded as a metric via
`increment_eval_metric` — a metric surfaces as a column in Logfire's
experiment list; an evaluator score does not.

PORT NOTE: the judge uses this repo's PydanticBaseAgent (already wired for
providers). For a standalone public release, swap it for a vanilla
pydantic-ai Agent + your own key. Behind a soft import so the module still
loads without `src/`; scoring then falls back to the primary check alone.
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlsplit

from pydantic import BaseModel

log = logging.getLogger(__name__)

JUDGE_MODEL = "gpt-5.4-mini"
JUDGE_TIMEOUT_S = 90

try:
    from src.ai.base.llm_config import LLMProvider, ThinkingLevel
    from src.ai.base.pydantic_base_agent import PydanticBaseAgent

    _JUDGE_AVAILABLE = True
except ImportError:
    _JUDGE_AVAILABLE = False


def _norm_url(url: str) -> str:
    """Host + path + query, lowercased; scheme/www/fragment/trailing-slash stripped.

    The query is kept because some canonical sources carry the document id there,
    not in the path (e.g. an official wire release surfaced on an aggregator feed
    at `.../announce/detail?dockey=...`).
    """
    parts = urlsplit(url.strip().lower())
    host = parts.netloc.removeprefix("www.")
    path = parts.path.rstrip("/")
    query = f"?{parts.query}" if parts.query else ""
    return f"{host}{path}{query}"


def _primary_reached(urls: list[str], report: str) -> bool:
    """Is any acceptable primary source declared in the report text?

    A case may list several canonical URLs for one source (e.g. a press release
    on the company site AND on the wire it went out on). The normalised target
    is matched as a substring of the lowercased report, so however the report
    writes the link it still matches, but a bare-domain mention does not.
    """
    body = report.lower()
    return any(_norm_url(u) in body for u in urls)


class JudgeVerdict(BaseModel):
    """All five LLM checks, each with its own one-sentence reason."""

    primary_reached: bool
    primary_reason: str
    key_facts_present: bool
    key_facts_reason: str
    secondary_facts_present: bool
    secondary_facts_reason: str
    cited_to_primary: bool
    citation_reason: str
    has_factual_error: bool
    errors: list[str]
    error_reason: str


class ScoreResult(BaseModel):
    """The composite plus its components and per-check reasons."""

    score: float
    primary: float
    key_facts_present: float
    secondary_facts_present: float
    citation: float
    has_factual_error: bool
    errors: list[str]
    primary_reason: str = ""
    present_reason: str = ""
    secondary_reason: str = ""
    citation_reason: str = ""
    error_reason: str = ""


JUDGE_SYSTEM = (
    "You are a meticulous editorial fact-checker scoring a research brief "
    "against a verified answer key. Judge only against what the key states."
)

JUDGE_TEMPLATE = """A research agent produced the brief below from a short news tip.
Judge it against the verified answer key.

<brief>
{report}
</brief>

<key_facts>
{key_facts}
</key_facts>
The primary source these facts should be cited to: {source} — {primary_url}

<secondary_facts>
{secondary_facts}
</secondary_facts>

<incidental_facts>
{incidental_facts}
</incidental_facts>

One of the listed canonical primary URLs appears verbatim in the brief: {url_match}

Assess five things, giving a one-sentence reason for each:

1. primary_reached (true/false) + primary_reason: true if the brief reaches the
   primary source — {source}'s own publication of this story — by citing or
   linking that source's own document, in ANY official form. The canonical forms
   are listed above, and the verbatim-match flag above is strong evidence. Count
   it reached if the brief points to that source's own document (one of those
   URLs, or another official URL from the same source for this story); false if
   it points only to a secondary outlet that re-reported the story.

2. key_facts_present (true/false) + key_facts_reason: true if the brief conveys
   the key facts — all the essential ones — in any form. A faithful translation
   or paraphrase counts; exact wording is not required. Ignore sourcing here.

3. secondary_facts_present (true/false) + secondary_facts_reason: true if the
   brief also conveys the secondary facts — all of them — in any form. These are
   the supporting detail a complete article carries. Same leniency: paraphrase
   counts, sourcing is ignored here. If no secondary facts are listed, true.

4. cited_to_primary (true/false) + citation_reason: true if the brief cites the
   key facts to the primary source above. Any clear reference to that source
   counts — its name, the publication, or a link to it. Crediting the outlet
   that carries the primary is enough; do NOT require a named wire agency,
   journalist, byline, or exact wording. False if the facts are credited only to
   a different, secondary outlet.

5. has_factual_error (true/false) + errors + error_reason: true if the brief
   asserts anything that contradicts a fact in ANY of the three lists above
   (key, secondary, or incidental). Incidental facts are background the story
   touches but is not about — the brief is not expected to mention them, but it
   must not get them wrong. List each contradicting claim in `errors`. A simple
   omission is never an error."""


_judge_agent = None


def _get_judge() -> "PydanticBaseAgent":
    global _judge_agent
    if _judge_agent is None:
        _judge_agent = PydanticBaseAgent(
            name="Journo eval judge",
            model_name=JUDGE_MODEL,
            provider=LLMProvider.AZURE,
            thinking_level=ThinkingLevel.MEDIUM,
            output_type=JudgeVerdict,
        )
    return _judge_agent


async def _judge_brief(
    report: str,
    key_facts: list[str],
    secondary: list[str],
    incidental: list[str],
    source: str,
    primary_url: str,
    url_match: bool,
) -> JudgeVerdict:
    prompt = JUDGE_TEMPLATE.format(
        report=report or "(empty)",
        key_facts="\n".join(f"- {f}" for f in key_facts),
        source=source or "(the primary source)",
        primary_url=primary_url or "(not given)",
        secondary_facts="\n".join(f"- {f}" for f in secondary) or "(none)",
        incidental_facts="\n".join(f"- {f}" for f in incidental) or "(none)",
        url_match="yes" if url_match else "no",
    )
    async with asyncio.timeout(JUDGE_TIMEOUT_S):
        return await _get_judge().run(prompt, JUDGE_SYSTEM)


async def score_report(report: str, expected: dict) -> ScoreResult | None:
    """Composite score in [-2, +4] with its components. None when no answer key."""
    urls = expected.get("primary_url") or []
    key_facts = expected.get("key_facts") or []
    if not urls and not key_facts:
        return None

    report = report or ""
    # Deterministic check on the known canonical URLs. It grounds the judge's
    # primary_reached call (a verbatim match is strong evidence) and is the
    # fallback when the judge is unavailable.
    url_match = _primary_reached(urls, report)
    primary = 1.0 if url_match else 0.0
    primary_reason = (
        "A listed canonical primary URL appears in the report."
        if url_match
        else "No listed canonical primary URL appears in the report."
    )

    present, secondary, citation = 0.0, 0.0, 0.0
    has_error, errors = False, []
    present_reason = secondary_reason = citation_reason = error_reason = ""
    if key_facts and _JUDGE_AVAILABLE:
        verdict = await _judge_brief(
            report,
            key_facts,
            expected.get("secondary_facts") or [],
            expected.get("incidental_facts") or [],
            expected.get("source"),
            "; ".join(urls),
            url_match,
        )
        primary = 1.0 if verdict.primary_reached else 0.0
        primary_reason = verdict.primary_reason
        present = 1.0 if verdict.key_facts_present else 0.0
        secondary = 1.0 if verdict.secondary_facts_present else 0.0
        citation = present if verdict.cited_to_primary else 0.0
        has_error, errors = verdict.has_factual_error, verdict.errors
        present_reason = verdict.key_facts_reason
        secondary_reason = verdict.secondary_facts_reason
        citation_reason = verdict.citation_reason
        error_reason = verdict.error_reason
        log.info(
            "journo primary=%.0f present=%.0f secondary=%.0f citation=%.0f error=%s %s",
            primary,
            present,
            secondary,
            citation,
            has_error,
            errors,
        )
    elif key_facts:
        log.warning("judge unavailable — scoring deterministic primary only")

    score = primary + present + secondary + citation - (2.0 if has_error else 0.0)
    return ScoreResult(
        score=score,
        primary=primary,
        key_facts_present=present,
        secondary_facts_present=secondary,
        citation=citation,
        has_factual_error=has_error,
        errors=errors,
        primary_reason=primary_reason,
        present_reason=present_reason,
        secondary_reason=secondary_reason,
        citation_reason=citation_reason,
        error_reason=error_reason,
    )
