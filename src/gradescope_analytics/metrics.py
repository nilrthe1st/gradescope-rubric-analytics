from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from .mapping import CANONICAL_COLUMNS, ensure_canonical_columns


def _cast_numeric(df: pd.DataFrame) -> pd.DataFrame:
    numeric = df.copy()
    numeric.loc[:, "points_lost"] = pd.to_numeric(numeric["points_lost"], errors="coerce")
    return numeric


def overall_summary(df: pd.DataFrame) -> Dict[str, float]:
    data = _cast_numeric(ensure_canonical_columns(df))
    avg_loss = data["points_lost"].mean()
    return {
        "rows": len(df),
        "students": data["student_id"].nunique(),
        "exams": data["exam_id"].nunique(),
        "questions": data["question_id"].nunique(),
        "avg_points_lost": avg_loss,
    }


def rubric_item_stats(df: pd.DataFrame) -> pd.DataFrame:
    data = _cast_numeric(ensure_canonical_columns(df))
    grouped = data.groupby(["rubric_item", "topic"], dropna=False)
    rows = []
    for (item, topic), subset in grouped:
        rows.append(
            {
                "rubric_item": item,
                "topic": topic if pd.notna(topic) else "",
                "count": len(subset),
                "avg_points_lost": subset["points_lost"].mean(),
                "median_points_lost": subset["points_lost"].median(),
                "std_points_lost": subset["points_lost"].std(ddof=0),
                "total_points_lost": subset["points_lost"].sum(),
            }
        )
    return pd.DataFrame(rows).sort_values(by=["topic", "rubric_item"])


def exam_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    data = _cast_numeric(ensure_canonical_columns(df))
    grouped = data.groupby("exam_id", dropna=False)
    rows = []
    for exam_id, subset in grouped:
        rows.append(
            {
                "exam_id": exam_id,
                "students": subset["student_id"].nunique(),
                "questions": subset["question_id"].nunique(),
                "total_points_lost": subset["points_lost"].sum(),
                "avg_points_lost": subset["points_lost"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values(by="exam_id")


def student_summary(df: pd.DataFrame, exam_order: Optional[Iterable[str]] = None) -> pd.DataFrame:
    data = _cast_numeric(ensure_canonical_columns(df))
    grouped = data.groupby(["student_id", "exam_id"], dropna=False)
    rows = []
    for (student_id, exam_id), subset in grouped:
        total_loss = subset["points_lost"].sum()
        rows.append(
            {
                "student_id": student_id,
                "exam_id": exam_id,
                "total_points_lost": total_loss,
                "questions": subset["question_id"].nunique(),
            }
        )
    result = pd.DataFrame(rows)
    if exam_order:
        cat_type = pd.CategoricalDtype(categories=list(exam_order), ordered=True)
        result.loc[:, "exam_id"] = result["exam_id"].astype(cat_type)
        result = result.sort_values(by=["exam_id", "total_points_lost"], ascending=[True, False])
    else:
        result = result.sort_values(by="total_points_lost", ascending=False)
    return result


def score_distribution(df: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    data = _cast_numeric(ensure_canonical_columns(df))
    metric = data["points_lost"].dropna()

    if metric.empty:
        return pd.DataFrame(columns=["bin", "count"])

    counts, edges = pd.cut(metric, bins=bins, include_lowest=True, retbins=True, right=False)
    bucket = counts.value_counts().sort_index()
    labels = [f"{float(edge_start):.1f}-{float(edge_end):.1f}" for edge_start, edge_end in zip(edges[:-1], edges[1:])]
    return pd.DataFrame({"bin": labels, "count": bucket.tolist()})


def summarize_errors(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate rubric-level error statistics.

    Returns a DataFrame with rubric_item, row counts, students affected,
    and points_lost totals/means. Assumes df is canonical; validation is
    performed via ensure_canonical_columns.
    """

    data = _cast_numeric(ensure_canonical_columns(df))
    grouped = data.groupby("rubric_item", dropna=False)
    rows = []
    for rubric_item, subset in grouped:
        rows.append(
            {
                "rubric_item": rubric_item,
                "count_rows": len(subset),
                "students_affected": subset["student_id"].nunique(),
                "points_lost_total": subset["points_lost"].sum(),
                "points_lost_mean": subset["points_lost"].mean(),
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(by="rubric_item")
    return result


def error_by_exam(df: pd.DataFrame) -> pd.DataFrame:
    """Return rubric error totals per exam in long form."""

    data = _cast_numeric(ensure_canonical_columns(df))
    grouped = data.groupby(["exam_id", "rubric_item"], dropna=False)
    rows = []
    for (exam_id, rubric_item), subset in grouped:
        rows.append(
            {
                "exam_id": exam_id,
                "rubric_item": rubric_item,
                "count_rows": len(subset),
                "points_lost_total": subset["points_lost"].sum(),
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(by=["exam_id", "rubric_item"])
    return result


def group_comparison(df: pd.DataFrame, group_col: str, missing_label: str = "Unassigned") -> pd.DataFrame:
    """Aggregate points lost by a grouping column (e.g., section_id or ta_id).

    Returns rows with counts, students affected, and average points lost per student.
    Missing or blank group labels are mapped to ``missing_label``.
    """

    data = _cast_numeric(ensure_canonical_columns(df))
    if group_col not in data.columns:
        return pd.DataFrame()

    data = data.copy()
    data.loc[:, group_col] = data[group_col].fillna("").astype(str).str.strip()
    data.loc[:, group_col] = data[group_col].replace({"": missing_label})

    grouped = data.groupby(group_col, dropna=False)
    rows = []
    for group_value, subset in grouped:
        students = subset["student_id"].nunique()
        total = subset["points_lost"].sum()
        rows.append(
            {
                group_col: group_value,
                "rows": len(subset),
                "students": students,
                "total_points_lost": total,
                "avg_points_per_student": total / students if students else 0.0,
                "avg_points_per_row": subset["points_lost"].mean(),
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(by="avg_points_per_student", ascending=False)
    return result


def compute_persistence(df: pd.DataFrame, exam_order: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """Compute persistence of rubric issues across exams.

    For each rubric_item, define the cohort as students with that item in the
    first exam. A student is repeated if they show the same item in any later
    exam. Persistence rate = repeated / cohort_size (0 when cohort_size is 0).
    exam_order optionally defines the ordering; otherwise uses lexicographic
    exam_id order.
    """

    data = _cast_numeric(ensure_canonical_columns(df))
    exams_seen = list(data["exam_id"].dropna().unique())

    if exam_order:
        order_list = [exam for exam in exam_order if exam in exams_seen]
        # Fallback to discovered exams if provided order is empty after filtering.
        if not order_list:
            order_list = sorted(exams_seen)
    else:
        order_list = sorted(exams_seen)

    if not order_list:
        return pd.DataFrame(columns=["rubric_item", "cohort_size", "repeated", "persistence_rate"])

    first_exam = order_list[0]
    later_exams = set(order_list[1:])
    exam_rank = {exam: idx for idx, exam in enumerate(order_list)}

    rows = []
    for rubric_item, subset in data.groupby("rubric_item", dropna=False):
        cohort_students = subset.loc[subset["exam_id"] == first_exam, "student_id"].unique()
        cohort_set = set(cohort_students)

        if later_exams:
            later_subset = subset[subset["exam_id"].map(lambda x: exam_rank.get(x, -1) > 0)]
        else:
            later_subset = subset.iloc[0:0]

        repeated_students = set(later_subset["student_id"].unique()) & cohort_set
        cohort_size = len(cohort_set)
        repeated = len(repeated_students)
        rate = repeated / cohort_size if cohort_size else 0.0

        rows.append(
            {
                "rubric_item": rubric_item,
                "cohort_size": cohort_size,
                "repeated": repeated,
                "persistence_rate": rate,
            }
        )

    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values(by="rubric_item")
    return result


def persist_dataset(df: pd.DataFrame, path: Path) -> Path:
    ensure_canonical_columns(df)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def load_persisted_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return ensure_canonical_columns(df)
