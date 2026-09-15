"""
V3's `last_14_days()` generalized into `tier5/_shared.py`'s
`last_n_days()` once Decade also needed a windowed day-list (see
docs/superpowers/specs/2026-09-14-tier5-decade-analytics-design.md) --
its tests moved to tests/test_tier5_shared.py along with it. Nothing
V3-specific is left to unit-test right now; build() is manually
verified in the running app, same as every other Tier 5 Rider's tab.
"""
