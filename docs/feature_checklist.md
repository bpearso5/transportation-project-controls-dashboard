# Feature Checklist — mapped to the HDR posting

This is the build checklist for the dashboard. Each item ties a feature to a
specific responsibility or qualification from the *Data Management Project
Coordinator* posting, and to the file that delivers it. Check items off as you
extend the scaffold.

## Primary Responsibilities

| Posting language | Feature in this project | File | Status |
|---|---|---|---|
| Project control: workflow tracking, scheduling, production monitoring | "Project Controls" tab — phase, % complete, schedule slip flag, status | `src/app.py` | ✅ scaffolded |
| Quality management; commitment to data accuracy | Data-quality gate that validates every record before reporting | `src/validation.py` | ✅ scaffolded |
| Financial commitments; summarize budgets | Budget tab — planned vs. spent vs. remaining per project | `src/app.py` | ✅ scaffolded |
| Integrate project data into mapping tools | Interactive Tennessee map, color = status, size = budget | `src/app.py` (Plotly) | ✅ scaffolded |
| Track trends | Program burn trend, planned vs. actual cumulative spend over time | `src/app.py` + `data/budget_snapshots.csv` | ✅ scaffolded |
| Generate standardized reports for PMs and executive leadership | Two report views (exec rollup + PM detail), one-click download | `src/reports.py` | ✅ scaffolded |
| Measure regional progress; support strategic planning | Region rollup in the exec summary + region filter | `src/reports.py`, `src/app.py` | ✅ scaffolded |
| Facilitate data sharing; organize so it's easy to access/understand | Filters, KPI tiles, downloadable reports | `src/app.py` | ✅ scaffolded |

## Preferred Qualifications

| Qualification | How this project speaks to it |
|---|---|
| Competency in transportation systems & data management | Whole project is DOT project-controls data, end to end |
| Strong attention to detail / data accuracy | Dedicated validation module with severity-ranked issues |
| Ability to analyze and interpret project data | KPIs, trends, status logic derived from raw fields |
| Knowledge of project control & PM processes | Phases, schedule baselines vs. forecast, budget variance |
| Produce clear, standardized reports for varied audiences | Same data, two audience-specific report formats |
| Strong collaboration & communication | README written problem → approach → result for a non-technical reader |

## Good next extensions (to deepen the project after the first pass)

- [ ] Add an **SQLite backend** instead of CSV, and write the validation rules as SQL — pulls your SQL data-validation project into this one.
- [ ] Add a **schedule baseline variance** chart (planned vs. forecast end dates across the portfolio).
- [ ] Export the executive summary to **PDF** (reportlab or weasyprint) for a true leadership deliverable.
- [ ] Add a small **"what changed since last month"** diff so the report reads like a real status update.
- [ ] Write a few **unit tests** for `validation.py` (pytest) — signals engineering discipline.
