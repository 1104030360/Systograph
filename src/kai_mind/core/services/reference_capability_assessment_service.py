from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
)
from kai_mind.core.models.capability_candidate import (
    CapabilityCandidateComponent,
)
from kai_mind.core.models.capability_reference_map import (
    CapabilityReferenceCatalog,
)
from kai_mind.core.models.profile_signal import (
    ActivationState,
    AssessmentConflict,
    ProfileStatus,
    ReferenceCapabilityAssessment,
)
from kai_mind.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)

_TYPE_TO_NODES: dict[str, tuple[str, ...]] = {
    "agent_loop": ("agent_loop", "agent_runtime"),
    "api_input": ("user_input", "api_server"),
    "chunker": ("chunker",),
    "conflict_checker": ("conflict_checker",),
    "context_composer": ("context_composer",),
    "document_loader": ("document_loader",),
    "embedder": ("embedder",),
    "embedding_model": ("embedder",),
    "graph_retriever": ("graph_retriever",),
    "hybrid_retriever": ("hybrid_retriever",),
    "index_builder": ("index_builder",),
    "llm": ("llm_answerer",),
    "long_term_memory": ("long_term_memory",),
    "memory": ("long_term_memory",),
    "metadata_extractor": ("metadata_extractor",),
    "orchestrator": ("orchestrator",),
    "parser": ("parser",),
    "query_classifier": ("query_classifier",),
    "rag_anything_system": ("rag_anything_system",),
    "reranker": ("reranker",),
    "retriever": ("dense_retriever",),
    "router": ("router",),
    "sparse_retriever": ("sparse_retriever",),
    "tool": ("tool_using_generator", "tool_network"),
    "vector_store": ("index_builder",),
    "worker_queue": ("worker_queue",),
    "workflow_node": ("orchestrator",),
}

_LEGACY_SLOT_TO_NODES: dict[str, tuple[str, ...]] = {
    "app_api_or_orchestrator": ("api_server",),
    "embedding_model": ("embedder",),
    "llm": ("llm_answerer",),
    "retriever": ("dense_retriever",),
    "vector_store": ("index_builder",),
}


class ReferenceCapabilityAssessmentService:
    def __init__(
        self,
        *,
        catalog: CapabilityReferenceCatalog | None = None,
    ) -> None:
        self._catalog = catalog or CapabilityReferenceMapLoader().load()

    def assess(
        self,
        system_map: AiSystemMapV2,
        *,
        build_id: str,
        scan_id: str,
        environment_id: str,
        capability_candidate_components: Sequence[
            CapabilityCandidateComponent
        ] = (),
    ) -> tuple[ReferenceCapabilityAssessment, ...]:
        evidence_kinds: dict[str, str] = {
            item.evidence_id: item.evidence_kind
            for item in system_map.evidence
        }
        coverage_evidence: dict[str, list[str]] = defaultdict(list)
        for evidence in system_map.evidence:
            prefix = "coverage.reference."
            if (
                evidence.evidence_kind == "explicit_negative"
                and evidence.rule_id is not None
                and evidence.rule_id.startswith(prefix)
            ):
                coverage_evidence[
                    evidence.rule_id.removeprefix(prefix)
                ].append(evidence.evidence_id)
        components_by_node: dict[str, list[CanonicalComponent]] = defaultdict(
            list
        )
        for component in system_map.components:
            for node_id in self._component_nodes(component):
                components_by_node[node_id].append(component)

        candidates_by_node: dict[str, list[CapabilityCandidateComponent]] = (
            defaultdict(list)
        )
        for candidate in capability_candidate_components:
            for node_id in _TYPE_TO_NODES.get(candidate.observed_kind, ()):
                candidates_by_node[node_id].append(candidate)
        unmapped_by_node: dict[str, list[str]] = defaultdict(list)
        for unmapped in system_map.unmapped_components:
            for node_id in _TYPE_TO_NODES.get(unmapped.observed_kind, ()):
                unmapped_by_node[node_id].append(unmapped.unmapped_id)

        return tuple(
            self._assessment(
                node.id,
                node.plane_id,
                node.activation_applicable,
                components_by_node[node.id],
                candidates_by_node[node.id],
                tuple(unmapped_by_node[node.id]),
                evidence_kinds,
                tuple(coverage_evidence[node.id]),
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
            )
            for node in self._catalog.nodes
        )

    @staticmethod
    def _component_nodes(component: CanonicalComponent) -> tuple[str, ...]:
        nodes = list(_TYPE_TO_NODES.get(component.canonical_type, ()))
        legacy_slot = component.metadata.get("legacy_slot")
        if isinstance(legacy_slot, str):
            nodes.extend(_LEGACY_SLOT_TO_NODES.get(legacy_slot, ()))
        return tuple(dict.fromkeys(nodes))

    @staticmethod
    def _assessment(
        node_id: str,
        plane_id: str,
        activation_applicable: bool,
        components: Sequence[CanonicalComponent],
        candidates: Sequence[CapabilityCandidateComponent],
        related_unmapped_component_ids: tuple[str, ...],
        evidence_kinds: Mapping[str, str],
        coverage_evidence_ids: tuple[str, ...],
        *,
        build_id: str,
        scan_id: str,
        environment_id: str,
    ) -> ReferenceCapabilityAssessment:
        component_evidence = tuple(
            dict.fromkeys(
                evidence_id
                for component in components
                for evidence_id in component.evidence_ids
            )
        )
        candidate_evidence = tuple(
            dict.fromkeys(
                evidence_id
                for candidate in candidates
                for evidence_id in candidate.evidence_ids
            )
        )
        evidence_ids = tuple(
            dict.fromkeys(
                (
                    *component_evidence,
                    *candidate_evidence,
                    *coverage_evidence_ids,
                )
            )
        )
        direct = tuple(
            item
            for item in component_evidence
            if evidence_kinds.get(item) == "direct"
        )
        indirect = tuple(
            item
            for item in evidence_ids
            if item not in direct
            and evidence_kinds.get(item) != "explicit_negative"
        )
        negative = tuple(
            item
            for item in evidence_ids
            if evidence_kinds.get(item) == "explicit_negative"
        )
        active_components = tuple(
            item
            for item in components
            if item.status in {"detected", "confirmed", "partial"}
        )
        status: ProfileStatus
        conflict_fields: tuple[AssessmentConflict, ...] = ()
        if active_components and direct and coverage_evidence_ids:
            status = "conflicted"
            conflict_fields = (
                AssessmentConflict(
                    field="status",
                    evidence_ids=tuple(
                        dict.fromkeys((*direct, *coverage_evidence_ids))
                    ),
                ),
            )
        elif active_components and direct:
            status = "detected"
        elif active_components or candidates:
            status = "partial"
        elif coverage_evidence_ids:
            status = "not_detected"
        else:
            status = "undetermined"
        activation = ReferenceCapabilityAssessmentService._activation(
            active_components,
            activation_applicable=activation_applicable,
        )
        return ReferenceCapabilityAssessment(
            reference_node_id=node_id,
            plane_id=plane_id,
            status=status,
            activation=activation,
            evidence_ids=evidence_ids,
            direct_evidence_ids=direct,
            indirect_evidence_ids=indirect,
            explicit_negative_evidence_ids=negative,
            conflict_fields=conflict_fields,
            not_detected_coverage_gate_passed=(status == "not_detected"),
            related_component_ids=tuple(
                item.component_id for item in active_components
            ),
            related_unmapped_component_ids=related_unmapped_component_ids,
            related_capability_candidate_component_ids=tuple(
                item.id for item in candidates
            ),
            build_id=build_id,
            scan_id=scan_id,
            environment_id=environment_id,
        )

    @staticmethod
    def _activation(
        components: Sequence[CanonicalComponent],
        *,
        activation_applicable: bool,
    ) -> ActivationState:
        if not activation_applicable:
            return "not_applicable"
        states = {item.activation for item in components}
        if not states:
            return "unknown"
        if len(states) > 1:
            return "conflicted"
        return next(iter(states))
