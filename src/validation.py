"""
Data-quality gate for the project portfolio.

Runs a set of validation rules and returns a tidy DataFrame of issues, each with a
severity. This is the "strong attention to detail and commitment to data accuracy"
piece of the posting: nothing should be reported to leadership before it passes here.
"""

from __future__ import annotations

import pandas as pd

# Rough TN bounding box for coordinate sanity checks.
TN_LAT = (34.98, 36.68)
TN_LON = (-90.31, -81.65)

REQUIRED_FIELDS = ["project_id", "project_name", "route", "region", "budget", "project_manager"]


def _issue(pid, field, severity, message):
    return {"project_id": pid, "field": field, "severity": severity, "issue": message}


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame of data-quality issues (empty if the data is clean)."""
    issues: list[dict] = []

    # Missing required fields
    for field in REQUIRED_FIELDS:
        blank = df[df[field].isna() | (df[field].astype(str).str.strip() == "")]
        for _, row in blank.iterrows():
            issues.append(_issue(row.get("project_id", "?"), field, "High", f"Missing required field '{field}'"))

    # Duplicate project IDs
    dupes = df[df["project_id"].duplicated(keep=False)]
    for pid in dupes["project_id"].unique():
        issues.append(_issue(pid, "project_id", "High", "Duplicate project_id — IDs must be unique"))

    # % complete out of range
    bad_pct = df[(df["pct_complete"] < 0) | (df["pct_complete"] > 100)]
    for _, row in bad_pct.iterrows():
        issues.append(_issue(row["project_id"], "pct_complete", "High",
                             f"pct_complete = {row['pct_complete']} is outside 0–100"))

    # Schedule logic: forecast end before start
    s = pd.to_datetime(df["start_date"], errors="coerce")
    f = pd.to_datetime(df["forecast_end_date"], errors="coerce")
    bad_dates = df[f < s]
    for _, row in bad_dates.iterrows():
        issues.append(_issue(row["project_id"], "forecast_end_date", "High",
                             "Forecast end date is before the start date"))

    # Budget logic: spent over budget but not flagged
    overspent = df[(df["spent_to_date"] > df["budget"]) & (df["status"].isin(["On Track", "At Risk"]))]
    for _, row in overspent.iterrows():
        pct_over = (row["spent_to_date"] / row["budget"] - 1) * 100
        issues.append(_issue(row["project_id"], "status", "Medium",
                             f"Spent {pct_over:.0f}% over budget but status is '{row['status']}'"))

    # Coordinates outside TN
    off_map = df[
        (df["latitude"] < TN_LAT[0]) | (df["latitude"] > TN_LAT[1]) |
        (df["longitude"] < TN_LON[0]) | (df["longitude"] > TN_LON[1])
    ]
    for _, row in off_map.iterrows():
        issues.append(_issue(row["project_id"], "coordinates", "Medium", "Coordinates fall outside Tennessee"))

    cols = ["project_id", "field", "severity", "issue"]
    return pd.DataFrame(issues, columns=cols)


def summary(issues: pd.DataFrame) -> dict:
    """Quick rollup for a KPI tile."""
    return {
        "total_issues": len(issues),
        "high": int((issues["severity"] == "High").sum()) if len(issues) else 0,
        "medium": int((issues["severity"] == "Medium").sum()) if len(issues) else 0,
    }


if __name__ == "__main__":
    import pathlib
    data = pd.read_csv(pathlib.Path(__file__).resolve().parents[1] / "data" / "projects.csv")
    found = validate(data)
    print(found.to_string(index=False))
    print("\nSummary:", summary(found))
