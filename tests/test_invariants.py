import pandas as pd

from gradescope_analytics import invariants


def test_run_invariants_pass(sample_df):
    results = invariants.run_invariants(sample_df)
    assert all(res["ok"] for res in results)


def test_run_invariants_flags_missing_ids(sample_df):
    bad = sample_df.copy()
    bad.loc[0, "student_id"] = ""
    results = invariants.run_invariants(bad)
    missing_row = next(res for res in results if res["name"] == "missing_identifiers")
    assert missing_row["ok"] is False
    assert missing_row["detail"] == 1


def test_run_invariants_flags_negative_points(sample_df):
    bad = sample_df.copy()
    bad.loc[0, "points_lost"] = -1
    results = invariants.run_invariants(bad)
    neg_row = next(res for res in results if res["name"] == "negative_points_lost")
    assert neg_row["ok"] is False
