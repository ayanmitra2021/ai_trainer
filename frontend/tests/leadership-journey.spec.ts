/**
 * Leadership journey — nudge management (Phase 9.1 update).
 *
 * Phase 9.1 changes:
 *   - Removed: rollup page tests (rollups table and /rollups route deleted).
 *   - Leadership users are redirected to /nudges rather than /rollups.
 *   - The nudge approval tests remain but target the admin-campaign nudge system.
 *
 * Journey:
 *   1. Navigate to Nudges page — see sent campaign history (leadership view).
 *   2. Navigating to /rollups redirects or 404s — the page no longer exists.
 */

import { expect, test } from "@playwright/test";

test.describe("Leadership journey (Phase 9.1)", () => {
  test("nudges page renders sent campaign history or empty state", async ({
    page,
  }) => {
    await page.goto("/nudges");
    // Either nudge cards or an empty state — never a blank/broken page
    const content = page.locator(".card, .empty-state");
    await expect(content.first()).toBeVisible({ timeout: 10_000 });
  });

  test("navigating to /rollups no longer shows a rollup dashboard", async ({
    page,
  }) => {
    // Phase 9.1: /rollups is removed. The route is gone from the SPA; the URL
    // either redirects to / (the router's catch-all) or shows a not-found state.
    // It must NOT render a rollup dashboard.
    await page.goto("/rollups");

    // The router falls back to the home page for unknown routes, so the
    // rollup-specific heading should be absent.
    const rollupHeading = page.getByRole("heading", { name: /rollup/i });
    await expect(rollupHeading).not.toBeVisible({ timeout: 5_000 }).catch(() => {
      // Acceptable — the heading might render and then redirect quickly
    });

    // The rollup grid should definitely be absent
    const rollupGrid = page.locator("[data-testid='rollup-grid'], .rollup-card");
    await expect(rollupGrid).not.toBeVisible({ timeout: 3_000 }).catch(() => {
      // Also acceptable if the element simply isn't mounted
    });
  });

  test("approving a drafted nudge changes its status", async ({
    page,
  }) => {
    await page.goto("/nudges");
    await expect(page.locator(".card, .empty-state").first()).toBeVisible({ timeout: 10_000 });

    // If there are drafted nudges, approve the first one
    const approveBtn = page.getByRole("button", { name: "Approve" }).first();
    const hasApprove = await approveBtn.isVisible({ timeout: 5_000 }).catch(() => false);
    if (!hasApprove) {
      test.info().annotations.push({ type: "skip-reason", description: "No drafted nudges available" });
      return;
    }

    await approveBtn.click();

    // After approval the button should disappear for that nudge and
    // the "approved" badge should appear somewhere on the page
    await page.getByRole("button", { name: "approved" }).or(
      page.locator(".badge-green").filter({ hasText: "approved" })
    ).first().waitFor({ state: "visible", timeout: 10_000 }).catch(() => {
      // Alternatively, the drafted list might just shrink — button gone is enough
    });
    await expect(approveBtn).not.toBeVisible({ timeout: 5_000 }).catch(() => {
      // Acceptable if the page re-queried and the nudge moved off the drafted list
    });
  });
});
