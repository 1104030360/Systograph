"""Shared FastAPI guards for retired legacy mapping write types."""

from __future__ import annotations

import json

from fastapi import HTTPException, Request

from systograph.core.services.legacy_manual_mapping_migration_service import (
    LegacyManualMappingType,
)

_LEGACY_MAPPING_TYPE = LegacyManualMappingType.NEW_EXTENSION.value


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
