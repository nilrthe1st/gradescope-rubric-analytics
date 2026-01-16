"""Streamlit UI for Gradescope rubric analytics.

This redesign focuses on a SaaS-style shell, guided ingestion, and drill-down
exploration while keeping analytics logic in ``src/gradescope_analytics``.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st
import json

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.ui import AppShell, Step, card, kpi_row, section_header, stepper  # noqa: E402
from gradescope_analytics import invariants, metrics  # noqa: E402
from gradescope_analytics.io import normalize_dataframe  # noqa: E402
from gradescope_analytics.mapping import MappingConfig, needs_mapping, suggest_mapping  # noqa: E402

st.set_page_config(page_title="Gradescope Rubric Analytics", layout="wide", page_icon="📊")

DATA_DIR = ROOT / "data"
CONCEPT_MAPPING_PATH = DATA_DIR / "concept_mappings.json"


def _rerun():
    """Compat wrapper for rerun across Streamlit versions."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:  # pragma: no cover - defensive
        raise RuntimeError("Streamlit rerun API not available")


def _load_concept_mapping() -> Dict[str, str]:
    if st.session_state.get("concept_mapping") is not None:
        return st.session_state["concept_mapping"]

    mapping: Dict[str, str] = {}
    try:
        if CONCEPT_MAPPING_PATH.exists():
            mapping = json.loads(CONCEPT_MAPPING_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive
        st.warning(f"Unable to load concept mappings: {exc}")

    st.session_state["concept_mapping"] = mapping
    return mapping


def _save_concept_mapping(mapping: Dict[str, str]):
    try:
        CONCEPT_MAPPING_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONCEPT_MAPPING_PATH.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:  # pragma: no cover - defensive
        st.warning(f"Unable to save concept mappings: {exc}")


def _init_state() -> None:
    defaults = {
        "demo_mode": False,
        "raw_df": None,
        "normalized_df": None,
        "mapping_cfg": None,
        "saved_mapping": None,
        "validation_results": None,
        "selected_rubric": None,
        "source_label": None,
        "concept_mapping": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _load_source(demo_mode: bool, upload) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    if demo_mode:
        return pd.read_csv(DATA_DIR / "sample_truth.csv"), "Demo dataset (sample_truth.csv)"
    if upload is not None:
        return pd.read_csv(upload), upload.name
    return None, None


def _mapping_wizard(df: pd.DataFrame) -> Optional[MappingConfig]:
    suggested = suggest_mapping(df)
    saved = st.session_state.get("saved_mapping") or {}
    required_cols = list(df.columns)
    optional_cols = [None] + list(df.columns)

    def select_index(key: str, options: List[str]) -> int:
        candidate = saved.get(key) or suggested.get(key)
        return options.index(candidate) if candidate in options else 0

    with st.form("mapping_form"):
        left, right = st.columns(2)
        with left:
            student_id = st.selectbox("student_id", options=required_cols, index=select_index("student_id", required_cols))
            exam_id = st.selectbox("exam_id", options=required_cols, index=select_index("exam_id", required_cols))
            question_id = st.selectbox("question_id", options=required_cols, index=select_index("question_id", required_cols))
        with right:
            rubric_item = st.selectbox("rubric_item", options=required_cols, index=select_index("rubric_item", required_cols))
            points_lost = st.selectbox("points_lost", options=required_cols, index=select_index("points_lost", required_cols))
            topic_index = 0
            saved_topic = saved.get("topic")
            suggested_topic = suggested.get("topic")
            if saved_topic in optional_cols:
                topic_index = optional_cols.index(saved_topic)
            elif suggested_topic in optional_cols:
                topic_index = optional_cols.index(suggested_topic)
            topic = st.selectbox("topic (optional)", options=optional_cols, index=topic_index)

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
    except ValueError as exc:  # pragma: no cover - guarded by UI
        st.error(str(exc))
        return None


def _apply_validation(df: pd.DataFrame) -> List[Dict[str, object]]:
    results = invariants.run_invariants(df)
    st.session_state["validation_results"] = results
    return results


def _exam_order(df: pd.DataFrame) -> List[str]:
    unique = sorted(df["exam_id"].dropna().unique())
    mode = st.radio("Exam order", options=["Lexicographic", "Manual"], horizontal=True)
    if mode == "Manual":
        ordered = st.multiselect("Select exams in desired order", options=unique, default=unique)
        if ordered:
            return ordered
    return unique


def _student_filter_controls(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    students = sorted(df["student_id"].dropna().unique())
    scope = st.radio("Student scope", options=["All students", "Single student", "Multi-select"], index=0, horizontal=True)
    selected_ids: List[str] = []

    if scope == "Single student":
        if students:
            chosen = st.selectbox("Choose a student", options=students, index=0)
            selected_ids = [chosen]
    elif scope == "Multi-select":
        selected_ids = st.multiselect("Filter students (optional)", options=students, default=[])

    if selected_ids:
        filtered = df[df["student_id"].isin(selected_ids)]
        desc = ", ".join(map(str, selected_ids))
    else:
        filtered = df
        desc = "All students"

    return filtered, desc


def _concept_stats(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data.loc[:, "concept"] = data.get("concept", "").fillna("").astype(str).str.strip()
    data.loc[:, "points_lost"] = pd.to_numeric(data["points_lost"], errors="coerce")
    scoped = data[data["concept"] != ""]
    if scoped.empty:
        return pd.DataFrame(columns=["concept", "rows", "students_affected", "points_lost_total", "points_lost_mean"])

    grouped = scoped.groupby("concept", dropna=False)
    rows = []
    for concept, subset in grouped:
        rows.append(
            {
                "concept": concept,
                "rows": len(subset),
                "students_affected": subset["student_id"].nunique(),
                "points_lost_total": subset["points_lost"].sum(),
                "points_lost_mean": subset["points_lost"].mean(),
            }
        )

    result = pd.DataFrame(rows)
    return result.sort_values(by="points_lost_total", ascending=False)


def _concept_mapping_controls(df: pd.DataFrame) -> Dict[str, str]:
    mapping = _load_concept_mapping()

    has_topic_col = "topic" in df.columns
    topic_values = df["topic"].fillna("").astype(str).str.strip() if has_topic_col else pd.Series([], dtype=str)
    has_topic_values = has_topic_col and topic_values.str.len().gt(0).any()

    if has_topic_values:
        st.success("Using provided topic column as concept dimension.")
        return mapping

    st.info("No topic column found; map rubric items to concepts.")
    rubric_items = sorted(df["rubric_item"].dropna().unique())
    with st.form("concept_map_form"):
        updated: Dict[str, str] = {}
        for item in rubric_items:
            default = mapping.get(item, "")
            updated[item] = st.text_input(f"Concept for '{item}'", value=default)
        submitted = st.form_submit_button("Save concept mapping")

    if submitted:
        cleaned = {k: v.strip() for k, v in updated.items() if v.strip()}
        mapping.update(cleaned)
        _save_concept_mapping(mapping)
        st.session_state["concept_mapping"] = mapping
        st.success("Concept mappings saved and will persist across sessions.")

    return mapping


def _apply_concepts(df: pd.DataFrame) -> pd.DataFrame:
    mapping = _concept_mapping_controls(df)

    has_topic_col = "topic" in df.columns
    topic_values = df["topic"].fillna("").astype(str).str.strip() if has_topic_col else pd.Series("", index=df.index)

    mapped_concepts = df["rubric_item"].map(mapping).fillna("")
    concept_series = topic_values.where(topic_values != "", mapped_concepts)

    result = df.copy()
    result.loc[:, "concept"] = concept_series

    missing = (result["concept"].fillna("") == "").sum()
    st.caption(f"Concept coverage: {len(result) - missing} rows mapped, {missing} rows unmapped.")
    return result


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


def _style_fig(fig, title: Optional[str] = None):
    fig.update_layout(
        title=title or fig.layout.title.text,
        margin=dict(t=60, r=24, b=40, l=24),
        template="plotly_dark",
        plot_bgcolor="#0b1220",
        paper_bgcolor="#0b1220",
        font=dict(family="Inter, sans-serif", color="#e5e7eb", size=12),
        hoverlabel=dict(bgcolor="#111827", font_size=12),
    )
    return fig


def _render_empty_state(shell: AppShell):
    with card("Welcome", "Load a sample or upload a CSV to explore analytics"):
        st.markdown(
            """
            - Use **Demo mode** to instantly explore the included `sample_truth.csv`.
            - Or upload a Gradescope rubric CSV and follow the stepper: Upload → Map → Validate → Explore.
            - Need column hints? The canonical headers are `student_id`, `exam_id`, `question_id`, `rubric_item`, `points_lost`, and optional `topic`.
            """
        )
        if st.button("Turn on demo mode"):
            st.session_state["demo_mode"] = True
            _rerun()


def _set_rubric_selection(rubric: Optional[str]):
    st.session_state["selected_rubric"] = rubric


def _drilldown_selector(errors_df: pd.DataFrame):
    st.markdown("**Drill into a rubric item**")
    cols = st.columns(3)
    for idx, (_, row) in enumerate(errors_df.head(9).iterrows()):
        target_col = cols[idx % 3]
        with target_col:
            label = f"{row['rubric_item']} ({int(row['count_rows'])} rows)"
            if st.button(label, key=f"rubric-select-{idx}"):
                _set_rubric_selection(row["rubric_item"])
    current = st.session_state.get("selected_rubric")
    if current:
        st.success(f"Filter applied: rubric item = '{current}'")
        if st.button("Reset filters"):
            _set_rubric_selection(None)
    else:
        st.caption("No filter applied")


def _instructor_summary(df: pd.DataFrame, errors: pd.DataFrame, persistence: pd.DataFrame):
    with card("Instructor summary", "Quick signals to help plan recitations"):
        high_persistence = persistence[persistence["cohort_size"] >= 3].sort_values("persistence_rate", ascending=False).head(3)
        high_points = errors.sort_values("points_lost_total", ascending=False).head(3)

        concept_df = df.copy()
        concept_df.loc[:, "concept"] = concept_df.get("concept", concept_df.get("topic", "")).fillna("").astype(str).str.strip()
        concept_rollup = concept_df[concept_df["concept"] != ""]
        concept_summary = pd.DataFrame()
        if not concept_rollup.empty:
            concept_summary = concept_rollup.groupby("concept", dropna=False)["points_lost"].sum().reset_index().sort_values("points_lost", ascending=False).head(3)

        st.markdown("**High-persistence rubric items**")
        if high_persistence.empty:
            st.caption("No repeated rubric items detected yet.")
        else:
            for _, row in high_persistence.iterrows():
                st.write(f"- {row['rubric_item']}: {row['persistence_rate']:.1%} repeat rate across {int(row['cohort_size'])} students")

        st.markdown("**Highest impact deductions**")
        if high_points.empty:
            st.caption("Upload data to see deductions.")
        else:
            for _, row in high_points.iterrows():
                st.write(f"- {row['rubric_item']}: {row['points_lost_total']:.1f} points lost total")

        st.markdown("**Suggested recitation topics**")
        if concept_summary.empty:
            st.caption("No concepts available; add topics or map rubric items to concepts.")
        else:
            for _, row in concept_summary.iterrows():
                st.write(f"- {row['concept']}: {row['points_lost']:.1f} points lost")


def _render_overview(df: pd.DataFrame, exam_order: List[str]):
    if df.empty:
        st.info("No data available for the selected students.")
        return

    summary = metrics.overall_summary(df)
    errors = metrics.summarize_errors(df)
    selected = st.session_state.get("selected_rubric")

    filtered_df = df.copy()
    if selected:
        filtered_df = filtered_df.loc[filtered_df["rubric_item"] == selected]
        errors = errors.loc[errors["rubric_item"] == selected]

    total_points = filtered_df["points_lost"].sum()
    numeric = filtered_df.copy()
    numeric.loc[:, "points_lost"] = pd.to_numeric(numeric["points_lost"], errors="coerce")
    per_student = numeric.groupby("student_id")["points_lost"].sum()
    avg_per_student = per_student.mean() if not per_student.empty else 0.0
    std_per_student = per_student.std(ddof=0) if len(per_student) > 0 else 0.0

    kpis = [
        {"label": "Rows", "value": f"{summary['rows']:,}"},
        {"label": "Students", "value": f"{summary['students']:,}"},
        {"label": "Avg pts / student", "value": f"{avg_per_student:.2f}"},
        {"label": "Std dev / student", "value": f"{std_per_student:.2f}"},
        {"label": "Exams", "value": summary["exams"], "hint": "Unique exam_id"},
        {"label": "Rubric items", "value": filtered_df["rubric_item"].nunique()},
        {"label": "Avg points lost", "value": f"{summary['avg_points_lost']:.2f}"},
        {"label": "Total points lost", "value": f"{total_points:.1f}"},
    ]
    kpi_row(kpis)

    persistence = metrics.compute_persistence(df, exam_order=exam_order)
    col_left, col_right = st.columns([0.65, 0.35])
    with col_left:
        section_header("Top rubric items")
        if errors.empty:
            st.info("No rubric items available yet. Check mappings or upload a dataset with rubric rows.")
        else:
            top_by_points = errors.sort_values("points_lost_total", ascending=False).head(10)
            st.dataframe(top_by_points, use_container_width=True, height=280)
            _download_df("Download points-lost CSV", top_by_points, "top_rubric_points.csv")
    with col_right:
        _instructor_summary(df, errors, persistence)

    st.subheader("Concepts")
    concept_stats = _concept_stats(df)
    if concept_stats.empty:
        st.info("Add topics or concept mappings to see concept-level analytics.")
    else:
        st.dataframe(concept_stats, use_container_width=True, height=260)
        _download_df("Download concepts CSV", concept_stats, "concepts.csv")
        concept_fig = px.bar(
            concept_stats.sort_values("points_lost_total", ascending=False),
            x="concept",
            y="points_lost_total",
            labels={"concept": "Concept", "points_lost_total": "Total points lost"},
            title="Points lost by concept",
        )
        concept_fig.update_traces(hovertemplate="<b>%{x}</b><br>Total points lost: %{y}<extra></extra>")
        _style_fig(concept_fig)
        st.plotly_chart(concept_fig, use_container_width=True)

    st.divider()
    _drilldown_selector(errors)

    st.subheader("Charts")
    if not errors.empty:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            count_fig = px.bar(
                errors.sort_values("count_rows", ascending=False),
                x="rubric_item",
                y="count_rows",
                labels={"rubric_item": "Rubric item", "count_rows": "Row count"},
                title="Occurrences by rubric item",
            )
            count_fig.update_traces(hovertemplate="<b>%{x}</b><br>Rows: %{y}<extra></extra>")
            _style_fig(count_fig)
            st.plotly_chart(count_fig, use_container_width=True)
            _download_fig("Export count bar (PNG)", count_fig, "rubric_counts.png")
        with chart_col2:
            points_fig = px.bar(
                errors.sort_values("points_lost_total", ascending=False),
                x="rubric_item",
                y="points_lost_total",
                labels={"rubric_item": "Rubric item", "points_lost_total": "Total points lost"},
                title="Points lost by rubric item",
            )
            points_fig.update_traces(hovertemplate="<b>%{x}</b><br>Total points lost: %{y}<extra></extra>")
            _style_fig(points_fig)
            st.plotly_chart(points_fig, use_container_width=True)
            _download_fig("Export points bar (PNG)", points_fig, "rubric_points_total.png")

    st.subheader("Normalized data preview")
    if selected:
        st.caption(f"Filtered by rubric item: {selected}")
    st.dataframe(filtered_df.head(200), use_container_width=True, height=320)
    _download_df("Download normalized dataset (CSV)", df, "normalized.csv")


def _render_persistence(df: pd.DataFrame, exam_order: List[str]):
    persistence = metrics.compute_persistence(df, exam_order=exam_order)
    persistence = persistence.sort_values(by="persistence_rate", ascending=False)

    with card("Persistence by rubric item"):
        st.dataframe(persistence, use_container_width=True, height=360)
        _download_df("Download persistence (CSV)", persistence, "persistence.csv")

    st.subheader("Rubric occurrences by exam")
    long_counts = metrics.error_by_exam(df)
    pivot = long_counts.pivot_table(index="rubric_item", columns="exam_id", values="count_rows", aggfunc="sum", fill_value=0)

    if pivot.empty:
        st.info("No rubric/exam combinations to visualize yet.")
        return

    heatmap = px.imshow(
        pivot,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Blues",
        title="Count of rubric items per exam",
        labels={"color": "Count"},
    )
    heatmap.update_layout(
        margin=dict(t=60, r=30, b=40, l=40),
        font=dict(color="#e5e7eb"),
        paper_bgcolor="#0b1220",
        plot_bgcolor="#0b1220",
        coloraxis_colorbar=dict(title="Count", bgcolor="#0b1220"),
    )
    st.plotly_chart(heatmap, use_container_width=True)
    _download_fig("Download heatmap (PNG)", heatmap, "rubric_exam_heatmap.png")


def _render_quality(df: pd.DataFrame):
    section_header("Invariant checks", "Validation results for the normalized dataset")
    results = _apply_validation(df)
    res_df = pd.DataFrame(results)

    if "detail" in res_df.columns:
        res_df = res_df.copy()
        res_df.loc[:, "detail"] = res_df["detail"].fillna("").astype(str)

    st.dataframe(res_df, use_container_width=True, height=220)

    section_header("Schema (columns and dtypes)")
    dtype_df = pd.DataFrame({"column": df.columns, "dtype": df.dtypes.astype(str)})
    st.dataframe(dtype_df, use_container_width=True, height=220)

    section_header("Cleaning summary")
    st.write("Rows dropped during normalization: 0 (data is validated but not dropped).")


def _ingestion_stepper(raw_df, mapping_cfg, normalized_df, validation_results):
    steps = [
        Step(title="Upload", description="Upload CSV or enable Demo mode", status="active" if raw_df is None else "done"),
        Step(
            title="Map",
            description="Align columns to canonical schema",
            status="waiting" if raw_df is None else ("done" if (mapping_cfg or not needs_mapping(raw_df)) else "active"),
        ),
        Step(
            title="Validate",
            description="Run invariants before exploring",
            status="waiting" if normalized_df is None else ("done" if validation_results else "active"),
        ),
        Step(title="Explore", description="Overview, Persistence, Data Quality", status="waiting" if normalized_df is None else "active"),
    ]
    stepper(steps)


def main():
    _init_state()
    shell = AppShell("Gradescope Rubric Analytics", "Guided ingestion → validation → insights")
    shell.header(right="Modern UI beta")
    shell.layout()

    st.sidebar.header("Data source")
    st.sidebar.write("Upload a CSV or toggle demo mode to load the included sample.")
    demo_mode = st.sidebar.toggle("Demo mode", value=st.session_state["demo_mode"], help="Load sample_truth.csv for a quick tour")
    st.session_state["demo_mode"] = demo_mode
    uploader = st.sidebar.file_uploader("Upload rubric CSV", type=["csv"])

    raw_df, source_label = _load_source(demo_mode, uploader)
    if raw_df is not None:
        if source_label != st.session_state.get("source_label"):
            st.session_state["mapping_cfg"] = None
            st.session_state["normalized_df"] = None
            st.session_state["validation_results"] = None
            st.session_state["selected_rubric"] = None
        st.session_state["raw_df"] = raw_df
        st.session_state["source_label"] = source_label
    if source_label:
        st.sidebar.success(source_label)

    raw_df = st.session_state.get("raw_df")
    mapping_cfg: Optional[MappingConfig] = st.session_state.get("mapping_cfg")
    normalized_df: Optional[pd.DataFrame] = st.session_state.get("normalized_df")

    _ingestion_stepper(raw_df, mapping_cfg, normalized_df, st.session_state.get("validation_results"))

    if raw_df is None:
        _render_empty_state(shell)
        return

    needs_map = needs_mapping(raw_df)
    if needs_map and mapping_cfg is None:
        section_header("Step 2 — Map columns", "Select which columns match the canonical schema")
        mapping_cfg = _mapping_wizard(raw_df)
        if mapping_cfg:
            st.session_state["mapping_cfg"] = mapping_cfg
        else:
            st.info("Provide mappings to continue.")
            return
    elif not needs_map:
        st.info("Headers match canonical schema; mapping skipped.")

    try:
        normalized_df, _, _ = normalize_dataframe(raw_df, mapping=mapping_cfg, infer_mapping=mapping_cfg is None)
        st.session_state["normalized_df"] = normalized_df
    except ValueError as exc:
        st.error(f"Normalization failed: {exc}")
        return

    section_header("Step 3 — Validate", "Run invariants to confirm the dataset is clean")
    validation_results = _apply_validation(normalized_df)
    ok = all(res.get("ok", False) for res in validation_results)
    if ok:
        st.success("Validation passed")
    else:
        st.warning("Validation found issues; review before trusting analytics.")

    section_header("Concept normalization", "Use topics or map rubric items to concepts")
    normalized_df = _apply_concepts(normalized_df)

    section_header("Student scope", "Analyze all students or a subset")
    filtered_df, student_scope_desc = _student_filter_controls(normalized_df)
    st.caption(f"Student scope: {student_scope_desc}")

    st.write("### Preview (first 20 rows)")
    st.dataframe(filtered_df.head(20), use_container_width=True)

    section_header("Step 4 — Explore")
    exam_order = _exam_order(filtered_df)
    overview_tab, persistence_tab, quality_tab = st.tabs(["Overview", "Persistence", "Data Quality"])

    with overview_tab:
        _render_overview(filtered_df, exam_order)
    with persistence_tab:
        _render_persistence(filtered_df, exam_order)
    with quality_tab:
        _render_quality(filtered_df)


if __name__ == "__main__":
    main()
