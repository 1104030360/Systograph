from __future__ import annotations

from systograph.core.models.ai_system_map_v2 import (
    CanonicalEdge,
    EdgeObservationStatus,
)
from systograph.core.models.system_map import Edge, Flow
from systograph.core.services.call_priority_edge_merge_service import (
    CallPriorityEdgeMergeService,
)


def _canonical_edge(
    *,
    edge_id: str,
    status: EdgeObservationStatus,
    reason: str | None,
    evidence_id: str,
) -> CanonicalEdge:
    return CanonicalEdge(
        edge_id=edge_id,
        source="component:retriever",
        target="component:vector",
        relationship="queries_vector_store",
        status=status,
        undetermined_reason=reason,
        evidence_ids=[evidence_id],
    )


def _template_flow() -> Flow:
    return Flow(
        id="flow:query_answer",
        edges=[
            Edge(
                id="edge:template",
                flow_id="flow:query_answer",
                from_slot="retriever",
                to_slot="vector_store",
                from_component_id="component:retriever",
                to_component_id="component:vector",
                relationship="queries_vector_store",
                status="undetermined",
                undetermined_reason="template_adjacency_only",
                evidence_ids=["evidence:template"],
            )
        ],
    )


def test_l1_wins_without_inheriting_l2_or_l3_evidence() -> None:
    # Given
    l1 = _canonical_edge(
        edge_id="edge:l1",
        status="observed",
        reason=None,
        evidence_id="evidence:call",
    )
    l2 = _canonical_edge(
        edge_id="edge:l2",
        status="undetermined",
        reason="import_only_no_call_site",
        evidence_id="evidence:import",
    )

    # When
    result = CallPriorityEdgeMergeService().merge(
        structural_edges=(l2, l1),
        template_flows=(_template_flow(),),
    )

    # Then
    assert result.edges == (l1,)
    assert result.discarded_lower_tier == 2


def test_l2_wins_over_l3_and_keeps_its_reason() -> None:
    # Given
    l2 = _canonical_edge(
        edge_id="edge:l2",
        status="undetermined",
        reason="import_only_no_call_site",
        evidence_id="evidence:import",
    )

    # When
    result = CallPriorityEdgeMergeService().merge(
        structural_edges=(l2,),
        template_flows=(_template_flow(),),
    )

    # Then
    assert result.edges == (l2,)
    assert result.discarded_lower_tier == 1


def test_template_only_edges_remain_undetermined() -> None:
    result = CallPriorityEdgeMergeService().merge(
        structural_edges=(),
        template_flows=(_template_flow(),),
    )

    assert len(result.edges) == 1
    assert result.edges[0].status == "undetermined"
    assert result.edges[0].undetermined_reason == "template_adjacency_only"
