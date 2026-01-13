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
    saved = st.session_state.get("saved_mapping")
    required_cols = list(df.columns)
    optional_cols = [None] + list(df.columns)

    def idx(key):
        preset = None
        if saved:
            preset = saved.get(key)
        if not preset:
            preset = suggested.get(key)
        return required_cols.index(preset) if preset in required_cols else 0

    with st.form("mapping_form"):
        left, right = st.columns(2)
        with left:
            student_id = st.selectbox("student_id", options=required_cols, index=idx("student_id"))
            exam_id = st.selectbox("exam_id", options=required_cols, index=idx("exam_id"))
            question_id = st.selectbox("question_id", options=required_cols, index=idx("question_id"))
        with right:
            rubric_item = st.selectbox("rubric_item", options=required_cols, index=idx("rubric_item"))
            points_lost = st.selectbox("points_lost", options=required_cols, index=idx("points_lost"))
            topic = st.selectbox("topic (optional)", options=optional_cols, index=0 if saved is None and suggested.get("topic") is None else optional_cols.index(saved.get("topic")) if saved and saved.get("topic") in optional_cols else optional_cols.index(suggested.get("topic")) if suggested.get("topic") in optional_cols else 0)
        submitted = st.form_submit_button("Apply mapping")

    if not submitted:
        return None

    mapping_dict = {
        "student_id": student_id,
        "exam_id": exam_id,
        "question_id": question_id,
        "rubric_item": rubric_item,
        "points_lost": points_lost,
        "topic": topic if topic else None,
    }

    try:
        mapping_cfg = MappingConfig.from_dict(mapping_dict)
        st.session_state["saved_mapping"] = mapping_dict
        return mapping_cfg
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


def _exam_order(df: pd.DataFrame) -> list[str]:
    unique = sorted(df["exam_id"].dropna().unique())
    mode = st.sidebar.radio("Exam ordering", options=["Lexicographic", "Reverse lexicographic"], index=0)
    return unique if mode == "Lexicographic" else list(reversed(unique))


def _render_overview(df: pd.DataFrame, exam_order: list[str]):
    summary = metrics.overall_summary(df)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Students", summary["students"])
    col2.metric("Exams", summary["exams"])
    col3.metric("Rows", summary["rows"])
    _metric_card("Avg points lost", summary["avg_points_lost"])

    rubrics = metrics.rubric_item_stats(df)
    exams = metrics.exam_breakdown(df)
    students = metrics.student_summary(df, exam_order=exam_order)
    distribution = metrics.score_distribution(df)

    chart_col, pie_col = st.columns([2, 1])
    with chart_col:
        dist_fig = plots.distribution_chart(distribution)
        st.plotly_chart(dist_fig, use_container_width=True)
        _download_fig("Export distribution (PNG)", dist_fig, "distribution.png")
    with pie_col:
        pie_fig = plots.exam_pie(exams)
        st.plotly_chart(pie_fig, use_container_width=True)
        _download_fig("Export exam pie (PNG)", pie_fig, "exams.png")

    st.subheader("Tables")
    st.write("Rubric items")
    st.dataframe(rubrics, use_container_width=True, height=260)
    _download_df("Export rubric table", rubrics, "rubric_items.csv")

    st.write("Exams")
    st.dataframe(exams, use_container_width=True, height=220)
    _download_df("Export exams table", exams, "exams.csv")

    st.write("Students")
    st.dataframe(students, use_container_width=True, height=260)
    _download_df("Export students table", students, "students.csv")

    st.write("Normalized data")
    st.dataframe(df.head(200), use_container_width=True, height=300)
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

    normalized_df: Optional[pd.DataFrame] = None
    mapping_cfg: Optional[MappingConfig] = None

    if needs_mapping(raw_df):
        mapping_cfg = _mapping_wizard(raw_df)
        if not mapping_cfg:
            st.warning("Select a column for each required field to continue.")
            return
    else:
        st.info("Headers match canonical schema; mapping skipped.")

    try:
        normalized_df, _, _ = normalize_dataframe(raw_df, mapping=mapping_cfg, infer_mapping=mapping_cfg is None)
    except ValueError as exc:
        st.error(f"Normalization failed: {exc}")
        return

    st.success("Dataset normalized.")
    st.write("### Preview (first 20 rows)")
    st.dataframe(normalized_df.head(20), use_container_width=True)

    st.write("### Validation")
    quality_results = invariants.run_invariants(normalized_df)
    for res in quality_results:
        status = "✅" if res["ok"] else "⚠️"
        st.write(f"{status} {res['name']}: {res['detail']}")
    if not all(res["ok"] for res in quality_results):
        st.warning("Please address validation issues before relying on analytics.")

    st.session_state["normalized_df"] = normalized_df

    exam_order = _exam_order(normalized_df)
    overview_tab, persistence_tab, quality_tab = st.tabs(["Overview", "Persistence", "Data Quality"])

    with overview_tab:
        _render_overview(normalized_df, exam_order)
    with persistence_tab:
        _render_persistence(normalized_df)
    with quality_tab:
        _render_quality(normalized_df)


if __name__ == "__main__":
    main()
