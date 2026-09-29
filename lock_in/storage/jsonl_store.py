"""
storage/jsonl_store.py
======================
Files with one JSON entry per line (focus history, observations).

Adding one entry is quick: it's written onto the end of the file. If the
app crashed in the middle of adding a line last time, the file ends with
a broken half-line. `append_jsonl` notices that and starts the new entry
on a fresh line, so only the broken line is lost -- never the new one.
(Before, the new entry was glued onto the broken one and both were lost.)

Rewriting the whole file (deleting or changing an old entry) uses the
same safe "spare file, then swap" step as json_store.py.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .json_store import atomic_write_text


def _line(entry: Any) -> str:
    return json.dumps(entry, ensure_ascii=False) + "\n"


def append_jsonl(path: Path, entry: Any) -> None:
    """Add one entry as a new line at the end of `path`, and flush it to
    the disk straight away."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        prefix = b""
        if handle.tell() > 0:
            handle.seek(-1, os.SEEK_END)
            if handle.read(1) != b"\n":
                prefix = b"\n"
        handle.seek(0, os.SEEK_END)
        handle.write(prefix + _line(entry).encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def rewrite_jsonl(path: Path, entries: Iterable[Any]) -> None:
    """Replace the whole file with `entries`, one per line, safely."""
    atomic_write_text(path, "".join(_line(entry) for entry in entries))


def read_jsonl(path: Path) -> Iterator[Any]:
    """Every readable entry in `path`, in order. Blank lines and broken
    lines (like one cut short by a crash) are skipped. A missing file
    reads as empty."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except ValueError:
            continue
