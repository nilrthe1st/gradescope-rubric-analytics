from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture()
def sample_truth_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sample_truth.csv"


@pytest.fixture()
def sample_df(sample_truth_path) -> pd.DataFrame:
    return pd.read_csv(sample_truth_path)
