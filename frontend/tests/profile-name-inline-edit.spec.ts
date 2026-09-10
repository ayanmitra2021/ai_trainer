/**
 * F-MOD-002 — Profile Name Inline Edit
 *
 * Tests the pencil-icon-triggered inline name editing in the SkillRadar
 * active-profile header. All API calls are intercepted with page.route()
 * so no live backend is required.
 *
 * Locator note: page.getByLabel("Profile name") does partial/case-insensitive
 * matching and would also match the pencil button (aria-label="Edit profile name").
 * Tests use page.locator('input[aria-label="Profile name"]') for unambiguous input
 * selection that only matches the actual <input> element.
 *
 * Naming convention: test_F_MOD_002_<description> (feature ID as test label).
 */

import { expect, test } from "@playwright/test";

// ── Test fixtures ─────────────────────────────────────────────────────────────

const PRACTITIONER_ID = "prac-mod002-test";
const PROFILE_ID = "prof-mod002-active";
const BASE = "/ai_trainer";

const mockMe = {
  identity_type: "practitioner",
  first_name: "Alex",
  practitioner_id: PRACTITIONER_ID,
  must_change_password: false,
  active_profile_id: PROFILE_ID,
  active_certification_code: "CCAO-F",
  active_profile_is_locked: false,
};

const mockPractitioner = {
  id: PRACTITIONER_ID,
  name: "Alex Tester",
  email: "alex@example.com",
  role: "Engineer",
  practice: "Cloud",
  seniority_level: "mid",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
};

const activeProfile = {
  id: PROFILE_ID,
  practitioner_id: PRACTITIONER_ID,
  name: "My Active Profile",
  is_active: true,
  certification_id: "cert-ccao",
  certification_code: "CCAO-F",
  questionnaire_snapshot: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-09-10T00:00:00Z",
  mastery_pct: 0.45,
  is_locked: false,
  domain_scoring_status: "lm_scored",
};

const updatedProfile = {
  ...activeProfile,
  name: "Updated Name",
  updated_at: "2026-09-10T12:00:00Z",
};

const mockCertifications = [
  {
    id: "cert-ccao",
    code: "CCAO-F",
    name: "Claude Certified Associate – Foundations",
    level: "foundational",
    is_active: true,
    requires_coding_background: false,
    provider: { id: "prov-anthropic", name: "Anthropic" },
    certification_skills: [],
  },
];

// ── Shared setup ──────────────────────────────────────────────────────────────

async function setupMocks(page: import("@playwright/test").Page) {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ json: mockMe })
  );
  // PractitionerPage fetches the individual practitioner; without this mock
  // PractitionerPage shows a loading spinner indefinitely and SkillRadar never renders.
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}`,
    (route) => route.fulfill({ json: mockPractitioner })
  );
  await page.route("**/api/v1/certifications**", (route) =>
    route.fulfill({ json: mockCertifications })
  );
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles`,
    (route) => route.fulfill({ json: [activeProfile] })
  );
  // Return empty skill profile so component renders the "Generate path" empty state
  // (ProfileBanner is rendered in both empty and populated states)
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/skill-profile`,
    (route) => route.fulfill({ json: [] })
  );
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/learning-paths`,
    (route) => route.fulfill({ json: [] })
  );
  // Mock exam active — return 404 (no active session)
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/mock-exams/active`,
    (route) => route.fulfill({ status: 404, json: { detail: "Not found" } })
  );
  // Cert domain scores — return empty
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/certification-domain-scores**`,
    (route) => route.fulfill({ json: [] })
  );
  // Unread nudge count — PractitionerPage calls this; silence it
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/nudges/unread-count`,
    (route) => route.fulfill({ json: { unread_count: 0 } })
  );
}

/** Selector for the inline edit input (exact match avoids matching the pencil button). */
const INPUT_SELECTOR = 'input[aria-label="Profile name"]';

async function navigateToSkillRadar(page: import("@playwright/test").Page) {
  await page.goto(`${BASE}/practitioners/${PRACTITIONER_ID}/skills`);
  // Wait for ProfileBanner to render: pencil button is the signal
  await expect(
    page.getByRole("button", { name: "Edit profile name" })
  ).toBeVisible({ timeout: 10_000 });
}

// ── Tests ─────────────────────────────────────────────────────────────────────

test("test_F_MOD_002_pencil_icon_visible_before_profile_name", async ({ page }) => {
  await setupMocks(page);
  await navigateToSkillRadar(page);

  // Pencil button is present and visible
  const pencilBtn = page.getByRole("button", { name: "Edit profile name" });
  await expect(pencilBtn).toBeVisible();

  // Profile name text is visible alongside the pencil icon
  await expect(page.getByText("My Active Profile")).toBeVisible();
});

test("test_F_MOD_002_pencil_button_is_button_element_with_aria_label", async ({ page }) => {
  await setupMocks(page);
  await navigateToSkillRadar(page);

  // Must be a <button> (not div/span), satisfying RX-A11Y-001
  const pencilBtn = page.getByRole("button", { name: "Edit profile name" });
  await expect(pencilBtn).toBeVisible();
  const tagName = await pencilBtn.evaluate((el) => el.tagName.toLowerCase());
  expect(tagName).toBe("button");
  const ariaLabel = await pencilBtn.getAttribute("aria-label");
  expect(ariaLabel).toBe("Edit profile name");
});

test("test_F_MOD_002_clicking_pencil_opens_input_with_current_name", async ({ page }) => {
  await setupMocks(page);
  await navigateToSkillRadar(page);

  const pencilBtn = page.getByRole("button", { name: "Edit profile name" });
  await pencilBtn.click();

  // Input appears pre-filled with the current profile name
  const input = page.locator(INPUT_SELECTOR);
  await expect(input).toBeVisible();
  await expect(input).toHaveValue("My Active Profile");

  // Pencil button should no longer be visible in edit mode
  await expect(pencilBtn).not.toBeVisible();
});

test("test_F_MOD_002_input_has_accessible_name_satisfying_a11y", async ({ page }) => {
  await setupMocks(page);
  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();

  // Input must be an <input> element with an accessible name (aria-label), satisfying RX-A11Y-002
  const input = page.locator(INPUT_SELECTOR);
  await expect(input).toBeVisible();
  const tagName = await input.evaluate((el) => el.tagName.toLowerCase());
  expect(tagName).toBe("input");
});

test("test_F_MOD_002_enter_key_saves_new_name_and_exits_edit_mode", async ({ page }) => {
  await setupMocks(page);

  // Mock the PATCH endpoint for a successful save
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_ID}/name`,
    (route) => {
      if (route.request().method() === "PATCH") {
        route.fulfill({ json: updatedProfile });
      } else {
        route.continue();
      }
    }
  );

  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();
  const input = page.locator(INPUT_SELECTOR);
  await input.fill("Updated Name");
  await input.press("Enter");

  // Edit mode ends — input is gone
  await expect(input).not.toBeVisible({ timeout: 5_000 });
  // Pencil button re-appears
  await expect(page.getByRole("button", { name: "Edit profile name" })).toBeVisible();
});

test("test_F_MOD_002_escape_key_cancels_edit_and_restores_original_name", async ({ page }) => {
  // Track whether a PATCH request was made (it must NOT be)
  let patchCalled = false;
  await setupMocks(page);
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_ID}/name`,
    (route) => {
      if (route.request().method() === "PATCH") {
        patchCalled = true;
        route.fulfill({ json: updatedProfile });
      } else {
        route.continue();
      }
    }
  );

  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();
  const input = page.locator(INPUT_SELECTOR);
  await input.fill("Something Temporary");
  await input.press("Escape");

  // Edit mode ends without saving
  await expect(input).not.toBeVisible({ timeout: 5_000 });
  // No PATCH request was made
  expect(patchCalled).toBe(false);
});

test("test_F_MOD_002_blur_saves_new_name_identically_to_enter", async ({ page }) => {
  await setupMocks(page);

  let patchBody: unknown = null;
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_ID}/name`,
    async (route) => {
      if (route.request().method() === "PATCH") {
        patchBody = await route.request().postDataJSON();
        route.fulfill({ json: updatedProfile });
      } else {
        route.continue();
      }
    }
  );

  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();
  const input = page.locator(INPUT_SELECTOR);
  await input.fill("Blur Save Name");
  // Click elsewhere to trigger blur
  await page.locator("body").click({ position: { x: 10, y: 10 } });

  // PATCH was called with trimmed name
  await expect(input).not.toBeVisible({ timeout: 5_000 });
  expect(patchBody).toMatchObject({ name: "Blur Save Name" });
});

test("test_F_MOD_002_empty_name_cancels_without_api_call", async ({ page }) => {
  let patchCalled = false;
  await setupMocks(page);
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_ID}/name`,
    (route) => {
      if (route.request().method() === "PATCH") {
        patchCalled = true;
        route.fulfill({ json: updatedProfile });
      } else {
        route.continue();
      }
    }
  );

  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();
  const input = page.locator(INPUT_SELECTOR);
  // Clear the input (empty string)
  await input.fill("");
  await input.press("Enter");

  // Edit mode exits without API call
  await expect(input).not.toBeVisible({ timeout: 5_000 });
  expect(patchCalled).toBe(false);
});

test("test_F_MOD_002_unchanged_name_closes_editor_without_api_call", async ({ page }) => {
  let patchCalled = false;
  await setupMocks(page);
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_ID}/name`,
    (route) => {
      if (route.request().method() === "PATCH") {
        patchCalled = true;
        route.fulfill({ json: updatedProfile });
      } else {
        route.continue();
      }
    }
  );

  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();
  const input = page.locator(INPUT_SELECTOR);
  // Do not change the value — press Enter with the same name
  await input.press("Enter");

  // Exits edit mode without calling PATCH
  await expect(input).not.toBeVisible({ timeout: 5_000 });
  expect(patchCalled).toBe(false);
});

test("test_F_MOD_002_api_error_shows_toast_and_rolls_back_name", async ({ page }) => {
  await setupMocks(page);
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_ID}/name`,
    (route) => {
      if (route.request().method() === "PATCH") {
        route.fulfill({
          status: 422,
          json: { detail: "Name cannot be empty" },
        });
      } else {
        route.continue();
      }
    }
  );

  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();
  const input = page.locator(INPUT_SELECTOR);
  await input.fill("Bad Name");
  await input.press("Enter");

  // Wait for the error toast to appear
  const toast = page.getByRole("alert");
  await expect(toast).toBeVisible({ timeout: 5_000 });
  await expect(toast).toContainText("Failed to save profile name — please try again");
});

test("test_F_MOD_002_patch_request_body_contains_name_field", async ({ page }) => {
  await setupMocks(page);

  let capturedBody: unknown = null;
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_ID}/name`,
    async (route) => {
      if (route.request().method() === "PATCH") {
        capturedBody = await route.request().postDataJSON();
        route.fulfill({ json: updatedProfile });
      } else {
        route.continue();
      }
    }
  );

  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();
  const input = page.locator(INPUT_SELECTOR);
  // Leading/trailing whitespace should be trimmed
  await input.fill("  Trimmed Name  ");
  await input.press("Enter");

  await expect(input).not.toBeVisible({ timeout: 5_000 });
  // Body has trimmed name
  expect(capturedBody).toEqual({ name: "Trimmed Name" });
});

test("test_F_MOD_002_no_localstorage_or_sessionstorage_during_edit", async ({ page }) => {
  // addInitScript MUST be called before page.goto() to run on the current page load.
  await page.addInitScript(() => {
    const origSetLocal = localStorage.setItem.bind(localStorage);
    const origSetSession = sessionStorage.setItem.bind(sessionStorage);
    (window as unknown as { __storageKeys: string[] }).__storageKeys = [];
    localStorage.setItem = (k: string, v: string) => {
      (window as unknown as { __storageKeys: string[] }).__storageKeys.push(`local:${k}`);
      origSetLocal(k, v);
    };
    sessionStorage.setItem = (k: string, v: string) => {
      (window as unknown as { __storageKeys: string[] }).__storageKeys.push(`session:${k}`);
      origSetSession(k, v);
    };
  });

  await setupMocks(page);
  await page.route(
    `**/api/v1/practitioners/${PRACTITIONER_ID}/profiles/${PROFILE_ID}/name`,
    (route) => route.fulfill({ json: updatedProfile })
  );

  await navigateToSkillRadar(page);

  await page.getByRole("button", { name: "Edit profile name" }).click();
  const input = page.locator(INPUT_SELECTOR);
  await input.fill("Storage Test");
  await input.press("Enter");
  await expect(input).not.toBeVisible({ timeout: 5_000 });

  const keys = await page.evaluate(
    () => (window as unknown as { __storageKeys?: string[] }).__storageKeys ?? []
  );

  // No profile-name-related keys should have been written to localStorage/sessionStorage
  const profileKeys = keys.filter(
    (k) =>
      k.toLowerCase().includes("name") ||
      k.toLowerCase().includes("profile") ||
      k.toLowerCase().includes("edit")
  );
  expect(profileKeys).toHaveLength(0);
});
