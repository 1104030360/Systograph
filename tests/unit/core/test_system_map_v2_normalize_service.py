from __future__ import annotations

from pathlib import Path

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalEdge,
)
from systograph.core.models.recommended_next_check import RecommendedNextCheck
from systograph.core.models.scan import ProjectScanResult
from systograph.core.models.system_map import ComponentInstance, ComponentSlot
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from systograph.core.services.system_map_v2_normalize_service import (
    SystemMapV2NormalizeService,
)


def _assemble_map(
    *,
    components: ComponentDetectionResult,
    checks: list[RecommendedNextCheck],
    edges: list[CanonicalEdge] | None = None,
) -> AiSystemMapV2:
    return SystemMapV2NormalizeService().assemble(
        project_name="fixture-project",
        project_id=None,
        project_root=Path("/fixture-project"),
        raw_scan=ProjectScanResult(),
        components=components,
        endpoints=[],
        edges=edges or [],
        risk_hints=[],
        recommended_next_checks=checks,
        no_snippets=False,
    )


def _single_component(
    *, slot_id: str, canonical_type: str
) -> ComponentDetectionResult:
    return ComponentDetectionResult(
        components_by_slot={
            slot_id: ComponentSlot(
                slot=slot_id,
                required_for_rag=True,
                status="detected",
                instances=[
                    ComponentInstance(
                        id=f"component:{slot_id}:fixture",
                        slot=slot_id,
                        kind=canonical_type,
                        name="Fixture Component",
                    )
                ],
            )
        },
        unmapped_components=[],
    )


def _assemble(
    checks: list[RecommendedNextCheck],
) -> list[RecommendedNextCheck]:
    system_map = _assemble_map(
        components=ComponentDetectionResult(
            components_by_slot={},
            unmapped_components=[],
        ),
        checks=checks,
    )
    return [
        RecommendedNextCheck(**check.model_dump())
        for check in system_map.recommended_next_checks
    ]


def test_assemble_copies_recommended_next_checks_field_for_field() -> None:
    """Given a derived check with every field populated,
    When the v2 normalize service assembles the canonical map,
    Then the canonical check carries the same five field values.
    """
    check = RecommendedNextCheck(
        id="check:privacy_exposure:component-instance:component-vector-store",
        target_type="component_instance",
        target="component:vector_store:pgvector",
        reason="External network exposure was observed.",
        action="Confirm whether this endpoint should be reachable.",
    )

    assembled = _assemble([check])

    assert assembled == [check]


def test_assemble_preserves_recommended_next_check_order() -> None:
    """Given checks in the order RecommendedNextCheckService emitted them,
    When the v2 normalize service assembles the canonical map,
    Then the canonical list keeps that order instead of re-sorting.
    """
    checks = [
        RecommendedNextCheck(
            id=f"check:runtime_readiness:component-slot:{slot}",
            target_type="component_slot",
            target=slot,
            reason="Runtime slot is missing.",
            action="Confirm the runtime wiring.",
        )
        for slot in ("retriever", "llm", "app_api_or_orchestrator")
    ]

    assembled = _assemble(checks)

    assert [item.id for item in assembled] == [item.id for item in checks]


def test_component_layer_follows_canonical_type_not_a_wrong_slot() -> None:
    """Given a component filed under the wrong legacy slot but carrying
    the right canonical type,
    When the v2 normalize service assembles the canonical map,
    Then `layer` follows the canonical type's capability node, so a slot
    mistake can no longer paint the component onto the wrong plane.

    `llm` used to force `generation` through the slot -> layer lookup;
    the type `vector_db` reaches the `index_builder` node, which lives
    in the ingestion/indexing plane.
    """
    # Given
    components = _single_component(
        slot_id="llm",
        canonical_type="vector_db",
    )

    # When
    system_map = _assemble_map(components=components, checks=[])

    # Then
    component = system_map.components[0]
    assert component.canonical_type == "vector_db"
    assert component.metadata["legacy_slot"] == "llm"
    assert component.layer == "ingestion_indexing"


def test_component_layer_ignores_a_wrong_slot_in_both_directions() -> None:
    """Given the mirror-image mistake (a prompt template filed under the
    vector store slot),
    When the v2 normalize service assembles the canonical map,
    Then the layer is the prompt builder's generation plane, not the
    slot's retrieval plane.
    """
    # Given
    components = _single_component(
        slot_id="vector_store",
        canonical_type="prompt_template",
    )

    # When
    system_map = _assemble_map(components=components, checks=[])

    # Then
    assert system_map.components[0].layer == "generation"


def test_component_layer_is_undetermined_for_an_unlisted_type() -> None:
    """Given a manual mapping whose free-text `component_kind` is not in
    the canonical type -> node map,
    When the v2 normalize service assembles the canonical map,
    Then the component lands in the undetermined band instead of
    borrowing a plane from its slot.
    """
    # Given
    components = _single_component(
        slot_id="llm",
        canonical_type="manual_mapping",
    )

    # When
    system_map = _assemble_map(components=components, checks=[])

    # Then
    assert system_map.components[0].layer == "undetermined"


def test_normalize_preserves_template_edge_status_and_reason() -> None:
    # Given
    source = ComponentInstance(
        id="component:retriever:fixture",
        slot="retriever",
        kind="retriever",
        name="Retriever",
        evidence_ids=["evidence:retriever"],
    )
    target = ComponentInstance(
        id="component:vector_store:fixture",
        slot="vector_store",
        kind="vector_db",
        name="Vector Store",
        evidence_ids=["evidence:vector"],
    )
    components = ComponentDetectionResult(
        components_by_slot={
            "retriever": ComponentSlot(
                slot="retriever",
                required_for_rag=True,
                status="detected",
                instances=[source],
            ),
            "vector_store": ComponentSlot(
                slot="vector_store",
                required_for_rag=True,
                status="detected",
                instances=[target],
            ),
        },
        unmapped_components=[],
    )
    template_edge = CanonicalEdge(
        edge_id="edge:template",
        source=source.id,
        target=target.id,
        relationship="queries_vector_store",
        status="undetermined",
        undetermined_reason="template_adjacency_only",
        evidence_ids=["evidence:retriever", "evidence:vector"],
    )

    # When
    system_map = _assemble_map(
        components=components,
        checks=[],
        edges=[template_edge],
    )

    # Then
    edge = system_map.edges[0]
    assert edge.status == "undetermined"
    assert edge.undetermined_reason == "template_adjacency_only"
