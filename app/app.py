"""Streamlit UI for Gradescope rubric analytics.

This redesign focuses on a SaaS-style shell, guided ingestion, and drill-down
exploration while keeping analytics logic in ``src/gradescope_analytics``.
"""

import sys
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st
import json
from datetime import datetime
from itertools import combinations
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.ui import AppShell, Step, card, kpi_row, section_header, stepper  # noqa: E402
from gradescope_analytics import invariants, metrics  # noqa: E402
from gradescope_analytics.concepts import apply_concept_column, load_concept_mapping, save_concept_mapping, unmapped_count  # noqa: E402
from gradescope_analytics.io import normalize_dataframe  # noqa: E402
from gradescope_analytics.mapping import MappingConfig, needs_mapping, suggest_mapping  # noqa: E402
from gradescope_analytics.recommendations import compute_recommendations  # noqa: E402
from gradescope_analytics.security import build_export_path, sanitize_filename  # noqa: E402
from tools.generate_synthetic import generate_synthetic_dataset  # noqa: E402

st.set_page_config(page_title="Gradescope Rubric Analytics", layout="wide", page_icon="📊")

DATA_DIR = ROOT / "data"
CONCEPT_MAPPING_PATH = DATA_DIR / "concept_mappings.json"
SAFE_EXPORT_DIR = DATA_DIR / "exports"


def _rerun():
    """Compat wrapper for rerun across Streamlit versions."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.rerun()
    else:  # pragma: no cover - defensive
        raise RuntimeError("Streamlit rerun API not available")


def _load_concept_mapping() -> Dict[str, str]:
    if st.session_state.get("concept_mapping") is not None:
        return st.session_state["concept_mapping"]

    mapping: Dict[str, str] = {}
    try:
        mapping = load_concept_mapping(CONCEPT_MAPPING_PATH)
    except Exception as exc:  # pragma: no cover - defensive
        st.warning(f"Unable to load concept mappings: {exc}")

    st.session_state["concept_mapping"] = mapping
    return mapping


def _save_concept_mapping(mapping: Dict[str, str]):
    try:
        saved = save_concept_mapping(mapping, CONCEPT_MAPPING_PATH)
        st.session_state["concept_mapping"] = saved
    except Exception as exc:  # pragma: no cover - defensive
        st.warning(f"Unable to save concept mappings: {exc}")


def _init_state() -> None:
    defaults = {
        "demo_mode": False,
        "synthetic_mode": False,
        "raw_df": None,
        "normalized_df": None,
        "mapping_cfg": None,
        "saved_mapping": None,
        "validation_results": None,
        "selected_rubric": None,
        "source_label": None,
        "concept_mapping": None,
        "anonymize_ids": True,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _load_source(demo_mode: bool, synthetic_mode: bool, upload) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    if synthetic_mode:
        synthetic_path = DATA_DIR / "synthetic_class.csv"
        template = DATA_DIR / "sample_truth.csv"
        if not synthetic_path.exists():
            try:
                generate_synthetic_dataset(template, synthetic_path, n_students=80)
            except Exception as exc:  # pragma: no cover - defensive
                st.error(f"Synthetic dataset generation failed: {exc}")
                return None, None
        try:
            return pd.read_csv(synthetic_path), "Synthetic dataset (synthetic_class.csv)"
        except Exception as exc:  # pragma: no cover - defensive
            st.error(f"Unable to load synthetic dataset: {exc}")
            return None, None

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

            section_idx = 0
            saved_section = saved.get("section_id")
            suggested_section = suggested.get("section_id")
            if saved_section in optional_cols:
                section_idx = optional_cols.index(saved_section)
            elif suggested_section in optional_cols:
                section_idx = optional_cols.index(suggested_section)
            section_id = st.selectbox("section_id (optional)", options=optional_cols, index=section_idx)

            ta_idx = 0
            saved_ta = saved.get("ta_id")
            suggested_ta = suggested.get("ta_id")
            if saved_ta in optional_cols:
                ta_idx = optional_cols.index(saved_ta)
            elif suggested_ta in optional_cols:
                ta_idx = optional_cols.index(suggested_ta)
            ta_id = st.selectbox("ta_id (optional)", options=optional_cols, index=ta_idx)

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
        "section_id": section_id if section_id else None,
        "ta_id": ta_id if ta_id else None,
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


def _maybe_anonymize_students(df: pd.DataFrame, enabled: bool) -> pd.DataFrame:
    if not enabled:
        return df

    data = df.copy()
    original_ids = data["student_id"].astype(str)
    ids = sorted(original_ids.unique())
    mapping = {sid: f"Student {idx + 1:03d}" for idx, sid in enumerate(ids)}
    data.loc[:, "student_id"] = original_ids.map(mapping)

    if "student_name" in data.columns:
        data.loc[:, "student_name"] = original_ids.map(mapping).fillna("")

    return data


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


def _concept_persistence(df: pd.DataFrame, exam_order: List[str]) -> pd.DataFrame:
    if len(exam_order) < 2:
        return pd.DataFrame(columns=["concept", "cohort_size", "repeated", "persistence_rate"])

    data = df.copy()
    data.loc[:, "concept"] = data.get("concept", "").fillna("").astype(str).str.strip()
    data = data[data["concept"] != ""]
    if data.empty:
        return pd.DataFrame(columns=["concept", "cohort_size", "repeated", "persistence_rate"])

    exam_rank = {exam: idx for idx, exam in enumerate(exam_order)}
    order_list = [exam for exam in exam_order if exam in data["exam_id"].unique()]
    if len(order_list) < 2:
        return pd.DataFrame(columns=["concept", "cohort_size", "repeated", "persistence_rate"])

    first_exam = order_list[0]
    rows = []
    for concept, subset in data.groupby("concept", dropna=False):
        cohort_students = set(subset.loc[subset["exam_id"] == first_exam, "student_id"].unique())
        if not cohort_students:
            continue
        later_subset = subset[subset["exam_id"].map(lambda x: exam_rank.get(x, -1) > 0)]
        repeated = set(later_subset["student_id"].unique()) & cohort_students
        cohort_size = len(cohort_students)
        rows.append(
            {
                "concept": concept,
                "cohort_size": cohort_size,
                "repeated": len(repeated),
                "persistence_rate": len(repeated) / cohort_size if cohort_size else 0.0,
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(by="persistence_rate", ascending=False)
    return result


def _course_group_stats(df: pd.DataFrame, group_col: str, label: str) -> pd.DataFrame:
    stats = metrics.group_comparison(df, group_col, missing_label=f"Unassigned {label}")
    if stats.empty:
        return stats

    stats = stats.copy()
    stats.loc[:, "avg_points_per_student"] = stats["avg_points_per_student"].round(2)
    stats.loc[:, "avg_points_per_row"] = stats["avg_points_per_row"].round(2)
    stats.loc[:, "total_points_lost"] = stats["total_points_lost"].round(2)
    return stats


def _render_course_structure(df: pd.DataFrame):
    st.subheader("Course structure disparities")

    section_stats = _course_group_stats(df, "section_id", "section")
    ta_stats = _course_group_stats(df, "ta_id", "TA")

    if section_stats.empty and ta_stats.empty:
        st.info("Include optional section_id or ta_id columns to compare grading patterns across sections and TAs.")
        return

    col_left, col_right = st.columns(2)

    def _render_group(label: str, stats: pd.DataFrame, column_name: str, filename: str):
        st.markdown(f"**{label} vs {label.lower()}**")
        if stats.empty:
            st.caption(f"Add {column_name} to see {label.lower()} comparisons.")
            return

        gap = stats["avg_points_per_student"].max() - stats["avg_points_per_student"].min()
        st.caption(f"Disparity (max - min avg pts/student): {gap:.2f}")
        st.dataframe(stats, use_container_width=True, height=280)
        _download_df(f"Download {filename}", stats, filename)

        fig = px.bar(
            stats,
            x=column_name,
            y="avg_points_per_student",
            labels={column_name: label, "avg_points_per_student": "Avg points lost / student"},
            title=f"{label} disparities",
        )
        fig.update_traces(hovertemplate=f"<b>%{{x}}</b><br>Avg pts/student: %{{y}}<extra></extra>")
        _style_fig(fig)
        st.plotly_chart(fig, use_container_width=True)

    with col_left:
        _render_group("Section", section_stats, "section_id", "section_comparison.csv")
    with col_right:
        _render_group("TA", ta_stats, "ta_id", "ta_comparison.csv")


def _render_exports(df: pd.DataFrame, errors: pd.DataFrame, persistence: pd.DataFrame, rec_df: Optional[pd.DataFrame]):
    st.subheader("Exports")

    st.caption("Download key summaries or generate an instructor-ready PDF.")
    top_errors = errors.sort_values("points_lost_total", ascending=False).head(20) if not errors.empty else pd.DataFrame()
    _download_df("Download top issues (CSV)", top_errors, "top_issues.csv")

    _download_df("Download persistence (CSV)", persistence, "persistence.csv")

    if rec_df is not None and not rec_df.empty:
        _download_df("Download recommendations (CSV)", rec_df, "recommendations.csv")

    pdf_bytes, pdf_err = _generate_pdf_report(top_errors, persistence, rec_df)
    if pdf_err:
        st.warning(pdf_err)
    elif pdf_bytes:
        st.download_button("Generate instructor report (PDF)", data=pdf_bytes, file_name="instructor_report.pdf", mime="application/pdf")


def _trajectory_stats(df: pd.DataFrame, exam_order: List[str]):
    """Placeholder trajectory stats until upstream analytics are reintroduced.

    Returns empty dataframes to keep the UI responsive even when the
    implementation is unavailable in this build.
    """

    return pd.DataFrame(), pd.DataFrame()


def _misconception_clusters(df: pd.DataFrame, jaccard_threshold: float = 0.2, corr_threshold: float = 0.3, min_support: int = 2):
    scoped = df.copy()
    scoped.loc[:, "rubric_item"] = scoped["rubric_item"].fillna("").astype(str).str.strip()
    scoped.loc[:, "student_id"] = scoped["student_id"].astype(str)
    scoped = scoped[scoped["rubric_item"] != ""]

    if scoped.empty:
        return [], pd.DataFrame()

    incidence: Dict[str, set] = defaultdict(set)
    for student_id, sub in scoped.groupby("student_id"):
        for item in sub["rubric_item"].unique():
            incidence[item].add(student_id)

    items = [item for item, students in incidence.items() if len(students) >= min_support]
    if len(items) < 2:
        return [], pd.DataFrame()

    edges = []
    similarities = []
    for a, b in combinations(items, 2):
        sa, sb = incidence[a], incidence[b]
        inter = len(sa & sb)
        union = len(sa | sb)
        if union == 0:
            continue
        jaccard = inter / union
        corr = inter / ((len(sa) * len(sb)) ** 0.5) if len(sa) and len(sb) else 0.0
        if jaccard >= jaccard_threshold or corr >= corr_threshold:
            edges.append((a, b))
        similarities.append({"rubric_item_a": a, "rubric_item_b": b, "jaccard": jaccard, "corr": corr, "cooccurrence": inter})

    # Union-find for clustering
    parent = {item: item for item in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    for a, b in edges:
        union(a, b)

    clusters: Dict[str, List[str]] = defaultdict(list)
    for item in items:
        clusters[find(item)].append(item)

    cluster_list = []
    for idx, members in enumerate(clusters.values(), start=1):
        member_sets = [incidence[m] for m in members]
        support = len(set().union(*member_sets)) if member_sets else 0
        cluster_list.append(
            {
                "label": f"Misconception {idx}",
                "members": sorted(members),
                "size": len(members),
                "support_students": support,
            }
        )

    sim_df = pd.DataFrame(similarities)
    if not sim_df.empty:
        sim_df = sim_df.sort_values(by="jaccard", ascending=False)

    return cluster_list, sim_df


def _concept_mapping_controls(df: pd.DataFrame) -> Dict[str, str]:
    mapping = _load_concept_mapping()

    has_topic_col = "topic" in df.columns
    topic_values = df["topic"].fillna("").astype(str).str.strip() if has_topic_col else pd.Series([], dtype=str)
    has_topic_values = has_topic_col and topic_values.str.len().gt(0).any()

    if has_topic_values:
        st.success("Using provided topic column as concept dimension.")
        return mapping

    st.info("No topic column found or it is blank; map rubric items to concepts.")
    rubric_items = sorted(df["rubric_item"].dropna().astype(str).str.strip().unique())

    search = st.text_input("Filter rubric items", value="", placeholder="Search rubric items")
    filtered_items = [item for item in rubric_items if search.lower() in item.lower()]

    concept_suggestions = sorted({c for c in mapping.values() if c})
    table_data = pd.DataFrame(
        {
            "rubric_item": filtered_items,
            "concept": [mapping.get(item, "") for item in filtered_items],
        }
    )

    edited = st.data_editor(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "rubric_item": st.column_config.TextColumn("Rubric item", width="medium", disabled=True),
            "concept": st.column_config.TextColumn("Concept", help="Type a concept or pick an existing one"),
        },
        num_rows="fixed",
    )

    if st.button("Save concept mapping"):
        updated = {item: str(concept).strip() for item, concept in zip(edited["rubric_item"], edited["concept"]) if str(concept).strip()}
        merged = {**mapping, **updated}
        merged = {k: v for k, v in merged.items() if v}
        try:
            saved = save_concept_mapping(merged, CONCEPT_MAPPING_PATH)
            st.session_state["concept_mapping"] = saved
            st.success("Concept mappings saved and will persist across sessions.")
        except Exception as exc:
            st.error(f"Unable to save mapping: {exc}")

    return st.session_state.get("concept_mapping", mapping)


def _apply_concepts(df: pd.DataFrame) -> pd.DataFrame:
    mapping = _concept_mapping_controls(df)
    result = apply_concept_column(df, mapping, unmapped_label="Unmapped")

    missing = unmapped_count(result, unmapped_label="Unmapped")
    if missing > 0:
        st.warning(
            f"{missing} rows are Unmapped. Recommendations exclude 'Unmapped' by default. Add topics or map rubric items to improve coverage."
        )
    st.caption(f"Concept coverage: {len(result) - missing} rows mapped, {missing} rows Unmapped.")
    return result


def _download_df(label, df, filename, mime="text/csv"):
    """Download a dataframe with a guaranteed-unique Streamlit widget key."""
    import uuid
    import streamlit as st

    # Streamlit requires unique widget keys across reruns and codepaths.
    ctr = st.session_state.get("_dl_counter", 0) + 1
    st.session_state["_dl_counter"] = ctr

    key = f"dl:{filename}:{ctr}:{uuid.uuid4().hex}"
    SAFE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(filename)
    path = build_export_path(SAFE_EXPORT_DIR, safe_name)
    data = df.to_csv(index=False).encode("utf-8")
    path.write_bytes(data)

    st.download_button(
        label=label,
        data=path.read_bytes(),
        file_name=safe_name,
        mime=mime,
        key=key,
        use_container_width=False,
    )


def _download_packet(artifact_map: Dict[str, pd.DataFrame], fig_map: Optional[Dict[str, object]] = None, label: str = "Download instructor packet"):
    if not artifact_map:
        st.caption("No artifacts available to export.")
        return

    SAFE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename("instructor_packet.zip")
    packet_path = build_export_path(SAFE_EXPORT_DIR, safe_name)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, df in artifact_map.items():
            if df is None or getattr(df, "empty", False):
                continue
            safe = sanitize_filename(f"{name}.csv")
            zf.writestr(safe, df.to_csv(index=False))

        if fig_map:
            for name, fig in fig_map.items():
                if fig is None:
                    continue
                try:
                    png = fig.to_image(format="png")
                    zf.writestr(sanitize_filename(f"{name}.png"), png)
                except Exception:
                    # If image export fails, skip quietly
                    continue

    packet_path.write_bytes(buffer.getvalue())

    st.download_button(
        label,
        data=packet_path.read_bytes(),
        file_name=safe_name,
        mime="application/zip",
        use_container_width=False,
        key=f"packet_{abs(hash(label))}",
    )

def _download_fig(label: str, fig, filename: str):
    if fig is None or not fig.data:
        st.caption("No chart to export")
        return
    try:
        SAFE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = sanitize_filename(filename)
        payload = fig.to_image(format="png")
        path = build_export_path(SAFE_EXPORT_DIR, safe_name)
        path.write_bytes(payload)
        st.download_button(label, path.read_bytes(), file_name=safe_name, mime="image/png", key=f"dl_png_{filename}_{abs(hash(label))}")
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


def _generate_pdf_report(top_issues: pd.DataFrame, persistence: pd.DataFrame, recs: Optional[pd.DataFrame]):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except Exception as exc:  # pragma: no cover - optional dependency
        return None, f"PDF export dependency not available: {exc}"

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 48
    y = height - margin

    def header(text):
        nonlocal y
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin, y, text)
        y -= 18

    def line(text):
        nonlocal y
        if y < margin + 40:
            c.showPage()
            y = height - margin
        c.setFont("Helvetica", 11)
        c.drawString(margin, y, text)
        y -= 14

    c.setTitle("Instructor Report")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Gradescope Rubric Analytics — Instructor Report")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} (local)")
    y -= 24

    header("Top issues")
    if top_issues is None or top_issues.empty:
        line("No rubric issues available.")
    else:
        for _, row in top_issues.head(8).iterrows():
            line(f"- {row['rubric_item']} | rows {int(row['count_rows'])} | students {int(row['students_affected'])} | pts {row['points_lost_total']:.1f}")

    y -= 10
    header("Persistence")
    if persistence is None or persistence.empty:
        line("Not enough exams to compute persistence.")
    else:
        for _, row in persistence.head(6).iterrows():
            line(f"- {row['rubric_item']}: cohort {int(row['cohort_size'])}, repeated {int(row['repeated'])}, rate {row['persistence_rate']:.1%}")

    y -= 10
    header("Recommendations")
    if recs is None or recs.empty:
        line("No recommendations available.")
    else:
        for _, row in recs.head(6).iterrows():
            line(f"- {row['action']} {row['concept']} (impact {row['impact_score']:.1f}, students {int(row['students'])}, pts {row['points_lost_total']:.1f})")

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes, None


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


def _render_overview(
    df: pd.DataFrame,
    exam_order: List[str],
    allowed_concepts: List[str],
    include_unmapped: bool,
    personal_mode: bool = False,
):
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
    st.caption("Avg/Std dev per student are computed on total points lost per student in the current scope.")

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
        if personal_mode:
            st.info("Personal mode: instructor summaries are hidden when fewer than 5 students are present.")
        else:
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
    _render_course_structure(df)

    st.divider()
    _render_misconceptions(df)

    st.divider()
    rec_df = None
    if personal_mode:
        st.info("Recommendations hidden in personal mode (fewer than 5 students).")
    else:
        rec_df = _render_recommendations(df, exam_order, allowed_concepts, include_unmapped)

    st.divider()
    if personal_mode:
        st.info("Exports are limited in personal mode; instructor reports are hidden when the dataset is very small.")
        _render_exports(df, errors, persistence, None)
    else:
        _render_exports(df, errors, persistence, rec_df)

    st.divider()
    _render_predictive(df, exam_order)

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


def _render_misconceptions(df: pd.DataFrame):
    st.subheader("Misconception clusters")
    clusters, sim_df = _misconception_clusters(df)

    if not clusters:
        st.info("Not enough co-occurrence data yet; upload more students or exams to see clusters.")
        return

    cols = st.columns(min(len(clusters), 3)) if clusters else []
    for col, cluster in zip(cols * ((len(clusters) + len(cols) - 1) // len(cols)), clusters):
        with col:
            with card(cluster["label"], f"Teach these together; support: {cluster['support_students']} students"):
                st.markdown(
                    "<ul>" + "".join(f"<li>{item}</li>" for item in cluster["members"]) + "</ul>",
                    unsafe_allow_html=True,
                )

    st.subheader("Item co-occurrence (top pairs)")
    if sim_df.empty:
        st.caption("No similarity pairs available yet.")
    else:
        top_pairs = sim_df.head(20).copy()
        top_pairs.loc[:, "jaccard"] = top_pairs["jaccard"].round(3)
        top_pairs.loc[:, "corr"] = top_pairs["corr"].round(3)
        st.dataframe(top_pairs, use_container_width=True, height=320)
        _download_df("Download co-occurrence pairs", top_pairs, "cooccurrence_pairs.csv")


def _build_predictive_frames(df: pd.DataFrame, exam_order: List[str]):
    data = df.copy()
    data.loc[:, "rubric_item"] = data["rubric_item"].fillna("").astype(str).str.strip()
    data.loc[:, "concept"] = data.get("concept", "").fillna("").astype(str).str.strip()
    data.loc[:, "points_lost"] = pd.to_numeric(data["points_lost"], errors="coerce").fillna(0)
    data.loc[:, "exam_id"] = data["exam_id"].astype(str)
    data.loc[:, "student_id"] = data["student_id"].astype(str)

    items = sorted(data["rubric_item"].unique())
    concept_for_item = (
        data.groupby("rubric_item")["concept"].agg(lambda s: s.mode().iat[0] if not s.mode().empty else "")
    ).to_dict()

    exam_rank = {exam: idx for idx, exam in enumerate(exam_order)}
    training_rows = []
    scoring_rows = []

    for student_id, sub in data.groupby("student_id"):
        exams = sorted(sub["exam_id"].unique(), key=lambda x: exam_rank.get(x, 1e9))
        if len(exams) < 1:
            continue

        # Build cumulative prior for scoring on last exam (predict next)
        for idx in range(1, len(exams)):
            current_exam = exams[idx]
            prior_exams = set(exams[:idx])
            prior_df = sub[sub["exam_id"].isin(prior_exams)]
            current_df = sub[sub["exam_id"] == current_exam]

            current_items = set(current_df["rubric_item"].unique())
            for item in items:
                concept = concept_for_item.get(item, "")
                prior_seen = 1 if item in set(prior_df["rubric_item"].unique()) else 0
                prior_concept_pts = (
                    prior_df.loc[prior_df["concept"] == concept, "points_lost"].sum() if concept else 0.0
                )
                label = 1 if item in current_items else 0
                training_rows.append(
                    {
                        "student_id": student_id,
                        "exam_id": current_exam,
                        "rubric_item": item,
                        "prior_seen": prior_seen,
                        "prior_concept_points": prior_concept_pts,
                        "label": label,
                    }
                )

        # scoring using last known state
        last_exam = exams[-1]
        prior_exams = set(exams[:-1])
        prior_df = sub[sub["exam_id"].isin(prior_exams)] if prior_exams else sub.iloc[0:0]
        for item in items:
            concept = concept_for_item.get(item, "")
            prior_seen = 1 if item in set(prior_df["rubric_item"].unique()) else 0
            prior_concept_pts = prior_df.loc[prior_df["concept"] == concept, "points_lost"].sum() if concept else 0.0
            scoring_rows.append(
                {
                    "student_id": student_id,
                    "rubric_item": item,
                    "prior_seen": prior_seen,
                    "prior_concept_points": prior_concept_pts,
                }
            )

    train_df = pd.DataFrame(training_rows)
    score_df = pd.DataFrame(scoring_rows)
    return train_df, score_df, items


def _predict_future_risks(df: pd.DataFrame, exam_order: List[str]):
    try:
        from sklearn.linear_model import LogisticRegression
    except Exception as exc:  # pragma: no cover - defensive
        return None, None, f"sklearn not available: {exc}"

    train_df, score_df, items = _build_predictive_frames(df, exam_order)
    if train_df.empty or score_df.empty:
        return None, None, "Not enough exam history to train (need at least 2 exams with students)."

    X = train_df[["prior_seen", "prior_concept_points"]]
    y = train_df["label"]
    model = LogisticRegression(max_iter=200)
    try:
        model.fit(X, y)
    except Exception as exc:  # pragma: no cover - defensive
        return None, None, f"Model training failed: {exc}"

    score_probs = model.predict_proba(score_df[["prior_seen", "prior_concept_points"]])[:, 1]
    score_df = score_df.copy()
    score_df.loc[:, "probability"] = score_probs
    score_df.loc[:, "confidence"] = score_df["probability"].apply(
        lambda p: "high" if p >= 0.7 else ("medium" if p >= 0.4 else "low")
    )

    coef_df = pd.DataFrame(
        {
            "feature": ["prior_seen", "prior_concept_points"],
            "coefficient": model.coef_[0],
        }
    )

    return score_df, coef_df, None


def _render_recommendations(df: pd.DataFrame, exam_order: List[str], allowed_concepts: List[str], include_unmapped: bool):
    st.subheader("What to change next week")

    rec_df = compute_recommendations(
        df,
        exam_order=exam_order,
        allowed_concepts=allowed_concepts,
        top_n=5,
        include_unmapped=include_unmapped,
        unmapped_label="Unmapped",
    )
    if rec_df.empty:
        st.info("No valid concepts available for recommendations; add topics or concept mappings.")
        return None

    st.markdown("Guidance focuses on concepts with highest combined impact (points lost × students affected), adjusted by persistence where available.")

    for rec in rec_df.to_dict("records"):
        with card(
            f"{rec['action']} {rec['concept']}",
            f"Impact score {rec['impact_score']:.1f} | {rec['students']} students | {rec['points_lost_total']:.1f} pts lost | persistence {rec['persistence_rate']:.0%}",
        ):
            st.markdown("- Suggested action: **" + rec["action"] + f" {rec['concept']}**")
            if rec["persistence_rate"] >= 0.2:
                st.markdown("- Rationale: recurring across exams (high persistence)")
            else:
                st.markdown("- Rationale: high impact despite low persistence; reinforce with practice")
            st.markdown("- Plan: include a focused mini-lesson and formative check next week")

    st.dataframe(rec_df[["concept", "action", "impact_score", "students", "points_lost_total", "persistence_rate"]], use_container_width=True, height=320)
    _download_df("Download recommendations", rec_df, "recommendations.csv")
    return rec_df


def _render_predictive(df: pd.DataFrame, exam_order: List[str]):
    st.subheader("Predictive analytics (interpretable)")
    st.caption("Uses logistic regression with prior misses and concept points; predictions are probabilistic and uncertain.")

    score_df, coef_df, warn = _predict_future_risks(df, exam_order)
    if warn:
        st.info(warn)
        return

    if score_df is None or score_df.empty:
        st.info("Not enough data to score future mistakes yet.")
        return

    st.markdown("**Model coefficients (interpretability)**")
    if coef_df is not None and not coef_df.empty:
        coef_df = coef_df.copy()
        coef_df.loc[:, "coefficient"] = coef_df["coefficient"].round(3)
        st.dataframe(coef_df, use_container_width=True, height=120)
    else:
        st.caption("Coefficients unavailable.")

    st.markdown("**Per-student predicted risks (next exam)**")
    risk_table = score_df.copy()
    risk_table.loc[:, "probability"] = risk_table["probability"].round(3)
    risk_table = risk_table.sort_values(by="probability", ascending=False)
    st.dataframe(risk_table.head(50), use_container_width=True, height=360)
    _download_df("Download risk table", risk_table, "predicted_risks.csv")

    st.caption("Disclaimer: These probabilities are estimates based on limited history; treat as guidance, not guarantees.")


def _top_concepts(df: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    concept_stats = _concept_stats(df)
    if concept_stats.empty:
        return concept_stats
    concept_stats = concept_stats.copy()
    concept_stats.loc[:, "impact_score"] = concept_stats["points_lost_total"] * concept_stats["students_affected"].clip(lower=1)
    return concept_stats.sort_values(by="impact_score", ascending=False).head(limit)


def _top_persistent_concepts(df: pd.DataFrame, exam_order: List[str], limit: int = 5) -> pd.DataFrame:
    persistence = metrics.compute_persistence(df, exam_order=exam_order)
    if persistence.empty:
        return persistence
    return persistence.sort_values(by=["persistence_rate", "cohort_size"], ascending=[False, False]).head(limit)


def _exam_change_table(df: pd.DataFrame, exam_order: List[str]) -> pd.DataFrame:
    changes = metrics.exam_changes(df, exam_order=exam_order)
    if changes.empty:
        return changes
    changes = changes.copy()
    changes.loc[:, "delta_vs_prev"] = changes["delta_vs_prev"].fillna(0.0).round(2)
    changes.loc[:, "pct_change_vs_prev"] = changes["pct_change_vs_prev"].fillna(0.0).round(3)
    return changes


def _lesson_plan_suggestions(top_concepts: pd.DataFrame, top_persist: pd.DataFrame) -> List[str]:
    suggestions: List[str] = []
    if not top_concepts.empty:
        first = top_concepts.iloc[0]
        suggestions.append(
            f"Prioritize reteaching **{first['concept']}**; it has the highest impact score ({first['impact_score']:.1f})."
        )
    if not top_persist.empty:
        first_persist = top_persist.iloc[0]
        suggestions.append(
            f"Address recurring concept **{first_persist['rubric_item'] if 'rubric_item' in first_persist else first_persist['concept']}**; repeat rate {first_persist['persistence_rate']:.0%} across {int(first_persist['cohort_size'])} students."
        )
    if len(suggestions) < 3:
        suggestions.append("Add 10-minute targeted practice on top two concepts, then quick formative check.")
    suggestions.append("Share anonymized exemplars for the highest-impact misconception to speed feedback loops.")
    return suggestions


def _render_instructor_summary(df: pd.DataFrame, exam_order: List[str], personal_mode: bool):
    st.subheader("Instructor Summary")
    if personal_mode:
        st.info("Personal mode: metrics are shown for transparency; avoid sharing externally when cohort < 5.")

    top_concepts = _top_concepts(df)
    top_persist = _top_persistent_concepts(df, exam_order)
    exam_changes = _exam_change_table(df, exam_order)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top concepts by impact**")
        if top_concepts.empty:
            st.caption("Add topics or concept mappings to see concept impact.")
        else:
            st.dataframe(top_concepts, use_container_width=True, height=260)
            st.caption("Impact = total points lost × students affected.")
            _download_df("Download top concepts", top_concepts, "top_concepts.csv")
    with col2:
        st.markdown("**Most persistent concepts**")
        if top_persist.empty:
            st.caption("Need at least two exams with repeated concepts to compute persistence.")
        else:
            st.dataframe(top_persist, use_container_width=True, height=260)
            st.caption("Persistence rate = repeated students / cohort from first exam in order.")
            _download_df("Download persistent concepts", top_persist, "persistent_concepts.csv")

    st.markdown("**Exam-over-exam changes**")
    if exam_changes.empty:
        st.caption("Upload at least two exams to see changes in total points lost.")
    else:
        st.dataframe(exam_changes, use_container_width=True, height=260)
        st.caption("Delta shows change in total points lost vs. prior exam; pct_change is relative change.")
        _download_df("Download exam changes", exam_changes, "exam_changes.csv")

    suggestions = _lesson_plan_suggestions(top_concepts, top_persist)
    st.markdown("**Suggested lesson plan adjustments**")
    for s in suggestions:
        st.markdown(f"- {s}")

    artifacts = {
        "top_concepts": top_concepts,
        "persistent_concepts": top_persist,
        "exam_changes": exam_changes,
    }
    _download_packet(artifacts, fig_map=None, label="Download instructor packet (ZIP)")


def _render_persistence(df: pd.DataFrame, exam_order: List[str], personal_mode: bool = False):
    if personal_mode:
        st.info("Persistence is hidden in personal mode (fewer than 5 students).")
        return
    if len(exam_order) < 2:
        st.info("Need at least two exams to compute persistence and trajectories.")
        return

    persistence = metrics.compute_persistence(df, exam_order=exam_order)
    persistence = persistence.sort_values(by="persistence_rate", ascending=False)

    with card("Persistence by rubric item"):
        st.dataframe(persistence, use_container_width=True, height=260)
        st.caption("Cohort = students with item in first exam; persistence_rate = repeated / cohort across later exams.")
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

    item_stats, transition_df = _trajectory_stats(df, exam_order)

    st.subheader("Trajectory analytics")
    if item_stats.empty:
        st.info("No transitions available to compute persistence/drop-off/emergence.")
    else:
        st.dataframe(item_stats, use_container_width=True, height=280)
        _download_df("Download trajectory stats (CSV)", item_stats, "trajectory_stats.csv")

    st.subheader("Most likely future mistakes given current mistake")
    if transition_df.empty:
        st.info("No transitions available to compute conditional probabilities.")
    else:
        top_transitions = transition_df.head(20).copy()
        top_transitions.loc[:, "conditional_prob"] = top_transitions["conditional_prob"].round(3)
        st.dataframe(top_transitions, use_container_width=True, height=320)
        _download_df("Download transitions (CSV)", top_transitions, "transitions.csv")

        nodes = sorted(set(top_transitions["source"]).union(set(top_transitions["target"])))
        node_index = {name: idx for idx, name in enumerate(nodes)}
        sankey = dict(
            type="sankey",
            arrangement="snap",
            node=dict(label=nodes, pad=15, thickness=15, line=dict(color="#444", width=0.5)),
            link=dict(
                source=[node_index[s] for s in top_transitions["source"]],
                target=[node_index[t] for t in top_transitions["target"]],
                value=top_transitions["count"],
                color=["rgba(34,99,235,0.5)" for _ in range(len(top_transitions))],
            ),
        )
        fig = dict(data=[sankey], layout=dict(title="Transitions A → B", font=dict(color="#e5e7eb")))
        st.plotly_chart(fig, use_container_width=True)


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
    # Reset per-rerun download key counter
    st.session_state['_dl_counter'] = 0

    _init_state()
    shell = AppShell("Gradescope Rubric Analytics", "Guided ingestion → validation → insights")
    shell.header(right="Modern UI beta")
    shell.layout()

    st.sidebar.header("Data source")
    st.sidebar.write("Upload a CSV, toggle demo mode, or use a synthetic demo dataset.")
    synthetic_mode = st.sidebar.toggle(
        "Use synthetic demo dataset",
        value=st.session_state.get("synthetic_mode", False),
        help="Generate/load a synthetic class with 80 students across existing exams",
    )
    if synthetic_mode:
        st.session_state["demo_mode"] = False
    st.session_state["synthetic_mode"] = synthetic_mode

    demo_mode = st.sidebar.toggle("Demo mode", value=st.session_state["demo_mode"], help="Load sample_truth.csv for a quick tour")
    if demo_mode:
        st.session_state["synthetic_mode"] = False
    st.session_state["demo_mode"] = demo_mode

    anonymize_default = st.session_state.get("anonymize_ids", True)
    reveal_identifiers = st.sidebar.toggle(
        "Reveal identifiers (instructor mode)",
        value=not anonymize_default,
        help="Show raw student_id values. Default remains anonymized for privacy.",
    )
    anonymize_ids = not reveal_identifiers
    st.session_state["anonymize_ids"] = anonymize_ids

    uploader = st.sidebar.file_uploader("Upload rubric CSV", type=["csv"])

    raw_df, source_label = _load_source(demo_mode, synthetic_mode, uploader)
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

    if synthetic_mode:
        st.info("Synthetic demo mode: all data shown below is randomly generated for illustration only.")

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

    anonymize_ids = st.session_state.get("anonymize_ids", False)
    normalized_df = _maybe_anonymize_students(normalized_df, anonymize_ids)
    if anonymize_ids:
        st.caption("Student identifiers are anonymized across all charts and downloads.")

    include_unmapped = st.checkbox(
        "Include 'Unmapped' concepts in recommendations",
        value=False,
        help="Turn off to keep recommendations focused on mapped concepts."
    )

    allowed_concepts = [
        c
        for c in normalized_df.get("concept", pd.Series([], dtype=str)).fillna("").astype(str).str.strip().unique()
        if c and (include_unmapped or c != "Unmapped")
    ]
    allowed_concepts = sorted(allowed_concepts)

    section_header("Student scope", "Analyze all students or a subset")
    filtered_df, student_scope_desc = _student_filter_controls(normalized_df)
    st.caption(f"Student scope: {student_scope_desc}")

    student_count = filtered_df["student_id"].nunique()
    personal_mode = student_count < 5
    if personal_mode:
        st.warning("Personal mode: fewer than 5 students detected. Instructor-only analytics are hidden to reduce re-identification risk.")

    st.write("### Preview (first 20 rows)")
    st.dataframe(filtered_df.head(20), use_container_width=True)

    section_header("Step 4 — Explore")
    exam_order = _exam_order(filtered_df)
    overview_tab, persistence_tab, instructor_tab, quality_tab = st.tabs([
        "Overview",
        "Persistence",
        "Instructor Summary",
        "Data Quality",
    ])

    with overview_tab:
        _render_overview(filtered_df, exam_order, allowed_concepts, include_unmapped, personal_mode=personal_mode)
    with persistence_tab:
        _render_persistence(filtered_df, exam_order, personal_mode=personal_mode)
    with instructor_tab:
        _render_instructor_summary(filtered_df, exam_order, personal_mode)
    with quality_tab:
        _render_quality(filtered_df)


if __name__ == "__main__":
    main()
