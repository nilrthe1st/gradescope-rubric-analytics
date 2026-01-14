# UI Guide

A quick walkthrough of the redesigned Streamlit UI and how to capture screenshots for docs or demos.

## How to launch
- Activate your environment and install deps: `source .venv/bin/activate && pip install -r requirements.txt`.
- Run the app: `PYTHONPATH=src streamlit run app/app.py`.
- For a zero-input walkthrough, toggle **Demo mode** in the sidebar to load `data/sample_truth.csv`.

## Layout shell
- Left sidebar handles data source controls and optional exam ordering.
- Main area uses KPI cards, cards, and tabs for a SaaS-style dashboard.
- Global dark theme is defined in `.streamlit/config.toml` and `app/ui/shell.py` (CSS variables and gradients).

## Guided ingestion stepper
1) **Upload**: Upload a rubric CSV or enable Demo mode.
2) **Map**: If headers are non-canonical, the mapping wizard requests each canonical column (`student_id`, `exam_id`, `question_id`, `rubric_item`, `points_lost`, optional `topic`).
3) **Validate**: Invariants run on the normalized dataframe; status pills surface pass/fail.
4) **Explore**: Tabs unlock once validation completes.

## Overview tab
- KPI belt (rows, students, exams, rubric items, avg and total points lost).
- Top rubric items table with export.
- **Instructor summary** panel shows high-persistence rubric items, highest points lost, and suggested recitation topics (when a topic column exists).
- Drilldown: click a rubric item button to filter charts/tables; use **Reset filters** to clear.
- Charts: bar charts for counts and total points lost; download PNG buttons; normalized data preview with CSV export.

## Persistence tab
- Persistence table with cohort size and repeat rate, sortable and exportable.
- Heatmap of rubric occurrences by exam (counts), exportable as PNG; shows an info state if no data.

## Data Quality tab
- Invariant table with normalized `detail` column for Arrow-safe display.
- Schema (columns/dtypes) table for quick verification.
- Cleaning summary clarifies that normalization validates but does not drop rows.

## Screenshot checklist
- **Empty state**: load app with no data and show the welcome card; optionally click "Turn on demo mode".
- **Stepper + demo**: enable Demo mode and show steps 1–4 completed.
- **Overview**: capture KPI cards, top rubric table, instructor summary, charts, and drilldown filter applied.
- **Persistence**: heatmap and export controls visible.
- **Data Quality**: invariant table with pass/fail badges and schema table.

## Export helpers
- Every major table includes a CSV download button.
- Charts include PNG export buttons (kaleido required; already in requirements).
