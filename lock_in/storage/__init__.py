"""
storage/
========
Safe saving for every file Lock In keeps on your computer.

The problem it solves: saving a file normally means "empty it, then
write the new words in". If the computer crashes or loses power right in
the middle, the file is left half-written, and the app can't read it the
next time it opens.

The fix, in plain words: write the new copy into a spare file next to
the real one first. Only when the spare copy is completely written does
it take the real file's place, in one single step. So the real file is
always either the complete old copy or the complete new copy, never half
of each.

    json_store.py   whole files (settings, tasks, the learned model)
    jsonl_store.py  one-line-per-entry files (history, observations)
"""

from .json_store import atomic_write_json, atomic_write_text, read_json
from .jsonl_store import append_jsonl, read_jsonl, rewrite_jsonl

__all__ = [
    "append_jsonl",
    "atomic_write_json",
    "atomic_write_text",
    "read_json",
    "read_jsonl",
    "rewrite_jsonl",
]
