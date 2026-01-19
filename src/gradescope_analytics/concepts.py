from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pandas as pd

# Values that indicate a placeholder instead of a meaningful concept name.
_PLACEHOLDER_VALUES = {"", "none", "null", "nil", "n/a", "na", "yes", "true", "false"}


def _clean_str(value: object) -> str:
    return str(value).strip()


def _is_valid_concept(value: str) -> bool:
    return value.lower() not in _PLACEHOLDER_VALUES and bool(value)


def normalize_mapping(mapping: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Return (cleaned_mapping, invalid_entries)."""
    cleaned: Dict[str, str] = {}
    invalid: Dict[str, str] = {}

    for raw_key, raw_val in mapping.items():
        key = _clean_str(raw_key)
        val = _clean_str(raw_val)
        if not key:
            invalid[raw_key] = raw_val
            continue
        if _is_valid_concept(val):
            cleaned[key] = val
        else:
            invalid[key] = val

    return cleaned, invalid


def load_concept_mapping(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Concept mapping JSON must be an object of rubric_item -> concept")

    cleaned, _ = normalize_mapping(raw)
    return cleaned


def save_concept_mapping(mapping: Dict[str, str], path: Path) -> Dict[str, str]:
    cleaned, invalid = normalize_mapping(mapping)
    if invalid:
        invalid_keys = ", ".join(sorted(invalid.keys()))
        raise ValueError(f"Invalid concept values for: {invalid_keys}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False), encoding="utf-8")
    return cleaned


def apply_concept_column(df: pd.DataFrame, mapping: Dict[str, str], unmapped_label: str = "Unmapped") -> pd.DataFrame:
    data = df.copy()
    data.loc[:, "rubric_item"] = data["rubric_item"].fillna("").astype(str).str.strip()
    topic_series = data.get("topic", "").fillna("").astype(str).str.strip()

    concept_series = topic_series
    missing_topic = topic_series == ""
    if mapping:
        mapped = data.loc[missing_topic, "rubric_item"].map(mapping).fillna("")
        concept_series = concept_series.where(~missing_topic, mapped)

    concept_series = concept_series.fillna("").astype(str).str.strip()
    concept_series = concept_series.where(concept_series != "", unmapped_label)

    result = data.copy()
    result.loc[:, "concept"] = concept_series
    return result


def unmapped_count(df: pd.DataFrame, unmapped_label: str = "Unmapped") -> int:
    if "concept" not in df.columns:
        return 0
    return int((df["concept"].fillna("") == unmapped_label).sum())
