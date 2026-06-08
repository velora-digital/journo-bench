"""List-price cost models for the comparison providers (verified June 2026).

Cost is computed from the usage each response reports, not from a billing
portal, so a run's `cost_usd` is reproducible. Rates are public list prices.

Free tiers are deliberately ignored — e.g. Gemini's 5,000 free grounded
prompts/month is an account-level allowance the API can't attribute to a single
call, so we report the MARGINAL cost of a call at scale. The reported number is
"what one more call costs once you're past any free quota".

Velora is not priced here — for it the benchmark reports external-call counts
(Serper, ScrapeCreators), not a dollar figure, since its cost is wholesale
(LLM tokens, already tracked in `analytics.llm_usage`) not a vendor price.

Each rate lives in one constant so a vendor price change is a one-line edit.
"""

from __future__ import annotations

# --- Gemini 3.1 Pro, grounded generation. $/1M tokens, prompt <=200k -----------
_GEMINI_PRO_IN = 2.00
_GEMINI_PRO_OUT = 12.00  # thinking tokens are billed at the output rate, already
_GEMINI_PRO_CACHED = 0.20  # included in the output count — do not add separately
_GEMINI_GROUNDING_PER_QUERY = 14.00 / 1_000  # $14 / 1k Google Search queries


def gemini_grounded_cost(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    search_queries: int,
) -> float:
    """One grounded `generate_content` call: tokens + per-search grounding fee.

    `input_tokens` (prompt_token_count) already includes `cached_tokens`, so the
    non-cached remainder bills at the full input rate and the cached part at the
    cached rate. `search_queries` = len(web_search_queries) with empty strings
    filtered out (the API returns blanks that would otherwise over-bill).
    """
    billable_input = max(input_tokens - cached_tokens, 0)
    token_cost = (
        billable_input * _GEMINI_PRO_IN
        + cached_tokens * _GEMINI_PRO_CACHED
        + output_tokens * _GEMINI_PRO_OUT
    ) / 1_000_000
    return token_cost + search_queries * _GEMINI_GROUNDING_PER_QUERY


# --- Gemini Deep Research (interactions API). Metered, not flat -----------------
# The agent loops over an underlying flash-tier model. Google's own per-task
# estimate (~$1-3 for the standard agent) reproduces with Gemini 3.5 Flash rates,
# so we price the loop's tokens at those. CONFIRM the underlying model on the
# first live run (print `interaction.usage` + reconcile against billing) — if
# the agent runs on a different tier, swap these three constants.
_GEMINI_DR_IN = 1.50
_GEMINI_DR_OUT = 9.00
_GEMINI_DR_CACHED = 0.15


def gemini_deep_research_cost(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    search_queries: int,
) -> float:
    """A whole Deep Research interaction: summed loop tokens + grounding fee.

    Reads `interaction.usage`: total_input_tokens / total_output_tokens /
    total_cached_tokens / grounding_tool_count. Thought tokens are already in the
    output total. Grounding uses the same $14/1k rate as grounded generation.
    """
    billable_input = max(input_tokens - cached_tokens, 0)
    token_cost = (
        billable_input * _GEMINI_DR_IN
        + cached_tokens * _GEMINI_DR_CACHED
        + output_tokens * _GEMINI_DR_OUT
    ) / 1_000_000
    return token_cost + search_queries * _GEMINI_GROUNDING_PER_QUERY


# --- Perplexity sonar-deep-research. $/1M tokens + $/1k searches ----------------
_PPLX_IN = 2.00
_PPLX_OUT = 8.00
_PPLX_CITATION = 2.00
_PPLX_REASONING = 3.00
_PPLX_SEARCH_PER_QUERY = 5.00 / 1_000  # $5 / 1k search queries


def perplexity_cost(usage: dict) -> float:
    """Cost of one sonar-deep-research call from its `usage` object.

    Prefer the response's own pre-computed `usage.cost.total_cost`; fall back to
    summing the raw billable axes (input/output/citation/reasoning tokens +
    search queries) if the `cost` block is absent.
    """
    cost = usage.get("cost")
    if isinstance(cost, dict) and cost.get("total_cost") is not None:
        return float(cost["total_cost"])
    tokens = (
        usage.get("prompt_tokens", 0) * _PPLX_IN
        + usage.get("completion_tokens", 0) * _PPLX_OUT
        + usage.get("citation_tokens", 0) * _PPLX_CITATION
        + usage.get("reasoning_tokens", 0) * _PPLX_REASONING
    ) / 1_000_000
    return tokens + usage.get("num_search_queries", 0) * _PPLX_SEARCH_PER_QUERY


# --- Linkup. Flat per request, keyed by (depth, output_type) --------------------
# The response carries no usage/credit field, so cost is a known constant.
_LINKUP_PRICES = {
    ("standard", "searchResults"): 0.005,
    ("standard", "sourcedAnswer"): 0.006,
    ("deep", "searchResults"): 0.05,
    ("deep", "sourcedAnswer"): 0.055,
}


def linkup_cost(depth: str = "deep", output_type: str = "sourcedAnswer") -> float:
    return _LINKUP_PRICES[(depth, output_type)]
