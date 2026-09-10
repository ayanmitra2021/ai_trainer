# Application Flow — Profile Name Editing

## Happy Path

1. Learner is authenticated and views their active profile in the SkillRadar component
2. A pencil icon (✏️) is rendered immediately before the profile name in the SkillRadar header
3. Learner clicks the pencil icon → component state `isEditing = true`
4. The profile name text is replaced by an `<input autoFocus>` containing the current name as the draft value
5. Learner types a new name
6. Learner presses **Enter** OR clicks elsewhere (**blur**):
   - `useUpdateProfileName` mutation fires
   - `onMutate`: TanStack Query snapshots the old name and sets the new name optimistically in the cache
   - UI immediately shows the new name (optimistic)
   - `PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}/name` request sent
   - Server validates ownership, active status, and name constraints
   - `200 OK` returned → `onSuccess`: invalidates `['profiles', profileId]` query key
   - `isEditing = false`
7. Learner sees the new name in the header

## Cancel Path

4. (same as above)
5. Learner presses **Escape**:
   - `isEditing = false`
   - Draft value discarded — no API call
   - Original name remains displayed

## Error Path

6. API returns error (network failure, 403, 422, etc.):
   - `onError`: TanStack Query rolls back the optimistic name to the snapshot
   - Error toast is displayed ("Failed to save profile name — please try again")
   - `isEditing = false`

## Auth Flow

- Endpoint requires a valid practitioner session cookie (`get_current_practitioner` dependency)
- If no session → `401 Unauthorized` (handled by the existing auth layer; learner is redirected to login)
- If session practitioner ≠ URL practitioner_id → `403 Forbidden`
