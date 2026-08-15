from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from systograph.core.models.ai_system_map_v2 import CanonicalEdge
from systograph.core.models.map_build import MapBuildRequest
from systograph.core.models.recommended_next_check import RecommendedNextCheck
from systograph.core.models.scan import ProjectScanResult, ScanFact
from systograph.core.models.structural_fact import StructuralFact
from systograph.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Evidence,
)
from systograph.core.models.template import RagTemplate
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from systograph.core.services.system_map_v2_materialization_service import (
    SystemMapV2MaterializationResult,
    SystemMapV2MaterializationService,
)
from systograph.core.services.ua_edge_derivation_models import (
    UaEdgeDerivationResult,
    UaEdgeDerivationStats,
)

SOURCE_ID = "component:retriever:fixture"
TARGET_ID = "component:vector_store:fixture"


class FixedComponentDetector(ComponentDetectionService):
    def detect(
        self,
        *,
        template: RagTemplate,
        facts: Sequence[ScanFact],
        evidence: Sequence[Evidence],
        structural_facts: Sequence[StructuralFact] = (),
    ) -> ComponentDetectionResult:
        del template, facts, evidence, structural_facts
        return ComponentDetectionResult(
            components_by_slot={
                "retriever": ComponentSlot(
                    slot="retriever",
                    required_for_rag=True,
                    status="detected",
                    instances=[
                        ComponentInstance(
                            id=SOURCE_ID,
                            slot="retriever",
                            kind="retriever",
                            name="Retriever",
                            evidence_ids=["evidence:retriever"],
                        )
                    ],
                ),
                "vector_store": ComponentSlot(
                    slot="vector_store",
                    required_for_rag=True,
                    status="detected",
                    instances=[
                        ComponentInstance(
                            id=TARGET_ID,
                            slot="vector_store",
                            kind="vector_db",
                            name="Vector Store",
                            evidence_ids=["evidence:vector"],
                        )
                    ],
                ),
            },
            unmapped_components=[],
        )


class FixedUaEdgeDeriver:
    def __init__(self, edges: tuple[CanonicalEdge, ...]) -> None:
        self.edges = edges
        self.calls = 0

    def derive(
        self,
        *,
        components: Sequence[ComponentInstance],
        evidence: Sequence[Evidence],
        structural_facts: Sequence[StructuralFact],
    ) -> UaEdgeDerivationResult:
        del components, evidence, structural_facts
        self.calls += 1
        return UaEdgeDerivationResult(
            edges=self.edges,
            warnings=("UA edge derivation unresolved target=1",),
            recommended_next_checks=(
                RecommendedNextCheck(
                    id="next_check:ua-edge-relationship:fixture",
                    target_type="edge_relationship",
                    target="retriever->vector_db:query",
                    reason="No audited relationship rule matched.",
                    action="Review the relationship catalog.",
                ),
            ),
            stats=UaEdgeDerivationStats(),
        )


def _raw_scan() -> ProjectScanResult:
    return ProjectScanResult(
        evidence=[
            Evidence(
                id="evidence:retriever",
                kind="code_pattern",
                file="src/app.py",
                line_start=1,
                rule_id="code_pattern_retriever_as_retriever",
            ),
            Evidence(
                id="evidence:vector",
                kind="code_pattern",
                file="src/store.py",
                line_start=1,
                rule_id="code_pattern_vector_store_qdrant",
            ),
            Evidence(
                id="evidence:call",
                kind="ua_call_hint",
                file="src/app.py",
                line_start=8,
                rule_id="ua_call_hint_vector_store_qdrant",
            ),
        ]
    )


def _materialize(
    *,
    tmp_path: Path,
    deriver: FixedUaEdgeDeriver,
) -> SystemMapV2MaterializationResult:
    return SystemMapV2MaterializationService(
        component_detection_service=FixedComponentDetector(),
        ua_edge_derivation_service=deriver,
    ).materialize(
        raw_scan=_raw_scan(),
        project_name="fixture",
        project_root=tmp_path,
        request=MapBuildRequest(project_path=tmp_path),
        project_id="project:fixture",
    )


def test_materialization_prefers_l1_and_surfaces_edge_diagnostics(
    tmp_path: Path,
) -> None:
    # Given
    l1 = CanonicalEdge(
        edge_id="edge:l1",
        source=SOURCE_ID,
        target=TARGET_ID,
        relationship="queries_vector_store",
        status="observed",
        evidence_ids=["evidence:call"],
    )
    deriver = FixedUaEdgeDeriver((l1,))

    # When
    result = _materialize(tmp_path=tmp_path, deriver=deriver)

    # Then
    assert result.system_map.edges == [l1]
    assert result.warnings == (
        "UA edge derivation unresolved target=1",
        "UA edge derivation discarded lower-tier L2/L3=1",
    )
    assert any(
        item.id == "next_check:ua-edge-relationship:fixture"
        for item in result.system_map.recommended_next_checks
    )
    assert deriver.calls == 1


def test_template_edges_can_be_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    monkeypatch.setenv("SYSTOGRAPH_TEMPLATE_FLOW_EDGES", "off")
    deriver = FixedUaEdgeDeriver(())

    # When
    result = _materialize(tmp_path=tmp_path, deriver=deriver)

    # Then
    assert result.system_map.edges == []
    assert deriver.calls == 1


def test_template_only_materialization_is_undetermined(
    tmp_path: Path,
) -> None:
    result = _materialize(
        tmp_path=tmp_path,
        deriver=FixedUaEdgeDeriver(()),
    )

    assert len(result.system_map.edges) == 1
    assert result.system_map.edges[0].status == "undetermined"
    assert (
        result.system_map.edges[0].undetermined_reason
        == "template_adjacency_only"
    )


def test_template_edge_flag_rejects_unknown_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SYSTOGRAPH_TEMPLATE_FLOW_EDGES", "maybe")

    with pytest.raises(
        ValueError,
        match="SYSTOGRAPH_TEMPLATE_FLOW_EDGES must be 'on' or 'off'",
    ):
        _materialize(tmp_path=tmp_path, deriver=FixedUaEdgeDeriver(()))
