# Gradescope Rubric Analytics

Option A architecture (Streamlit-only) with all analytics in a reusable Python package.

## Features
- Upload Gradescope-style rubric CSVs or use the bundled sample truth dataset.
- Mapping wizard when headers are non-canonical; canonical schema is `student_id, student_name, assignment, rubric_item, category, score, max_score, comment`.
- Tabs: Overview (stats, charts, tables), Persistence (save/load normalized data), Data Quality (invariant checks).
- Export buttons for tables and charts (CSV + PNG).
- Exam ordering control (lexicographic by default).

## Quickstart
1. Create and activate a virtualenv (recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit app:
   ```bash
   PYTHONPATH=src streamlit run app/app.py
   ```
4. In the sidebar, upload a CSV or click **Load sample truth**.

## Testing
```bash
PYTHONPATH=src pytest
```

## Project layout
- `src/gradescope_analytics/` – library code (io, mapping, invariants, metrics, plots)
- `app/app.py` – Streamlit UI that consumes the library
- `data/sample_truth.csv` – canonical sample dataset
- `tests/` – pytest suite for the library

## Optional: Docker
Build and run locally:
```bash
docker compose up --build
```

## Notes
- All analytics live in the library; the UI orchestrates only.
- Persistence tab writes normalized CSVs under `data/` by default.
