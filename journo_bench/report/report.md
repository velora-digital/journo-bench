---
title: "journo-bench"
subtitle: "Do AI research agents reach the primary source a newsroom would actually cite?"
author:
  - Danny Bellion (Velora)
  - Peter Stuart (Velora)
date: 2026-06-09
version: "0.1 (draft)"
abstract: >
  journo-bench measures whether an AI research agent reaches the primary source a
  newsroom would cite and ties each fact to it, the axis existing benchmarks leave
  open. Across nine products on thirty recent news events, the field finds the
  facts but struggles to source them: almost one brief in four reaches the primary
  and then credits its facts to a write-up, a failure we call fact laundering.
  GPT-5.5 scores highest at 81 percent; Velora comes within four points at 77 for
  a twenty-fifth of the cost.
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

journo-bench measures a research agent the way an editor checks a story before it runs: did it reach the sources and gather the information the story actually needs. We built thirty cases from recent news events, each with a documentable primary source and a human-authored answer key, then ran nine research products over the same thirty.

Each case scores on five checks. An agent earns a point for reaching the primary source, a point for carrying the key facts the story rests on, a point for the supporting detail that shows it read the source in full, and a point for tying each fact back to that source so a reader can verify it. It loses two points for any claim a known fact contradicts. We present the total as a percentage of the four points on offer.

The clearest finding is about the field, not any one tool. Reaching the facts is the easy part: every product conveys the key facts most of the time. Showing where they came from is the hard part. Across the nine, almost one in four reaches the primary source and then ties its facts to a write-up instead. We call this fact laundering: the fact survives, the source a reader could check does not. The share of briefs whose key facts are tied to a source a reader can follow runs from 83 percent at the top to 7 percent at the bottom.

[[DATA: charts/leaderboard_lollipop | Composite score as a percentage of a perfect brief, averaged over two runs. The ranking tracks how well a tool sources, not whether it finds the facts.]]

[[DATA: charts/cost_quality | Score against cost per case. Velora sits near the top score at the lowest price, while GPT-5.5 buys the lead at twenty-five times the cost. Velora's cost is wholesale, the others vendor list rates.]]

- **GPT-5.5 leads, at the highest cost in the field.** It scores 81 percent and ties its facts to the source better than any other tool, but at around fifty cents a case it is the most expensive tested.
- **Velora is near-frontier at a fraction of the cost.** It scores 77 percent, four points off the lead, ties for the best rate of reaching the primary, and costs around two cents a case, a twenty-fifth of GPT-5.5.
- **The bigger Claude is the weaker buy.** Opus 4.8 scores 60 percent to Sonnet 4.6's 62, costs more than twice as much, and contradicts a known fact in nearly one brief in five.
- **Quality does not track cost.** Opus costs more than twenty times Velora for a lower score, and the cheapest tools score lowest.
- **Velora's own weakness is supporting detail.** At 62 percent on secondary facts it trails the Gemini and Claude models, which read the source more fully. It reaches and attributes better than it elaborates.

---

# Current research benchmarks do not accurately reflect real editorial work

Most benchmarks focus on fact retrieval and pay less attention to locating the correct primary source and tracing each fact back to it. For a newsroom the source is the product. Reaching the document the news came from, whether a filing or the post where it broke, is what makes a piece defensible when a subject disputes it. Citing a secondary write-up instead hands another outlet's error to your readers under your name.

Research benchmarks have moved towards harder retrieval without ever scoring provenance. Factuality sets like SimpleQA and FRAMES check whether a short answer is correct, drawing it from the model's memory or a corpus the test supplies. Open-web sets like BrowseComp send an agent to find hard-to-locate facts on the live web and score the answer it returns. Attribution work, closest to journo-bench, measures whether cited documents support a claim, but grades against a fixed reference corpus rather than the original document a story broke in. Journo-bench scores the axis these leave open: on news the model cannot have memorised, did the agent reach the primary source a newsroom would cite, and is each fact tied to it.

In the AI age, a research agent can return a fluent brief with figures, dates, and quotes, but without a trace back to the document the claim came from, an editor has to redo the sourcing by hand and a reader has to take it on faith. Provenance is the part of research that a confident summary erases, and tracing each fact to its primary source is what journo-bench measures.

## Journo-bench aims to measure real editorial work

The benchmark scores against four key criteria:

1. Does the agent reach the primary source
2. Does the report contain the facts / quotes relevant to the story
3. Does the report correctly link the facts / quotes to the correct primary source
4. Is the report free of factual errors

It does not score writing quality or long-form features. Unlike deep-research benchmarks that reward a fluent, comprehensive report, journo-bench scores whether the agent reached the primary source and tied each fact to it. A brief that reads well and sources from the wrong place fails here.

# The benchmark

## A case

Each case is a seed of around twenty words, the length a real assignment arrives at, paired with a human-authored answer key. The seed names an event and little else, so reaching the facts takes research rather than a reading of the prompt.

Here is one case in full, Lululemon's cut to its full-year outlook. We follow it through the rest of the report.

**Seed.** Lululemon cut its full-year fiscal 2026 outlook after first-quarter results, lowering its revenue and earnings guidance.

**Primary source.** The company's own results release, canonical on corporate.lululemon.com, in the SEC filing, and on the wire it went out on; reaching any of the three counts. The story broke through CNBC, and a newsroom would cite the company, not CNBC.

**Key facts.** The new guidance itself: full-year net revenue lowered to $11.0 billion to $11.15 billion, and diluted EPS to $10.95 to $11.15. The seed says the outlook was cut; the numbers take research.

**Secondary fact.** The first-quarter result that prompted the cut, net revenue of $2.5 billion, up 4 percent.

**The trap.** Lululemon's prior guidance was higher, $11.35 to $11.50 billion in revenue and $12.10 to $12.30 in EPS. Those stale figures sit all over pre-cut coverage, and a brief that presents them as the current outlook has asserted a fact the release contradicts.

## How the cases were built

Every case is a real news event chosen for two properties: a documentable primary source a newsroom would cite, a filing or a first-hand post, and an event date that postdates the training cutoffs of every model tested. The cutoff rule is what makes a correct answer evidence of research, so a date or figure pulled from memory is the failure the benchmark catches. The events span sport, retail, public policy, finance, and consumer launches. We wrote each answer key from the primary itself, before running any agent. The case set was committed and tagged before the first run, and the runs followed on 8 to 10 June 2026, so the keys verifiably predate every result. The full case set, one YAML file per case with its seed, primary URL and answer key, lives in the public repository under that tag.

## The answer key

The key pins the primary source itself, the document or post the news came from, recorded as the URL a newsroom would cite. Both `primary_reached` and `citation` are scored against it: one asks whether the agent got to that document, the other whether it tied its facts back to it. An event can have more than one valid primary, an official filing and the first-hand post that broke it, and the key lists each.

The key then holds three kinds of fact drawn from that source, scored differently.

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

Velora is the multi-step research agent we built and use inside the Velora platform. It plans a search, reaches and reads the sources, follows an attributed quote back to where it was said, and writes a sourced brief. For the benchmark it runs the agent as it ships for news across any domain. That shipped configuration includes the generic editorial-news research skills the article pipeline loads for every news story, guidance to reach the primary and follow an attributed quote, with no site-specific configuration. The skills are part of the product rather than the benchmark, and they do real work: a stripped runner without them reaches the primary far less often.

Grounded search APIs return a sourced answer from a single call, the model paired with web search or retrieval. We ran three: Google's Gemini grounding on the 3.1 Pro and 3.5 Flash models, Linkup's deep search, and Perplexity's sonar-pro. None runs the multi-step loop that plans, reads a source in full, and follows a lead to the next, so they stand for the off-the-shelf grounded answer a newsroom could wire up with one request.

Consumer-assistant web search is what you get when you ask ChatGPT or Claude to look something up. Each desktop app's search is the same web-search tool the provider exposes on its API, so we ran it headless: GPT-5.4 and GPT-5.5 through OpenAI's Responses API, and Claude Sonnet 4.6 and Opus 4.8 through Anthropic's Messages API, each with that provider's web_search tool. 

This is the model and the search the app runs on, and it is not the consumer product. The apps wrap the model in a hidden system prompt and interface we cannot see or replicate, so we label these entries by model and web search rather than by app name.

| Product | Model | Access | How it searches |
|---|---|---|---|
| Velora | velora-research | this repository | multi-step agent; editorial-news skills, no site config |
| Gemini Grounded | gemini-3.1-pro-preview, gemini-3.5-flash | Gemini API | Google Search grounding, single pass |
| Linkup | deep search, sourcedAnswer | Linkup API | source-quality deep search |
| Perplexity | sonar-pro | Perplexity API | grounded search, single pass |
| ChatGPT | gpt-5.4, gpt-5.5 | OpenAI Responses API | web_search tool, reasoning effort medium |
| Claude | claude-sonnet-4-6, claude-opus-4-8 | Anthropic Messages API | web_search tool, default effort |

All runs were executed between 8 and 10 June 2026.

Every agent received the same instruction, to produce a sourced, verifiable research report for a news publication, and otherwise ran as it ships. The instruction names no primary, no source, and no fact, so whether an agent sources well is what the benchmark measures rather than what it was told to do. We tuned none of them to the cases.

One setting on the consumer-assistant models needed a deliberate choice. OpenAI's web search runs under a reasoning-effort dial, and left unset each GPT version picks a different default: GPT-5.4 barely searched, while GPT-5.5 ran an open-ended loop of more than thirty queries that took two minutes and cost ten times as much. 

We pinned both to medium effort, a thorough but bounded search that matches how the other products work and how the app answers an ordinary question, and that makes the two GPT versions measure the same behaviour. Claude's web search is bounded by default and needed no such setting.

## How it is scored

Every check comes from one language model judge, GPT-5.4-mini. The judge compares the brief against the fixed answer key and marks each one yes or no, so it scores agreement with known facts. The judge prompt is in the appendix.

`primary_reached` is decided by the judge, grounded by a code check. The harness normalises every listed canonical URL and flags whether one appears verbatim in the brief; that flag goes to the judge as strong evidence. The judge also accepts another official URL of the same source for the story, so the verdict is robust to which form the agent cites, and it rejects a fact carried over from a secondary write-up that never reached the primary.

Research agents vary from run to run. We ran each provider twice over the full set, rank on the average, and show both runs so the spread is visible. The variance is real: the widest spread came from GPT-5.4, whose two runs landed eight points apart, while GPT-5.5 scored identically on both. A gap of a point or two sits inside that observed swing and should be read accordingly.

## Sample size

The benchmark runs 30 cases. Every provider answers the same 30, so each comparison measures a within-case difference, and that paired design is what lets a set this size separate providers. The 30 span around twenty domains, from central-bank policy to a game reveal to a road-race result, and the primary often sits in a non-obvious place, so the set tests whether an agent sources well in general rather than on one familiar beat. 

Thirty is the floor: small enough that every answer key stays human-authored and every primary validated against real coverage, large enough to read as a deliberate test. The set will grow.

## How cost is measured

Each provider reports its own usage, the tokens or searches a run consumed. We price that usage at the provider's public list rates, so every cost figure is reproducible from the run data. Where a tool charges a per-search fee we count the searches the run reports and price them at the published rate. For a web-search tool on a reasoning model the search results injected into the context are billed as input tokens at the model's rate, so we include them, which is why a thorough search costs more than its answer length suggests.

Velora's cost is wholesale, the model tokens and API calls a run consumes. The third-party figures are retail, the price each vendor charges for the same work. The two are not strictly comparable, and we label which is which.

# Results

## Leaderboard

[[DATA: charts/leaderboard_lollipop | GPT-5.5 leads at 81 percent and Velora follows at 77; GPT-5.4 and the two Gemini models form a band in the low seventies; Perplexity and Linkup trail by a wide margin.]]

GPT-5.5 leads at 81 percent, the only tool clear of the pack and the most expensive in the field. Velora follows at 77: GPT-5.5 scored 81 on both runs, Velora's runs landed at 76 and 78. A band sits behind them, GPT-5.4 at 71, Gemini 3.5 Flash at 70 and Gemini 3.1 Pro at 68, separated by three points across the three. Claude Sonnet 4.6 is at 62 and Opus 4.8 at 60. A wide gap then opens to Perplexity sonar-pro at 35 and Linkup at 29. Each figure is the percentage of a perfect brief, averaged over two runs, and the band on each marker is the spread between them.

## Where the points come from

[[DATA: charts/checks_heatmap | Every tool conveys the key facts; they separate on reaching the primary and tying facts to it. The tools that gather the most detail cite it the least.]]

The split is in how a tool sources, not whether it finds facts. Every tool conveys the key facts most of the time, with key-fact rates from 63 to 92 percent. The separation opens on the two axes a newsroom cannot compromise: reaching the primary, and tying each fact to it.

Three tools reach the primary most often, Velora, GPT-5.4 and GPT-5.5 at 87 percent each. GPT-5.5 then cites best in the field at 83, ahead of GPT-5.4 at 77 and Velora at 73. Velora and GPT-5.5 keep their briefs cleanest of error, contradicting a listed fact in 2 percent of cases.

The tools that gather the most detail cite it the least. Claude Sonnet 4.6 carries the fullest supporting record, passing on secondary facts in 77 percent of cases, and earns the citation point in only 35. Claude Opus 4.8 matches that record at 77 and cites in 45. Gemini 3.1 Pro reaches the primary in 73 percent of cases and cites in 48. Linkup earns the citation point in 7 percent of cases, the lowest in the field.

Velora's relative weakness is the supporting detail. At 62 percent on secondary facts it trails Gemini Flash at 85, both Claude models at 77, Gemini Pro at 75 and GPT-5.5 at 65, each of which reads the source more fully. It reaches and attributes a fact better than it elaborates on it.

## Breadth, not per-domain ranking

We do not break the leaderboard down by domain. At one or two cases a domain the per-domain numbers would be noise, and ranking on them would invite a reader to over-read a single case. The spread across roughly twenty domains is a property of the set, listed in full in the public repository, and what it buys is generalisation: a score earned here is not a score on one familiar beat. Where a provider wins or loses on a particular kind of source, the failure-mode section names it from the cases themselves.

## Quality against cost

[[DATA: charts/cost_quality | Quality does not track cost. Velora sits in the cheap-and-accurate corner; GPT-5.5 buys the top score at the field's highest price, and Opus 4.8 costs nearly as much for a lower one.]]

Velora sits near the top score at the lowest cost, around two cents a case. GPT-5.5 scores highest and costs the most, around fifty cents a case, because a thorough search on a reasoning model bills its injected results as input tokens. The grounded tools sit mid-cost, Gemini Pro at eight cents and Flash at twelve. Claude Opus 4.8 is the clearest miss on this axis, around forty-seven cents for a score below the cheaper Sonnet. Perplexity and Linkup are cheap and score low. Quality does not track cost across this field, where the second-cheapest tool comes within four points of the most expensive.

Velora's figure is wholesale, its model tokens plus the per-call price of its own searches. Every other figure is the retail price the vendor charges for the same work. The two are not strictly comparable, and the methodology section flags which is which.

# Failure modes

The same failures recur across the field. The categories overlap, a brief can fail in more than one way, so the shares below sum past 100. Counted over all 540 scored briefs, nine products over thirty cases run twice:

| Failure | Share of briefs |
|---|---|
| Thin: a supporting fact dropped | 40% |
| Missing the primary: only a secondary write-up reached | 27% |
| Fact laundering: the primary reached, the facts credited elsewhere | 23% |
| Fabricated specific: a claim a listed fact contradicts | 11% |

Thin briefs are the most common and the least damaging. The fact exists in the source and the article just carries less of the record. It is the failure that most often costs Velora a point.

Fact laundering is the one the benchmark exists to catch. Almost a quarter of all briefs reach the authoritative document and then tie their facts to a write-up instead, so a reader cannot tell the original claim from a rephrasing of it. Among the briefs that did reach the primary, the rate is 31 percent: nearly a third of the time, the source survives the research and dies in the writing. Claude Sonnet 4.6 shows the widest gap in the field, reaching the primary in two-thirds of cases and earning the citation point in barely more than a third.

Missing the primary sits close behind: more than a quarter of briefs never reach the authoritative document and report from a secondary write-up. Linkup misses it most, reaching the primary in 53 percent of cases. The fabricated specific is the rarest and the worst. More than one brief in ten asserts a figure or claim that a listed fact contradicts, the error that becomes a correction, and Gemini Flash and Claude Opus 4.8 do it in nearly one in five.

Fact laundering is easiest to see in a single case. On the Lululemon guidance cut, Velora and Gemini 3.1 Pro both scored 3 out of 4, and lost different points. Velora carried less of the quarter's detail and tied the guidance, the spine of the story, to the release itself:

> "For 2026, the Company now expects net revenue to be in the range of $11.000 billion to $11.150 billion, representing a decline of 1% to 0%." (lululemon athletica inc. press release) [2]

Gemini wrote the fuller brief, with the prior guidance, the margin numbers and a paragraph of analyst reaction, and its source list includes the same release. The guidance figures themselves it footnoted to write-ups:

> **Full-Year Revenue:** Adjusted downward to a range of $11.00 billion to $11.15 billion[6]. **Full-Year EPS:** Lowered to $10.95 to $11.15, down from previously expected $12.10 to $12.30[3].
>
> [3] qz.com/lululemon-full-year-guidance-cut-product-sales · [6] retailtouchpoints.com/news/lululemons-q1-profits-slide

A reader checking the new numbers lands on qz.com while the company's own release sits unused in the same source list. The fact is right and the provenance is gone. Gemini lost the citation point and Velora lost the secondary-detail point, the same score by opposite failures, and only one of the two lets an editor check the central claim against the source.

# Limitations

The set is 30 cases. It separates providers that differ by a clear margin; a gap of a point or two between neighbours is within the run-to-run swing we observed and should be read loosely. The cases spread across roughly twenty domains for breadth, so the set supports no per-domain claims at all: one or two cases a domain is a sample of one or two, and we rank only the overall result.

Research agents are not deterministic. We rank on the average of two runs and show both, so a reader can see where a ranking rests on a fine difference.

The soft checks come from a language model judge, GPT-5.4-mini, the same model family as two of the products it scores. It is a different model version from either entry, and it judges agreement with a human-authored answer key rather than its own sense of quality, so the family overlap buys it no say in what counts as correct. The most load-bearing check, primary_reached, is further grounded by a deterministic URL match. It stays a model's judgment, and we publish the judge prompt so it can be read.

Cost is wholesale for Velora and retail for the third parties. The figures show what a run costs to an order of magnitude, not a like-for-like price.

We build Velora and Velora is in the benchmark. The harness, the cases, the keys, and the per-case scores are public, the keys are written from primary sources, and we report Velora's losses. You can run it yourself.

# Reproducibility

The harness, the cases, the answer keys, and the per-case results live in a public repository. Running it reproduces the scoring on fixed inputs.

The repository is [github.com/velora-digital/journo-bench](https://github.com/velora-digital/journo-bench), and the case set behind these results is frozen at the tag `journo-bench-cases-v0.1`. The run command:

```
uv sync --extra providers
uv run -m journo_bench.run --agent all
```

Scoring needs `OPENAI_API_KEY` for the judge; each adapter wakes when its provider key is present.

Each case is one file. Adding a case or a provider is one file or one adapter. The model versions and run dates are pinned above, so a later run with newer models is a new measurement under a new version.

Live results drift. The agents read the open web, pages move under them, models change, and a primary can go offline. The scoring logic stays fixed, so a given report scores the same way every time, while the numbers across providers belong to the date they were run.

# Appendix: the judge prompt

The judge runs once per brief and returns all five checks with a one-sentence reason each. Its system message and per-case template, verbatim; the braced placeholders are filled from the case's answer key and the brief under judgment.

System message:

```
You are a meticulous editorial fact-checker scoring a research brief
against a verified answer key. Judge only against what the key states.
```

Per-case template:

```
A research agent produced the brief below from a short news tip.
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

4. cited_to_primary (true/false) + citation_reason: true only if the brief
   attributes the key facts to the primary source DETERMINATELY — a reader can
   tell those facts came from the primary specifically, without guessing. An
   inline citation or footnote marker tied to the facts, or explicit phrasing
   ("the release said", "according to {source}"), establishes this. A naked
   statement of the facts followed by an undifferentiated list of sources does
   NOT count, even when the primary is in that list: if the reader must dig
   through several links to work out which one a fact came from, the provenance
   is not established. Do NOT require a named journalist, byline, or exact
   wording — only that each key fact is traceable to the primary. False if the
   facts are tied only to a secondary outlet, or to no specific source.

5. has_factual_error (true/false) + errors + error_reason: true if the brief
   asserts anything that contradicts a fact in ANY of the three lists above
   (key, secondary, or incidental). Incidental facts are background the story
   touches but is not about — the brief is not expected to mention them, but it
   must not get them wrong. List each contradicting claim in `errors`. A simple
   omission is never an error.
```
