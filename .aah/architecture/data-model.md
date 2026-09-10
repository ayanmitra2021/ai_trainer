# Data Model — Profile Name Editing

**No schema changes required for this feature.**

The `PractitionerProfile.name` column (`VARCHAR(500), NOT NULL`) already exists
in `backend/app/db/models.py` (line 1624). No Alembic migration is needed.

## Relevant Existing Columns

| Table | Column | Type | Notes |
|-------|--------|------|-------|
| `practitioner_profiles` | `name` | `VARCHAR(500) NOT NULL` | The field being updated |
| `practitioner_profiles` | `is_locked` | `BOOLEAN` | NOT touched by new endpoint |
| `practitioner_profiles` | `is_active` | `BOOLEAN` | Server validates `== True` before allowing rename |
| `practitioner_profiles` | `practitioner_id` | `UUID FK` | Ownership check: must match session practitioner |

## Pydantic Schema Changes

New schema added to `backend/app/schemas/profiles.py`:

```python
class ProfileNameUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
```

The existing `ProfileUpdate` schema (which includes `name: str | None`) is unchanged.
