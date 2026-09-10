## Id
F-MOD-002

## Title
Profile Name Inline Edit UI

## Module Ref
MOD-002

## Description
This module adds a pencil-icon-triggered inline edit experience for the active-profile name in `frontend/src/components/SkillRadar/SkillRadar.tsx` (the static `{profile.name}` render at line ~934). It also adds a new `profiles.updateName` call in `frontend/src/api/index.ts` and a new `useUpdateProfileName` TanStack Query v5 mutation hook in `frontend/src/hooks/index.ts`.

**Context.** The architecture is documented in `.aah/architecture/architecture-overview.md` and `.aah/architecture/application-flow.md`. The product requirements and user stories (US-1 through US-6) are in `.aah/discuss/discuss-prd.md`. The module-map entry is `MOD-002` in `.aah/architecture/module-map.yaml`. All three documents must be read before implementing.

**What the module does.** The SkillRadar active-profile header (the card that currently renders the avatar initial, profile name badge, certification code badge, and "Edit profile →" button) gains a second affordance for the name specifically: a pencil icon rendered immediately before `{profile.name}`. The icon is the sole entry point for name editing — no other screen or button surfaces this action. Clicking the icon switches the name span into an `<input autoFocus>` pre-filled with the current name draft. The learner types a new name and confirms it via Enter or blur; Escape cancels without any API call. On save, the `useUpdateProfileName` mutation fires `PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}/name` (delivered by F-MOD-001). The UI shows the new name immediately via TanStack Query v5 optimistic update before the network round-trip completes; if the request fails, the name rolls back to the pre-edit value and an error toast appears.

**API call — `frontend/src/api/index.ts`.** A new `updateName` entry is appended to the existing `profiles` object (`.list`, `.create`, `.get`, `.update`, `.activate`, `.delete`, `.upsertSkillAssessments`). The call issues `PATCH /practitioners/${practitionerId}/profiles/${profileId}/name` with body `{ name }` and returns the updated `PractitionerProfile` shape. The addition follows the existing pattern of using `api.patch<PractitionerProfile>(...)` as seen in `profiles.update` and `profiles.activate`.

**Mutation hook — `frontend/src/hooks/index.ts`.** A new exported hook `useUpdateProfileName(practitionerId: string, profileId: string)` is added, following the pattern of `useDeactivatePractitioner` and `useReactivatePractitioner`. It uses `useMutation` with:
- `mutationFn`: calls `profiles.updateName(practitionerId, profileId, name)` where `name` is the mutation variable.
- `onMutate`: retrieves the current `['profiles', practitionerId]` cache entry, applies an optimistic update setting `profile.name` to the new value, and returns the previous cache snapshot as context.
- `onSuccess`: calls `queryClient.invalidateQueries({ queryKey: ['profiles', practitionerId] })` to reconcile server state.
- `onError`: rolls back to the snapshot captured in `onMutate` and shows an error toast ("Failed to save profile name — please try again").

**Component change — `SkillRadar.tsx` at line ~934.** The component adds two `useState` calls (`isEditing: boolean` and `draftName: string`, both local) and imports `useUpdateProfileName`. The previously static `{profile.name}` expression is replaced with a conditional block: in view mode a `<button aria-label="Edit profile name">` pencil icon precedes the name text; in edit mode the name text is replaced by `<input autoFocus value={draftName} onChange={...} onKeyDown={handleKeyDown} onBlur={handleSave} />`. `handleKeyDown` maps Enter to `handleSave` and Escape to `handleCancel`. `handleSave` trims the draft, guards against an empty string or an unchanged name (skips the mutation if the trimmed value equals `profile.name`), then fires the mutation and sets `isEditing = false`. `handleCancel` resets `draftName` to `profile.name` and sets `isEditing = false`. No `localStorage` or `sessionStorage` is used; all transient edit state lives in component `useState`.

The pencil icon is rendered only for the active-profile header card — the same card that already has `is_active === true` filtering applied when the parent component selects which profile to display prominently.

Applicable standards from `.aah/plan/resolved-standards.yaml`: RX-A11Y-001 (interactive elements must be keyboard accessible and use semantic HTML with `aria-label` for icon-only buttons), RX-SEC-002 (no `localStorage`/`sessionStorage`), RX-ARCH-001 (hooks called only at the top level of the component), RX-ARCH-002 (business logic extracted into `useUpdateProfileName`; component handles only view logic), TS-TYPE-001 (no `any`; mutation variable is typed `string`), TS-TYPE-003 (edit/view modes modelled as two explicit `useState` flags rather than a single ambiguous optional).

**Behavioral expectations.**

- Given a learner is authenticated and viewing the SkillRadar page, when the active-profile header renders, then a pencil icon `<button aria-label="Edit profile name">` is visible immediately before the profile name text.
- Given the SkillRadar header is in view mode, when a learner clicks the pencil icon, then `isEditing` becomes `true`, the profile name text is replaced by an `<input autoFocus>` whose value equals the current `profile.name`, and focus lands on the input without additional user action.
- Given the input is focused and the learner types a new name, when the learner presses Enter, then `handleSave` fires: the draft is trimmed, `useUpdateProfileName.mutate` is called with the trimmed name, `isEditing` returns to `false`, and the header immediately shows the optimistic new name before the network response arrives.
- Given the input is focused and the learner types a new name, when the learner clicks away (blur event), then the same `handleSave` logic fires identically to the Enter path.
- Given the input is focused, when the learner presses Escape, then `handleCancel` fires: `draftName` resets to the original `profile.name`, `isEditing` returns to `false`, and no API call is made.
- Given the learner attempts to save, when the trimmed draft is an empty string, then the mutation is not fired and the edit is cancelled (restoring the original name), protecting the server-side min_length=1 constraint from unnecessary network round-trips.
- Given the learner attempts to save, when the trimmed draft is identical to the current `profile.name`, then the mutation is not fired and `isEditing` returns to `false` without a network call.
- Given `useUpdateProfileName.mutate` fires, when the `onMutate` callback executes, then the TanStack Query cache entry for `['profiles', practitionerId]` is updated optimistically to reflect the new name before the HTTP response arrives, so the header displays the new name with no visible latency.
- Given the `PATCH /name` request returns `200 OK`, when `onSuccess` executes, then `queryClient.invalidateQueries({ queryKey: ['profiles', practitionerId] })` is called, reconciling the cache with the server-confirmed profile object.
- Given the `PATCH /name` request returns any error (network failure, 403, 422), when `onError` executes, then the cache is rolled back to the snapshot captured in `onMutate`, the header displays the original profile name, and a toast notification reads "Failed to save profile name — please try again".
- Given `profiles.updateName` is called, when the HTTP request is issued, then the method sends `PATCH /practitioners/{practitionerId}/profiles/{profileId}/name` with body `{ name: <trimmed string> }` using the same `api.patch` helper used by existing `profiles.update`.
- Given the entire module, when `npm run build` completes in the `frontend/` directory, then the build exits with code 0 and no TypeScript type errors — consistent with the `smoke_test` defined in module-map.yaml.
- Given the pencil icon button, when it is rendered, then it carries `aria-label="Edit profile name"` and is implemented as a `<button>` element (not a `<div>` or `<span>` with onClick), satisfying RX-A11Y-001.
- Given the edit input, when it renders, then it is an `<input>` element (semantic HTML) with an associated `<label>` or accessible name via `aria-label`, satisfying RX-A11Y-002.
- Given the entire component, when any edit interaction occurs, then no value is written to `localStorage` or `sessionStorage`, satisfying RX-SEC-002 and the project-wide browser storage ban stated in `CLAUDE.md`.
- Given the pencil icon, when the profile displayed is not the learner's active profile (i.e., any non-active profile card), then the pencil icon is not rendered — the edit affordance is limited strictly to the active-profile header.

## Layers
- ui/ux

## Dependencies
- F-MOD-001

## Required Env Variables

## Lint Config

## Test Config

## Constraints

## Applicable Standards
- Total rules: 40
- Critical:
  - PY-SEC-001
  - PY-SEC-002
  - PY-SEC-003
  - TS-SEC-001
  - TS-SEC-002
  - FA-SEC-001
  - FA-SEC-002
  - RX-SEC-001
  - RX-SEC-002
  - PG-SEC-001
- High:
  - PY-SEC-004
  - PY-TEST-001
  - PY-ERR-001
  - TS-TYPE-001
  - TS-TYPE-002
  - TS-TEST-001
  - TS-ERR-001
  - FA-ARCH-001
  - FA-ARCH-002
  - RX-ARCH-001
  - RX-ARCH-002
  - RX-A11Y-001
  - PG-SEC-002
  - PG-PERF-001
  - PG-PERF-002
  - PG-DATA-001
  - PG-DATA-002
- Medium:
  - PY-ERR-002
  - PY-PERF-001
  - PY-PERF-002
  - TS-TYPE-003
  - FA-PERF-001
  - FA-PERF-002
  - RX-A11Y-002
  - RX-PERF-001
  - PG-PERF-003
- Low:
  - PY-CONV-001
  - PY-CONV-002
  - PY-CONV-003
  - TS-CONV-001

## Status
planned