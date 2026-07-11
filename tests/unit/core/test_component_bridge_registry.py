from __future__ import annotations

from kai_mind.core.models.scan import ScanFact
from kai_mind.core.services.component_bridge_registry import (
    ComponentBridgeDecisionKind,
    ComponentBridgeRegistry,
)


def test_qdrant_rule_maps_to_component_with_evidence() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="docker_service",
            file="docker-compose.yml",
            path="services.qdrant.image",
            value="qdrant/qdrant:v1.12.1",
            rule_id="docker_qdrant_image_detected",
        ),
        evidence_ids=("evidence:qdrant",),
    )

    assert decision.kind is ComponentBridgeDecisionKind.COMPONENT_CANDIDATE
    assert decision.component_candidates[0].slot == "vector_store"
    assert decision.component_candidates[0].provider == "qdrant"


def test_bridge_marks_reranker_as_non_baseline_review_signal() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="code_pattern",
            file="src/rerank.py",
            path="Reranker.rerank",
            value="rerank_documents",
            rule_id="code_pattern_reranker",
        ),
        evidence_ids=("evidence:reranker",),
    )

    assert (
        decision.kind
        is ComponentBridgeDecisionKind.NON_BASELINE_CAPABILITY_SIGNAL
    )
    assert decision.unmapped_component is not None
    assert decision.unmapped_component.observed_kind == "reranker_candidate"


def test_bridge_does_not_materialize_items_without_evidence() -> None:
    decision = ComponentBridgeRegistry().match(
        ScanFact(
            kind="docker_service",
            file="docker-compose.yml",
            path="services.qdrant.image",
            value="qdrant/qdrant:v1.12.1",
            rule_id="docker_qdrant_image_detected",
        ),
        evidence_ids=(),
    )

    assert decision.kind is ComponentBridgeDecisionKind.NO_MATCH
    assert decision.component_candidates == ()
    assert decision.unmapped_component is None
