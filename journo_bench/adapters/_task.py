"""The shared task framing given to every instructable provider.

Fairness rule: each agent is told the same task and otherwise runs as it ships.
Velora gets this through its `editorial_news` skills; the third parties get it
as a system instruction. The framing is deliberately context-only: it names the
job (a sourced, verifiable research report for a news publication) — the
newsroom bar every provider should meet — but names no primary, no source, and
no fact. Whether an agent actually reaches the primary and ties each fact to it
is exactly what the benchmark tests, so we do not hand it the rubric.

Linkup's API has no instruction channel, only a `query` (which it interprets
with an LLM in sourcedAnswer mode), so the same framing goes into the query
ahead of the seed. Every provider receives identical words.
"""

from __future__ import annotations

TASK_INSTRUCTION = (
    "You are researching a story for a news publication. "
    "Produce a sourced, verifiable research report that will inform the article written about it."
)
