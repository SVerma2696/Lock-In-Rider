"""
Keeps the two lists of libraries in step: requirements.txt (used by the
release build and CI) and pyproject.toml (the grouped list). It also
checks the version number is the same everywhere it appears.
"""

import re
import tomllib
from pathlib import Path

import lock_in

ROOT = Path(__file__).resolve().parent.parent


def _name(requirement: str) -> str:
    return re.split(r"[<>=!~;\[ ]", requirement.strip(), maxsplit=1)[0].lower()


def _requirements_txt() -> dict[str, str]:
    out = {}
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out[_name(line)] = line.replace(" ", "")
    return out


def _pyproject() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_requirements_txt_matches_pyproject():
    project = _pyproject()["project"]
    grouped = list(project["dependencies"])
    for group in ("camera", "claude", "test"):
        grouped += project["optional-dependencies"][group]
    wanted = {_name(r): r.replace(" ", "").replace("'", '"') for r in grouped}
    wanted.pop("pytest-cov")  # only CI's coverage job needs it
    have = {k: v.replace("'", '"') for k, v in _requirements_txt().items()}
    assert have == wanted


def test_windows_only_libraries_stay_windows_only():
    for name, line in _requirements_txt().items():
        if name in {"pywin32", "winotify"}:
            assert 'sys_platform=="win32"' in line.replace("'", '"')


def test_the_version_is_read_from_one_place():
    assert _pyproject()["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "lock_in.__version__"
    }
    assert re.fullmatch(r"\d+\.\d+\.\d+", lock_in.__version__)
