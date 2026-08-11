"""Step 3.4 — Rollup Reporter Agent scenarios.

⚠️  DEPRECATED — Phase 9.1.

The Rollup Reporter agent has been removed from the active product and archived
to ``backend/app/agents/_deprecated/rollup_reporter.py``.  These tests are kept
as a historical record but are skipped so they do not pollute the test suite.

See ``test_phase9_1_removals.py`` for the replacement scenarios that verify the
removal is clean (404 on /rollups, NotImplementedError from nightly_pulse).
"""

import pytest

pytest.skip(
    "Rollup Reporter removed in Phase 9.1 — see test_phase9_1_removals.py",
    allow_module_level=True,
)
