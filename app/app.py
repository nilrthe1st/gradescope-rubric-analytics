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
    use_sample = st.sidebar.checkbox("Use sample_truth.csv", value=False)
    uploader = st.sidebar.file_uploader("Upload rubric CSV", type=["csv"])

    if use_sample:
        return pd.read_csv(DATA_DIR / "sample_truth.csv")
    if uploader is not None:
        return pd.read_csv(uploader)
    return None


def _exam_order(df: pd.DataFrame) -> list[str]:
    unique = sorted(df["exam_id"].dropna().unique())
    mode = st.sidebar.radio("Exam order", options=["Lexicographic", "Manual"], index=0)
    if mode == "Manual":
        ordered = st.sidebar.multiselect("Select exams in desired order", options=unique, default=unique)
        if ordered:
            return ordered
    return unique


def _render_overview(df: pd.DataFrame, exam_order: list[str]):
    summary = metrics.overall_summary(df)
    errors = metrics.summarize_errors(df)

    total_points = df["points_lost"].sum()
    unique_rubrics = df["rubric_item"].nunique()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Rows", summary["rows"])
    col2.metric("Students", summary["students"])
    col3.metric("Rubric items", unique_rubrics)
    _metric_card("Total points lost", total_points)

    # Top tables
    top_by_points = errors.sort_values("points_lost_total", ascending=False).head(10)
    top_by_students = errors.sort_values("students_affected", ascending=False).head(10)

    st.subheader("Top rubric items by points lost")
    st.dataframe(top_by_points, use_container_width=True, height=260)
    _download_df("Download (CSV) — points lost", top_by_points, "top_rubric_points.csv")

    st.subheader("Top rubric items by students affected")
    st.dataframe(top_by_students, use_container_width=True, height=260)
    _download_df("Download (CSV) — students affected", top_by_students, "top_rubric_students.csv")

    st.subheader("Charts")
    import plotly.express as px

    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        count_fig = px.bar(
            errors.sort_values("count_rows", ascending=False),
            x="rubric_item",
            y="count_rows",
            title="Occurrences by rubric item",
            labels={"rubric_item": "Rubric item", "count_rows": "Row count"},
        )
        st.plotly_chart(count_fig, use_container_width=True)
        _download_fig("Export count bar (PNG)", count_fig, "rubric_counts.png")
    with chart_col2:
        points_fig = px.bar(
            errors.sort_values("points_lost_total", ascending=False),
            x="rubric_item",
            y="points_lost_total",
            title="Points lost by rubric item",
            labels={"rubric_item": "Rubric item", "points_lost_total": "Total points lost"},
        )
        st.plotly_chart(points_fig, use_container_width=True)
        _download_fig("Export points bar (PNG)", points_fig, "rubric_points_total.png")

    st.subheader("Normalized data preview")
    st.dataframe(df.head(200), use_container_width=True, height=320)
    _download_df("Download normalized dataset (CSV)", df, "normalized.csv")


def _render_persistence(df: pd.DataFrame, exam_order: list[str]):
    persistence = metrics.compute_persistence(df, exam_order=exam_order)
    persistence = persistence.sort_values(by="persistence_rate", ascending=False)
    st.subheader("Persistence by rubric item")
    st.dataframe(persistence, use_container_width=True, height=320)
    _download_df("Download persistence (CSV)", persistence, "persistence.csv")

    st.subheader("Rubric occurrences by exam (heatmap)")
    long_counts = metrics.error_by_exam(df)
    pivot = long_counts.pivot_table(index="rubric_item", columns="exam_id", values="count_rows", aggfunc="sum", fill_value=0)

    import plotly.express as px

    heatmap = px.imshow(pivot, text_auto=True, aspect="auto", color_continuous_scale="Blues", title="Count of rubric items per exam")
    st.plotly_chart(heatmap, use_container_width=True)
    _download_fig("Download heatmap (PNG)", heatmap, "rubric_exam_heatmap.png")


def _render_quality(df: pd.DataFrame):
    st.subheader("Invariant checks")
    results = invariants.run_invariants(df)
    res_df = pd.DataFrame(results)

    # Make Arrow serialization stable for Streamlit display (mixed int/str in `detail`)
    if "detail" in res_df.columns:
        res_df = res_df.copy()
        res_df["detail"] = res_df["detail"].fillna("").astype(str)

    st.dataframe(res_df, use_container_width=True, height=200)

    st.subheader("Schema (columns and dtypes)")
    dtype_df = pd.DataFrame({"column": df.columns, "dtype": df.dtypes.astype(str)})
    st.dataframe(dtype_df, use_container_width=True, height=200)

    st.subheader("Cleaning summary")
    st.write("Rows dropped during normalization: 0 (data is validated but not dropped).")


def main():
    st.title("Gradescope Rubric Analytics")
    st.write("Turn Gradescope rubric CSVs into dashboards: upload, map columns, validate, and explore analytics.")
    st.info("Accepts CSV uploads; if headers are non-canonical, use the mapping wizard to align to the canonical schema.")
    st.warning("Use anonymized or non-PII exports — this app does not store data.")

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
        _render_persistence(normalized_df, exam_order)
    with quality_tab:
        _render_quality(normalized_df)


if __name__ == "__main__":
    main()
