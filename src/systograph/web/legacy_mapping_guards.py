"""Shared FastAPI guards for retired legacy mapping write types."""

from __future__ import annotations

import json

from fastapi import HTTPException, Request

# The retired mapping type is deliberately inlined as a literal instead of
# imported from LegacyManualMappingType in the legacy migration module,
# for two reasons:
# 1. the literal keeps this guard independent of that module's lifetime, so
#    Plan 15 can delete the module without breaking the web layer;
# 2. this guard's lifecycle is owned by Plan 15 Task 3b bullet 5 — it must
#    NOT be deleted together with the legacy migration module.
# Restoring the import would silently re-create that deletion coupling. The
# census now tracks the enum names too, so census visibility alone is not a
# reason to keep the literal; reason 1 is.
_LEGACY_MAPPING_TYPE = "new_extension_component"


def _payload_contains_legacy_mapping_type(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("mapping_type") == _LEGACY_MAPPING_TYPE:
        return True
    edited = payload.get("edited_mapping")
    return (
        isinstance(edited, dict)
        and edited.get("mapping_type") == _LEGACY_MAPPING_TYPE
    )


async def reject_legacy_mapping_type(request: Request) -> None:
    """Fail closed with a stable code before Pydantic enum validation."""
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return
    if _payload_contains_legacy_mapping_type(payload):
        raise HTTPException(
            status_code=422,
            detail="legacy_mapping_type_read_only",
        )
