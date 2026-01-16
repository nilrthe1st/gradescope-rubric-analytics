import pandas as pd
import pytest

from gradescope_analytics.metrics import (
    compute_persistence,
    error_by_exam,
    exam_breakdown,
    group_comparison,
    overall_summary,
    rubric_item_stats,
    score_distribution,
    summarize_errors,
    student_summary,
)


def test_overall_summary(sample_df):
    summary = overall_summary(sample_df)
    assert summary["students"] == 6
    assert summary["exams"] == 3
    assert pytest.approx(summary["avg_points_lost"], rel=1e-3) == 14.5 / 11


def test_rubric_item_stats(sample_df):
    stats = rubric_item_stats(sample_df)
    arrow = stats[stats["rubric_item"] == "Arrow direction"].iloc[0]
    assert pytest.approx(arrow["total_points_lost"], rel=1e-3) == 7.0


def test_exam_breakdown(sample_df):
    exams = exam_breakdown(sample_df)
    assert exams.iloc[0]["exam_id"] == "Exam1"
    assert pytest.approx(exams.iloc[0]["total_points_lost"], rel=1e-3) == 5.0


def test_student_summary_order(sample_df):
    order = ["Exam1", "Exam2", "Exam3"]
    students = student_summary(sample_df, exam_order=order)
    assert list(students["exam_id"].unique()) == order


def test_score_distribution(sample_df):
    dist = score_distribution(sample_df, bins=3)
    assert not dist.empty
    assert set(dist.columns) == {"bin", "count"}


def test_summarize_errors(sample_df):
    summary = summarize_errors(sample_df)
    arrow = summary[summary["rubric_item"] == "Arrow direction"].iloc[0]
    assert arrow["count_rows"] == 5
    assert arrow["students_affected"] == 3
    assert pytest.approx(arrow["points_lost_total"], rel=1e-3) == 7.0
    assert pytest.approx(arrow["points_lost_mean"], rel=1e-3) == 7.0 / 5

    wrong_nuc = summary[summary["rubric_item"] == "Wrong nucleophile"].iloc[0]
    assert wrong_nuc["count_rows"] == 2
    assert wrong_nuc["students_affected"] == 1
    assert pytest.approx(wrong_nuc["points_lost_total"], rel=1e-3) == 3.5

    total_points = sample_df["points_lost"].sum()
    assert pytest.approx(summary["points_lost_total"].sum(), rel=1e-9) == total_points


def test_error_by_exam_long_format():
    df = pd.DataFrame(
        [
            {"student_id": "s1", "exam_id": "Exam1", "question_id": "Q1", "rubric_item": "A", "points_lost": 1, "topic": "T"},
            {"student_id": "s2", "exam_id": "Exam1", "question_id": "Q2", "rubric_item": "B", "points_lost": 2, "topic": "T"},
            {"student_id": "s1", "exam_id": "Exam2", "question_id": "Q1", "rubric_item": "A", "points_lost": 3, "topic": "T"},
        ]
    )

    result = error_by_exam(df)
    assert set(result.columns) == {"exam_id", "rubric_item", "count_rows", "points_lost_total"}

    exam1_a = result[(result["exam_id"] == "Exam1") & (result["rubric_item"] == "A")].iloc[0]
    assert exam1_a["count_rows"] == 1
    assert exam1_a["points_lost_total"] == 1

    exam2_a = result[(result["exam_id"] == "Exam2") & (result["rubric_item"] == "A")].iloc[0]
    assert exam2_a["points_lost_total"] == 3


def test_group_comparison_section_and_ta():
    df = pd.DataFrame(
        [
            {"student_id": "s1", "exam_id": "Exam1", "question_id": "Q1", "rubric_item": "A", "points_lost": 1, "topic": "T", "section_id": "S1", "ta_id": "TA1"},
            {"student_id": "s2", "exam_id": "Exam1", "question_id": "Q2", "rubric_item": "B", "points_lost": 2, "topic": "T", "section_id": "S2", "ta_id": "TA1"},
            {"student_id": "s3", "exam_id": "Exam2", "question_id": "Q1", "rubric_item": "A", "points_lost": 3, "topic": "T", "section_id": "S1", "ta_id": "TA2"},
        ]
    )

    sections = group_comparison(df, "section_id")
    assert set(sections.columns) == {
        "section_id",
        "rows",
        "students",
        "total_points_lost",
        "avg_points_per_student",
        "avg_points_per_row",
    }
    assert sections.iloc[0]["section_id"] == "S1"

    tas = group_comparison(df, "ta_id")
    assert "TA1" in tas["ta_id"].values
    assert tas[tas["ta_id"] == "TA1"].iloc[0]["total_points_lost"] == 3


def test_group_comparison_missing_column_returns_empty(sample_df):
    missing = group_comparison(sample_df, "section_id")
    assert missing.empty


def test_compute_persistence_with_order():
    df = pd.DataFrame(
        [
            {"student_id": "s1", "exam_id": "Exam1", "question_id": "Q1", "rubric_item": "A", "points_lost": 1, "topic": ""},
            {"student_id": "s1", "exam_id": "Exam2", "question_id": "Q1", "rubric_item": "A", "points_lost": 2, "topic": ""},
            {"student_id": "s2", "exam_id": "Exam1", "question_id": "Q1", "rubric_item": "A", "points_lost": 0.5, "topic": ""},
            {"student_id": "s2", "exam_id": "Exam2", "question_id": "Q1", "rubric_item": "B", "points_lost": 1, "topic": ""},
            {"student_id": "s3", "exam_id": "Exam1", "question_id": "Q1", "rubric_item": "B", "points_lost": 1, "topic": ""},
            {"student_id": "s3", "exam_id": "Exam2", "question_id": "Q1", "rubric_item": "B", "points_lost": 1.5, "topic": ""},
        ]
    )

    result = compute_persistence(df, exam_order=["Exam1", "Exam2"])
    assert set(result.columns) == {"rubric_item", "cohort_size", "repeated", "persistence_rate"}

    row_a = result[result["rubric_item"] == "A"].iloc[0]
    assert row_a["cohort_size"] == 2
    assert row_a["repeated"] == 1
    assert pytest.approx(row_a["persistence_rate"], rel=1e-9) == 0.5

    row_b = result[result["rubric_item"] == "B"].iloc[0]
    assert row_b["cohort_size"] == 1
    assert row_b["repeated"] == 1
    assert pytest.approx(row_b["persistence_rate"], rel=1e-9) == 1.0


def test_compute_persistence_truth_dataset(sample_df):
    result = compute_persistence(sample_df)
    arrow = result[result["rubric_item"] == "Arrow direction"].iloc[0]
    assert arrow["cohort_size"] == 2
    assert arrow["repeated"] == 2
    assert arrow["persistence_rate"] == 1.0

    wrong = result[result["rubric_item"] == "Wrong nucleophile"].iloc[0]
    assert wrong["cohort_size"] == 0
    assert wrong["repeated"] == 0
    assert wrong["persistence_rate"] == 0
