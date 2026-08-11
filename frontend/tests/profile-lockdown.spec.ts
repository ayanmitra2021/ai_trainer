/**
 * Step 9.3 — Profile lockdown after first full submission.
 *
 * Definition of done (three scenarios):
 *   1. Completing the full wizard locks the profile — a subsequent PATCH returns 403.
 *      (Covered by backend scenario tests; not duplicated in Playwright — no live stack.)
 *   2. A locked profile card on BuildProfilePage shows "View" in place of "Edit".
 *   3. The ProfileSkillAssessmentPage for a locked profile shows the locked banner and
 *      all skill pickers are disabled (no Save button visible).
 *
 * All API calls are intercepted with page.route() — no live backend required.
 */

import { expect, test } from "@playwright/test";

const PRACTITIONER_ID = "prac-lockdown-9v3";
const PROFILE_LOCKED_ID = "prof-locked-9v3";
const PROFILE_UNLOCKED_ID = "prof-unlocked-9v3";

// Vite base path
const BASE = "/ai_trainer";

// ── Shared mock payloads ──────────────────────────────────────────────────────

const mockMe = {
  identity_type: "practitioner",
  first_name: "Taylor",
  practitioner_id: PRACTITIONER_ID,
  must_change_password: false,
  active_profile_id: PROFILE_LOCKED_ID,
  active_certification_code: "CCAO-F",
  active_profile_is_locked: true,
};

const lockedProfile = {
  id: PROFILE_LOCKED_ID,
  practitioner_id: PRACTITIONER_ID,
  name: "My Locked Path",
  is_active: true,
  certification_id: "cert-ccao",
  certification_code: "CCAO-F",
  questionnaire_snapshot: { writes_code: false },
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-06-01T00:00:00Z",
  mastery_pct: 0.32,
  is_locked: true,
};

const unlockedProfile = {
  id: PROFILE_UNLOCKED_ID,
  practitioner_id: PRACTITIONER_ID,
  name: "My Draft Path",
  is_active: false,
  certification_id: null,
  certification_code: null,
  questionnaire_snapshot: null,
  created_at: "2026-07-01T00:00:00Z",
  updated_at: "2026-07-01T00:00:00Z",
  mastery_pct: null,
  is_locked: false,
};

const lockedProfileDetail = {
  ...lockedProfile,
  skill_assessments: [
    { id: "sa-1", profile_id: PROFILE_LOCKED_ID, skill_id: "sk-prompt", signal_strength: 0.75, updated_at: "2026-06-01T00:00:00Z" },
  ],
};

const mockSkills = [
  { id: "sk-prompt", name: "Prompt Engineering", category: "AI", parent_skill_id: null, description: null },
  { id: "sk-agents", name: "Agent Design", category: "AI", parent_skill_id: null, description: null },
];

const mockCertifications = [
  {
    id: "cert-ccao",
    code: "CCAO-F",
    name: "Claude Certified Associate – Foundations",
    level: "foundational",
    is_active: true,
    requires_coding_background: false,
    provider: { id: "prov-anthropic", name: "Anthropic" },
    certification_skills: [{ skill_id: "sk-prompt", weight: 1.0 }],
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

async function setupCommonMocks(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ json: mockMe })
  );
  await page.route("**/api/v1/certifications**", (route) =>
    route.fulfill({ json: mockCertifications })
  );
  await page.route("**/api/v1/skills**", (route) =>
    route.fulfill({ json: mockSkills })
  );
  await page.route(`**/api/v1/practitioners/${PRACTITIONER_ID}/profiles`, (route) =>
    route.fulfill({ json: [lockedProfile, unlockedProfile] })
  );
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_LOCKED_ID}`,
    (route) => route.fulfill({ json: lockedProfileDetail })
  );
}

// ── Scenario 2: BuildProfilePage shows "View" for locked profiles ─────────────

test("Locked profile card shows 'View' not 'Edit'", async ({ page }) => {
  await setupCommonMocks(page);

  // Navigate to the profiles page
  await page.goto(`${BASE}/profile`);

  // Wait for profile cards to render
  await expect(page.getByText("My Locked Path")).toBeVisible();
  await expect(page.getByText("My Draft Path")).toBeVisible();

  // The locked profile card shows "View"
  const lockedCard = page.locator(".card", { hasText: "My Locked Path" });
  await expect(lockedCard.getByRole("button", { name: "View" })).toBeVisible();
  // "Edit" must NOT appear on the locked card
  await expect(lockedCard.getByRole("button", { name: "Edit" })).not.toBeVisible();

  // The unlocked profile card still shows "Edit"
  const unlockedCard = page.locator(".card", { hasText: "My Draft Path" });
  await expect(unlockedCard.getByRole("button", { name: "Edit" })).toBeVisible();
  await expect(unlockedCard.getByRole("button", { name: "View" })).not.toBeVisible();
});

// ── Scenario 2b: Clicking "View" shows read-only summary, not the wizard ──────

test("Clicking 'View' on a locked profile opens a read-only summary, not the editable wizard", async ({ page }) => {
  await setupCommonMocks(page);

  await page.goto(`${BASE}/profile`);
  await expect(page.getByText("My Locked Path")).toBeVisible();

  const lockedCard = page.locator(".card", { hasText: "My Locked Path" });
  await lockedCard.getByRole("button", { name: "View" }).click();

  // The read-only modal should be visible with the locked badge
  await expect(page.getByText("🔒 Locked")).toBeVisible();
  await expect(page.getByText("This profile is saved and locked")).toBeVisible();
  // The certification code appears in a <dd> inside the modal (not in the nav badge)
  await expect(page.locator("main dd", { hasText: "CCAO-F" })).toBeVisible();

  // The wizard form fields (e.g. profile name input, step progress) must NOT be visible
  await expect(page.getByLabel(/profile name/i)).not.toBeVisible();
  await expect(page.getByText("Step 1 of 3")).not.toBeVisible();
});

// ── Scenario 3: ProfileSkillAssessmentPage shows locked banner ────────────────

test("ProfileSkillAssessmentPage for a locked profile shows disabled banner and no Save button", async ({ page }) => {
  await setupCommonMocks(page);

  await page.goto(`${BASE}/profile/${PROFILE_LOCKED_ID}/skills`);

  // The locked banner should be visible
  const banner = page.getByTestId("profile-locked-banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("saved and locked");

  // The Save assessment button must NOT be present
  await expect(page.getByRole("button", { name: /save assessment/i })).not.toBeVisible();

  // Skill level pickers should be disabled
  // Wait for skills to load
  await expect(page.getByText("Prompt Engineering")).toBeVisible();
  const buttons = page.locator("button[disabled]");
  // There should be at least one disabled button (the level pickers)
  await expect(buttons.first()).toBeVisible();
});
