from typing import Dict, List

import pandas as pd

REQUIRED_COLUMNS = [
    "student_id",
    "student_name",
    "assignment",
    "rubric_item",
    "category",
    "score",
    "max_score",
    "comment",
]


def check_required_columns(df: pd.DataFrame) -> Dict[str, bool]:
    return {col: col in df.columns for col in REQUIRED_COLUMNS}


def check_missing_identifiers(df: pd.DataFrame) -> int:
    missing_ids = df["student_id"].astype(str).str.strip() == ""
    missing_items = df["rubric_item"].astype(str).str.strip() == ""
    return int((missing_ids | missing_items).sum())


def check_numeric_scores(df: pd.DataFrame) -> int:
    numeric_score = pd.to_numeric(df["score"], errors="coerce")
    return int(numeric_score.isna().sum())


def check_score_ranges(df: pd.DataFrame) -> int:
    numeric_score = pd.to_numeric(df["score"], errors="coerce")
    numeric_max = pd.to_numeric(df["max_score"], errors="coerce")
    invalid = (numeric_score < 0) | (numeric_max < 0)
    over_max = (numeric_max.notna()) & (numeric_score > numeric_max)
    return int((invalid | over_max).sum())


def run_invariants(df: pd.DataFrame) -> List[Dict[str, object]]:
    results = []

    required = check_required_columns(df)
    missing_required = [col for col, present in required.items() if not present]
    results.append(
        {
            "name": "required_columns",
            "ok": len(missing_required) == 0,
            "detail": ", ".join(missing_required) if missing_required else "all present",
        }
    )

    missing_ids = check_missing_identifiers(df)
    results.append({"name": "missing_identifiers", "ok": missing_ids == 0, "detail": missing_ids})

    non_numeric = check_numeric_scores(df)
    results.append({"name": "non_numeric_scores", "ok": non_numeric == 0, "detail": non_numeric})

    out_of_range = check_score_ranges(df)
    results.append({"name": "score_range_violations", "ok": out_of_range == 0, "detail": out_of_range})

    return results
