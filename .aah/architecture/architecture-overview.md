# Architecture Overview — Profile Name Editing

**Feature:** Learner Profile Name Editing
**Iteration:** 1
**Date:** 2026-09-10
**Project type:** Brownfield enhancement

---

## Problem

Active profiles in Mastery Pulse are locked (`PractitionerProfile.is_locked = True`).
The existing `PATCH /api/v1/profiles/{id}` route returns HTTP 403 for ANY edit on a locked profile
(see `backend/app/api/routes/profiles.py` line 378).
Learners cannot rename their own active profile without admin intervention.

---

## Solution Architecture

A single-field carve-out from the lock. The system adds:

1. **New backend endpoint** — `PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}/name`
   - Skips the `is_locked` gate entirely (dedicated endpoint = intentional carve-out)
   - Validates session ownership: `current_practitioner.id == profile.practitioner_id`
   - Validates profile is active: `profile.is_active == True`
   - Validates name: trimmed, 1–500 characters (reuses existing validation logic)
   - Persists `profile.name = body.name.strip()`
   - Returns the updated profile object

2. **Frontend inline edit** — SkillRadar profile header
   - Pencil icon (✏️ or SVG) rendered immediately before the profile name
   - Click → name text replaced by `<input autoFocus>`
   - Enter / blur → fires `PATCH /name` mutation
   - Escape → cancels, restores original name without API call
   - TanStack Query v5 optimistic update: snapshot on `onMutate`, rollback on `onError`
   - Error toast on API failure
   - No `localStorage` / `sessionStorage` used anywhere

---

## Data Model

No schema changes. No Alembic migration required.

Existing columns used:
- `practitioner_profiles.name` — `VARCHAR(500), NOT NULL` (already exists, Phase 9.3)
- `practitioner_profiles.is_locked` — `BOOLEAN` (not touched; endpoint bypasses the check)
- `practitioner_profiles.is_active` — `BOOLEAN` (validated: only active profiles can be renamed)
- `practitioner_profiles.practitioner_id` — `UUID FK` (ownership check)

---

## API Contracts

### New Endpoint

**`PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}/name`**

Request body (`ProfileNameUpdate` schema):
```json
{
  "name": "My Custom Profile Name"
}
```

Validations:
- `name`: string, min_length=1, max_length=500, required (trimmed before persistence)

Responses:
- `200 OK` — updated profile object (same shape as existing profile GET response)
- `403 Forbidden` — caller does not own the profile
- `404 Not Found` — profile not found or not active
- `422 Unprocessable Entity` — validation failure (empty name, too long)
- `401 Unauthorized` — no practitioner session

### Existing Endpoint (unchanged)

`PATCH /api/v1/profiles/{id}` — still returns `403` for all locked profile edits.
The new endpoint is additive and does NOT modify this behavior.

---

## Frontend Component Changes

**`frontend/src/components/SkillRadar/SkillRadar.tsx`** (line ~934)

Before:
```tsx
{profile.name}
```

After:
```tsx
{isEditing ? (
  <input
    autoFocus
    value={draftName}
    onChange={e => setDraftName(e.target.value)}
    onKeyDown={handleKeyDown}   // Enter → save, Esc → cancel
    onBlur={handleSave}
  />
) : (
  <>
    <button onClick={() => setIsEditing(true)} aria-label="Edit profile name">
      ✏️
    </button>
    {profile.name}
  </>
)}
```

**`frontend/src/hooks/index.ts`** — new `useUpdateProfileName` mutation:
- `mutationFn`: calls `api.profiles.updateName(practitionerId, profileId, name)`
- `onMutate`: snapshot old name, optimistically set new name in cache
- `onSuccess`: `queryClient.invalidateQueries({queryKey: ['profiles', profileId]})`
- `onError`: rollback to snapshot, show error toast

**`frontend/src/api/index.ts`** — new `profiles.updateName(practitionerId, profileId, name)`:
- `PATCH /practitioners/${practitionerId}/profiles/${profileId}/name`
- Body: `{ name }`

---

## Constraints

- Only `name` is editable — no other profile fields
- Active profile only (`is_active == True` enforced server-side)
- Pencil icon in SkillRadar header is the sole UI entry point
- Profile lock (`is_locked`) remains intact — this endpoint is the only carve-out
- No browser storage (`localStorage` / `sessionStorage`) — banned project-wide
- Self-only access — no admin override path for this endpoint
- Python invoked as `py` (Windows environment)
