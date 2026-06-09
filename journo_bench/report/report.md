---
title: "The Primary-Source Benchmark"
subtitle: "Do AI research agents reach the source a newsroom would actually cite?"
author:
  - Danny Bellion (Velora)
  - Peter Stuart (Velora)
date: 2026-06-XX
version: "0.1 (draft)"
abstract: >
  PLACEHOLDER, written last. The one-paragraph version: what we measured
  (whether research agents reach the primary source and report it faithfully),
  how (cross-domain news seeds, human-authored answer keys, a five-check
  rubric), who we tested, and the single most important finding.
---

<!--
AUTHORING NOTES (won't render):
- `> _italic blockquote_` = guidance for a section still to be written.
- `[[DATA: ...]]` = a slot filled from a benchmark run (table / figure / number).
- Results, failure modes, exec summary, appendix wait on the full run.
- Writing rules: no em dashes; no "not X but Y"; every sentence carries a fact;
  no three-item lists; "said" for attribution; no dead-weight qualifiers.
-->

> **Disclosure.** Danny Bellion and Peter Stuart build Velora, one of the
> products evaluated here. The harness, every case, and every answer key are
> public and runnable; keys are authored against primary sources, not any
> agent's output; and Velora's own failures are reported alongside its results.

# Executive summary

> _Write last, once numbers exist. Open with one bold headline verdict, on its
> own line, that a journalist could paste into an article. Then the leaderboard.
> Then findings. One finding must be a Velora weakness._

[[DATA: headline verdict, one sentence]]

[[DATA: leaderboard: provider, score over two runs, cost per run]]

- **Finding 1:** PLACEHOLDER (the headline result).
- **Finding 2:** PLACEHOLDER (the sharpest divergence between providers).
- **Finding 3:** PLACEHOLDER (a cost-and-quality point).
- **Finding 4:** PLACEHOLDER (a failure mode that recurs across providers).
- **Finding 5:** PLACEHOLDER (a Velora weakness the benchmark surfaced).

---

# Why reaching the primary source matters

A research agent tells you a transfer fee was 40 million pounds. The number is right. It cites a rival outlet that published 40 million an hour before the official figure of 42 million landed. You run the story under your byline. The next morning you are writing a correction for a mistake that started somewhere else.

Generic research quality misses this failure. A fluent, comprehensive brief can carry a fact that came from the wrong place and still score well. For a newsroom the source is the product. Reaching the document the news came from, whether a filing or the post where it broke, is what makes a piece defensible when a subject disputes it. Citing a secondary write-up instead hands another outlet's error to your readers under your name.

Existing benchmarks reward the brief that reads well. They do not check whether the agent reached the authoritative source, or whether each fact is attributed to it. We built the measurement for that axis and ran the research products a newsroom could buy through it.

## What this measures, and what it does not

The benchmark scores whether an agent reaches the primary source for a news event and reports its facts faithfully. It does not score writing quality or speed. It does not test multi-turn editing or long-form features, and it reads a foreign-language primary without judging wider non-English fluency. The cases probe across domains rather than covering any single beat in depth. A high score means an agent sources well from a short seed. It says nothing about the rest of the work a newsroom needs.

# The benchmark

## A case

Each case is a seed of around twenty words, the length a real assignment arrives at, paired with a human-authored answer key. The seed names an event and little else, so reaching the facts takes research rather than a reading of the prompt.

[[DATA: one example case rendered inline: seed plus its key]]

## How the cases were built

Cases come from real news events across cycling, retail, public policy, finance, and consumer launches. We selected events that have a documentable primary source, a filing or a first-hand post that a newsroom would cite. Each event postdates the knowledge cutoffs of the models under test, so a correct answer is evidence of research and a date or figure pulled from memory is the failure the benchmark catches. We wrote each answer key from the primary itself, before running any agent.

[[DATA: per-case event dates and cutoff margins, in the appendix]]

## The answer key

The key holds three kinds of fact, scored differently.

Key facts are the spine of the story. The story does not exist without them.

Secondary facts are the supporting detail a complete article carries. Reporting them shows the agent read the primary in full.

Incidental facts are the background the story touches without being about, a team name or a ticker. The brief carries no obligation to mention them. It must not get them wrong.

## The score

Each case scores on a single composite. An agent earns a point for reaching the primary source, a point for the key facts, a point for the secondary facts, and a point for tying each key fact to that primary so a reader can check it. It loses two points for asserting anything that contradicts a fact in any tier. Scores run from minus two to plus four.

```
score = primary_reached + key_facts_present + secondary_facts_present
        + citation − 2 × factual_error
```

`primary_reached` asks whether the agent reached the designated primary source. A judge decides it, grounded by a code check that matches the primary's URL against the report, so a different official URL of the same source still counts and a fact lifted from a write-up that never reached the primary does not.

`key_facts_present` and `secondary_facts_present` are judged against the fixed key. A faithful translation or a paraphrase counts.

`citation` asks whether each key fact is traceably tied to that primary, by an inline marker or an explicit reference a reader can follow. A primary that only sits in an undifferentiated list of sources does not earn the point: reaching a source and showing which fact came from it are scored apart.

`factual_error` is the one penalty. It fires when the brief states something a listed fact contradicts.

The score reads only the report the agent returns, with the sources declared inside it. A source the agent found and left out does not count, applied the same way to every agent.

We present the composite as a percentage of the four points on offer, so a brief that passes every check reads 100 percent and one that reaches nothing reads 0. A factual error can push a score below zero.

# Methodology

## What we tested

We grouped the field into three kinds of product a newsroom could buy, and ran the current model of each.

Velora is the multi-step research agent we build. It plans a search, reaches and reads the sources, follows an attributed quote back to where it was said, and writes a sourced brief. For the benchmark it runs the generic editorial-news research skills the article pipeline uses, with no customer or site configuration loaded, so it is the agent as it ships for news across any domain.

Single-pass grounded search returns one cited answer from a single grounded generation rather than a browsing loop. We ran Gemini with Google Search grounding in its Pro and Flash tiers, Linkup deep search, and Perplexity's sonar-pro.

Consumer-assistant web search is what you get when you ask ChatGPT or Claude to look something up. Each desktop app's search is the same web-search tool the provider exposes on its API, so we ran it headless: GPT-5.4 and GPT-5.5 through OpenAI's Responses API, and Claude Sonnet 4.6 and Opus 4.8 through Anthropic's Messages API, each with that provider's web_search tool. This is the model and the search the app runs on, and it is not the consumer product. The apps wrap the model in a hidden system prompt and interface we cannot see or replicate, so we label these entries by model and web search rather than by app name.

| Product | Model | Access | How it searches |
|---|---|---|---|
| Velora | velora-research | this repository | multi-step agent; editorial-news skills, no site config |
| Gemini Grounded | gemini-3.1-pro-preview, gemini-3.5-flash | Gemini API | Google Search grounding, single pass |
| Linkup | deep search, sourcedAnswer | Linkup API | source-quality deep search |
| Perplexity | sonar-pro | Perplexity API | grounded search, single pass |
| ChatGPT | gpt-5.4, gpt-5.5 | OpenAI Responses API | web_search tool, reasoning effort medium |
| Claude | claude-sonnet-4-6, claude-opus-4-8 | Anthropic Messages API | web_search tool, default effort |

Every agent received the same instruction, to produce a sourced, verifiable research report for a news publication, and otherwise ran as it ships. The instruction names no primary, no source, and no fact, so whether an agent sources well is what the benchmark measures rather than what it was told to do. We tuned none of them to the cases.

One setting on the consumer-assistant models needed a deliberate choice. OpenAI's web search runs under a reasoning-effort dial, and left unset each GPT version picks a different default: GPT-5.4 barely searched, while GPT-5.5 ran an open-ended loop of more than thirty queries that took two minutes and cost ten times as much. We pinned both to medium effort, a thorough but bounded search that matches how the other products work and how the app answers an ordinary question, and that makes the two GPT versions measure the same behaviour. Claude's web search is bounded by default and needed no such setting.

## How it is scored

Every check comes from one language model judge. The judge compares the brief against the fixed answer key and marks each one yes or no, so it scores agreement with known facts. The judge prompt is in the appendix.

`primary_reached` is grounded in code before the judge rules. The harness normalizes every listed primary URL and reports whether one appears in the brief, and the judge takes that match as evidence in deciding whether the agent reached the source. The grounding keeps the verdict robust to URL form: an official source cited in a different form still counts, and a fact carried over from a secondary write-up does not.

Research agents vary from run to run. We ran each provider twice over the full set and report both runs. Where two providers' ranges overlap we treat them as level.

## Sample size

The benchmark runs 30 cases. Every provider answers the same 30, so each comparison measures a within-case difference, and that paired design is what lets a set this size separate providers. The 30 span around twenty domains, from central-bank policy to a game reveal to a road-race result, and the primary often sits in a non-obvious place, so the set tests whether an agent sources well in general rather than on one familiar beat. It resolves score gaps of roughly half a point and wider, and reports providers closer than that as level. Thirty is the floor: small enough that every answer key stays human-authored and every primary validated against real coverage, large enough to read as a deliberate test. The set will grow.

## How cost is measured

Each provider reports its own usage, the tokens or searches a run consumed. We price that usage at the provider's public list rates, so every cost figure is reproducible from the run data. Where a tool charges a per-search fee we count the searches the run reports and price them at the published rate. For a web-search tool on a reasoning model the search results injected into the context are billed as input tokens at the model's rate, so we include them, which is why a thorough search costs more than its answer length suggests.

Velora's cost is wholesale, the model tokens and API calls a run consumes. The third-party figures are retail, the price each vendor charges for the same work. The two are not strictly comparable, and we label which is which.

# Results

> _Wait on the full two-run set under the −2..+4 rubric._

## Leaderboard

> _Composite as a percentage, sorted, with a band marking the two-run range so
> close providers read as level rather than ranked._

[[DATA: charts/leaderboard_lollipop]]

## Where the points come from

> _The per-dimension breakdown: pass rate per provider on each of the five checks.
> A provider can score on the facts while failing to reach the primary or to cite
> it, the laundering pattern. Shown as a provider-by-check heatmap._

[[DATA: charts/checks_heatmap]]

## Breadth, not per-domain ranking

We do not break the leaderboard down by domain. At one or two cases a domain the per-domain numbers would be noise, and ranking on them would invite a reader to over-read a single case. The spread across roughly twenty domains is a property of the set, listed in full in the appendix, and what it buys is generalisation: a score earned here is not a score on one familiar beat. Where a provider wins or loses on a particular kind of source, the failure-mode section names it from the cases themselves.

## Quality against cost

> _Composite percentage against cost per case, cost on a linear axis from zero so
> a cheap provider reads cheap and not free. Read the wholesale-versus-retail
> label when reading Velora's position. Let the data decide whether this leads
> the results or supports them._

[[DATA: charts/cost_quality]]

# Failure modes

> _The qualitative core. Lead with a frequency table of each mode across all
> cases and providers, Velora included, then show two or four excerpts as
> illustration, chosen by a stated rule. The patterns to count:_
>
> - **Laundering.** The fact is right but credited to a secondary outlet.
> - **No provenance trace.** The primary is reached and listed, but no fact is
>   tied to it; the reader must dig through the sources to learn where each came
>   from.
> - **Fabricated specifics.** A date or figure the source never stated.
> - **Missing the primary.** A tracker or a rival's write-up in place of the
>   authoritative document.
> - **Stale incidentals.** A changeable fact answered from memory.

[[DATA: failure-mode frequency table, then selected excerpts]]

# Limitations

The set is 30 cases. It separates providers that differ by a clear margin and leaves closer ones level. The cases spread across roughly twenty domains for breadth, so the set supports no per-domain claims at all: one or two cases a domain is a sample of one or two, and we rank only the overall result.

Research agents are not deterministic. Two runs catch gross variance but not fine differences, so we present close providers as level.

The soft checks come from a language model judge. We anchor it to fixed keys and keep each check binary, and it stays a model's judgment. We publish the judge prompt so it can be read.

Cost is wholesale for Velora and retail for the third parties. The figures show what a run costs to an order of magnitude, not a like-for-like price.

We build Velora and Velora is in the benchmark. The harness, the cases, the keys, and the per-case scores are public, the keys are written from primary sources, and we report Velora's losses. You can run it yourself.

# Reproducibility

The harness, the cases, the answer keys, and the per-case results live in a public repository. Running it reproduces the scoring on fixed inputs.

[[DATA: repository link and the exact run command]]

Each case is one file. Adding a case or a provider is one file or one adapter. The model versions and run dates are pinned above, so a later run with newer models is a new measurement under a new version.

Live results drift. The agents read the open web, pages move under them, models change, and a primary can go offline. The scoring logic stays fixed, so a given report scores the same way every time, while the numbers across providers belong to the date they were run.

# Appendix: the full case set

[[DATA: every case: name, domain, seed, primary source, event date]]
