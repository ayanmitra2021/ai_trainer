/**
 * Admin/Leadership practitioner view — Step 9.2.
 *
 * Definition of done (three scenarios):
 *   1. An admin who navigates to /admin/practitioners/:id sees exactly one tab
 *      labelled "Skill Radar" and no other tabs (Quiz, Adoption Trends, Nudge Inbox).
 *   2. The page has no "Regenerate path" button and no "Edit profile →" link.
 *   3. The read-only profile panel shows the practitioner's certification code and
 *      profile name as plain text.
 *
 * All API calls are mocked with page.route() so the tests run without a live backend.
 */

import { expect, test } from "@playwright/test";

const PRACTITIONER_ID = "test-admin-prac-9v2";
// The Vite app uses base: "/ai_trainer/" (see vite.config.ts) so in dev mode the
// React Router basename is "/ai_trainer/". All page.goto() calls must include the prefix.
const PAGE_URL = `/ai_trainer/admin/practitioners/${PRACTITIONER_ID}`;

// ── Mock payloads ──────────────────────────────────────────────────────────────

const mockMe = {
  identity_type: "admin",
  first_name: "Ada",
  admin_role: "admin",
  must_change_password: false,
};

const mockPractitioner = {
  id: PRACTITIONER_ID,
  name: "Jordan Kim",
  email: "jordan.kim@example.com",
  role: "AI Engineer",
  practice: "Technology",
  seniority_level: "Mid",
  created_at: "2026-02-01T00:00:00Z",
};

const mockActiveProfile = {
  id: "prof-step92",
  practitioner_id: PRACTITIONER_ID,
  name: "Cloud AI Path",
  is_active: true,
  certification_id: "cert-step92",
  certification_code: "ANS-C01",
  questionnaire_snapshot: null,
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-07-15T00:00:00Z",
  mastery_pct: 0.54,
  is_locked: false,
};

const mockSkillSnapshots = [
  {
    skill_id: "sk-prompt",
    skill_name: "Prompt Engineering",
    mastery_score: 0.68,
    confidence: 0.75,
    last_computed_at: "2026-07-15T00:00:00Z",
  },
  {
    skill_id: "sk-model",
    skill_name: "Model Selection",
    mastery_score: 0.41,
    confidence: 0.55,
    last_computed_at: "2026-07-15T00:00:00Z",
  },
];

const mockCertifications = [
  {
    id: "cert-step92",
    code: "ANS-C01",
    name: "AWS Certified AI Practitioner",
    level: "associate",
    is_active: true,
    requires_coding_background: false,
    provider: { id: "aws", name: "Amazon Web Services" },
    certification_skills: [],
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────────

async function setupMocks(page: import("@playwright/test").Page) {
  // Auth
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockMe) })
  );

  // Practitioner detail
  await page.route(`**/api/v1/practitioners/${PRACTITIONER_ID}`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockPractitioner) })
  );

  // Profiles list
  await page.route(`**/api/v1/practitioners/${PRACTITIONER_ID}/profiles`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([mockActiveProfile]) })
  );

  // Skill profile snapshots
  await page.route(`**/api/v1/practitioners/${PRACTITIONER_ID}/skill-profile`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockSkillSnapshots) })
  );

  // Certifications list
  await page.route("**/api/v1/certifications", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(mockCertifications) })
  );

  // Learning paths — empty (read-only view doesn't need them)
  await page.route(`**/api/v1/practitioners/${PRACTITIONER_ID}/learning-paths`, (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) })
  );

  // Practitioners list (for any nav prefetch)
  await page.route("**/api/v1/practitioners", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([mockPractitioner]) })
  );
}

// ── DoD Scenario 1 ─────────────────────────────────────────────────────────────

test("Step 9.2 DoD 1 — admin sees only 'Skill Radar' (no Quiz, Trends, or Nudge Inbox tabs)", async ({
  page,
}) => {
  await setupMocks(page);
  await page.goto(PAGE_URL);

  // Wait for the page to load — the read-only profile panel is the anchor
  await expect(page.getByTestId("readonly-profile-panel")).toBeVisible({ timeout: 10_000 });

  // The page title / radar section heading must mention "Skill Radar"
  const radarHeading = page.getByText(/skill radar/i).first();
  await expect(radarHeading).toBeVisible({ timeout: 5_000 });

  // These tab buttons must NOT appear — the page has no tab strip
  await expect(page.getByRole("button", { name: /^quiz$/i })).not.toBeVisible();
  await expect(page.getByRole("button", { name: /adoption trends/i })).not.toBeVisible();
  await expect(page.getByRole("button", { name: /nudge inbox/i })).not.toBeVisible();
  await expect(page.getByRole("button", { name: /certifications/i })).not.toBeVisible();
});

// ── DoD Scenario 2 ─────────────────────────────────────────────────────────────

test("Step 9.2 DoD 2 — no 'Regenerate path' button and no 'Edit profile' link", async ({
  page,
}) => {
  await setupMocks(page);
  await page.goto(PAGE_URL);

  // Wait for the page to settle
  await expect(page.getByTestId("readonly-profile-panel")).toBeVisible({ timeout: 10_000 });

  // "Regenerate path" must not appear
  await expect(
    page.getByRole("button", { name: /regenerate path/i })
  ).not.toBeVisible();

  // "Generate path" must not appear either
  await expect(
    page.getByRole("button", { name: /generate path/i })
  ).not.toBeVisible();

  // "Edit profile →" must not appear (the ProfileBanner button is suppressed)
  await expect(
    page.getByRole("button", { name: /edit profile/i })
  ).not.toBeVisible();
});

// ── DoD Scenario 3 ─────────────────────────────────────────────────────────────

test("Step 9.2 DoD 3 — read-only profile panel shows certification code and profile name as plain text", async ({
  page,
}) => {
  await setupMocks(page);
  await page.goto(PAGE_URL);

  // Profile panel renders
  const panel = page.getByTestId("readonly-profile-panel");
  await expect(panel).toBeVisible({ timeout: 10_000 });

  // Profile name is visible as plain text
  const profileName = page.getByTestId("profile-name");
  await expect(profileName).toBeVisible();
  await expect(profileName).toHaveText("Cloud AI Path");

  // Cert code is visible as plain text (inside a badge span)
  const certCode = page.getByTestId("cert-code");
  await expect(certCode).toBeVisible();
  await expect(certCode).toHaveText("ANS-C01");
});
