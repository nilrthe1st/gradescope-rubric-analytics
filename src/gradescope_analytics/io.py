from pathlib import Path
from typing import IO, Optional, Tuple

import pandas as pd

from .mapping import (
    CANONICAL_COLUMNS,
    REQUIRED_CANONICAL,
    MappingConfig,
    apply_mapping,
    ensure_canonical_columns,
    needs_mapping,
    suggest_mapping,
)


def read_csv(source: str | Path | IO[str] | IO[bytes]) -> pd.DataFrame:
    # Preserve literal strings like "None" instead of auto-converting to NaN so we can validate explicitly.
    return pd.read_csv(source, keep_default_na=False)


def is_canonical(df: pd.DataFrame) -> bool:
    return all(col in df.columns for col in REQUIRED_CANONICAL)


def load_and_normalize(
    source: str | Path | IO[str] | IO[bytes],
    mapping: Optional[MappingConfig] = None,
    infer_mapping: bool = True,
) -> Tuple[pd.DataFrame, Optional[MappingConfig], Optional[dict]]:
    raw_df = read_csv(source)
    return normalize_dataframe(raw_df, mapping=mapping, infer_mapping=infer_mapping)


def normalize_dataframe(
    df: pd.DataFrame,
    mapping: Optional[MappingConfig] = None,
    infer_mapping: bool = True,
) -> Tuple[pd.DataFrame, Optional[MappingConfig], Optional[dict]]:
    suggested = None

    if not needs_mapping(df) and is_canonical(df):
        normalized = ensure_canonical_columns(df)
        return normalized, None, suggested

    if mapping is None:
        if not infer_mapping:
            raise ValueError("Mapping required to normalize this dataset")
        suggested = suggest_mapping(df)
        mapping = MappingConfig.from_dict(suggested)

    normalized = apply_mapping(df, mapping)
    return normalized, mapping, suggested


def export_dataframe(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
