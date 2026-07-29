from __future__ import annotations

from tests.helpers.profile_inference import load_profile_map

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
)
from kai_mind.core.models.profile_signal import ProfileFinding
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)

RERANKER_COMPONENT_ID = "component:reranker"
RETRIEVER_COMPONENT_ID = "component:retriever"
VECTOR_STORE_COMPONENT_ID = "component:vector-store"


def _map_with_rerank_edge(*, source: str, target: str) -> AiSystemMapV2:
    """Build a map whose only `rerank` edge runs source -> target.

    The reranker component always carries direct evidence, so the
    `reranking` card's node gate passes on every scenario. Only the
    relationship gate differs between scenarios.
    """
    base = load_profile_map("non_grounded_llm_app.v2.json")
    evidence = [
        CanonicalEvidence(
            evidence_id=f"evidence:{canonical_type}",
            artifact_type="python",
            evidence_kind="direct",
            location=CanonicalEvidenceLocation(
                path=f"src/{canonical_type}.py",
                start_line=1,
            ),
            rule_id=f"test.{canonical_type}",
        )
        for canonical_type in ("reranker", "retriever", "vector_store")
    ]
    components = [
        CanonicalComponent(
            component_id=component_id,
            display_name=canonical_type.replace("_", " ").title(),
            canonical_type=canonical_type,
            layer="undetermined",
            status="detected",
            activation="enabled",
            evidence_ids=[f"evidence:{canonical_type}"],
            metadata={},
        )
        for component_id, canonical_type in (
            (RERANKER_COMPONENT_ID, "reranker"),
            (RETRIEVER_COMPONENT_ID, "retriever"),
            (VECTOR_STORE_COMPONENT_ID, "vector_store"),
        )
    ]
    edges = [
        CanonicalEdge(
            edge_id="edge:rerank",
            source=source,
            target=target,
            relationship="rerank",
            status="observed",
            evidence_ids=["evidence:retriever"],
        )
    ]
    return base.model_copy(
        update={
            "components": components,
            "edges": edges,
            "evidence": evidence,
            "endpoints": [],
            "risk_hints": [],
            "unmapped_components": [],
        }
    )


def _reranking_finding(system_map: AiSystemMapV2) -> ProfileFinding:
    result = ProfileInferenceService().infer(
        system_map,
        build_id="build:endpoint-constraint",
        scan_id="scan:endpoint-constraint",
        environment_id=system_map.environment_id,
    )
    return next(
        item for item in result.profiles if item.profile_id == "reranking"
    )


def test_relationship_edge_off_required_components_cannot_detect() -> None:
    # Given: a detected reranker plus a `rerank`-named edge whose two
    # endpoints are both unrelated to the reranking card.
    system_map = _map_with_rerank_edge(
        source=RETRIEVER_COMPONENT_ID,
        target=VECTOR_STORE_COMPONENT_ID,
    )

    # When: the sole owner of profile assessment evaluates the card.
    finding = _reranking_finding(system_map)

    # Then: a matching relationship name alone never satisfies the gate.
    assert finding.status == "partial"
    assert "evidence:retriever" not in finding.evidence_ids


def test_relationship_edge_on_required_component_detects() -> None:
    # Given: the same map except the `rerank` edge lands one endpoint on
    # the component backing the card's required `reranker` node.
    system_map = _map_with_rerank_edge(
        source=RETRIEVER_COMPONENT_ID,
        target=RERANKER_COMPONENT_ID,
    )

    # When: the sole owner of profile assessment evaluates the card.
    finding = _reranking_finding(system_map)

    # Then: one endpoint on a required component is enough — the
    # constraint stays at "at least one endpoint", not "both endpoints".
    assert finding.status == "detected"
    assert "evidence:retriever" in finding.direct_evidence_ids


def test_relationship_edge_reaching_required_component_detects() -> None:
    # Given: the reverse direction of the same wiring.
    system_map = _map_with_rerank_edge(
        source=RERANKER_COMPONENT_ID,
        target=VECTOR_STORE_COMPONENT_ID,
    )

    # When: the sole owner of profile assessment evaluates the card.
    finding = _reranking_finding(system_map)

    # Then: the constraint is direction-agnostic.
    assert finding.status == "detected"
