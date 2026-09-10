# PRD Header — Profile Name Editing

**Feature:** Learner Profile Name Editing
**Iteration:** 1
**Date:** 2026-09-10
**Status:** Approved

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
