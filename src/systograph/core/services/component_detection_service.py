from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from typing import Protocol, assert_never

from systograph.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from systograph.core.models.scan import ScanFact
from systograph.core.models.structural_fact import (
    ImportStructuralFact,
    StructuralFact,
)
from systograph.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Evidence,
    SlotStatus,
    UnmappedComponent,
)
from systograph.core.models.template import RagTemplate
from systograph.core.services.ast_construction_output import (
    EXTERNAL_IMPORT_FACT_KIND,
    EXTERNAL_IMPORT_RULE_ID,
)
from systograph.core.services.component_bridge_registry import (
    ComponentBridgeDecisionKind as DecisionKind,
)
from systograph.core.services.component_bridge_registry import (
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
        structural_facts: Sequence[StructuralFact] = (),
    ) -> ComponentDetectionResult:
        evidence_lookup = EvidenceLookup(evidence)
        usage_index = ImportUsageEvidenceIndex(evidence, structural_facts)
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
                    usage_ids = usage_index.call_evidence_ids_for(fact)
                    for candidate in decision.component_candidates:
                        self._merge_candidate(
                            candidates,
                            _with_usage_evidence(candidate, usage_ids),
                        )
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
            instances_by_slot.setdefault(candidate.slot, []).append(
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
        # Capability slots outside the legacy rag-core-v1 template
        # (e.g. "parser" from the package identity layer) only appear
        # when detected, are never required, and never report missing.
        template_slot_ids = {slot.id for slot in template.slots}
        for slot_id in sorted(set(instances_by_slot) - template_slot_ids):
            slots[slot_id] = ComponentSlot(
                slot=slot_id,
                required_for_rag=False,
                status="detected",
                instances=instances_by_slot[slot_id],
            )
        return slots


class EvidenceLookup:
    def __init__(self, evidence: Sequence[Evidence]) -> None:
        # Facts and evidence both reach tens of thousands on real
        # repositories; a per-fact linear scan is quadratic.
        index: dict[
            tuple[str | None, str | None, str, str | None], list[str]
        ] = {}
        for item in evidence:
            key = (item.file, item.path, item.kind, item.rule_id)
            index.setdefault(key, []).append(item.id)
        self._ids_by_key = {
            key: tuple(sorted(ids)) for key, ids in index.items()
        }

    def ids_for_fact(self, fact: ScanFact) -> tuple[str, ...]:
        return self._ids_by_key.get(
            (fact.file, fact.path, fact.kind, fact.rule_id),
            (),
        )


class ImportUsageEvidenceIndex:
    """File-scoped join: package-identity import -> same-file call use.

    A component created from a registry-matched external import starts
    with indirect import evidence only, which caps its capability node
    at ``partial`` under the five-state contract. When the imported
    name is actually CALLED in the same file, the UA call evidence row
    at that call span (``path = "calls[caller->callee]"``, value =
    callee, hint = direct) is direct proof of the capability in use,
    so its evidence id is attached to the same component candidate.

    Deterministic and file-scoped by design, mirroring the UA callee
    resolver: the usable name is the import alias when present (the
    name actually bound in code), otherwise the imported symbol,
    otherwise the full dotted module path. A callee matches when it
    equals the usable name or extends it through an attribute access
    (``ChatMemoryBuffer.from_defaults``). No cross-file matching, no
    casefolding, no partial-name matching -- an import whose bound
    name is never called stays import-only, and that is correct.
    """

    def __init__(
        self,
        evidence: Sequence[Evidence],
        structural_facts: Sequence[StructuralFact],
    ) -> None:
        calls_by_file: dict[str, set[tuple[str, str]]] = {}
        for item in evidence:
            if (
                item.file is None
                or item.value is None
                or item.path is None
                or not item.path.startswith("calls[")
                or item.evidence_kind_hint != "direct"
            ):
                continue
            calls_by_file.setdefault(item.file, set()).add(
                (item.value, item.id)
            )
        self._calls_by_file: dict[str, tuple[tuple[str, str], ...]] = {
            file: tuple(sorted(rows)) for file, rows in calls_by_file.items()
        }
        usable_names: dict[tuple[str, str, str], set[str]] = {}
        for fact in structural_facts:
            if (
                not isinstance(fact, ImportStructuralFact)
                or fact.import_scope != "external"
                or fact.span.line_start is None
            ):
                continue
            value = fact.module
            if fact.symbol is not None:
                value = f"{value}.{fact.symbol}"
            # (file, path, value) mirrors the ScanFact the import
            # emitter derives from the same binding, so the join keys
            # on exactly the fact the bridge registry matched.
            key = (
                fact.span.file,
                f"line[{fact.span.line_start}]",
                value,
            )
            usable = fact.alias or fact.symbol or fact.module
            usable_names.setdefault(key, set()).add(usable)
        self._usable_names: dict[tuple[str, str, str], tuple[str, ...]] = {
            key: tuple(sorted(names)) for key, names in usable_names.items()
        }

    def call_evidence_ids_for(self, fact: ScanFact) -> tuple[str, ...]:
        if (
            fact.kind != EXTERNAL_IMPORT_FACT_KIND
            or fact.rule_id != EXTERNAL_IMPORT_RULE_ID
        ):
            return ()
        names = self._usable_names.get(
            (fact.file, fact.path, fact.value or "")
        )
        if names is None:
            return ()
        return tuple(
            sorted(
                {
                    evidence_id
                    for callee, evidence_id in self._calls_by_file.get(
                        fact.file, ()
                    )
                    for name in names
                    if callee == name or callee.startswith(f"{name}.")
                }
            )
        )


def _with_usage_evidence(
    candidate: ComponentCandidate,
    usage_ids: tuple[str, ...],
) -> ComponentCandidate:
    if not usage_ids:
        return candidate
    return replace(
        candidate,
        evidence_ids=tuple(
            sorted(set(candidate.evidence_ids) | set(usage_ids))
        ),
    )
