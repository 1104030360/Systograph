from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import assert_never

from systograph.core.models.mapping import ManualMapping, ManualMappingType
from systograph.core.models.system_map import UnmappedComponent
from systograph.core.services.rag_template_service import RagTemplateService

SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|api[_-]?key\s*[:=]\s*[^,\s]+|secret\s*[:=]\s*[^,\s]+)"
)


def template_slots() -> set[str]:
    return {slot.id for slot in RagTemplateService.load("rag-core-v1").slots}


def require_text(field: str, value: str | None) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{field} is required")
    return value


def validate_relative_posix_path(value: str) -> None:
    if "\\" in value or value.startswith("/"):
        raise ValueError("source_file must be a POSIX relative path")
    if ".." in PurePosixPath(value).parts:
        raise ValueError("source_file must stay within the project")


def contains_secret_like_value(payload: object) -> bool:
    return (
        SECRET_VALUE_PATTERN.search(json.dumps(payload, sort_keys=True))
        is not None
    )


def digest(payload: object) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def draft_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in payload.items()
        if key
        not in {"mapping_id", "mapping_digest", "created_at", "updated_at"}
    }


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def has_live_evidence(
    mapping: ManualMapping,
    unmapped: list[UnmappedComponent],
) -> bool:
    match mapping.mapping_type:
        case (
            ManualMappingType.EXISTING_SLOT
            | ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE
        ):
            return has_live_unmapped_evidence(mapping, unmapped)
        case unreachable:
            assert_never(unreachable)


def has_live_unmapped_evidence(
    mapping: ManualMapping,
    unmapped: list[UnmappedComponent],
) -> bool:
    mapping_evidence = set(mapping.evidence_ids)
    return any(
        mapping_evidence.intersection(component.evidence_ids)
        for component in unmapped
    )


def remove_mapped_unmapped(
    mapping: ManualMapping,
    unmapped: list[UnmappedComponent],
) -> list[UnmappedComponent]:
    mapping_evidence = set(mapping.evidence_ids)
    return [
        component
        for component in unmapped
        if not (
            (
                mapping.source_unmapped_id
                and component.id == mapping.source_unmapped_id
            )
            or mapping_evidence.intersection(component.evidence_ids)
        )
    ]


def slug(value: str) -> str:
    value_slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value_slug or "manual_mapping"
