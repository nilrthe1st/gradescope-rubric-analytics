#!/usr/bin/env python3
"""Generate a synthetic rubric dataset for demos.

Usage:
    python tools/generate_synthetic.py --template data/sample_truth.csv --output data/synthetic_class.csv --students 80 --seed 42

The generator keeps the same exam IDs, rubric items, and topics as the template
but synthesizes students, rows, and points with some persistence, improvement,
and correlated mistakes.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd

REQUIRED_COLS = ["student_id", "exam_id", "question_id", "rubric_item", "points_lost"]
OPTIONAL_COLS = ["topic"]


def _validate_template(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        raise ValueError(f"Template missing required columns: {', '.join(missing)}")
    return df


def _choose_correlated_items(rubric_items: List[str]) -> Tuple[str, str]:
    if len(rubric_items) < 2:
        return rubric_items[0], rubric_items[0]
    rng = np.random.default_rng()
    a, b = rng.choice(rubric_items, size=2, replace=False)
    return str(a), str(b)


def _pick_question_ids(template: pd.DataFrame) -> List[str]:
    questions = list(template["question_id"].dropna().astype(str).unique())
    if not questions:
        return ["Q1"]
    return questions


def generate_synthetic_dataset(
    template_path: Path,
    output_path: Path,
    n_students: int = 80,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    template = pd.read_csv(template_path)
    template = _validate_template(template)

    exams = list(template["exam_id"].dropna().astype(str).unique())
    rubric_items = list(template["rubric_item"].dropna().astype(str).unique())
    topics_map = template.groupby("rubric_item")["topic"].agg(lambda s: s.mode().iat[0] if not s.mode().empty else "").to_dict()
    question_ids = _pick_question_ids(template)

    if not exams or not rubric_items:
        raise ValueError("Template must contain at least one exam and one rubric_item")

    correlated_a, correlated_b = _choose_correlated_items(rubric_items)
    base_probs = template["rubric_item"].value_counts(normalize=True).reindex(rubric_items, fill_value=1 / len(rubric_items))

    students = [f"Student_{i:03d}" for i in range(1, n_students + 1)]
    rows = []
    persistent_students = set(rng.choice(students, size=max(4, n_students // 6), replace=False))
    improving_students = set(rng.choice(students, size=max(4, n_students // 5), replace=False))

    for student in students:
        persistent_item = rng.choice(rubric_items)
        for exam_idx, exam_id in enumerate(exams):
            # base mistakes per exam per student
            mistakes = max(1, rng.poisson(2))
            for _ in range(mistakes):
                # start with base distribution
                item = rng.choice(rubric_items, p=base_probs.values)

                # correlated pair boost
                if item == correlated_a and rng.random() < 0.35:
                    rows.append(
                        {
                            "student_id": student,
                            "exam_id": exam_id,
                            "question_id": rng.choice(question_ids),
                            "rubric_item": correlated_b,
                            "topic": topics_map.get(correlated_b, ""),
                            "points_lost": float(max(0.5, rng.normal(1.5, 0.5))),
                        }
                    )

                # persistence: keep repeating the same item for flagged students
                if student in persistent_students and rng.random() < 0.6:
                    item = persistent_item

                # improvement: later exams reduce probability of points lost
                improvement_factor = 0.9 ** exam_idx if student in improving_students else 1.0
                points = float(max(0.25, rng.normal(2.0 * improvement_factor, 0.8)))
                if student in improving_students and rng.random() < 0.25:
                    points *= 0.5

                rows.append(
                    {
                        "student_id": student,
                        "exam_id": exam_id,
                        "question_id": rng.choice(question_ids),
                        "rubric_item": item,
                        "topic": topics_map.get(item, ""),
                        "points_lost": points,
                    }
                )

            # occasional noise row
            if rng.random() < 0.1:
                noise_item = rng.choice(rubric_items)
                rows.append(
                    {
                        "student_id": student,
                        "exam_id": exam_id,
                        "question_id": rng.choice(question_ids),
                        "rubric_item": noise_item,
                        "topic": topics_map.get(noise_item, ""),
                        "points_lost": float(max(0.1, rng.exponential(0.5))),
                    }
                )

    result = pd.DataFrame(rows)
    result = result.sample(frac=1, random_state=seed).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False)
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic rubric dataset for demos")
    parser.add_argument("--template", type=Path, default=Path("data/sample_truth.csv"), help="Path to canonical template CSV")
    parser.add_argument("--output", type=Path, default=Path("data/synthetic_class.csv"), help="Where to write synthetic CSV")
    parser.add_argument("--students", type=int, default=80, help="Number of synthetic students")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args(list(argv) if argv is not None else None)

    generate_synthetic_dataset(args.template, args.output, n_students=args.students, seed=args.seed)
    print(f"Synthetic dataset written to {args.output}")


if __name__ == "__main__":
    main()
