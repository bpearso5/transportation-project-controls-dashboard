"""
Unit tests for the data-quality gate (src/validation.py).

Each test targets one of the failure modes that data/generate_data.py
deliberately injects into projects.csv, so the suite proves the validation
gate actually catches the problems the project claims it catches.

Run from the repo root with:  pytest
"""

import pathlib
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import validation  # noqa: E402


def make_clean_project(**overrides) -> dict:
    """One internally consistent project row; tests break exactly one rule at a time."""
    row = {
        "project_id": "PRJ-2025-9001",
        "project_name": "I-40 Resurfacing – Test Co.",
        "route": "I-40",
        "county": "Davidson",
        "region": "Region 3 (Middle)",
        "project_type": "Resurfacing",
        "phase": "Construction",
        "status": "On Track",
        "pct_complete": 50,
        "start_date": "2025-01-01",
        "planned_end_date": "2026-01-01",
        "forecast_end_date": "2026-01-01",
        "budget": 10_000_000.0,
        "spent_to_date": 5_000_000.0,
        "project_manager": "T. Test",
        "latitude": 36.16,
        "longitude": -86.78,
        "last_updated": "2026-05-01",
    }
    row.update(overrides)
    return row


def test_clean_data_produces_no_issues():
    # Baseline: if this fails, every other test is meaningless, because the
    # validator would be flagging healthy records (false positives).
    df = pd.DataFrame([make_clean_project()])
    issues = validation.validate(df)
    assert len(issues) == 0


def test_duplicate_project_id_flagged_high():
    # generate_data.py injects a duplicated project_id (issue #5). Duplicate IDs
    # silently double-count budgets in every rollup, so this must be High severity.
    a = make_clean_project()
    b = make_clean_project(project_name="I-24 Widening – Other Co.")  # same project_id
    issues = validation.validate(pd.DataFrame([a, b]))
    dup = issues[issues["field"] == "project_id"]
    assert len(dup) == 1
    assert dup.iloc[0]["severity"] == "High"


def test_forecast_end_before_start_flagged():
    # generate_data.py injects a forecast end date earlier than the start date
    # (issue #2). An impossible schedule corrupts every slip calculation downstream.
    df = pd.DataFrame([make_clean_project(forecast_end_date="2024-12-01")])
    issues = validation.validate(df)
    assert (issues["field"] == "forecast_end_date").sum() == 1
    assert issues.iloc[0]["severity"] == "High"


@pytest.mark.parametrize("bad_pct", [-5, 140])
def test_pct_complete_out_of_range_flagged(bad_pct):
    # generate_data.py injects pct_complete = 140 (issue #1). Values outside
    # 0-100 break the progress bars and any weighted-average completion metric.
    df = pd.DataFrame([make_clean_project(pct_complete=bad_pct)])
    issues = validation.validate(df)
    assert (issues["field"] == "pct_complete").sum() == 1


def test_missing_project_manager_flagged():
    # generate_data.py blanks out a project_manager (issue #3). Reports route
    # follow-ups through the PM, so a missing owner is a High-severity gap.
    df = pd.DataFrame([make_clean_project(project_manager="")])
    issues = validation.validate(df)
    assert (issues["field"] == "project_manager").sum() == 1
    assert issues.iloc[0]["severity"] == "High"


def test_overspent_but_on_track_flagged():
    # generate_data.py injects a project 60% over budget still marked "On Track"
    # (issue #4). This is the status-vs-financials mismatch leadership most
    # needs surfaced before a report goes out.
    df = pd.DataFrame([make_clean_project(spent_to_date=16_000_000.0)])
    issues = validation.validate(df)
    assert (issues["field"] == "status").sum() == 1
    assert issues.iloc[0]["severity"] == "Medium"
