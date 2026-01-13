# Codex Audit Report

## 1) Executive summary
- Built a Streamlit-based rubric analytics app with canonical schema normalization, invariants, metrics (summaries, persistence, distributions), and plots, backed by a reusable `gradescope_analytics` Python package. Added Docker/compose scaffolding and GitHub Actions CI for pytest.
- Current status: app launches (headless smoke on port 8503 succeeded), all tests pass (18/18), CI workflow present, Dockerfile/compose present (Docker not available locally to build).
- Known limitations: no anonymization of uploads; mapping relies on header heuristics; chart export depends on Plotly/kaleido availability; Docker build unverified locally due to missing Docker binary.

## 2) File tree + highlights (depth ≤3)
- `app/app.py` – primary Streamlit UI (upload/mapping/analytics tabs). Duplicate legacy entrypoints exist (`streamlit_app.py`, `app/analytics.py` etc.); `app/app.py` is the intended one.
- `src/gradescope_analytics/` – library modules: `io` (load/normalize), `mapping` (mapping config/validation), `invariants` (schema/data checks), `metrics` (summaries, persistence, error aggregations), `plots` (Plotly charts).
- `data/sample_truth.csv` – canonical sample dataset with planted rubric patterns across three exams.
- `tests/` – pytest coverage for mapping/io/metrics/invariants with known-answer assertions.
- `Dockerfile` – Streamlit container image, exposes 8501, installs requirements, runs `app/app.py`.
- `docker-compose.yml` – builds local image, binds `./` and sets `PYTHONPATH=/app/src`.
- `.github/workflows/ci.yml` – CI running pytest on push/PR with Python 3.12.
- `CHANGELOG.md` – running changelog.
- `README.md` – setup, Docker, CI instructions.
- `streamlit_app.py` – older/alternate entrypoint (keep or remove; current app uses `app/app.py`).

## 3) Git audit
- Commands run: `git status` (clean), `git remote -v` (origin https://github.com/nilrthe1st/gradescope-rubric-analytics.git), `git branch --show-current` (main), `git log --oneline --decorate -n 30` (see below).
- Commit sequence (newest→old):
  - 03a4c3e Polish and document MVP
  - 623621e Add Docker and CI for rubric analytics
  - 01c4ec0 Add Streamlit UI for rubric analytics
  - 4d4d98e Add analytics core with truth dataset tests
  - ccbdd93 Implement Streamlit option A architecture
  - 0bbb182 Add Streamlit rubric analytics app
  - 70bef55 Initial commit
- Remote/push status: earlier a push failed before remote was set; remote `origin` is now configured and pushes are succeeding. Last pushed commit is `03a4c3e` on `main` at `origin/main`.

## 4) Tests and verification
- Command run: `./.venv/bin/python -m pytest -q` → **18 passed**.
- Module coverage (by tests):
  - `io`/`mapping`: normalization with/without mapping, optional topic, rejection of negative/non-numeric points.
  - `metrics`: overall summary, rubric stats, exam breakdown, student summary ordering, score distribution, `summarize_errors` totals and means, `error_by_exam` aggregation, `compute_persistence` cohorts/repeats (both synthetic and truth dataset cases).
  - `invariants`: required columns present, missing identifiers detected, non-numeric/negative `points_lost` flagged.
- Explicit assertions include: `summarize_errors` totals for Arrow direction and Wrong nucleophile, `compute_persistence` cohort_size/repeated/rate (arrow 2→2 rate 1.0; wrong nucleophile 0), invariants pass on sample truth and fail on negative points.

## 5) Runbook / smoke test
- Create venv:
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  ```
- Install deps:
  ```bash
  pip install -r requirements.txt
  ```
- Run tests:
  ```bash
  PYTHONPATH=src pytest
  ```
- Run Streamlit app:
  ```bash
  PYTHONPATH=src streamlit run app/app.py
  ```
- Smoke test performed: headless Streamlit start on port 8503 (`--server.headless true --server.port 8503 --server.address 127.0.0.1 --server.fileWatcherType none`) started and stopped cleanly; no tracebacks in `/tmp/streamlit_smoke.log` (only standard usage banner). Default Streamlit banner appears; no warnings observed.

## 6) CI and Docker
- CI: `.github/workflows/ci.yml` checks out code, sets up Python 3.12, installs `requirements.txt`, runs `pytest` with `PYTHONPATH=src` on push and PR.
- Docker: `Dockerfile` uses `python:3.12-slim`, sets `PYTHONPATH=/app/src`, installs requirements, exposes 8501, runs `streamlit run app/app.py --server.address 0.0.0.0 --server.port 8501`.
- Compose: `docker-compose.yml` defines `app` service (builds current context, maps 8501:8501, mounts repo, sets `PYTHONPATH=/app/src`).
- Local Docker build: **not executed** because `docker` binary is unavailable in this environment (`zsh: command not found: docker`). Recommended verification command where Docker exists:
  ```bash
  docker build -t gradescope-rubric-analytics .
  docker run -p 8501:8501 gradescope-rubric-analytics
  ```

## 7) Data handling + privacy
- Uploads handled via Streamlit `file_uploader`; data is processed in-memory. Persistence tab allows explicit saving to CSV under `data/` when the user clicks save.
- No anonymization or PII scrubbing is implemented; users are warned to use anonymized exports. Recommendation: add optional hashing/redaction for student identifiers before processing.

## 8) Risks / TODOs
1. Mapping heuristics: relies on header keyword matching; edge cases may mis-map. Add preview validation and manual override persistence.
2. Exam ordering: defaults lexicographic; manual order via UI exists, but persistence calculations assume a single "first" exam; consider per-student first attempt logic.
3. Plot exports: Plotly PNG export requires kaleido; in constrained environments this may fail—surface clearer UI messaging.
4. Docker unverified locally: build not run here; validate on a machine with Docker and optionally add a lightweight CI build job.
5. Privacy: no anonymization; add hashing/redaction option and document retention for saved files.

## 9) Duplicate/legacy entrypoints
- `app/app.py` is the canonical Streamlit entrypoint. `streamlit_app.py` and `app/analytics.py` appear legacy; consolidate or remove to avoid confusion.
