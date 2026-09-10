/**
 * F-MOD-002 Playwright test runner.
 *
 * The AAH harness injects a JUnit output path into PYTEST_ADDOPTS for pytest.
 * Playwright needs the path via PLAYWRIGHT_JUNIT_OUTPUT_FILE instead. This
 * script bridges the two: it extracts the harness-injected path from
 * PYTEST_ADDOPTS (when present) and sets PLAYWRIGHT_JUNIT_OUTPUT_FILE before
 * invoking Playwright, so the JUnit file lands where the harness expects it.
 *
 * Entry point used in F-MOD-002.md Test Config to avoid the harness's
 * bare-interpreter rewrite (which catches `py`/`python` but not `node`).
 */

"use strict";

const { spawnSync } = require("child_process");
const path = require("path");

// ── Resolve JUnit output path ─────────────────────────────────────────────

const pytestOpts = process.env.PYTEST_ADDOPTS || "";
const match = pytestOpts.match(/--junitxml=(\S+)/);

const junitOutputFile = match
  ? match[1]
  : path.join(__dirname, "..", "test-results", "results.xml");

// ── Run Playwright ────────────────────────────────────────────────────────

const frontendDir = path.join(__dirname, "..", "frontend");
const env = { ...process.env, PLAYWRIGHT_JUNIT_OUTPUT_FILE: junitOutputFile };

const result = spawnSync(
  "npx",
  [
    "playwright",
    "test",
    "tests/profile-name-inline-edit.spec.ts",
    "--reporter=junit",
    "--workers=1",
  ],
  {
    cwd: frontendDir,
    env,
    stdio: "inherit",
    shell: true,   // needed on Windows for `npx` to resolve
  }
);

process.exit(result.status ?? 1);
