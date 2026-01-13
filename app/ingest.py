from io import BytesIO
from typing import List

import pandas as pd

REQUIRED_FIELDS = ["student_id", "student_name", "rubric_item", "score"]


def load_csv(file_obj: BytesIO) -> pd.DataFrame:
    """Read a CSV upload into a DataFrame."""

    return pd.read_csv(file_obj)


def validate_normalized(df: pd.DataFrame) -> List[str]:
    """Return a list of validation errors for a normalized dataframe."""

    errors = []
    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            errors.append(f"Missing required column: {field}")
    if df.empty:
        errors.append("Dataset is empty")
    if "score" in df.columns and df["score"].notna().sum() == 0:
        errors.append("No numeric scores detected after mapping")
    return errors


def sanitize_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove rows lacking basic identifiers."""

    filtered = df.copy()
    filtered = filtered[filtered["student_id"].astype(str).str.strip() != ""]
    filtered = filtered[filtered["rubric_item"].astype(str).str.strip() != ""]
    return filtered
