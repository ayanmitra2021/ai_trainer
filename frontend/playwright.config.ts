import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for Mastery Pulse end-to-end tests.
 * Phase 4+ will add page-level tests; this is the skeleton.
 *
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ["html"],
    // JUnit reporter writes to a file so CI / AAH harness can parse test results.
    // Path is relative to this config file (frontend/); "../test-results/results.xml"
    // places the file at the project root's test-results/ directory, which is where
    // the AAH harness globs for JUnit XML (test-results/*.xml).
    ["junit", { outputFile: "../test-results/results.xml" }],
  ],

  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  /* Run the Vite dev server before tests. */
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
  },
});
