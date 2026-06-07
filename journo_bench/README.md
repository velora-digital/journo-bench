# Journalism Deep-Research Benchmark

A small, reproducible benchmark for what a newsroom actually needs from a
research agent — not generic "deep research" quality, but whether the output
is publishable. Each case gets **one composite score**, in `[-2, +3]`:

```
score = primary_reached + key_facts_present + citation - 2 × factual_error
```
Each check is 0 or 1; the composite ranges -2 to +3.

- **primary_reached** — is the *specific* primary article declared in the
  agent's report (the canonical origin, not a secondary aggregator)?
  Deterministic substring match on the report text.
- **key_facts_present** — did the defining quotes/stats surface, in any form?
  (A faithful translation or paraphrase counts.)
- **citation** — are those facts *cited to the primary source*? The laundering
  check: found the fact but credited a secondary outlet counts on presence,
  not here. Tolerant of how the source is named. Only counts if present.
- **factual_error (−2)** — did the brief assert anything that contradicts a
  known fact? "First, do no harm." Fires on key facts *and* supporting facts.

The three soft checks are made by a single LLM judge; everything is anchored
to a **human-authored answer key**, so the judge compares against fixed ground
truth rather than judging open-ended quality.

## How it works

Each case is one YAML file in `cases/`:

```yaml
name: 2026-05-28-some-story
seed: "A ~20-word news item — what a tip actually looks like."
event_date: 2026-05-28          # must postdate model cutoffs (recency guard)
primary_url: https://regulator.gov/decisions/123   # the specific document, not the outlet.
                                                   # may be a LIST when one release is canonical
                                                   # at several URLs (company site + the wire)
key_facts:                      # the defining quotes/stats; scored for presence + citation
  - "the key quote or statistic"
  - "the second key fact"
supporting_facts:               # NOT required to surface — only a contradiction tripwire
  - "a changeable fact the agent could get wrong (team name, age, placing)"
source: "the primary outlet the key facts should be cited to"   # tolerant of naming
notes: "why this case exists / what it tests"
```

The ~20-word **seed** forces real research instead of rewarding whoever got
the richest prompt, and mirrors how a story actually arrives.

`supporting_facts` are the trap: things an agent can easily get wrong (stale
team names, ages, prior placings). The brief isn't expected to mention them,
but contradicting one costs the −2.

Every agent is a thin **runner** (`adapters/`) that returns its report as a
string. We score that report and only that report — including the sources the
agent declares in it. A source it found but left out does not count, for every
agent equally. No normalisation layer; adding a competitor is one file.

## Running

```bash
uv run -m evals_public.journo_research.run --agent all
uv run -m evals_public.journo_research.run --agent velora --case 2026-05-28-some-story
```

Adapters are dormant unless their dependency is present: Velora needs this
repo; `openai_dr` needs `OPENAI_API_KEY`; `perplexity` needs `PERPLEXITY_API_KEY`.

The Velora runner injects the generic `editorial_news` research skills (the
same guidance the article pipeline uses for news — reach the primary, follow
the attributed quote — plus the news synthesis template), with `site_id=None`
so no site-specific skills load. That tests the agent as it ships for news,
fairly across domains. Without those skills it runs as a stripped researcher
and primary-reaching collapses, so this matters a lot.

## Viewing results (Logfire)

Runs push to Logfire. The two views show different things, so the score is
surfaced two ways from the one judge call:

- **Experiment list** (across runs) shows the headline `score` as an
  `AVG METRIC` column — recorded as a metric, because the list only surfaces
  pass-rate and metrics.
- **Run detail** (per case) shows the breakdown via a `Diagnostics` evaluator:
  all four checks (`primary_reached`, `key_facts_present`, `citation`,
  `no_factual_error`) as pass/fail assertions, with the judge's reasoning on
  `citation` and the flagged claim on `no_factual_error`. This is where you see
  *what* failed and *why*.

A self-contained static scorecard (for publishing, where a Logfire link won't
do) is a deliberate later step.

## Methodology notes (read before citing a result)

- **Anchored to a fixed answer key.** Only `primary_reached` is fully
  deterministic; presence, citation and errors are LLM-judged — but always
  against the case's human-authored facts, never open-ended "did this feel
  good." The judge's job is comparison, not taste.
- **Recency is the validity guard.** Cases must postdate training cutoffs or
  the benchmark measures recall, not research.
- **Author the answer key against the real primary source** — never against
  what any agent (including Velora) returned. Stored runs are fine for
  *finding* candidate stories, not for setting the correct answer.
- **The primary is what a best-in-class desk would actually link.** The
  authoritative document itself — the filing, bill, ruling, or release — not a
  third-party tracker, a press release / sponsor's framing, or another outlet's
  write-up. (A legislature's bill page, yes; LegiScan or a news article, no.
  A company's results release, yes; a wire story about it, no.) This is the
  line `primary_reached` is meant to draw, so set `primary_url` to the
  document a top publication would cite.
- **Scored on the report, not the browse trail.** Only what the agent puts
  in its report counts — sources gathered but omitted don't, which holds every
  agent to the same "what did you actually deliver" bar.
- **Document-level attribution in v1.** Whether the primary is declared at all,
  not claim-level sourcing (only some agents' formats support that). A v2.
- **Small N is directional.** A few points of total is noise; read the cases.
- **Freeze before running.** Tag the case set before invoking any agent so
  there's no question the cases were fitted to the results.
