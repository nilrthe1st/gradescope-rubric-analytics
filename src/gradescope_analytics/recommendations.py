import pandas as pd
from typing import Iterable, List, Optional, Set


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


def _filter_allowed_concepts(df: pd.DataFrame, allowed: Optional[Iterable[str]]) -> pd.DataFrame:
    if allowed is None:
        return df
    allowed_set: Set[str] = {c.strip() for c in allowed if str(c).strip()}
    if not allowed_set:
        return df.iloc[0:0]
    return df[df["concept"].isin(allowed_set)]


def compute_recommendations(
    df: pd.DataFrame,
    exam_order: Optional[Iterable[str]] = None,
    allowed_concepts: Optional[Iterable[str]] = None,
    top_n: int = 5,
    include_unmapped: bool = False,
    unmapped_label: str = "Unmapped",
) -> pd.DataFrame:
    """Compute concept-level recommendations with optional concept whitelist.

    Returns a dataframe with columns: concept, action, impact_score, students,
    points_lost_total, persistence_rate.
    """

    data = df.copy()
    data.loc[:, "exam_id"] = data["exam_id"].astype(str)
    data.loc[:, "concept"] = data.get("concept", "").fillna("").astype(str).str.strip()

    if not include_unmapped:
        data = data[data["concept"] != unmapped_label]

    concept_stats = _filter_allowed_concepts(_concept_stats(data), allowed_concepts)

    if concept_stats.empty:
        return pd.DataFrame(columns=["concept", "action", "impact_score", "students", "points_lost_total", "persistence_rate"])

    concept_stats = concept_stats.copy()
    concept_stats.loc[:, "impact_score"] = concept_stats["points_lost_total"] * concept_stats["students_affected"].clip(lower=1)
    concept_stats = concept_stats.sort_values(by="impact_score", ascending=False)

    exams = list(data["exam_id"].dropna().unique())
    if exam_order:
        order_list = [exam for exam in exam_order if exam in exams]
        if not order_list:
            order_list = sorted(exams)
    else:
        order_list = sorted(exams)

    concept_persist = _concept_persistence(data, order_list) if order_list else pd.DataFrame(columns=["concept", "persistence_rate"])

    recs = []
    for _, row in concept_stats.head(top_n).iterrows():
        concept = row["concept"]
        rate = float(concept_persist[concept_persist["concept"] == concept]["persistence_rate"].fillna(0).values[0]) if not concept_persist.empty else 0.0
        students = int(row["students_affected"])
        pts = float(row["points_lost_total"])
        impact = float(row["impact_score"])
        action = "Re-teach" if rate >= 0.2 else "Add practice for"
        recs.append(
            {
                "concept": concept,
                "action": action,
                "impact_score": impact,
                "students": students,
                "points_lost_total": pts,
                "persistence_rate": rate,
            }
        )

    return pd.DataFrame(recs)
