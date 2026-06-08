"""List-price cost models for the comparison providers (verified June 2026).

Cost is computed from the usage each response reports, not from a billing
portal, so a run's `cost_usd` is reproducible. Rates are public list prices.

Free tiers are deliberately ignored — e.g. Gemini's 5,000 free grounded
prompts/month is an account-level allowance the API can't attribute to a single
call, so we report the MARGINAL cost of a call at scale. The reported number is
"what one more call costs once you're past any free quota".

Velora's LLM cost stays wholesale (model tokens, tracked separately as the
`cost` metric, not priced here). Its paid third-party calls are retail, though,
the per-call prices Velora pays each vendor, so `velora_external_cost` prices
those. Overall Velora cost is that external figure plus the wholesale LLM cost.

Each rate lives in one constant so a vendor price change is a one-line edit.
"""

from __future__ import annotations

# --- Gemini grounded generation. $/1M tokens (input, output, cached) per model --
# Thinking tokens bill at the output rate but are reported separately from
# candidates_token_count, so the adapter folds thoughts into output_tokens before
# pricing. Cached tokens are part of the input count, billed at the cached rate.
_GROUNDED_RATES: dict[str, tuple[float, float, float]] = {
    "gemini-3.1-pro-preview": (2.00, 12.00, 0.20),
    "gemini-3.5-flash": (1.50, 9.00, 0.15),
}
_GEMINI_GROUNDING_PER_QUERY = 14.00 / 1_000  # $14 / 1k Google Search queries, both


def gemini_grounded_cost(
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    search_queries: int,
    model: str = "gemini-3.1-pro-preview",
) -> float:
    """One grounded `generate_content` call: tokens + per-search grounding fee.

    `input_tokens` (prompt_token_count) already includes `cached_tokens`, so the
    non-cached remainder bills at the full input rate and the cached part at the
    cached rate. `search_queries` = len(web_search_queries) with empty strings
    filtered out (the API returns blanks that would otherwise over-bill).
    """
    in_rate, out_rate, cached_rate = _GROUNDED_RATES[model]
    billable_input = max(input_tokens - cached_tokens, 0)
    token_cost = (
        billable_input * in_rate + cached_tokens * cached_rate + output_tokens * out_rate
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
    total_cached_tokens / grounding_tool_count. total_thought_tokens is reported
    separately and bills at the output rate, so the adapter folds it into
    output_tokens. Grounding uses the same $14/1k rate as grounded generation.
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


# --- Velora's paid per-call third-party rates (retail) --------------------------
# Velora pays these per call inside a research run. The LLM token cost is wholesale
# and tracked separately; this prices only the external calls.
_SERPER_PER_CALL = 0.00075  # $0.00075 / Serper search (0.075 cents)
_SCRAPECREATORS_PER_CALL = 0.002  # $0.002 / ScrapeCreators fetch (0.2 cents)
_LINKUP_FETCH_PER_CALL = 0.001  # $0.001 / Linkup URL-fetch fallback (0.1 cents)


def velora_external_cost(serper_calls: int, scrapecreators_calls: int, linkup_calls: int) -> float:
    """Retail cost of a run's paid third-party calls; excludes wholesale LLM tokens."""
    return (
        serper_calls * _SERPER_PER_CALL
        + scrapecreators_calls * _SCRAPECREATORS_PER_CALL
        + linkup_calls * _LINKUP_FETCH_PER_CALL
    )
