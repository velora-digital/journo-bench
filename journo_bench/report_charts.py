"""Report charts (plotnine / ggplot grammar) from results.jsonl.

Static charts for the report. Composite scores are shown as a percentage of the
maximum (+4), so a brief that passes every check reads 100%. Run:

    uv run -m evals_public.journo_research.report_charts
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import pandas as pd
from plotnine import (
    aes,
    coord_flip,
    element_blank,
    element_line,
    element_rect,
    element_text,
    geom_col,
    geom_hline,
    geom_point,
    geom_segment,
    geom_text,
    geom_tile,
    geom_vline,
    ggplot,
    ggtitle,
    labs,
    scale_color_manual,
    scale_fill_gradient,
    scale_fill_manual,
    scale_x_continuous,
    scale_y_continuous,
    theme,
    theme_minimal,
)

HERE = Path(__file__).parent
RESULTS = HERE / "results" / "results.jsonl"
OUT = HERE / "charts"
MAXSCORE = 4.0

LABELS = {
    "velora": "Velora",
    "gemini_grounded_pro": "Gemini 3.1 Pro",
    "gemini_grounded_flash": "Gemini 3.5 Flash",
    "perplexity_pro": "Perplexity sonar-pro",
    "linkup": "Linkup",
    "gemini_deep_research": "Gemini Deep Research",
    "perplexity_deep_research": "Perplexity sonar-DR",
}
ACCENT = {
    "Velora": "#3b5bdb",
    "Gemini 3.1 Pro": "#2f9e44",
    "Gemini 3.5 Flash": "#74c476",
    "Perplexity sonar-pro": "#9c36b5",
    "Linkup": "#e8590c",
    "Gemini Deep Research": "#1971c2",
    "Perplexity sonar-DR": "#c2255c",
}
CHECKS = [
    ("primary_reached", "Primary"),
    ("key_facts", "Key facts"),
    ("secondary_facts", "Secondary"),
    ("cited_to_primary", "Citation"),
    ("no_error", "No error"),
]
INK, MUTED, GRIDC, PAPER = "#1d1d24", "#6b6b76", "#ece9e2", "#ffffff"


def _cost(r: dict) -> float:
    if r.get("cost_usd") is not None:
        return r["cost_usd"]
    return (r.get("llm_cost_usd") or 0) + (r.get("external_cost_usd") or 0)


def _load() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = [json.loads(x) for x in RESULTS.read_text().splitlines() if x.strip()]
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        r["no_error"] = r.get("factual_error") is False
        by[r["provider"]].append(r)

    recs, heat = [], []
    for prov, rs in by.items():
        label = LABELS.get(prov, prov)
        runs: dict[str, list[dict]] = defaultdict(list)
        for r in rs:
            runs[r["run_id"]].append(r)
        run_means = [mean(x["score"] for x in g) for g in runs.values() if g]
        score = mean(r["score"] for r in rs)
        durs = [r["duration_s"] for r in rs if r.get("duration_s")]
        dur_runs = [
            mean(d)
            for g in runs.values()
            if (d := [x["duration_s"] for x in g if x.get("duration_s")])
        ]
        recs.append(
            {
                "provider": prov,
                "label": label,
                "pct": score / MAXSCORE * 100,
                "pct_lo": min(run_means) / MAXSCORE * 100,
                "pct_hi": max(run_means) / MAXSCORE * 100,
                "cost": mean(_cost(r) for r in rs),
                "dur": mean(durs) if durs else 0,
                "dur_lo": min(dur_runs) if dur_runs else 0,
                "dur_hi": max(dur_runs) if dur_runs else 0,
            }
        )
        for key, lab in CHECKS:
            heat.append(
                {
                    "label": label,
                    "check": lab,
                    "rate": mean(1.0 if r.get(key) else 0.0 for r in rs) * 100,
                }
            )
    df = pd.DataFrame(recs).sort_values("pct", ascending=False).reset_index(drop=True)
    df["pct_lbl"] = df["pct"].round().astype(int).astype(str) + "%"
    df["dur_lbl"] = df["dur"].round().astype(int).astype(str) + "s"
    heat_df = pd.DataFrame(heat)
    heat_df["rate_lbl"] = heat_df["rate"].round().astype(int).astype(str)
    return df, heat_df


def _theme():
    return theme_minimal() + theme(
        figure_size=(8, 5),
        text=element_text(color=INK, size=11),
        plot_title=element_text(size=15, weight="bold", ha="left"),
        axis_title=element_text(size=11, color=MUTED),
        axis_text=element_text(color=MUTED),
        panel_grid_minor=element_blank(),
        panel_grid_major_y=element_blank(),
        panel_grid_major_x=element_line(color=GRIDC, size=0.6),
        legend_position="none",
        plot_background=element_rect(fill=PAPER, color="none"),
        panel_background=element_rect(fill=PAPER, color="none"),
    )


def _cats(df: pd.DataFrame, col: str, by: str, asc: bool) -> pd.DataFrame:
    order = df.sort_values(by, ascending=asc)[col].tolist()
    df = df.copy()
    df[col] = pd.Categorical(df[col], categories=order, ordered=True)
    return df


def _save(p, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p.save(OUT / f"{name}.png", dpi=200, verbose=False)
    p.save(OUT / f"{name}.svg", verbose=False)


def _pal(df: pd.DataFrame) -> dict:
    return {lab: ACCENT.get(lab, "#888") for lab in df["label"]}


# ----------------------------------------------------------------- leaderboard
def leaderboard_lollipop(df: pd.DataFrame) -> None:
    d = _cats(df, "label", "pct", asc=True)
    p = (
        ggplot(d, aes("pct", "label"))
        + geom_segment(aes(x=0, xend="pct", y="label", yend="label"), color=GRIDC, size=1.3)
        + geom_segment(
            aes(x="pct_lo", xend="pct_hi", y="label", yend="label", color="label"),
            size=4.5,
            alpha=0.28,
        )
        + geom_point(aes(color="label"), size=5.5)
        + geom_text(aes(label="pct_lbl"), nudge_x=5.5, ha="left", size=10, color=INK)
        + scale_color_manual(values=_pal(d))
        + scale_x_continuous(limits=(0, 108), expand=(0, 0, 0.02, 0))
        + labs(x="Quality score (% of max)", y="")
        + ggtitle("Primary-source benchmark")
        + _theme()
    )
    _save(p, "leaderboard_lollipop")


def leaderboard_bars(df: pd.DataFrame) -> None:
    d = _cats(df, "label", "pct", asc=True)
    p = (
        ggplot(d, aes("label", "pct", fill="label"))
        + geom_col(width=0.66)
        + geom_text(aes(label="pct_lbl"), nudge_y=2.5, ha="left", size=10, color=INK)
        + scale_fill_manual(values=_pal(d))
        + scale_y_continuous(limits=(0, 105), expand=(0, 0))
        + coord_flip()
        + labs(x="", y="Quality score (% of max)")
        + ggtitle("Primary-source benchmark")
        + _theme()
    )
    _save(p, "leaderboard_bars")


# ----------------------------------------------------------------- cost/quality
def cost_quality(df: pd.DataFrame) -> None:
    xmax = df["cost"].max() * 1.18
    p = (
        ggplot(df, aes("cost", "pct"))
        + geom_point(aes(color="label"), size=5.5, alpha=0.95)
        + geom_text(aes(label="label"), nudge_y=5.5, ha="center", size=9, color=INK)
        + scale_color_manual(values=_pal(df))
        + scale_x_continuous(limits=(0, xmax), labels=lambda xs: [f"${x:.2f}" for x in xs])
        + scale_y_continuous(limits=(0, 100))
        + labs(x="Cost per case (USD)", y="Quality score (% of max)")
        + ggtitle("Quality vs cost")
        + _theme()
        + theme(panel_grid_major_y=element_line(color=GRIDC, size=0.6))
    )
    _save(p, "cost_quality")


# ----------------------------------------------------------------- speed
def speed_lollipop(df: pd.DataFrame) -> None:
    d = _cats(df, "label", "dur", asc=False)
    p = (
        ggplot(d, aes("dur", "label"))
        + geom_segment(aes(x=0, xend="dur", y="label", yend="label"), color=GRIDC, size=1.3)
        + geom_segment(
            aes(x="dur_lo", xend="dur_hi", y="label", yend="label", color="label"),
            size=4.5,
            alpha=0.28,
        )
        + geom_point(aes(color="label"), size=5.5)
        + geom_text(aes(label="dur_lbl"), nudge_x=4.0, ha="left", size=10, color=INK)
        + scale_color_manual(values=_pal(d))
        + scale_x_continuous(expand=(0, 0, 0.13, 0))
        + labs(x="Mean time per case (s)", y="")
        + ggtitle("Speed")
        + _theme()
    )
    _save(p, "speed_lollipop")


def speed_quality(df: pd.DataFrame) -> None:
    p = (
        ggplot(df, aes("dur", "pct"))
        + geom_vline(xintercept=df["dur"].median(), color=GRIDC, size=0.6)
        + geom_hline(yintercept=df["pct"].median(), color=GRIDC, size=0.6)
        + geom_point(aes(color="label"), size=5.5, alpha=0.95)
        + geom_text(aes(label="label"), nudge_y=5.5, ha="center", size=9, color=INK)
        + scale_color_manual(values=_pal(df))
        + scale_x_continuous(expand=(0.12, 0, 0.08, 0))
        + scale_y_continuous(limits=(0, 100))
        + labs(x="Mean time per case (s)", y="Quality score (% of max)")
        + ggtitle("Quality vs speed")
        + _theme()
        + theme(panel_grid_major_y=element_line(color=GRIDC, size=0.6))
    )
    _save(p, "speed_quality")


# ----------------------------------------------------------------- heatmap
def checks_heatmap(heat: pd.DataFrame, order: list[str]) -> None:
    h = heat.copy()
    h["label"] = pd.Categorical(h["label"], categories=order[::-1], ordered=True)
    h["check"] = pd.Categorical(h["check"], categories=[c for _, c in CHECKS], ordered=True)
    p = (
        ggplot(h, aes("check", "label", fill="rate"))
        + geom_tile(color="white", size=1.5)
        + geom_text(aes(label="rate_lbl"), size=10, color=INK)
        + scale_fill_gradient(low="#fbfdf6", high="#74c476", limits=(0, 100), guide=None)
        + labs(x="", y="")
        + ggtitle("Pass rate by check (%)")
        + _theme()
        + theme(
            panel_grid_major_x=element_blank(),
            panel_grid_major_y=element_blank(),
            axis_text_x=element_text(size=11),
        )
    )
    _save(p, "checks_heatmap")


def main() -> None:
    df, heat = _load()
    leaderboard_lollipop(df)
    leaderboard_bars(df)
    cost_quality(df)
    speed_lollipop(df)
    speed_quality(df)
    checks_heatmap(heat, df["label"].tolist())
    print("providers:", ", ".join(df["label"]))
    for _, r in df.iterrows():
        print(
            f"  {r['label']:24} {r['pct']:.0f}%  [{r['pct_lo']:.0f}-{r['pct_hi']:.0f}]  ${r['cost']:.3f}  {r['dur']:.0f}s"
        )
    print(f"\nwrote charts to {OUT}")


if __name__ == "__main__":
    main()
