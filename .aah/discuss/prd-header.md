## Problem Statement

As an admin of the Mastery Pulse portal, you want to deactivate a particular learner so they can no longer log in, and re-activate them to restore access. This is needed to handle personnel changes, offboarding, or temporary access restrictions. The pain today is uncertainty about whether this capability exists and whether it works correctly.

## Solution

The deactivation/re-activation feature is already implemented in Phase 21. The system uses a `Practitioner.is_active` boolean column that defaults to `True`. When an admin calls `PATCH /api/v1/practitioners/{id}/deactivate`, `is_active` is set to `False` and all existing sessions for that practitioner are force-deleted. At the next login attempt, `auth.py` detects `is_active == False` and returns a 403 with `error: account_deactivated`. The admin can reverse this via `PATCH /api/v1/practitioners/{id}/reactivate`. The admin frontend exposes a `DeactivateButton` in `AdminPractitionerPage.tsx` with a confirmation modal. All data (profiles, learning paths, quiz history) is preserved through deactivation. The single known risk is that the deactivate route does not enforce org-scoping — an admin could theoretically deactivate a practitioner from another org; this risk has been accepted as admins are trusted Deloitte employees.

## User Stories

1. As an admin, I want to deactivate a learner from the admin practitioner page so that they cannot log in to the portal.
2. As an admin, I want to re-activate a previously deactivated learner so that they can resume using the portal.
3. As a deactivated learner, I want to see a clear error message when I try to log in so that I know to contact my administrator.
4. As an admin, I want the deactivation to take effect immediately (force-logout any active sessions) so that security is enforced without delay.
