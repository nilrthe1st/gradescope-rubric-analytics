from pathlib import Path

import pandas as pd

from tools.generate_synthetic import generate_synthetic_dataset


def test_generate_synthetic_dataset_creates_expected_columns(tmp_path: Path):
    template = tmp_path / "template.csv"
    template_df = pd.DataFrame(
        [
            {"student_id": "s1", "exam_id": "Exam1", "question_id": "Q1", "rubric_item": "ItemA", "points_lost": 2, "topic": "ConceptA"},
            {"student_id": "s2", "exam_id": "Exam2", "question_id": "Q2", "rubric_item": "ItemB", "points_lost": 1, "topic": "ConceptB"},
        ]
    )
    template_df.to_csv(template, index=False)

    output = tmp_path / "synthetic.csv"
    result = generate_synthetic_dataset(template, output, n_students=12, seed=123)

    assert output.exists()
    required_cols = {"student_id", "exam_id", "question_id", "rubric_item", "points_lost", "topic"}
    assert required_cols.issubset(result.columns)

    exams = result["exam_id"].unique()
    assert set(exams) == {"Exam1", "Exam2"}

    student_ids = set(result["student_id"].unique())
    assert len(student_ids) == 12
    assert any(s.startswith("Student_") for s in student_ids)

    # At least one row per student per exam on average
    assert len(result) >= 12 * len(exams)
