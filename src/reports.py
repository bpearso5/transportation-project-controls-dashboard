"""
Standardized report generation.

Produces two views of the same portfolio for different audiences — clear,
standardized reports for Project Managers and executive leadership:

  - executive_summary(): one-page portfolio rollup for leadership
  - pm_detail_report():  project-by-project detail for a PM / region

Both return Markdown strings so they can be displayed in the app, downloaded,
copied into email, or later rendered to PDF.
"""

from __future__ import annotations

import pandas as pd


def _money(x: float) -> str:
    return f"${x/1_000_000:,.1f}M"


def _variance(df: pd.DataFrame) -> pd.Series:
    return df["spent_to_date"] - df["budget"] * (df["pct_complete"] / 100)


def executive_summary(df: pd.DataFrame, as_of: str = "2026-05-01") -> str:
    total = len(df)
    by_status = df["status"].value_counts().to_dict()
    on_track = by_status.get("On Track", 0)
    pct_on_track = (on_track / total * 100) if total else 0
    total_budget = df["budget"].sum()
    total_spent = df["spent_to_date"].sum()

    status_lines = "\n".join(
        f"- **{status}:** {count} ({count/total*100:.0f}%)"
        for status, count in sorted(by_status.items())
    )
    region_tbl = (
        df.groupby("region")
        .agg(projects=("project_id", "count"),
             budget=("budget", "sum"),
             spent=("spent_to_date", "sum"))
        .reset_index()
    )
    region_lines = "\n".join(
        f"| {r['region']} | {int(r['projects'])} | {_money(r['budget'])} | {_money(r['spent'])} |"
        for _, r in region_tbl.iterrows()
    )

    attention = df[df["status"].isin(["Delayed", "At Risk"])].sort_values("budget", ascending=False).head(5)
    attention_lines = "\n".join(
        f"- {row['project_id']} — {row['project_name']} ({row['status']}, {_money(row['budget'])})"
        for _, row in attention.iterrows()
    ) or "- None"

    return f"""# Portfolio Executive Summary
**As of {as_of}**

## Snapshot
- **Active projects:** {total}
- **Total program budget:** {_money(total_budget)}
- **Spent to date:** {_money(total_spent)} ({total_spent/total_budget*100:.0f}% of budget)
- **On-track rate:** {pct_on_track:.0f}%

## Status breakdown
{status_lines}

## By region
| Region | Projects | Budget | Spent |
|---|---|---|---|
{region_lines}

## Needs leadership attention
{attention_lines}
"""


def pm_detail_report(df: pd.DataFrame, region: str | None = None, as_of: str = "2026-05-01") -> str:
    scope = df if region in (None, "All regions") else df[df["region"] == region]
    scope = scope.copy()
    scope["sched_flag"] = (
        pd.to_datetime(scope["forecast_end_date"]) > pd.to_datetime(scope["planned_end_date"])
    ).map({True: "⚠ Slipped", False: "On schedule"})

    rows = "\n".join(
        f"| {r['project_id']} | {r['route']} | {r['phase']} | {r['pct_complete']}% | "
        f"{_money(r['budget'])} | {_money(r['spent_to_date'])} | {r['status']} | {r['sched_flag']} |"
        for _, r in scope.sort_values("status").iterrows()
    )
    title = region if region not in (None, "All regions") else "All Regions"
    return f"""# PM Detail Report — {title}
**As of {as_of} · {len(scope)} projects**

| Project ID | Route | Phase | % Comp | Budget | Spent | Status | Schedule |
|---|---|---|---|---|---|---|---|
{rows}
"""


if __name__ == "__main__":
    import pathlib
    data = pd.read_csv(pathlib.Path(__file__).resolve().parents[1] / "data" / "projects.csv")
    print(executive_summary(data)[:600], "...\n")
    print(pm_detail_report(data, "Region 3 (Middle)")[:600], "...")
