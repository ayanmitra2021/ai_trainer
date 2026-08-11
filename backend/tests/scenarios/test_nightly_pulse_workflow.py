"""Step 9.1 — nightly_pulse workflow removal scenarios.

The original Step 3.5 scenarios (full nightly run, per-practitioner failure
isolation) are superseded by this file. The nightly_pulse workflow was removed
in Phase 9.1; its body now raises NotImplementedError so any accidental trigger
surfaces as a loud error rather than silently doing nothing.

Scenario: Calling nightly_pulse raises NotImplementedError, not a silent no-op.
"""

from __future__ import annotations

import pytest

from app.workflows.nightly_pulse import run_nightly_pulse


class TestNightlyPulseRemovedInPhase91:
    async def test_nightly_pulse_raises_not_implemented(self) -> None:
        """
        Scenario: Calling the nightly_pulse workflow raises a clear error.
          Given the nightly_pulse workflow was removed in Phase 9.1
          When run_nightly_pulse() is called (by any means — scheduler, test, stray import)
          Then it raises NotImplementedError immediately
          And the error message references the replacement (nudge campaign workflow)
        """
        # When / Then — calling the function must raise NotImplementedError
        with pytest.raises(NotImplementedError) as exc_info:
            await run_nightly_pulse(
                practitioner_ids=["some-id"],
                scope="practice",
                scope_ref="Test Practice",
                period_start=None,  # type: ignore[arg-type]
                period_end=None,  # type: ignore[arg-type]
                db=None,  # type: ignore[arg-type]
            )

        # And the message should mention the removal and replacement
        message = str(exc_info.value)
        assert "nightly_pulse" in message.lower() or "Phase 9.1" in message
        assert "removed" in message.lower() or "nudge campaign" in message.lower()

    async def test_nightly_pulse_raises_even_with_no_args(self) -> None:
        """
        Additional guard: calling with zero positional args also raises,
        not a TypeError that could be mistaken for a bug in the caller.
        """
        with pytest.raises(NotImplementedError):
            await run_nightly_pulse()
