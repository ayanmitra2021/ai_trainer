# Discuss PRD — Profile Name Editing

**Feature:** Learner Profile Name Editing
**Iteration:** 1
**Date:** 2026-09-10
**Status:** Approved — ready for plan phase

---

## Problem Statement

Learner profiles in Mastery Pulse are locked after activation — all fields become read-only. However, the name assigned at profile creation is often a default or placeholder value. Learners have no way to personalise their profile name after activation without admin intervention. This friction reduces ownership and engagement with the learning journey.

---

## Solution

A name-only edit path carved out from the existing lock. A pencil icon appears directly before the profile name in the SkillRadar header — the only entry point for editing. Clicking it turns the name into an inline text input; Enter or clicking away saves the change; Escape cancels. The backend exposes a new dedicated endpoint (`PATCH /practitioners/{id}/profiles/{profile_id}/name`) that accepts only the `name` field, bypasses the lock, and validates the existing 1–500 character constraint. The rest of the profile remains fully locked. Optimistic update shows the new name immediately; any API failure rolls back the name and shows an error toast.

---

## User Stories

1. As a learner, when I view my active profile in the SkillRadar header, I see a pencil icon next to my profile name so that I know editing is available.
2. As a learner, when I click the pencil icon, my profile name becomes an editable inline text input so that I can type a new name without leaving the page.
3. As a learner, when I press Enter or click away, my new name is saved immediately so that I see the change take effect without a page reload.
4. As a learner, when I press Escape, the edit is cancelled and the original name is restored so that I can safely exit without making changes.
5. As a learner, if the save fails, I see an error toast and my original name is restored so that I am not left with a misleading state.
6. As a learner, I cannot edit any field other than the name so that the integrity of my certified skill profile is preserved.

---

## Decision Registry Summary

| Slug | Decision | Rationale |
|------|----------|-----------|
| `profile-name-backend-approach` | New dedicated endpoint: `PATCH /practitioners/{id}/profiles/{profile_id}/name` | Active profiles are locked (`is_locked=True`); the existing PATCH route returns 403 for all locked-profile edits. A dedicated endpoint bypasses the lock gate for name-only, keeping the lock semantics intact everywhere else. |
| `profile-name-access-control` | Learner (self) only | Only the profile owner can rename their own active profile. Endpoint validates `practitioner_id` from session matches the URL param — no admin override path. |
| `profile-name-url-shape` | `/profiles/{profile_id}/name` (explicit profile_id) | Consistent with all existing profile routes; server validates ownership. Avoids `/active/name` convenience path that would diverge from the pattern. |
| `profile-name-frontend-placement` | SkillRadar profile header only (`SkillRadar.tsx` line ~934) | Single canonical location where the profile name is rendered to the learner in the active state. No duplicate edit affordances elsewhere. |
| `profile-name-edit-ux` | Inline input — Enter saves, Esc cancels | In-place text input replacing the name label. No modal, no separate edit page. Keeps the learner in context. |
| `profile-name-blur-behaviour` | Save on blur | Clicking away (blur) triggers save — consistent with Enter. Esc cancels without saving. |
| `profile-name-validation` | Keep existing constraints: 1–500 chars, trimmed, any printable character | Reuses `ProfileUpdate.name` schema rules (`min_length=1, max_length=500`). Client-side trim + length guard runs before the mutation fires to avoid unnecessary API calls. |
| `profile-name-optimistic-update` | Optimistic update with TanStack Query rollback + error toast | TanStack Query v5 `onMutate` snapshot + `onError` rollback. Shows new name immediately; rolls back to previous name + shows error toast if the API call fails. No browser storage involved. |

---

## Technical Design Notes

### Backend

**New endpoint:** `PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}/name`

- **Auth:** Practitioner session required (`get_current_practitioner` dependency)
- **Ownership check:** `profile.practitioner_id == current_practitioner.id` — 403 if mismatch
- **Lock bypass:** Does NOT check `profile.is_locked` — the dedicated endpoint is the carve-out
- **Active-only check:** `profile.is_active == True` — 404 (or 403) if profile is not active
- **Body schema:** New `ProfileNameUpdate` Pydantic schema: `name: str = Field(..., min_length=1, max_length=500)` (name trimmed before persistence)
- **Response:** `200 OK` with updated profile object (or minimal `{"name": "<new>"}`)
- **No model changes:** `PractitionerProfile.name` already exists; no Alembic migration needed

**Existing route (`PATCH /profiles/{id}`) is unchanged.** Lock gate remains intact for all other fields.

### Frontend

**File:** `frontend/src/components/SkillRadar/SkillRadar.tsx` (profile name display at line ~934)

**Changes:**
1. Import `useState` for local edit-mode flag + draft value
2. Add `useUpdateProfileName` mutation hook (new hook in `frontend/src/hooks/index.ts`)
3. Add `useUpdateProfileName` API call in `frontend/src/api/index.ts`
4. Replace static `{profile.name}` render with conditional: pencil icon (view mode) ↔ inline `<input>` (edit mode)
5. Pencil icon: render only on the active profile; use a standard icon (e.g. `✏️` or an SVG icon already in use)
6. Inline input: `autoFocus`, value = draft, `onKeyDown` handles Enter (save) and Esc (cancel), `onBlur` triggers save
7. TanStack Query `onMutate` snapshot, `onSuccess` invalidate `profiles` query, `onError` rollback + show toast

**No browser storage.** Edit state lives in component `useState` only; persisted name comes from TanStack Query cache (invalidated on success).

### Constraints Honoured

- ✅ Only `name` is editable — no other fields exposed
- ✅ Active profile only — endpoint enforces `is_active`
- ✅ Pencil icon is sole entry point — one render location in SkillRadar header
- ✅ Profile stays locked — `is_locked` untouched; no unlock side-effect
- ✅ No browser storage — all state via TanStack Query + component useState
- ✅ Self-only access — practitioner session ownership check

---

## Out of Scope

- Admin-initiated profile rename (admin has no edit path for learner profile names in this feature)
- Audit trail for name changes
- Rename on non-active (archived/draft) profiles
- Rename from any page other than the SkillRadar header
