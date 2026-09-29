"""
storage/json_store.py
=====================
Saving and reading whole files safely. See storage/__init__.py for why.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

# On Windows another program (a virus scanner, OneDrive) can hold the real
# file open for a moment, which makes the final swap fail. A few quick
# tries fix that almost every time.
_REPLACE_TRIES = 5
_REPLACE_WAIT_SECONDS = 0.05


def atomic_write_text(path: Path, text: str) -> None:
    """Save `text` to `path` so a crash can never leave it half-written.

    The words go into a spare file in the same folder first. Only once
    that spare file is completely written and flushed to the disk does it
    replace the real file, in one step. If anything goes wrong, the spare
    file is removed and the real file is left exactly as it was.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as file:
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        _replace(temp_path, path)
    except BaseException:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def atomic_write_json(
    path: Path, data: Any, *, indent: int | None = 2, ensure_ascii: bool = False
) -> None:
    """Save `data` as JSON, safely. The words in the file come out exactly
    as a plain json.dumps() with the same settings would write them."""
    atomic_write_text(path, json.dumps(data, indent=indent, ensure_ascii=ensure_ascii))


def read_json(path: Path) -> Any | None:
    """The JSON in `path`, or None if the file is missing, unreadable, or
    not valid JSON. Never raises for a bad file -- a broken file should
    mean "start fresh", not "the app won't open"."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _replace(source: Path, target: Path) -> None:
    for attempt in range(_REPLACE_TRIES):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == _REPLACE_TRIES - 1:
                raise
            time.sleep(_REPLACE_WAIT_SECONDS)
