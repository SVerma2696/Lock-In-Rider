"""
history.py
==========
This file is the honest, append-only record of every focus block you've
actually run -- one line per block, written the moment it ends, never
edited afterward (editing past history is a later Rider's job, not
this file's).

Unlike tasks.py, nothing here is ever renamed or deleted in place, so
this is saved the same shape observations.jsonl already is: one JSON
object per line, safe to append, safe if the file gets cut off mid-save
(you'd lose at most one line, not everything).

A record's task_id is a snapshot of whichever task was current when
that block ended -- it is never looked up or re-validated against
tasks.py again after that. If you later delete that task, its past
history entries keep the old id rather than being changed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class SessionRecord:
    """One completed (or cut-short) focus block."""

    start: str                     # ISO timestamp, when the block began
    end: str                       # ISO timestamp, when it ended/was cut short
    duration_seconds: int
    task_id: Optional[str]         # None if no task was picked -- still logged
    completed: bool                # False if skipped or reset before time ran out


class HistoryStore:
    """Appends, loads, and queries the session-history log."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: List[SessionRecord] = []
        self.load()

    def load(self) -> None:
        """Read every line, skipping any that's broken rather than failing."""
        self._records.clear()
        if not self.path.exists():
            return
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    self._records.append(SessionRecord(**json.loads(line)))
                except (json.JSONDecodeError, TypeError):
                    continue
        except OSError:
            pass

    def record(self, session_record: SessionRecord) -> None:
        """Append one completed block. Written and flushed immediately --
        there's no in-memory buffering to lose on a crash."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(session_record), ensure_ascii=False) + "\n")
        self._records.append(session_record)

    def all(self) -> List[SessionRecord]:
        return list(self._records)

    def for_date(self, day: date) -> List[SessionRecord]:
        return [r for r in self._records if datetime.fromisoformat(r.start).date() == day]

    def for_task(self, task_id: str) -> List[SessionRecord]:
        return [r for r in self._records if r.task_id == task_id]

    def earliest_date(self) -> Optional[date]:
        """The calendar day of the very first record ever logged, or
        None if nothing has been logged yet -- backs how far back Den-O's
        Prev-day button can go."""
        if not self._records:
            return None
        return min(datetime.fromisoformat(r.start).date() for r in self._records)

    def total_seconds_by_task(self) -> Dict[Optional[str], int]:
        """{'abc123': 1500, None: 900, ...} -- total focused seconds per
        task_id, with None holding every untagged block's time. The
        aggregate Decade's "Top tasks" ranking reads from."""
        totals: Dict[Optional[str], int] = {}
        for r in self._records:
            totals[r.task_id] = totals.get(r.task_id, 0) + r.duration_seconds
        return totals

    def total_seconds_by_day(self) -> Dict[str, int]:
        """{'2026-09-04': 2400, ...} -- the one aggregate every history-
        reading Rider downstream (V3, Decade, Den-O) will start from."""
        totals: Dict[str, int] = {}
        for r in self._records:
            day = datetime.fromisoformat(r.start).date().isoformat()
            totals[day] = totals.get(day, 0) + r.duration_seconds
        return totals
