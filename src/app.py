"""
TDOT-style Project Controls Dashboard
=====================================
Run with:  streamlit run src/app.py

Turns a synthetic transportation project portfolio into the outputs a Data
Management Project Coordinator produces: project controls, budget tracking,
a geographic view, a data-quality gate, and standardized reports.
"""

from __future__ import annotations

import pathlib

import pandas as pd
import plotly.express as px
import streamlit as st

import reports
import validation

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"

STATUS_COLORS = {
    "On Track": "#2E7D32", "At Risk": "#F9A825",
    "Delayed": "#C62828", "Complete": "#1565C0",
}

st.set_page_config(page_title="TDOT Project Controls", layout="wide")


@st.cache_data
def load_data():
    projects = pd.read_csv(DATA_DIR / "projects.csv")
    snapshots = pd.read_csv(DATA_DIR / "budget_snapshots.csv")
    return projects, snapshots


projects, snapshots = load_data()

# ----- Sidebar filters -------------------------------------------------------
st.sidebar.title("Filters")
region = st.sidebar.selectbox("Region", ["All regions"] + sorted(projects["region"].unique()))
statuses = st.sidebar.multiselect("Status", sorted(projects["status"].unique()),
                                  default=sorted(projects["status"].unique()))
ptypes = st.sidebar.multiselect("Project type", sorted(projects["project_type"].unique()),
                                default=sorted(projects["project_type"].unique()))

view = projects.copy()
if region != "All regions":
    view = view[view["region"] == region]
view = view[view["status"].isin(statuses) & view["project_type"].isin(ptypes)]

# ----- Header + KPI row ------------------------------------------------------
st.title("Tennessee Transportation — Project Controls Dashboard")
st.caption("Synthetic demo data. Not affiliated with or sourced from TDOT.")

issues = validation.validate(view)
isum = validation.summary(issues)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Projects", len(view))
k2.metric("Total budget", f"${view['budget'].sum()/1e6:,.0f}M")
k3.metric("Spent to date", f"${view['spent_to_date'].sum()/1e6:,.0f}M")
on_track = (view["status"] == "On Track").mean() * 100 if len(view) else 0
k4.metric("On-track rate", f"{on_track:.0f}%")
k5.metric("Data issues", isum["total_issues"], delta=f"{isum['high']} high", delta_color="inverse")

st.divider()

tab_map, tab_controls, tab_budget, tab_quality, tab_reports = st.tabs(
    ["🗺 Map", "📋 Project Controls", "💵 Budget & Trends", "✅ Data Quality", "📄 Reports"]
)

# ----- Map -------------------------------------------------------------------
with tab_map:
    st.subheader("Geographic distribution")
    st.write("Project locations across Tennessee, sized by budget and colored by status — "
             "the *integrate project data into mapping tools* requirement.")
    fig = px.scatter_mapbox(
        view, lat="latitude", lon="longitude",
        color="status", size="budget", size_max=22,
        color_discrete_map=STATUS_COLORS,
        hover_name="project_name",
        hover_data={"project_id": True, "route": True, "phase": True,
                    "pct_complete": True, "latitude": False, "longitude": False},
        zoom=6, height=560,
    )
    fig.update_layout(mapbox_style="open-street-map", margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)

# ----- Project controls ------------------------------------------------------
with tab_controls:
    st.subheader("Workflow, schedule & status")
    ctrl = view.copy()
    ctrl["schedule"] = (
        pd.to_datetime(ctrl["forecast_end_date"]) > pd.to_datetime(ctrl["planned_end_date"])
    ).map({True: "⚠ Slipped", False: "On schedule"})
    cols = ["project_id", "project_name", "phase", "pct_complete", "status",
            "schedule", "planned_end_date", "forecast_end_date", "project_manager"]
    st.dataframe(
        ctrl[cols].rename(columns={"pct_complete": "% complete"}),
        use_container_width=True, hide_index=True,
        column_config={"% complete": st.column_config.ProgressColumn(
            "% complete", min_value=0, max_value=100, format="%d%%")},
    )
    phase_counts = ctrl["phase"].value_counts().reindex(
        ["Planning", "Design", "Right-of-Way", "Construction", "Closeout"]).fillna(0)
    st.bar_chart(phase_counts, horizontal=True)

# ----- Budget ----------------------------------------------------------------
with tab_budget:
    st.subheader("Budget vs. spend")
    bud = view.copy()
    bud["remaining"] = bud["budget"] - bud["spent_to_date"]
    fig_b = px.bar(bud.sort_values("budget", ascending=False).head(15),
                   x="project_id", y=["spent_to_date", "remaining"],
                   labels={"value": "USD", "variable": ""}, height=420)
    st.plotly_chart(fig_b, use_container_width=True)

    st.subheader("Program burn trend (planned vs. actual)")
    snap = snapshots[snapshots["project_id"].isin(view["project_id"])]
    trend = (snap.groupby("snapshot_date")[["planned_cumulative", "actual_cumulative"]]
             .sum().reset_index())
    fig_t = px.line(trend, x="snapshot_date", y=["planned_cumulative", "actual_cumulative"],
                    labels={"value": "Cumulative USD", "snapshot_date": "", "variable": ""},
                    height=380)
    st.plotly_chart(fig_t, use_container_width=True)

# ----- Data quality ----------------------------------------------------------
with tab_quality:
    st.subheader("Data-quality gate")
    st.write("Every record passes these checks before it reaches a report. "
             "This is the *commitment to data accuracy* the role calls for.")
    if len(issues):
        st.error(f"{isum['total_issues']} issue(s): {isum['high']} high, {isum['medium']} medium")
        st.dataframe(issues, use_container_width=True, hide_index=True)
    else:
        st.success("No data-quality issues found in the current view.")

# ----- Reports ---------------------------------------------------------------
with tab_reports:
    st.subheader("Standardized reports")
    audience = st.radio("Audience", ["Executive leadership", "Project manager"], horizontal=True)
    if audience == "Executive leadership":
        md = reports.executive_summary(view)
        fname = "executive_summary.md"
    else:
        md = reports.pm_detail_report(view, region)
        fname = "pm_detail_report.md"
    st.markdown(md)
    st.download_button("⬇ Download report (Markdown)", md, file_name=fname)
