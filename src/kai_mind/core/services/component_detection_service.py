from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Protocol, assert_never

from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.scan import ScanFact
from kai_mind.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Evidence,
    SlotStatus,
    UnmappedComponent,
)
from kai_mind.core.models.template import RagTemplate
from kai_mind.core.services.component_bridge_registry import (
    ComponentBridgeDecisionKind as DecisionKind,
)
from kai_mind.core.services.component_bridge_registry import (
    ComponentBridgeMatcher,
    ComponentBridgeRegistry,
    ComponentCandidate,
)


@dataclass(frozen=True)
class ComponentDetectionResult:
    components_by_slot: dict[str, ComponentSlot]
    unmapped_components: list[UnmappedComponent]
    capability_candidate_components: list[CapabilityCandidateComponent] = (
        field(default_factory=list)
    )


class ManualMappingHook(Protocol):
    def apply(
        self,
        result: ComponentDetectionResult,
    ) -> ComponentDetectionResult: ...


class ComponentDetectionService:
    def __init__(
        self,
        *,
        manual_mapping_hook: ManualMappingHook | None = None,
        bridge_registry: ComponentBridgeMatcher | None = None,
    ) -> None:
        self._manual_mapping_hook = manual_mapping_hook
        self._bridge_registry = bridge_registry or ComponentBridgeRegistry()

    def detect(
        self,
        *,
        template: RagTemplate,
        facts: Sequence[ScanFact],
        evidence: Sequence[Evidence],
    ) -> ComponentDetectionResult:
        evidence_lookup = EvidenceLookup(evidence)
        candidates: dict[str, ComponentCandidate] = {}
        unmapped: dict[str, UnmappedComponent] = {}
        for fact in facts:
            evidence_ids = evidence_lookup.ids_for_fact(fact)
            decision = self._bridge_registry.match(
                fact,
                evidence_ids=evidence_ids,
            )
            match decision.kind:
                case DecisionKind.COMPONENT_CANDIDATE:
                    for candidate in decision.component_candidates:
                        self._merge_candidate(candidates, candidate)
                case (
                    DecisionKind.UNMAPPED_REVIEW_ITEM
                    | DecisionKind.NON_BASELINE_CAPABILITY_SIGNAL
                ):
                    if decision.unmapped_component is not None:
                        unmapped.setdefault(
                            decision.unmapped_component.id,
                            decision.unmapped_component,
                        )
                case DecisionKind.NO_MATCH:
                    continue
                case unreachable:
                    assert_never(unreachable)
        result = ComponentDetectionResult(
            components_by_slot=self._build_slots(
                template, candidates.values()
            ),
            unmapped_components=sorted(
                unmapped.values(), key=lambda item: item.id
            ),
        )
        if self._manual_mapping_hook is None:
            return result
        return self._manual_mapping_hook.apply(result)

    def _merge_candidate(
        self,
        candidates: dict[str, ComponentCandidate],
        candidate: ComponentCandidate,
    ) -> None:
        existing = candidates.get(candidate.id)
        if existing is None:
            candidates[candidate.id] = candidate
            return
        candidates[candidate.id] = ComponentCandidate(
            slot=existing.slot,
            kind=existing.kind,
            name=existing.name,
            provider=existing.provider,
            evidence_ids=tuple(
                sorted(
                    set(existing.evidence_ids) | set(candidate.evidence_ids)
                )
            ),
        )

    def _build_slots(
        self,
        template: RagTemplate,
        candidates: Iterable[ComponentCandidate],
    ) -> dict[str, ComponentSlot]:
        instances_by_slot: dict[str, list[ComponentInstance]] = {
            slot.id: [] for slot in template.slots
        }
        for candidate in sorted(candidates, key=lambda item: item.id):
            instances_by_slot[candidate.slot].append(
                ComponentInstance(
                    id=candidate.id,
                    slot=candidate.slot,
                    kind=candidate.kind,
                    name=candidate.name,
                    provider=candidate.provider,
                    evidence_ids=list(candidate.evidence_ids),
                )
            )
        slots: dict[str, ComponentSlot] = {}
        for slot in template.slots:
            instances = instances_by_slot[slot.id]
            status: SlotStatus = (
                "detected"
                if instances
                else "missing"
                if slot.required_for_rag_hint
                else "not_applicable"
            )
            slots[slot.id] = ComponentSlot(
                slot=slot.id,
                required_for_rag=slot.required_for_rag_hint,
                status=status,
                instances=instances,
            )
        return slots


class EvidenceLookup:
    def __init__(self, evidence: Sequence[Evidence]) -> None:
        self._evidence = tuple(evidence)

    def ids_for_fact(self, fact: ScanFact) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.id
                for item in self._evidence
                if item.file == fact.file
                and item.path == fact.path
                and item.kind == fact.kind
                and item.rule_id == fact.rule_id
            )
        )
