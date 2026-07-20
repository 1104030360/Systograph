from __future__ import annotations

from collections.abc import Iterable
from typing import assert_never
from uuid import uuid4

from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingCreate,
    ManualMappingDecision,
    ManualMappingType,
    ManualMappingUpdate,
)
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from kai_mind.core.services.manual_mapping_materializer import (
    materialize_mappings,
)
from kai_mind.core.services.manual_mapping_repository import (
    InMemoryManualMappingRepository,
    ManualMappingRepository,
)
from kai_mind.core.services.manual_mapping_support import (
    contains_secret_like_value,
    digest,
    draft_payload,
    now,
    require_text,
    template_slots,
    validate_relative_posix_path,
)

__all__ = [
    "InMemoryManualMappingRepository",
    "ManualMappingRepository",
    "ManualMappingService",
]


class ManualMappingService:
    def __init__(
        self,
        *,
        repository: ManualMappingRepository | None = None,
        allowed_slots: Iterable[str] | None = None,
        project_id: str | None = None,
    ) -> None:
        self._repository = repository or InMemoryManualMappingRepository()
        self._allowed_slots = set(allowed_slots or template_slots())
        self._project_id = project_id

    def create_mapping(self, draft: ManualMappingCreate) -> ManualMapping:
        self._validate_create(draft)
        created_at = now()
        mapping = ManualMapping(
            **draft.model_dump(mode="python"),
            mapping_id=f"mapping:{uuid4()}",
            mapping_digest=digest(draft.model_dump(mode="json")),
            created_at=created_at,
            updated_at=created_at,
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
        payload.update(update.model_dump(exclude_none=True, mode="python"))
        draft = ManualMappingCreate.model_validate(draft_payload(payload))
        self._validate_create(draft)
        updated = ManualMapping(
            **draft.model_dump(mode="python"),
            mapping_id=existing.mapping_id,
            mapping_digest=digest(draft.model_dump(mode="json")),
            created_at=existing.created_at,
            updated_at=now(),
        )
        return self._repository.save(updated)

    def list_for_project(self, project_id: str) -> list[ManualMapping]:
        require_text("project_id", project_id)
        return self._repository.list_for_project(project_id)

    def for_project(self, project_id: str) -> ManualMappingService:
        require_text("project_id", project_id)
        return ManualMappingService(
            repository=self._repository,
            allowed_slots=self._allowed_slots,
            project_id=project_id,
        )

    def apply(
        self,
        result: ComponentDetectionResult,
    ) -> ComponentDetectionResult:
        if self._project_id is None:
            return result
        return materialize_mappings(result, self._confirmed_mappings())

    def apply_selected(
        self,
        result: ComponentDetectionResult,
        mapping_ids: tuple[str, ...],
    ) -> ComponentDetectionResult:
        if self._project_id is None:
            raise ValueError("project_id is required for selected mappings")
        if len(mapping_ids) != len(set(mapping_ids)):
            raise ValueError("mapping_ids must be unique")
        mappings = self._confirmed_mappings(set(mapping_ids))
        if {item.mapping_id for item in mappings} != set(mapping_ids):
            raise KeyError("selected mapping is missing or unconfirmed")
        return materialize_mappings(result, mappings)

    def _confirmed_mappings(
        self,
        selected_ids: set[str] | None = None,
    ) -> list[ManualMapping]:
        confirmed: list[ManualMapping] = []
        for mapping in self._repository.list_for_project(
            self._project_id or ""
        ):
            if (
                selected_ids is not None
                and mapping.mapping_id not in selected_ids
            ):
                continue
            match mapping.decision:
                case ManualMappingDecision.CONFIRMED:
                    confirmed.append(mapping)
                case (
                    ManualMappingDecision.REJECTED
                    | ManualMappingDecision.SKIP_FOR_NOW
                    | ManualMappingDecision.NOT_APPLICABLE
                ):
                    continue
                case unreachable:
                    assert_never(unreachable)
        return confirmed

    def _validate_create(self, draft: ManualMappingCreate) -> None:
        require_text("project_id", draft.project_id)
        if draft.source_file is not None:
            validate_relative_posix_path(draft.source_file)
        if not draft.evidence_ids:
            raise ValueError("Manual mapping must reference evidence")
        if contains_secret_like_value(draft.model_dump(mode="json")):
            raise ValueError(
                "Manual mapping must not contain unmasked secrets"
            )
        match draft.decision:
            case ManualMappingDecision.CONFIRMED:
                self._validate_confirmed(draft)
            case (
                ManualMappingDecision.REJECTED
                | ManualMappingDecision.SKIP_FOR_NOW
                | ManualMappingDecision.NOT_APPLICABLE
            ):
                return
            case unreachable:
                assert_never(unreachable)

    def _validate_confirmed(self, draft: ManualMappingCreate) -> None:
        match draft.mapping_type:
            case ManualMappingType.EXISTING_SLOT:
                target_slot = require_text("target_slot", draft.target_slot)
                require_text("component_name", draft.component_name)
                if target_slot not in self._allowed_slots:
                    raise ValueError(f"Unknown target slot: {target_slot}")
            case ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE:
                require_text(
                    "capability_candidate_id", draft.capability_candidate_id
                )
                require_text(
                    "capability_candidate_name",
                    draft.capability_candidate_name,
                )
                require_text(
                    "capability_candidate_kind",
                    draft.capability_candidate_kind,
                )
            case unreachable:
                assert_never(unreachable)
