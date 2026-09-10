#!/usr/bin/env python3
"""Playwright test runner for F-MOD-002.

The AAH test harness injects a JUnit output path into PYTEST_ADDOPTS for
pytest, but Playwright needs it via PLAYWRIGHT_JUNIT_OUTPUT_FILE instead.
This script bridges the two: it extracts the harness-injected path from
PYTEST_ADDOPTS (when present) and sets PLAYWRIGHT_JUNIT_OUTPUT_FILE before
invoking Playwright, so the JUnit file lands where the harness expects it.

When PYTEST_ADDOPTS is absent (e.g. running manually), falls back to
../test-results/results.xml relative to the frontend/ directory.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# ── Resolve JUnit output path ────────────────────────────────────────────────

pytest_opts = os.environ.get("PYTEST_ADDOPTS", "")
match = re.search(r"--junitxml=(\S+)", pytest_opts)

if match:
    junit_output_file = match.group(1)
else:
    # Fallback: project-root test-results/ directory (matches NodeAdapter globs
    # when the harness detects Node for the frontend sub-tree).
    project_root = Path(__file__).parent.parent
    junit_output_file = str(project_root / "test-results" / "results.xml")

# ── Run Playwright ───────────────────────────────────────────────────────────

frontend_dir = Path(__file__).parent.parent / "frontend"
env = dict(os.environ, PLAYWRIGHT_JUNIT_OUTPUT_FILE=junit_output_file)

result = subprocess.run(
    [
        "npx",
        "playwright",
        "test",
        "tests/profile-name-inline-edit.spec.ts",
        "--reporter=junit",
        "--workers=1",
    ],
    cwd=str(frontend_dir),
    env=env,
)
sys.exit(result.returncode)
