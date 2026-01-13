import pandas as pd
import pytest

from app.sample_data import load_sample_dataframe


@pytest.fixture()
def sample_df():
    return load_sample_dataframe()


@pytest.fixture()
def sample_csv_path(tmp_path):
    df = load_sample_dataframe()
    file_path = tmp_path / "sample.csv"
    df.to_csv(file_path, index=False)
    return file_path
