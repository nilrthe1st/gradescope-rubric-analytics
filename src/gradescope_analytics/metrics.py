from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd

from .mapping import CANONICAL_COLUMNS, ensure_canonical_columns


def _cast_numeric(df: pd.DataFrame) -> pd.DataFrame:
    numeric = df.copy()
    numeric.loc[:, "score"] = pd.to_numeric(numeric["score"], errors="coerce")
    if "max_score" in numeric.columns:
        numeric.loc[:, "max_score"] = pd.to_numeric(numeric["max_score"], errors="coerce")
    return numeric


def overall_summary(df: pd.DataFrame) -> Dict[str, float]:
    data = _cast_numeric(ensure_canonical_columns(df))
    avg_score = data["score"].mean()
    max_score = data["max_score"].dropna()
    avg_pct = (avg_score / max_score.mean() * 100) if not max_score.empty else float("nan")
    return {
        "rows": len(df),
        "students": data["student_id"].nunique(),
        "assignments": data["assignment"].nunique(),
        "avg_score": avg_score,
        "avg_pct": avg_pct,
    }


def rubric_item_stats(df: pd.DataFrame) -> pd.DataFrame:
    data = _cast_numeric(ensure_canonical_columns(df))
    grouped = data.groupby(["rubric_item", "category"], dropna=False)
    rows = []
    for (item, category), subset in grouped:
        max_score = subset["max_score"].dropna()
        pct_full = (subset["score"] >= max_score).mean() * 100 if not max_score.empty else float("nan")
        rows.append(
            {
                "rubric_item": item,
                "category": category if pd.notna(category) else "Uncategorized",
                "count": len(subset),
                "avg_score": subset["score"].mean(),
                "median_score": subset["score"].median(),
                "std_score": subset["score"].std(ddof=0),
                "max_score_value": max_score.max() if not max_score.empty else float("nan"),
                "full_points_pct": pct_full,
            }
        )
    return pd.DataFrame(rows).sort_values(by=["category", "rubric_item"])


def category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    data = _cast_numeric(ensure_canonical_columns(df))
    grouped = data.groupby("category", dropna=False)
    rows = []
    for category, subset in grouped:
        total_scored = subset["score"].sum()
        total_possible = subset["max_score"].sum() if "max_score" in subset else float("nan")
        pct_of_total = (total_scored / total_possible * 100) if total_possible and total_possible > 0 else float("nan")
        rows.append(
            {
                "category": category if pd.notna(category) else "Uncategorized",
                "items": subset["rubric_item"].nunique(),
                "submissions": subset["student_id"].nunique(),
                "score_sum": total_scored,
                "max_sum": total_possible,
                "pct_of_total": pct_of_total,
            }
        )
    return pd.DataFrame(rows).sort_values(by="category")


def student_summary(df: pd.DataFrame, assignment_order: Optional[Iterable[str]] = None) -> pd.DataFrame:
    data = _cast_numeric(ensure_canonical_columns(df))
    grouped = data.groupby(["student_id", "student_name", "assignment"], dropna=False)
    rows = []
    for (student_id, name, assignment), subset in grouped:
        total_score = subset["score"].sum()
        total_max = subset["max_score"].sum() if "max_score" in subset else float("nan")
        pct = (total_score / total_max * 100) if total_max and total_max > 0 else float("nan")
        rows.append(
            {
                "student_id": student_id,
                "student_name": name,
                "assignment": assignment,
                "score_sum": total_score,
                "max_sum": total_max,
                "percent": pct,
            }
        )
    result = pd.DataFrame(rows)
    if assignment_order:
        cat_type = pd.CategoricalDtype(categories=list(assignment_order), ordered=True)
        result.loc[:, "assignment"] = result["assignment"].astype(cat_type)
        result = result.sort_values(by=["assignment", "percent"], ascending=[True, False])
    else:
        result = result.sort_values(by="percent", ascending=False)
    return result


def score_distribution(df: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    data = _cast_numeric(ensure_canonical_columns(df))
    if "max_score" in data and data["max_score"].notna().any():
        ratio = data["score"] / data["max_score"].replace(0, pd.NA)
        ratio = ratio.dropna().clip(lower=0, upper=1)
        metric = ratio * 100
    else:
        metric = data["score"].dropna()

    if metric.empty:
        return pd.DataFrame(columns=["bin", "count"])

    counts, edges = pd.cut(metric, bins=bins, include_lowest=True, retbins=True, right=False)
    bucket = counts.value_counts().sort_index()
    labels = [f"{int(edge_start)}-{int(edge_end)}" for edge_start, edge_end in zip(edges[:-1], edges[1:])]
    return pd.DataFrame({"bin": labels, "count": bucket.tolist()})


def persist_dataset(df: pd.DataFrame, path: Path) -> Path:
    ensure_canonical_columns(df)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def load_persisted_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return ensure_canonical_columns(df)
