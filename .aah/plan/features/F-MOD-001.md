## Id
F-MOD-001

## Title
Profile Name PATCH Endpoint

## Module Ref
MOD-001

## Description
This module adds a dedicated `PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}/name` endpoint to the existing FastAPI backend. It is a brownfield carve-out — no Alembic migration is required because `PractitionerProfile.name` (`VARCHAR(500) NOT NULL`) already exists (see `.aah/architecture/data-model.md` § "Relevant Existing Columns").

**What it does:** Allows an authenticated learner to rename their own active profile without being blocked by the profile lock. The existing `PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}` route (line 378 of `backend/app/api/routes/profiles.py`) returns HTTP 403 for any edit on a locked profile. This new endpoint is the intentional carve-out: it skips the `is_locked` gate entirely and updates only the `name` field. All other profile fields, and the lock semantics of the existing PATCH route, remain completely untouched.

**How it is implemented:**

1. **New route** in `backend/app/api/routes/profiles.py` — following the pattern of the existing `activate_profile` route (line 404 of that file). The handler must:
   - Require an authenticated practitioner session via `Depends(require_any_authenticated)`.
   - Call `enforce_self_or_admin(session, practitioner_id)`, raising HTTP 403 if the session practitioner does not match the URL `practitioner_id`.
   - Look up the profile by `profile_id`; return HTTP 404 if not found or if `profile.practitioner_id != practitioner_id`.
   - Reject non-active profiles (`profile.is_active != True`) with HTTP 404.
   - NOT inspect `profile.is_locked` — the dedicated endpoint is the only bypass the architecture authorises (see `.aah/discuss/discuss-prd.md` § "Decision Registry Summary", slug `profile-name-backend-approach`).
   - Apply `profile.name = body.name.strip()` and update `profile.updated_at`.
   - Commit and refresh, then return the updated profile as `ProfileRead` (same response shape as the existing profile GET routes).

2. **New Pydantic schema** in `backend/app/schemas/profiles.py`:
   ```python
   class ProfileNameUpdate(BaseModel):
       name: str = Field(..., min_length=1, max_length=500)
   ```
   This is the sole accepted input schema. No other profile fields are exposed by this endpoint.

3. **No other changes** — `ProfileUpdate`, the existing `PATCH /profiles/{profile_id}` route, the `is_locked` gate at line 378, and all other profile routes are left entirely unchanged.

**Architecture references:**
- Endpoint contract, status codes, and response shape: `.aah/architecture/architecture-overview.md` § "New Endpoint"
- Relevant DB columns and schema invariants: `.aah/architecture/data-model.md` § "Relevant Existing Columns" and § "Pydantic Schema Changes"
- End-to-end happy / cancel / error paths: `.aah/architecture/application-flow.md`
- Product rationale and decision log: `.aah/discuss/discuss-prd.md` § "Decision Registry Summary"
- Applicable standards (FA-SEC-001, FA-SEC-002, FA-ARCH-001, FA-ARCH-002, PY-SEC-002, PY-SEC-003, PY-TEST-001): `.aah/plan/resolved-standards.yaml`

**Behavioral expectations:**

- Given a valid practitioner session, when `PATCH .../profiles/{profile_id}/name` is called with `{"name": "New Name"}` and the caller is the owner of an active profile, then the response is HTTP 200 and the body is a `ProfileRead` object with `name == "New Name"`.
- Given a valid practitioner session, when the endpoint is called with `{"name": "  trimmed  "}`, then `profile.name` is persisted as `"trimmed"` (leading and trailing whitespace stripped before persistence).
- Given a valid practitioner session whose `practitioner_id` does not match the `practitioner_id` URL path parameter, when the endpoint is called, then HTTP 403 is returned.
- Given a valid practitioner session that owns the profile but the profile's `is_active` is `False`, when the endpoint is called, then HTTP 404 is returned.
- Given a valid practitioner session, when the endpoint is called with `{"name": ""}` (empty string after trimming) or with the `name` field absent from the body, then HTTP 422 is returned.
- Given a valid practitioner session, when the endpoint is called with a `name` value exceeding 500 characters, then HTTP 422 is returned.
- Given a valid practitioner session that owns an active profile where `is_locked` is `True`, when the endpoint is called with a valid name, then HTTP 200 is returned and the name is updated — the lock gate is NOT consulted by this endpoint.
- Given no authenticated session (missing or invalid cookie), when the endpoint is called, then HTTP 401 is returned.
- Given a `profile_id` that does not exist in the database, when the endpoint is called, then HTTP 404 is returned.
- Given the name update succeeds, when the response is inspected, then `is_locked`, `certification_id`, `questionnaire_snapshot`, and `is_active` on the returned profile are identical to their pre-update values.
- Given the existing `PATCH /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}` route, when called with any body on a locked profile, then HTTP 403 is still returned — the new endpoint does not alter this behavior.
- Given `DATABASE_URL` is absent from the environment, when the application starts, then the startup env checker raises `ERR_CDR_78_EX_CONFIG` naming the missing variable before any route is reachable.

## Layers
- api

## Dependencies

## API Contracts
```yaml
produces:
  - operation_id: patch_profile_name
    method: PATCH
    path: /api/v1/practitioners/{practitioner_id}/profiles/{profile_id}/name
    schema_file: schema/MOD-001-api-schema.yaml
    request_schema: ProfileNameUpdate
    response_schema: ProfileRead
    responses:
      200: ProfileRead — updated profile object with name reflecting the new value
      401: Unauthorized — no valid practitioner session
      403: Forbidden — session practitioner_id does not match URL practitioner_id
      404: Not Found — profile does not exist, or profile is not active
      422: Unprocessable Entity — name is empty, missing, or exceeds 500 characters
```

## Required Env Variables
- DATABASE_URL — PostgreSQL connection string read by the existing SQLAlchemy engine

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