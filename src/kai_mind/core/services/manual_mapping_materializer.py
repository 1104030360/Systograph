from __future__ import annotations

from copy import deepcopy
from typing import assert_never

from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.mapping import ManualMapping, ManualMappingType
from kai_mind.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
)
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from kai_mind.core.services.manual_mapping_support import (
    has_live_evidence,
    remove_mapped_unmapped,
    require_text,
    slug,
)


def materialize_mappings(
    result: ComponentDetectionResult,
    mappings: list[ManualMapping],
) -> ComponentDetectionResult:
    if not mappings:
        return result
    components_by_slot = deepcopy(result.components_by_slot)
    unmapped = list(result.unmapped_components)
    candidates = list(result.capability_candidate_components)
    for mapping in mappings:
        if not has_live_evidence(mapping, unmapped):
            continue
        match mapping.mapping_type:
            case ManualMappingType.EXISTING_SLOT:
                _apply_existing_slot(mapping, components_by_slot)
            case ManualMappingType.NON_BASELINE_CAPABILITY_CANDIDATE:
                candidates = _apply_capability_candidate(mapping, candidates)
            case unreachable:
                assert_never(unreachable)
        unmapped = remove_mapped_unmapped(mapping, unmapped)
    return ComponentDetectionResult(
        components_by_slot=components_by_slot,
        unmapped_components=sorted(unmapped, key=lambda item: item.id),
        capability_candidate_components=sorted(
            candidates,
            key=lambda item: item.id,
        ),
    )


def _apply_existing_slot(
    mapping: ManualMapping,
    components_by_slot: dict[str, ComponentSlot],
) -> None:
    target_slot = require_text("target_slot", mapping.target_slot)
    component_name = require_text("component_name", mapping.component_name)
    slot = components_by_slot.get(target_slot)
    if slot is None:
        return
    instance = ComponentInstance(
        id=f"component:{target_slot}:{slug(component_name)}",
        slot=target_slot,
        kind=mapping.component_kind
        or mapping.observed_kind
        or "manual_mapping",
        name=component_name,
        provider=mapping.provider,
        evidence_ids=sorted(mapping.evidence_ids),
    )
    instances = [item for item in slot.instances if item.id != instance.id]
    instances.append(instance)
    components_by_slot[target_slot] = ComponentSlot(
        slot=slot.slot,
        required_for_rag=slot.required_for_rag,
        status="detected",
        instances=sorted(instances, key=lambda item: item.id),
    )


def _apply_capability_candidate(
    mapping: ManualMapping,
    candidates: list[CapabilityCandidateComponent],
) -> list[CapabilityCandidateComponent]:
    candidate = CapabilityCandidateComponent(
        id=require_text(
            "capability_candidate_id",
            mapping.capability_candidate_id,
        ),
        name=require_text(
            "capability_candidate_name",
            mapping.capability_candidate_name,
        ),
        observed_kind=require_text(
            "capability_candidate_kind",
            mapping.capability_candidate_kind,
        ),
        evidence_ids=sorted(mapping.evidence_ids),
        source_unmapped_component_id=mapping.source_unmapped_id,
        source_file=mapping.source_file,
        proposal_id=mapping.proposal_id,
        decision_source=mapping.decision_source,
    )
    return [item for item in candidates if item.id != candidate.id] + [
        candidate
    ]
