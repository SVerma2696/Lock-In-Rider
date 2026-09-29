"""
lock_in/ui/
===========
Everything you see on the screen. This used to be one very long file,
ui.py; now it's a folder of small ones (see ui/app.py for the map).

The names other code already imports from `lock_in.ui` still work:

    from lock_in.ui import run, LockInApp
    from lock_in.ui import flip_pack_kwargs, flip_place_kwargs, flip_grid_kwargs
    from lock_in.ui import build_task_picker_entries
    from lock_in.ui import _TIER5_TAB_LABELS
"""

from .app import LockInApp, run
from .mirror import flip_grid_kwargs, flip_pack_kwargs, flip_place_kwargs
from .router import TIER5_ROUTE_LABELS
from .task_picker import build_task_picker_entries

# The old name for the Tier 5 page labels (they were tabs back then).
_TIER5_TAB_LABELS = TIER5_ROUTE_LABELS

__all__ = [
    "LockInApp",
    "run",
    "flip_grid_kwargs",
    "flip_pack_kwargs",
    "flip_place_kwargs",
    "build_task_picker_entries",
    "TIER5_ROUTE_LABELS",
]
