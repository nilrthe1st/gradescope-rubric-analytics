1) Executive summary
- Exceptions hit: `ModuleNotFoundError: No module named 'app.ui'`; `ImportError: attempted relative import with no known parent package` / `'app' is not a package`; `SyntaxError: f-string: single '}' not allowed`; `NameError: name 'font' is not defined`; `AttributeError: module 'streamlit' has no attribute 'experimental_rerun'`; UI showed literal placeholders `{indicator} {step.title} {step.description}`; zsh reported `no matches found: stepper(steps: List[Step]):` and `unknown file attribute: <`.
- Root causes: Streamlit entrypoint lacked an importable package path while pytest set `PYTHONPATH=src`; CSS was emitted via f-strings so bare `{}` braces were parsed as expressions and missing identifiers; Streamlit version exposes `st.rerun()` (not `experimental_rerun`); stepper markup was a plain triple-quoted string without `f` prefix; shell treated pasted Python/HTML as glob/attribute syntax rather than code.
- Fix strategy: normalize imports with explicit `sys.path` priming and consistent `PYTHONPATH`; move global CSS to a `string.Template` (no f-string); add rerun compatibility helper that prefers `st.rerun()`; make the stepper block an f-string only; avoid pasting code into zsh and use heredocs/editor instead.

2) Evidence collected (MANDATORY)
- `git status -sb`: `## main...origin/main`
- `git log --oneline --decorate -n 10`: `cbcbf77 Fix stepper rendering and Streamlit rerun compatibility`; `3a38a41 Document runtime fix technical summary`; `de93b32 Fix Streamlit imports and CSS f-string issues`; `e11ccd7 Document UI redesign technical summary`; `32f04fa Document UI tour and screenshot guide`; `d07b640 Polish dashboard charts and tooltips`; `422d50c Add guided ingestion flow and drilldowns`; `32af2ea Add themed UI shell and layout helpers`; `4b5bbfb Fix Streamlit Arrow serialization for invariant detail column`; `7c7656c Clean up entrypoints and harden pandas operations`.
- `git diff --stat HEAD~5..HEAD`: `README.md | 30 ++++++++++++----------`; `app/app.py | 18 ++++++++++---`; `app/ui/shell.py | 117 +++++++++++++++++++++++++++++++++++++++++++++++------------------------------------`; `docs/RUNTIME_FIX_TECH_SUMMARY.md | 29 +++++++++++++++++++++`; `docs/UI_GUIDE.md | 46 +++++++++++++++++++++++++++++++++`; `docs/UI_REDESIGN_TECH_SUMMARY.md | 72 +++++++++++++++++++++++++++++++++++++++++++++++++++` (244 insertions, 68 deletions).
- `grep -R "experimental_rerun" -n app app/ui || true`: `app/app.py:36:    elif hasattr(st, "experimental_rerun"):`
- `grep -R "st.rerun" -n app app/ui || true`: `app/app.py:35:        st.rerun()`
- `grep -R "f\"" -n app/ui/shell.py || true`: f-strings remain only where safe (labels, kpis, stepper) e.g. `app/ui/shell.py:165`, `172`, `178`, `186`, `204`, `221`, `233`.
- `grep -R "CSS_TEMPLATE" -n app/ui/shell.py || true`: `app/ui/shell.py:20:CSS_TEMPLATE = """` and `app/ui/shell.py:141:GLOBAL_CSS = string.Template(CSS_TEMPLATE).safe_substitute(...)`.

3) File-by-file changes (MANDATORY)
- `app/app.py`: Added `_rerun()` helper that prefers `st.rerun()` and falls back to `experimental_rerun`, and routed the demo-mode button through it; kept the existing `sys.path` priming for `ROOT` and `SRC`. Necessary to align with the Streamlit version and prevent AttributeError while still supporting older APIs. Alternatives considered: direct `st.rerun()` (would break older releases) or vendoring a custom rerun flag (overkill), so the helper was chosen for compatibility.
- `app/ui/shell.py`: Kept global CSS in a `string.Template` (not an f-string) to avoid brace parsing, and converted the stepper markup block to an f-string so `{indicator}` / `{step.title}` / `{step.description}` interpolate. Necessary to resolve SyntaxError/NameError from CSS braces and to render the stepper labels instead of placeholders. Alternatives considered: `str.format` for the stepper (less readable) and Jinja (extra dependency); f-string for the small HTML block was simplest.

4) Import/path resolution
- Streamlit runs `app/app.py` as a script with CWD at repo root, so it does not treat `app/` as a package unless the directory is on `sys.path` and `__init__.py` exists. Pytest worked because `PYTHONPATH=src` provided `gradescope_analytics`, but Streamlit still needed `ROOT` and `SRC` injected.
- Chosen strategy: prepend `ROOT` (repo) and `SRC` to `sys.path` at startup, keeping `app/` importable without relying on implicit packages.
- Interaction with `PYTHONPATH=src`: ensures analytics modules resolve uniformly in tests and Streamlit; `sys.path` shim handles the `app` module itself.
- Final run command:
  cd /Users/nilroy/Documents/gradescope-rubric-analytics
  source .venv/bin/activate
  PYTHONPATH=src streamlit run app/app.py --browser.gatherUsageStats false

5) CSS/f-string resolution
- Bare `{}` in f-strings are parsed as expressions, so CSS braces triggered `SyntaxError: f-string: single '}' not allowed` and missing identifiers caused `NameError` (e.g., `{font}`) when emitted via f-string.
- Global CSS now lives in a plain triple-quoted string wrapped by `string.Template.safe_substitute`, so braces remain literal and only named tokens are substituted.
- Only the small stepper HTML block is an f-string, which is safe because it carries no CSS braces—just indicator/title/description placeholders.

6) Streamlit rerun compatibility
- Primary API now `st.rerun()`; `_rerun()` helper falls back to `st.experimental_rerun` if needed. This matches the installed Streamlit version while retaining backward compatibility.

7) UI symptom fix: Stepper placeholders
- Cause: the stepper’s `st.markdown` block lacked an `f` prefix, so `{indicator}`, `{step.title}`, and `{step.description}` rendered literally.
- Fix: converted that block to an f-string; the stepper now shows real labels (e.g., `✔ Upload`, `➜ Map`).

8) “unknown file attribute” / zsh errors
- `no matches found: stepper(steps: List[Step]):` and `unknown file attribute: <` arose because Python/HTML snippets were pasted into zsh; the shell treated braces/angle brackets as globs or file attributes.
- Rule: do not paste Python/HTML into the shell. Use the editor or a heredoc instead:
  python3 - <<'PY'
  print("edit files in an editor; this is only for deliberate one-offs")
  PY

9) Verification evidence (MANDATORY)
- Tests: `PYTHONPATH=src /Users/nilroy/Documents/gradescope-rubric-analytics/.venv/bin/python -m pytest -q` → 18 passed in 0.10s (exit 0).
- Smoke: `PYTHONPATH=src /Users/nilroy/Documents/gradescope-rubric-analytics/.venv/bin/python -m streamlit run app/app.py --server.headless true --server.port 8505 --server.address 127.0.0.1 --browser.gatherUsageStats false` for ~8s → No tracebacks observed; app served on http://127.0.0.1:8505 then cleanly stopped.

10) Regression risks / TODOs
- sys.path shim is fragile if new entrypoints skip `_init_state` and import ordering; consider packaging or adding `__init__.py`.
- Streamlit API drift (rerun signature or location) could reappear; recheck on upgrades.
- CSS templating must stay out of f-strings; future style work should continue using `Template` or raw strings to avoid brace parsing.
- Stepper HTML interpolates unescaped titles/descriptions; sanitize if user-provided content is introduced.
- Python 3.14 locally vs possible CI version differences could surface syntax/stdlib gaps; align runtime versions in CI.
