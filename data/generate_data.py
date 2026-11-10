"""
Generate synthetic transportation project data styled after state DOT project controls.

IMPORTANT: This is 100% fabricated data for portfolio/demo purposes.
It does not use, reference, or reproduce any real transportation agency records.

Outputs three files in this directory:
  - projects.csv          one row per project (the portfolio)
  - budget_snapshots.csv  monthly planned-vs-actual spend per project (for trend lines)
  - deliverables.csv      submittal / deliverable log per project (for review tracking)

A handful of deliberate data-quality issues are injected at the end so the
validation module has something real to catch. They are documented in README.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEED = 42
N_PROJECTS = 42
TODAY = pd.Timestamp("2026-05-01")

rng = np.random.default_rng(SEED)

# The state is split into 4 regions. We cluster projects around the regional hub cities
# and scatter them with noise so the map looks realistic.
REGIONS = {
    "Region 1 (East)":      {"hub": (35.96, -83.92), "counties": ["Knox", "Blount", "Sevier", "Anderson", "Loudon"]},
    "Region 2 (Southeast)": {"hub": (35.05, -85.31), "counties": ["Hamilton", "Bradley", "Marion", "McMinn", "Rhea"]},
    "Region 3 (Middle)":    {"hub": (36.16, -86.78), "counties": ["Davidson", "Williamson", "Rutherford", "Wilson", "Sumner"]},
    "Region 4 (West)":      {"hub": (35.15, -90.05), "counties": ["Shelby", "Madison", "Tipton", "Fayette", "Gibson"]},
}

ROUTES_BY_REGION = {
    "Region 1 (East)":      ["I-40", "I-75", "I-275", "US-129", "SR-62"],
    "Region 2 (Southeast)": ["I-24", "I-75", "US-27", "SR-153", "US-64"],
    "Region 3 (Middle)":    ["I-40", "I-24", "I-65", "I-440", "US-31", "SR-840"],
    "Region 4 (West)":      ["I-40", "I-55", "I-240", "US-51", "SR-385"],
}

PROJECT_TYPES = [
    "Resurfacing", "Bridge Replacement", "Interchange Reconstruction",
    "Lane Widening", "Safety Improvement", "ITS / Signals",
]

PHASES = ["Planning", "Design", "Right-of-Way", "Construction", "Closeout"]

PROJECT_MANAGERS = [
    "M. Sheeran", "D. Patel", "R. Coleman", "T. Nguyen",
    "A. Brooks", "J. Rivera", "S. Okafor",
]


def _make_project(i: int) -> dict:
    region = rng.choice(list(REGIONS.keys()))
    hub_lat, hub_lon = REGIONS[region]["hub"]
    county = rng.choice(REGIONS[region]["counties"])
    route = rng.choice(ROUTES_BY_REGION[region])
    ptype = rng.choice(PROJECT_TYPES)
    pm = rng.choice(PROJECT_MANAGERS)

    # Scatter around the regional hub, then clamp to a rough TN bounding box.
    lat = float(np.clip(hub_lat + rng.normal(0, 0.45), 34.98, 36.68))
    lon = float(np.clip(hub_lon + rng.normal(0, 0.55), -90.31, -81.65))

    phase = rng.choice(PHASES, p=[0.12, 0.20, 0.13, 0.45, 0.10])

    # % complete is tied to phase so the data is internally consistent.
    phase_pct = {
        "Planning": (2, 15), "Design": (15, 40), "Right-of-Way": (35, 55),
        "Construction": (45, 95), "Closeout": (95, 100),
    }[phase]
    pct_complete = int(rng.integers(phase_pct[0], phase_pct[1] + 1))

    start = TODAY - pd.Timedelta(days=int(rng.integers(120, 900)))
    planned_duration = int(rng.integers(240, 1100))
    planned_end = start + pd.Timedelta(days=planned_duration)

    # Most projects track close to plan; some slip.
    slip_days = int(rng.choice([0, 0, 0, 30, 60, 120, 200], p=[0.4, 0.15, 0.1, 0.12, 0.1, 0.08, 0.05]))
    forecast_end = planned_end + pd.Timedelta(days=slip_days)

    budget = round(float(rng.uniform(0.8, 48.0)), 2) * 1_000_000  # $0.8M - $48M
    # Spend roughly tracks % complete, with a little noise (some over/under).
    spend_ratio = (pct_complete / 100) * rng.uniform(0.90, 1.12)
    spent = round(budget * spend_ratio, 0)

    # Status derived from schedule + budget health.
    over_budget = spent > budget
    if pct_complete >= 100:
        status = "Complete"
    elif slip_days >= 120 or over_budget:
        status = "Delayed"
    elif slip_days >= 30 or spend_ratio > 1.0:
        status = "At Risk"
    else:
        status = "On Track"

    return {
        "project_id": f"PRJ-{start.year}-{1000 + i}",
        "project_name": f"{route} {ptype} – {county} Co.",
        "route": route,
        "county": county,
        "region": region,
        "project_type": ptype,
        "phase": phase,
        "status": status,
        "pct_complete": pct_complete,
        "start_date": start.date().isoformat(),
        "planned_end_date": planned_end.date().isoformat(),
        "forecast_end_date": forecast_end.date().isoformat(),
        "budget": round(budget, 2),
        "spent_to_date": float(spent),
        "project_manager": pm,
        "latitude": round(lat, 5),
        "longitude": round(lon, 5),
        "last_updated": TODAY.date().isoformat(),
    }


def build_projects() -> pd.DataFrame:
    return pd.DataFrame([_make_project(i) for i in range(N_PROJECTS)])


def build_snapshots(projects: pd.DataFrame) -> pd.DataFrame:
    """Monthly cumulative planned vs. actual spend per project, for burn-trend charts."""
    rows = []
    for _, p in projects.iterrows():
        start = pd.Timestamp(p["start_date"])
        planned_end = pd.Timestamp(p["planned_end_date"])
        end = min(TODAY, planned_end)
        if end <= start:
            continue
        months = pd.date_range(start, end, freq="MS")
        total_days = (planned_end - start).days or 1
        for m in months:
            frac = np.clip((m - start).days / total_days, 0, 1)
            planned_cum = round(p["budget"] * frac, 0)
            # Actual wobbles around planned and lands near spent_to_date.
            noise = rng.uniform(0.85, 1.10)
            actual_cum = round(min(p["spent_to_date"], p["budget"] * frac * noise), 0)
            rows.append({
                "project_id": p["project_id"],
                "snapshot_date": m.date().isoformat(),
                "planned_cumulative": float(planned_cum),
                "actual_cumulative": float(actual_cum),
            })
    return pd.DataFrame(rows)


def inject_issues(projects: pd.DataFrame) -> pd.DataFrame:
    """Insert a few deliberate, documented data-quality problems for the validator to catch."""
    df = projects.copy()
    # 1. % complete out of range
    df.loc[3, "pct_complete"] = 140
    # 2. Forecast end before start date (impossible schedule)
    df.loc[7, "forecast_end_date"] = (pd.Timestamp(df.loc[7, "start_date"]) - pd.Timedelta(days=10)).date().isoformat()
    # 3. Missing project manager
    df.loc[12, "project_manager"] = ""
    # 4. Spend far over budget but still flagged "On Track"
    df.loc[18, "spent_to_date"] = round(df.loc[18, "budget"] * 1.6, 0)
    df.loc[18, "status"] = "On Track"
    # 5. Duplicate project_id
    df.loc[25, "project_id"] = df.loc[24, "project_id"]
    return df


# ----- Deliverables / submittal log ------------------------------------------

DISCIPLINES = [
    "Roadway", "Structures", "Drainage", "Utilities",
    "Right-of-Way", "Environmental", "Traffic / ITS", "Geotechnical",
]

SUBMITTAL_TYPES = [
    "Design Package", "Shop Drawing", "RFI Response", "Monthly Progress Report",
    "Permit Application", "Schedule Update", "QC Inspection Report",
]

REVIEWERS = ["L. Hartman", "K. Osei", "P. Delgado", "C. Mott", "E. Zhang"]


def build_deliverables(projects: pd.DataFrame) -> pd.DataFrame:
    """One row per submittal: what the developer/contractor turned in, when the
    review was due, its current review status, and the evaluation score."""
    drng = np.random.default_rng(7)  # separate stream so existing CSVs are unchanged
    rows = []
    n_sub = 1
    for _, p in projects.iterrows():
        start = pd.Timestamp(p["start_date"])
        window = max((TODAY - start).days, 30)
        for _ in range(int(drng.integers(2, 5))):
            discipline = str(drng.choice(DISCIPLINES))
            stype = str(drng.choice(SUBMITTAL_TYPES))
            submitted = start + pd.Timedelta(days=int(drng.integers(0, window)))
            review_days = int(drng.choice([14, 21, 30]))
            due = submitted + pd.Timedelta(days=review_days)

            status = str(drng.choice(
                ["Approved", "Approved as Noted", "Revise & Resubmit", "Under Review"],
                p=[0.45, 0.20, 0.12, 0.23]))
            if status == "Under Review":
                # open reviews are recent: some current, some past due
                submitted = TODAY - pd.Timedelta(days=int(drng.integers(1, 60)))
                due = submitted + pd.Timedelta(days=review_days)
            completed = submitted + pd.Timedelta(days=int(drng.integers(3, review_days + 25)))
            if status == "Under Review" or completed > TODAY:
                status, completed_str, score = "Under Review", "", ""
            else:
                completed_str = completed.date().isoformat()
                score = int(drng.choice([2, 3, 4, 5], p=[0.05, 0.20, 0.45, 0.30]))

            rows.append({
                "submittal_id": f"SUB-{n_sub:04d}",
                "project_id": p["project_id"],
                "title": f"{discipline} — {stype}",
                "discipline": discipline,
                "submittal_type": stype,
                "submitted_date": submitted.date().isoformat(),
                "review_due_date": due.date().isoformat(),
                "review_status": status,
                "review_completed_date": completed_str,
                "evaluation_score": score,
                "reviewer": str(drng.choice(REVIEWERS)),
            })
            n_sub += 1
    return pd.DataFrame(rows)


def main() -> None:
    projects = build_projects()
    snapshots = build_snapshots(projects)
    deliverables = build_deliverables(projects)
    projects = inject_issues(projects)

    out_dir = __import__("pathlib").Path(__file__).resolve().parent
    projects.to_csv(out_dir / "projects.csv", index=False)
    snapshots.to_csv(out_dir / "budget_snapshots.csv", index=False)
    deliverables.to_csv(out_dir / "deliverables.csv", index=False)
    print(f"Wrote {len(projects)} projects, {len(snapshots)} budget snapshots, "
          f"and {len(deliverables)} deliverables.")


if __name__ == "__main__":
    main()
