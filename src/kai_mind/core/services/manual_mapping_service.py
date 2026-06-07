"""Persist and apply user-confirmed manual mapping decisions."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Protocol
from uuid import uuid4

from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
    ManualMappingUpdate,
)
from kai_mind.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    ExtensionComponent,
    UnmappedComponent,
)
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from kai_mind.core.services.rag_template_service import RagTemplateService

SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(sk-[a-z0-9_-]{8,}|api[_-]?key\s*[:=]\s*[^,\s]+|secret\s*[:=]\s*[^,\s]+)"
)


class ManualMappingRepository(Protocol):
    """Storage boundary for manual mapping decisions."""

    def save(self, mapping: ManualMapping) -> ManualMapping:
        """Create or replace one mapping decision."""
        ...

    def get(self, mapping_id: str) -> ManualMapping | None:
        """Return one mapping decision by id."""
        ...

    def list_for_project(self, project_id: str) -> list[ManualMapping]:
        """Return all mapping decisions for one project."""
        ...


class InMemoryManualMappingRepository:
    """Process-local repository used for tests and local fallback wiring."""

    def __init__(self) -> None:
        self._items: dict[str, ManualMapping] = {}

    def save(self, mapping: ManualMapping) -> ManualMapping:
        self._items[mapping.mapping_id] = mapping
        return mapping

    def get(self, mapping_id: str) -> ManualMapping | None:
        return self._items.get(mapping_id)

    def list_for_project(self, project_id: str) -> list[ManualMapping]:
        return sorted(
            [
                mapping
                for mapping in self._items.values()
                if mapping.project_id == project_id
            ],
            key=lambda item: item.created_at,
        )


class ManualMappingService:
    """Validate, persist, and apply project-level manual mappings."""

    def __init__(
        self,
        *,
        repository: ManualMappingRepository | None = None,
        allowed_slots: Iterable[str] | None = None,
        project_id: str | None = None,
    ) -> None:
        self._repository = repository or InMemoryManualMappingRepository()
        self._allowed_slots = set(allowed_slots or _template_slots())
        self._project_id = project_id

    def create_mapping(self, draft: ManualMappingCreate) -> ManualMapping:
        self._validate_create(draft)
        now = _now()
        mapping = ManualMapping(
            **draft.model_dump(mode="python"),
            mapping_id=f"mapping:{uuid4()}",
            mapping_digest=_digest(draft.model_dump(mode="json")),
            created_at=now,
            updated_at=now,
        )
        return self._repository.save(mapping)

    def update_mapping(
        self,
        mapping_id: str,
        update: ManualMappingUpdate,
    ) -> ManualMapping:
        existing = self._repository.get(mapping_id)
        if existing is None:
            raise KeyError(mapping_id)

        payload = existing.model_dump(mode="python")
        updates = update.model_dump(exclude_none=True, mode="python")
        payload.update(updates)
        draft = ManualMappingCreate.model_validate(_draft_payload(payload))
        self._validate_create(draft)

        updated = ManualMapping(
            **draft.model_dump(mode="python"),
            mapping_id=existing.mapping_id,
            mapping_digest=_digest(draft.model_dump(mode="json")),
            created_at=existing.created_at,
            updated_at=_now(),
        )
        return self._repository.save(updated)

    def list_for_project(self, project_id: str) -> list[ManualMapping]:
        _require_text("project_id", project_id)
        return self._repository.list_for_project(project_id)

    def for_project(self, project_id: str) -> ManualMappingService:
        _require_text("project_id", project_id)
        return ManualMappingService(
            repository=self._repository,
            allowed_slots=self._allowed_slots,
            project_id=project_id,
        )

    def apply(
        self,
        result: ComponentDetectionResult,
    ) -> ComponentDetectionResult:
        """Return a detection result with confirmed mappings applied."""

        if self._project_id is None:
            return result

        mappings = [
            item
            for item in self._repository.list_for_project(self._project_id)
            if item.decision == ManualMappingDecision.CONFIRMED
        ]
        if not mappings:
            return result

        components_by_slot = deepcopy(result.components_by_slot)
        extensions = list(result.extensions)
        unmapped = list(result.unmapped_components)

        for mapping in mappings:
            if not _has_live_evidence(mapping, unmapped):
                continue
            if mapping.mapping_type == ManualMappingType.EXISTING_SLOT:
                self._apply_existing_slot(mapping, components_by_slot)
                unmapped = _remove_mapped_unmapped(mapping, unmapped)
            elif mapping.mapping_type == ManualMappingType.NEW_EXTENSION:
                extensions = self._apply_extension(mapping, extensions)
                unmapped = _remove_mapped_unmapped(mapping, unmapped)

        return ComponentDetectionResult(
            components_by_slot=components_by_slot,
            extensions=sorted(extensions, key=lambda item: item.id),
            unmapped_components=sorted(unmapped, key=lambda item: item.id),
        )

    def _validate_create(self, draft: ManualMappingCreate) -> None:
        _require_text("project_id", draft.project_id)
        if draft.source_file is not None:
            _validate_relative_posix_path(draft.source_file)
        if not draft.evidence_ids:
            raise ValueError("Manual mapping must reference evidence")
        if _contains_secret_like_value(draft.model_dump(mode="json")):
            raise ValueError(
                "Manual mapping must not contain unmasked secrets"
            )

        if draft.decision != ManualMappingDecision.CONFIRMED:
            return
        if draft.mapping_type == ManualMappingType.EXISTING_SLOT:
            self._validate_existing_slot(draft)
            return
        self._validate_extension(draft)

    def _validate_existing_slot(self, draft: ManualMappingCreate) -> None:
        _require_text("target_slot", draft.target_slot)
        _require_text("component_name", draft.component_name)
        if draft.target_slot not in self._allowed_slots:
            raise ValueError(f"Unknown target slot: {draft.target_slot}")

    def _validate_extension(self, draft: ManualMappingCreate) -> None:
        _require_text("extension_id", draft.extension_id)
        _require_text("extension_name", draft.extension_name)
        _require_text("extension_kind", draft.extension_kind)
        endpoints = set(self._allowed_slots)
        if draft.extension_id is not None:
            endpoints.add(draft.extension_id)
        for edge in draft.extension_edges:
            for key in ("from", "to"):
                endpoint = edge.get(key)
                if endpoint not in endpoints:
                    raise ValueError(
                        "Extension edge references unknown endpoint: "
                        f"{endpoint}"
                    )

    def _apply_existing_slot(
        self,
        mapping: ManualMapping,
        components_by_slot: dict[str, ComponentSlot],
    ) -> None:
        if mapping.target_slot is None or mapping.component_name is None:
            return
        slot = components_by_slot.get(mapping.target_slot)
        if slot is None:
            return

        instance = ComponentInstance(
            id=f"component:{mapping.target_slot}:{_slug(mapping.component_name)}",
            slot=mapping.target_slot,
            kind=(
                mapping.component_kind
                or mapping.observed_kind
                or "manual_mapping"
            ),
            name=mapping.component_name,
            provider=mapping.provider,
            evidence_ids=sorted(mapping.evidence_ids),
        )
        instances = [
            existing
            for existing in slot.instances
            if existing.id != instance.id
        ]
        instances.append(instance)
        components_by_slot[mapping.target_slot] = ComponentSlot(
            slot=slot.slot,
            required_for_rag=slot.required_for_rag,
            status="detected",
            instances=sorted(instances, key=lambda item: item.id),
        )

    def _apply_extension(
        self,
        mapping: ManualMapping,
        extensions: list[ExtensionComponent],
    ) -> list[ExtensionComponent]:
        if (
            mapping.extension_id is None
            or mapping.extension_name is None
            or mapping.extension_kind is None
        ):
            return extensions

        extension = ExtensionComponent(
            id=mapping.extension_id,
            name=mapping.extension_name,
            kind=mapping.extension_kind,
            status="confirmed",
            confirmed_by_user=True,
            evidence_ids=sorted(mapping.evidence_ids),
        )
        return [item for item in extensions if item.id != extension.id] + [
            extension
        ]


def _template_slots() -> set[str]:
    return {slot.id for slot in RagTemplateService.load("rag-core-v1").slots}


def _require_text(field: str, value: str | None) -> None:
    if value is None or not value.strip():
        raise ValueError(f"{field} is required")


def _validate_relative_posix_path(value: str) -> None:
    if "\\" in value or value.startswith("/"):
        raise ValueError("source_file must be a POSIX relative path")
    path = PurePosixPath(value)
    if ".." in path.parts:
        raise ValueError("source_file must stay within the project")


def _contains_secret_like_value(payload: object) -> bool:
    return (
        SECRET_VALUE_PATTERN.search(json.dumps(payload, sort_keys=True))
        is not None
    )


def _digest(payload: object) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _draft_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in payload.items()
        if key
        not in {"mapping_id", "mapping_digest", "created_at", "updated_at"}
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _has_live_evidence(
    mapping: ManualMapping,
    unmapped: list[UnmappedComponent],
) -> bool:
    mapping_evidence = set(mapping.evidence_ids)
    return any(
        mapping_evidence.intersection(component.evidence_ids)
        for component in unmapped
    )


def _remove_mapped_unmapped(
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


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "manual_mapping"
