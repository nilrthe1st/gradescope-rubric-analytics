from pathlib import Path

import pytest

from gradescope_analytics.security import build_export_path, sanitize_filename


def test_sanitize_filename_removes_traversal_and_weird_chars():
    with pytest.raises(ValueError):
        sanitize_filename("../secret.csv")
    assert sanitize_filename("/abs/path.png") == "abs_path.png"
    assert sanitize_filename("report..zip") == "report.zip"
    assert sanitize_filename("bad name!.csv") == "bad_name_.csv"
    assert sanitize_filename("") == "export"


def test_build_export_path_guard(tmp_path: Path):
    base = tmp_path / "exports"
    base.mkdir()
    safe_path = build_export_path(base, "report.csv")
    assert safe_path.parent == base
    with pytest.raises(ValueError):
        sanitize_filename("../escape.csv")
