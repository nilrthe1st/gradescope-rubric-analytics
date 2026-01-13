# Gradescope Rubric Analytics

Option A architecture (Streamlit-only) with all analytics in a reusable Python package.

## Features
- Upload Gradescope-style rubric CSVs or use the bundled sample truth dataset.
- Canonical schema: `student_id, exam_id, question_id, rubric_item, points_lost` (+ optional `topic`).
- Mapping wizard appears when headers are non-canonical; mapping is required for every canonical field (topic optional). Mapping persists in session state.
- Tabs: Overview (stats, charts, tables), Persistence (save/load normalized data), Data Quality (invariant checks).
- Export buttons for tables and charts (CSV + PNG).
- Exam ordering control (lexicographic by default).

## Local development (venv)
> Recommended Python: **3.12** (matches CI). If using pyenv, set the version via `.python-version` or `pyenv local 3.12.0`.

1. Create and activate a virtualenv
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Run the Streamlit app (single supported entrypoint)
   ```bash
   PYTHONPATH=src streamlit run app/app.py
   ```
4. In the sidebar, upload a CSV or check **Use sample_truth.csv** to explore the bundled data.

## Testing
Run the library tests locally:
```bash
PYTHONPATH=src pytest
```

## Docker
Build and run the Streamlit app in a container:
```bash
docker build -t gradescope-rubric-analytics .
docker run -p 8501:8501 gradescope-rubric-analytics
```

Or use Compose (rebuilds when code changes thanks to the bind mount):
```bash
docker compose up --build
```

## CI
GitHub Actions (`.github/workflows/ci.yml`) runs `pytest` on each push and pull request using Python 3.12.

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
