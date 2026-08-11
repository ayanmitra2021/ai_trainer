"""nightly_pulse workflow — REMOVED in Phase 9.1.

The fully-automated nightly nudge + rollup pipeline is no longer part of the
active product. Correlation snapshots (Step 3.2) still exist and feed the
admin-driven nudge campaign system (Phase 7), but there is no longer a scheduled
nightly run that auto-generates nudges or rollups.

The archived implementation lived here up through Phase 8.6. The Rollup Reporter
agent has been moved to ``backend/app/agents/_deprecated/rollup_reporter.py``.

If this function is called — by a stale scheduler, a test, or an erroneous import
— it raises immediately so the error is loud and obvious rather than silently
producing nothing.
"""


async def run_nightly_pulse(*args, **kwargs):  # noqa: ANN002, ANN003
    """Removed entry point — raises NotImplementedError on any call."""
    raise NotImplementedError(
        "nightly_pulse removed in Phase 9.1. "
        "Use the admin-driven nudge campaign workflow instead "
        "(POST /nudges/categories/{id}/compose → POST /nudges/send)."
    )
