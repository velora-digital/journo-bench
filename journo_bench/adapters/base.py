"""Each agent is just `async (seed: str) -> str` — it returns its report.

The report is the whole deliverable: the prose plus the sources the agent
declares in it. We score that and only that. A source the agent found but
left out of its report does not count — for every agent equally. So there's
no normalisation layer and no citation extraction; a runner returns a string.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

Agent = Callable[[str], Awaitable[str]]
