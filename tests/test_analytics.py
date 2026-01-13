import pytest

from gradescope_analytics.metrics import (
    category_breakdown,
    overall_summary,
    rubric_item_stats,
    score_distribution,
    student_summary,
)


def test_overall_summary(sample_df):
    summary = overall_summary(sample_df)
    assert summary["students"] == 3
    assert summary["assignments"] == 1
    assert pytest.approx(summary["avg_score"], rel=1e-3) == 6.0


def test_rubric_item_stats(sample_df):
    stats = rubric_item_stats(sample_df)
    correctness = stats[stats["rubric_item"] == "Correctness"].iloc[0]
    assert correctness["count"] == 3
    assert pytest.approx(correctness["avg_score"], rel=1e-3) == 8.0


def test_category_breakdown(sample_df):
    categories = category_breakdown(sample_df)
    tech = categories.iloc[0]
    assert tech["category"] == "Technical"
    assert tech["items"] == 2
    assert pytest.approx(tech["score_sum"], rel=1e-3) == 36.0


def test_student_summary_order(sample_df):
    order = ["Project 1"]
    students = student_summary(sample_df, assignment_order=order)
    assert list(students["assignment"].unique()) == order


def test_score_distribution(sample_df):
    dist = score_distribution(sample_df, bins=4)
    assert not dist.empty
    assert set(dist.columns) == {"bin", "count"}
