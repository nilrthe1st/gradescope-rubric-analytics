# Synthetic Demo Data

Use the synthetic dataset to demo instructor analytics without real student data.

## How to generate
- CLI: `python tools/generate_synthetic.py --template data/sample_truth.csv --output data/synthetic_class.csv --students 80 --seed 42`
- The script preserves exam IDs, rubric items, and topics from the template and synthesizes:
  - Persistent mistakes for some students
  - Improvements over later exams
  - Correlated rubric items that co-occur
  - Random noise rows
- Student IDs are anonymized aliases (`Student_001`, …).

## How to use in the app
- Open the sidebar and toggle **Use synthetic demo dataset**.
- If `data/synthetic_class.csv` is missing, it will be generated automatically from `data/sample_truth.csv`.
- A banner in the app labels synthetic mode clearly.

## Messaging to instructors
- Be explicit: “This view uses synthetic data for demonstration; no student records are included.”
- Avoid implying performance insights are real; keep screenshots watermarked or accompanied by the above disclaimer.
- Use synthetic mode for UI tours, not for decision-making or reports.
