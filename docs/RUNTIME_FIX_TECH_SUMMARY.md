# Runtime Fix Technical Summary

## 1) Executive summary
- Failures observed: `ModuleNotFoundError: No module named 'app.ui'; 'app' is not a package` when running Streamlit; `SyntaxError`/`NameError: name 'font' is not defined` from CSS braces being interpreted inside an f-string.
- Root causes: Streamlit runs from the repo root without `app` on the import path; CSS was wrapped in an f-string so single `{`/`}` braces were parsed as Python expressions.
- Fixes: Added robust path setup (prepend repo root and `src` to `sys.path`, import UI via `app.ui`); replaced f-string CSS with `string.Template` substitution to emit literal braces safely.

## 2) File-by-file changes
- `app/app.py`: Consolidated path handling (prepend ROOT and SRC to `sys.path`), removed redundant app-dir shim, and imported UI helpers via `from app.ui ...` so Streamlit recognizes `app` as a package. Rationale: make imports deterministic for both pytest and `streamlit run`. Alternatives considered: adding a separate launcher script or modifying run commands; rejected in favor of minimal sys.path shim.
- `app/ui/shell.py`: Replaced f-string CSS block with `string.Template` (`CSS_TEMPLATE` + `safe_substitute`) to avoid brace interpolation errors; kept design tokens and CSS intact. Rationale: eliminate SyntaxError/NameError while retaining variable substitution. Alternatives: manual brace escaping or `.format_map`; Template is simpler and safer for braces.

## 3) Import/path resolution
- Difference: `pytest` uses `PYTHONPATH=src` from config, but `streamlit run app/app.py` executes from repo root and does not auto-treat `app/` as a package.
- Final strategy: At startup, prepend repo ROOT and `src` to `sys.path` (only if absent). UI imports use `from app.ui ...`. This works consistently for both pytest and Streamlit.
- Recommended run command: `PYTHONPATH=src streamlit run app/app.py --browser.gatherUsageStats false`

## 4) CSS/f-string resolution
- Cause: CSS defined in an f-string, so `{`/`}` braces were parsed, triggering `SyntaxError` and `NameError` (e.g., `font`).
- Fix: Removed f-string usage; use `string.Template` with `$TOKEN` placeholders and `safe_substitute` to inject colors while emitting literal braces.
- Confirmation: No remaining f-strings contain CSS braces; CSS is emitted from Template.

## 5) Verification evidence
- Pytest: `PYTHONPATH=src .venv/bin/python -m pytest -q` → 18 passed, no failures.
- Streamlit smoke (8s headless): `PYTHONPATH=src .venv/bin/python -m streamlit run app/app.py --server.headless true --server.port 8505 --server.address 127.0.0.1 --browser.gatherUsageStats false` → started cleanly; no tracebacks observed (only optional Watchdog suggestion).

## 6) Regression risks / TODOs
1) Relying on `sys.path` mutation in `app/app.py`; if further entrypoints are added, keep path handling consistent or add a lightweight launcher.
2) Theme tokens live in code; if future dynamic theming is needed, consider externalizing to config.
3) Smoke test is short; for heavier datasets, consider a longer health check or add an automated e2e UI test.
