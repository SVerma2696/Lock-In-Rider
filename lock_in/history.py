"""
history.py
==========
This file is the app's diary of every focus block you've run -- one line
per block, written the moment the block ends.

Adding a block is quick and safe: the app just writes one new line at
the end of the file. If the app closes in the middle of a save, you'd
lose at most that one line, never the whole diary.

Only one thing ever goes back and changes old lines: Zi-O's History tab.
It lets you pick a different task for an old block, or delete the block.
When that happens the app writes the whole diary out again, the same way
tasks.py does when you rename or delete a task.

Every block has its own little name tag (an id) so the app knows exactly
which block you mean. Blocks saved before name tags existed get one the
first time the app opens them.

A block remembers which task was picked when it ended, and that's all.
If you delete that task later, the block keeps the old task id -- it
just shows up as "Deleted task".
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
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
    # The block's own name tag. Every new block gets one automatically.
    # Old lines saved before this existed get one when they are loaded --
    # see HistoryStore.load().
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


class HistoryStore:
    """Appends, loads, and queries the session-history log."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: List[SessionRecord] = []
        self.load()

    def load(self) -> None:
        """Read every line, skipping any that's broken rather than failing.

        A line with no "id" (saved before name tags existed) gets one
        here. If that happened even once, the file is saved again with
        the new ids in it, so each block keeps the SAME id every time
        the app opens -- not a brand new one each time.
        """
        self._records.clear()
        if not self.path.exists():
            return
        needs_save = False
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict):
                        continue
                    if "id" not in raw:
                        needs_save = True
                    self._records.append(SessionRecord(**raw))
                except (json.JSONDecodeError, TypeError):
                    continue
        except OSError:
            return
        if needs_save:
            # If the file can't be saved (say, it's locked), keep going.
            # The blocks already have their ids in memory, and the next
            # time the app opens it just tries the save again.
            try:
                self._rewrite()
            except OSError:
                pass

    def _rewrite(self) -> None:
        """Write every block back to the file, in the same order.

        Only three things use this: load() (giving old blocks their
        name tags), reassign_task(), and delete().
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(asdict(r), ensure_ascii=False) for r in self._records]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def reassign_task(self, record_id: str, new_task_id: Optional[str]) -> bool:
        """Change which task an old block belongs to. None means "no
        task". Only the task changes -- the start, end and length stay
        exactly as they were. Returns False if no block has that id.

        This never touches tasks.py: moving a block to another task is
        just fixing the diary, it doesn't finish or start any task.
        """
        for record in self._records:
            if record.id == record_id:
                record.task_id = new_task_id
                self._rewrite()
                return True
        return False

    def delete(self, record_id: str) -> bool:
        """Remove one block for good. Returns False if no block has
        that id."""
        for index, record in enumerate(self._records):
            if record.id == record_id:
                del self._records[index]
                self._rewrite()
                return True
        return False

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
