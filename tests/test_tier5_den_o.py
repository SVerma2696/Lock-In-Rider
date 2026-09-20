"""
The helpers Den-O used (sorted_blocks, format_time_range,
format_day_heading) moved to tier5/_shared.py because Zi-O needs them
too -- their tests moved to tests/test_tier5_shared.py with them.
(resolve_task_name made the same move earlier, for Decade.)

Nothing here is left to test on its own. Den-O's build() is checked by
running the real app, like every other Tier 5 tab.
"""
