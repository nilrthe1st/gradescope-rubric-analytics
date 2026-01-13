import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.append(str(SRC))

from gradescope_analytics import invariants, metrics, plots  # noqa: E402
from gradescope_analytics.io import normalize_dataframe
from gradescope_analytics.mapping import MappingConfig, needs_mapping, suggest_mapping

st.set_page_config(page_title="Gradescope Rubric Analytics", layout="wide", page_icon="📊")

DATA_DIR = ROOT / "data"
DEFAULT_PERSIST_PATH = DATA_DIR / "normalized_latest.csv"


def _metric_card(label: str, value):
    if isinstance(value, float):
        display = f"{value:.2f}" if pd.notna(value) else "-"
    else:
        display = value
    st.metric(label, display)


def _download_df(label: str, df: pd.DataFrame, filename: str):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=filename, mime="text/csv")


def _download_fig(label: str, fig, filename: str):
    if fig is None or not fig.data:
        st.caption("No chart to export")
        return
    try:
        payload = fig.to_image(format="png")
        st.download_button(label, payload, file_name=filename, mime="image/png")
    except Exception as exc:  # pragma: no cover - GUI only
        st.warning(f"Unable to export chart: {exc}")


def _mapping_wizard(df: pd.DataFrame) -> Optional[MappingConfig]:
    st.subheader("Mapping wizard")
    suggested = suggest_mapping(df)
    cols = [None] + list(df.columns)

    with st.form("mapping_form"):
        left, right = st.columns(2)
        with left:
            student_id = st.selectbox("Student ID", options=cols, index=cols.index(suggested.get("student_id")) if suggested.get("student_id") in cols else 0)
            student_name = st.selectbox("Student name", options=cols, index=cols.index(suggested.get("student_name")) if suggested.get("student_name") in cols else 0)
            assignment = st.selectbox("Assignment / exam", options=cols, index=cols.index(suggested.get("assignment")) if suggested.get("assignment") in cols else 0)
            rubric_item = st.selectbox("Rubric item", options=cols, index=cols.index(suggested.get("rubric_item")) if suggested.get("rubric_item") in cols else 0)
        with right:
            category = st.selectbox("Category", options=cols, index=cols.index(suggested.get("category")) if suggested.get("category") in cols else 0)
            score = st.selectbox("Score", options=cols, index=cols.index(suggested.get("score")) if suggested.get("score") in cols else 0)
            max_score = st.selectbox("Max score", options=cols, index=cols.index(suggested.get("max_score")) if suggested.get("max_score") in cols else 0)
            comment = st.selectbox("Comment", options=cols, index=cols.index(suggested.get("comment")) if suggested.get("comment") in cols else 0)
        submitted = st.form_submit_button("Apply mapping")

    if not submitted:
        return None

    mapping_dict = {
        "student_id": student_id,
        "student_name": student_name,
        "assignment": assignment,
        "rubric_item": rubric_item,
        "category": category,
        "score": score,
        "max_score": max_score,
        "comment": comment,
    }

    try:
        return MappingConfig.from_dict(mapping_dict)
    except ValueError as exc:
        st.error(str(exc))
        return None


def _load_source() -> Optional[pd.DataFrame]:
    st.sidebar.subheader("Data source")
    uploader = st.sidebar.file_uploader("Upload rubric CSV", type=["csv"])
    if st.sidebar.button("Load sample truth"):
        return pd.read_csv(DATA_DIR / "sample_truth.csv")
    if uploader:
        return pd.read_csv(uploader)
    return None


def _assignment_order(df: pd.DataFrame) -> list[str]:
    unique = sorted(df["assignment"].dropna().unique())
    mode = st.sidebar.radio("Exam ordering", options=["Lexicographic", "Reverse lexicographic"], index=0)
    return unique if mode == "Lexicographic" else list(reversed(unique))


def _render_overview(df: pd.DataFrame, assignment_order: list[str]):
    summary = metrics.overall_summary(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Students", summary["students"])
    col2.metric("Assignments", summary["assignments"])
    col3.metric("Rows", summary["rows"])
    _metric_card("Average score", summary["avg_score"])

    rubrics = metrics.rubric_item_stats(df)
    categories = metrics.category_breakdown(df)
    students = metrics.student_summary(df, assignment_order=assignment_order)
    distribution = metrics.score_distribution(df)

    chart_col, pie_col = st.columns([2, 1])
    with chart_col:
        dist_fig = plots.distribution_chart(distribution)
        st.plotly_chart(dist_fig, use_container_width=True)
        _download_fig("Export distribution (PNG)", dist_fig, "distribution.png")
    with pie_col:
        pie_fig = plots.category_pie(categories)
        st.plotly_chart(pie_fig, use_container_width=True)
        _download_fig("Export category pie (PNG)", pie_fig, "categories.png")

    st.subheader("Tables")
    st.write("Rubric items")
    st.dataframe(rubrics, use_container_width=True, height=300)
    _download_df("Export rubric table", rubrics, "rubric_items.csv")

    st.write("Categories")
    st.dataframe(categories, use_container_width=True, height=220)
    _download_df("Export categories table", categories, "categories.csv")

    st.write("Students")
    st.dataframe(students, use_container_width=True, height=320)
    _download_df("Export students table", students, "students.csv")

    st.write("Normalized data")
    st.dataframe(df, use_container_width=True, height=300)
    _download_df("Export normalized dataset", df, "normalized.csv")


def _render_persistence(df: pd.DataFrame):
    st.write("Save or load normalized data")
    path_str = st.text_input("Path", value=str(DEFAULT_PERSIST_PATH))
    target = Path(path_str)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save normalized dataset"):
            metrics.persist_dataset(df, target)
            st.success(f"Saved to {target}")
    with col2:
        if st.button("Load dataset from path"):
            if target.exists():
                loaded = metrics.load_persisted_dataset(target)
                st.session_state["normalized_df"] = loaded
                st.success(f"Loaded {len(loaded)} rows")
            else:
                st.error("Path does not exist")


def _render_quality(df: pd.DataFrame):
    st.write("Invariant checks")
    results = invariants.run_invariants(df)
    for res in results:
        status = "✅" if res["ok"] else "⚠️"
        st.write(f"{status} {res['name']}: {res['detail']}")


def main():
    st.title("Gradescope Rubric Analytics")
    st.caption("Map arbitrary rubric exports into analytics-ready tables and charts.")

    raw_df = _load_source()
    if raw_df is None:
        st.info("Upload a CSV or load the sample truth to begin.")
        return

    normalized_df = None
    if needs_mapping(raw_df):
        mapping_cfg = _mapping_wizard(raw_df)
        if mapping_cfg:
            normalized_df, _, _ = normalize_dataframe(raw_df, mapping=mapping_cfg, infer_mapping=False)
    else:
        normalized_df, _, _ = normalize_dataframe(raw_df, infer_mapping=False)

    if normalized_df is None:
        st.warning("Apply a mapping to continue.")
        return

    st.success("Dataset normalized.")
    st.session_state["normalized_df"] = normalized_df

    assignment_order = _assignment_order(normalized_df)
    overview_tab, persistence_tab, quality_tab = st.tabs(["Overview", "Persistence", "Data Quality"])

    with overview_tab:
        _render_overview(normalized_df, assignment_order)
    with persistence_tab:
        _render_persistence(normalized_df)
    with quality_tab:
        _render_quality(normalized_df)


if __name__ == "__main__":
    main()
