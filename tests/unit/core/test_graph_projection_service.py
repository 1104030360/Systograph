from __future__ import annotations

import inspect
from importlib import import_module
from pathlib import Path

import pytest
from pydantic import ValidationError
from tests.helpers.fixtures import rag_project_fixture_path

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalEvidence,
    CanonicalEvidenceLocation,
    CanonicalProject,
    CanonicalRiskHint,
)
from systograph.core.models.system_map import RagSystemMap
from systograph.core.models.viewer import GraphNodeModel
from systograph.core.services.capability_reference_map_loader import (
    CapabilityReferenceMapLoader,
)
from systograph.core.services.component_detection_service import (
    ComponentDetectionService,
)
from systograph.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from systograph.core.services.flow_derivation_service import (
    FlowDerivationService,
)
from systograph.core.services.graph_projection_service import (
    GraphProjectionService,
    _assert_unique_graph_node_ids,
    _slug,
)
from systograph.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from systograph.core.services.project_scan_service import ProjectScanService
from systograph.core.services.rag_template_service import RagTemplateService
from systograph.core.services.risk_hint_service import RiskHintService
from systograph.core.services.system_map_normalize_service import (
    SystemMapNormalizeService,
)
from systograph.core.services.system_map_v1_to_v2_adapter import (
    SystemMapV1ToV2Adapter,
)
from systograph.core.services.system_map_validation_service import (
    SystemMapValidationService,
)

V1_RICH_MAP = (
    Path(__file__).parents[2]
    / "fixtures"
    / "ai_system_map"
    / "valid_rich_frontend_sample.v1.json"
)


@pytest.fixture
def canonical_map() -> AiSystemMapV2:
    legacy = RagSystemMap.model_validate_json(
        V1_RICH_MAP.read_text(encoding="utf-8")
    )
    return SystemMapV1ToV2Adapter().adapt_to_canonical(legacy)


def test_graph_projection_service_contract_is_available() -> None:
    # Given
    module_name = "systograph.core.services.graph_projection_service"

    # When
    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        pytest.fail(
            "GraphProjectionService module is not implemented",
            pytrace=False,
        )

    # Then
    assert hasattr(module, "GraphProjectionService")


def test_graph_projection_service_exposes_narrow_project_interface() -> None:
    # Given
    module = import_module("systograph.core.services.graph_projection_service")
    service_type = module.GraphProjectionService

    # When
    signature = inspect.signature(service_type.project)

    # Then
    assert list(signature.parameters) == [
        "self",
        "system_map",
        "profile_result",
        "artifact_ref",
        "recommended_next_checks",
    ]
    assert signature.parameters["profile_result"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )
    assert signature.parameters["artifact_ref"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )
    assert signature.parameters["recommended_next_checks"].kind is (
        inspect.Parameter.KEYWORD_ONLY
    )


def test_projects_normalized_base_graph_with_canonical_details(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    expected_source_ids = [
        component.component_id for component in canonical_map.components
    ] + [
        component.unmapped_id
        for component in canonical_map.unmapped_components
    ]

    # When
    graph = GraphProjectionService().project(
        canonical_map,
        artifact_ref="builds/B1/ai_system_map.json",
    )

    # Then
    assert graph.schema_version == "graph-view-model/v1"
    assert graph.source_schema_version == "ai-system-map/v1"
    assert graph.map_json == "builds/B1/ai_system_map.json"
    reference_nodes = [
        node
        for node in graph.nodes
        if node.semantic_kind == "reference_capability"
    ]
    base_nodes = [
        node
        for node in graph.nodes
        if node.semantic_kind in {"repo_component", "unmapped_component"}
    ]
    assert [node.reference_node_id for node in reference_nodes] == [
        node.id for node in CapabilityReferenceMapLoader().load().nodes
    ]
    assert [node.source_id for node in base_nodes] == expected_source_ids
    assert all(
        node.semantic_kind == "repo_component"
        for node in base_nodes[: len(canonical_map.components)]
    )
    assert base_nodes[-1].semantic_kind == "unmapped_component"
    assert [edge.source_id for edge in graph.edges] == [
        edge.edge_id for edge in canonical_map.edges
    ]
    node_ids_by_source = {
        node.source_id: node.id for node in graph.nodes if node.source_id
    }
    assert all(
        edge.from_id == node_ids_by_source[canonical_edge.source]
        and edge.to == node_ids_by_source[canonical_edge.target]
        for edge, canonical_edge in zip(
            graph.edges,
            canonical_map.edges,
            strict=True,
        )
    )
    assert list(graph.details.evidence_by_id) == [
        evidence.evidence_id for evidence in canonical_map.evidence
    ]
    assert list(graph.details.risk_hints_by_id) == [
        risk.risk_id for risk in canonical_map.risk_hints
    ]
    assert graph.summary == {
        "project_name": canonical_map.project.name,
        "schema_version": canonical_map.schema_version,
        "node_count": len(expected_source_ids) + 52,
        "edge_count": len(canonical_map.edges),
    }


def test_rejects_absolute_artifact_reference(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    absolute_ref = "/private/builds/B1/ai_system_map.json"

    # When / Then
    with pytest.raises(
        ValueError,
        match="artifact_ref must be build-relative",
    ):
        GraphProjectionService().project(
            canonical_map,
            artifact_ref=absolute_ref,
        )


def test_base_projection_is_deterministic_and_does_not_mutate_map(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    original = canonical_map.model_copy(deep=True)
    service = GraphProjectionService()

    # When
    first = service.project(canonical_map)
    first.nodes[0].evidence_ids.append("evidence:viewer-only")
    second = service.project(canonical_map)

    # Then
    assert canonical_map == original
    assert "evidence:viewer-only" not in second.nodes[0].evidence_ids
    assert [item.id for item in second.filters.available]
    assert all(
        item.matches_node_ids
        or item.matches_edge_ids
        or (
            item.active is False
            and item.kind in {"profile_attachment", "capability_candidate"}
        )
        for item in second.filters.available
    )
    assert "filter:risk:has_risk" in {
        item.id for item in second.filters.available
    }


def test_profile_overlay_is_additive_and_never_fabricates_topology_edges(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    profile_result = ProfileInferenceService().infer(
        canonical_map,
        build_id="build:b1",
        scan_id="scan:s1",
        environment_id=canonical_map.environment_id,
    )

    # When
    graph = GraphProjectionService().project(
        canonical_map,
        profile_result=profile_result,
    )

    # Then
    assert (
        len(
            [
                node
                for node in graph.nodes
                if node.semantic_kind == "reference_capability"
            ]
        )
        == 52
    )
    assert (
        len(
            [
                node
                for node in graph.nodes
                if node.semantic_kind == "profile_attachment"
            ]
        )
        > 0
    )
    assert len(graph.edges) == len(canonical_map.edges)
    assert all(
        edge.source_id in {item.edge_id for item in canonical_map.edges}
        for edge in graph.edges
    )
    assert graph.mapping_completeness is profile_result.mapping_completeness
    assert list(graph.details.profile_findings_by_id) == [
        finding.profile_id for finding in profile_result.profiles
    ]
    profile_filter = next(
        item
        for item in graph.filters.available
        if item.id == "filter:profile_attachments"
    )
    assert profile_filter.active is False
    assert graph.relationships


def test_projection_emits_six_backend_owned_lenses(
    canonical_map: AiSystemMapV2,
) -> None:
    # When
    graph = GraphProjectionService().project(canonical_map)

    # Then
    assert [lens.id for lens in graph.filters.lenses] == [
        "lens:data",
        "lens:control",
        "lens:evidence",
        "lens:governance",
        "lens:source",
        "lens:risk",
    ]
    assert all(
        lens.supported
        or (
            not lens.matches_node_ids
            and not lens.matches_edge_ids
            and lens.unavailable_reason
        )
        for lens in graph.filters.lenses
    )
    assert graph.filters.behavior == "highlight_and_dim"


def test_lens_membership_references_only_projected_graph_ids(
    canonical_map: AiSystemMapV2,
) -> None:
    # When
    graph = GraphProjectionService().project(canonical_map)

    # Then
    node_ids = {node.id for node in graph.nodes}
    edge_ids = {edge.id for edge in graph.edges}
    assert all(
        set(lens.matches_node_ids) <= node_ids
        and set(lens.matches_edge_ids) <= edge_ids
        for lens in graph.filters.lenses
    )


def test_projection_models_reject_field_reassignment(
    canonical_map: AiSystemMapV2,
) -> None:
    # Given
    graph = GraphProjectionService().project(canonical_map)

    # When / Then
    with pytest.raises(ValidationError, match="frozen"):
        graph.nodes[0].label = "Caller mutation"


def _canonical_map_from_rag_fixture(fixture_name: str) -> AiSystemMapV2:
    fixture_path = rag_project_fixture_path(fixture_name)
    raw_scan = ProjectScanService().scan(fixture_path)
    template = RagTemplateService.load("rag-core-v1")
    components = ComponentDetectionService().detect(
        template=template,
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
    )
    endpoints = EndpointDetectionService().detect(
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
        components=components,
    )
    risk_hints = RiskHintService().derive(
        facts=raw_scan.facts,
        evidence=raw_scan.evidence,
        issues=raw_scan.issues,
        components=components,
        endpoints=endpoints,
    )
    flows = FlowDerivationService().derive(
        template=template,
        components=components,
    )
    legacy = SystemMapNormalizeService().assemble(
        project_name=fixture_name,
        raw_scan=raw_scan,
        template=template,
        components=components,
        endpoints=endpoints,
        flows=flows,
        risk_hints=risk_hints,
    )
    validated = SystemMapValidationService().validate(
        legacy.model_dump(mode="json")
    )
    return SystemMapV1ToV2Adapter().adapt_to_canonical(validated)


def test_assert_unique_graph_node_ids_fails_loud_on_duplicate() -> None:
    # Given: two nodes that share a graph id (lossy-encoding bug class)
    nodes = [
        GraphNodeModel(
            id="node:component:collision",
            source_id="component:vector_store:a/b",
            label="Left",
        ),
        GraphNodeModel(
            id="node:component:collision",
            source_id="component:vector_store:a-b",
            label="Right",
        ),
    ]

    # When / Then
    with pytest.raises(ValueError, match="duplicate graph node id"):
        _assert_unique_graph_node_ids(nodes)


def test_file_targeted_risks_attach_only_via_shared_evidence() -> None:
    # Given: file risk with orphan evidence stays details-only;
    #        file risk whose evidence_id is on a component mounts to that node.
    orphan_evidence_id = "evidence:parse_error:orphan-settings"
    shared_evidence_id = "evidence:parse_error:shared-settings"
    component_id = "component:llm:openai-chat"
    system_map = AiSystemMapV2(
        schema_version="ai-system-map/v2",
        system_type="ai_system",
        project=CanonicalProject(name="file-risk-membership"),
        evidence=[
            CanonicalEvidence(
                evidence_id=orphan_evidence_id,
                artifact_type="config",
                evidence_kind="direct",
                location=CanonicalEvidenceLocation(path="config/orphan.yaml"),
                extract_summary="orphan parse error",
            ),
            CanonicalEvidence(
                evidence_id=shared_evidence_id,
                artifact_type="config",
                evidence_kind="direct",
                location=CanonicalEvidenceLocation(path="config/shared.yaml"),
                extract_summary="shared parse error",
            ),
        ],
        components=[
            CanonicalComponent(
                component_id=component_id,
                display_name="OpenAI Chat",
                canonical_type="llm",
                layer="generation",
                status="detected",
                activation="enabled",
                evidence_ids=[shared_evidence_id],
                metadata={"legacy_slot": "llm"},
            ),
        ],
        risk_hints=[
            CanonicalRiskHint(
                risk_id="risk:config_parse_error:orphan",
                type="partial_scan",
                target="config/orphan.yaml",
                target_type="file",
                evidence_id=orphan_evidence_id,
                rule_id="config_parse_error",
                rationale="Orphan file risk without component evidence.",
            ),
            CanonicalRiskHint(
                risk_id="risk:config_parse_error:shared",
                type="partial_scan",
                target="config/shared.yaml",
                target_type="file",
                evidence_id=shared_evidence_id,
                rule_id="config_parse_error",
                rationale="File risk sharing evidence with a component.",
            ),
        ],
    )

    # When
    graph = GraphProjectionService().project(system_map)

    # Then
    node = next(item for item in graph.nodes if item.source_id == component_id)
    assert "risk:config_parse_error:orphan" in graph.details.risk_hints_by_id
    assert "risk:config_parse_error:shared" in graph.details.risk_hints_by_id
    assert "risk:config_parse_error:orphan" not in node.risk_hint_ids
    assert "risk:config_parse_error:shared" in node.risk_hint_ids
    risk_filter = next(
        item
        for item in graph.filters.available
        if item.id == "filter:risk:has_risk"
    )
    assert node.id in risk_filter.matches_node_ids


def test_slug_colliding_component_ids_remain_distinct_graph_nodes() -> None:
    # Given: two canonical ids that collapse under naive non-alnum→'-' slugging
    left_id = "component:vector_store:a/b"
    right_id = "component:vector_store:a-b"
    assert _slug(left_id) == _slug(right_id) == "component-vector-store-a-b"
    system_map = AiSystemMapV2(
        schema_version="ai-system-map/v2",
        system_type="ai_system",
        project=CanonicalProject(name="slug-collision"),
        components=[
            CanonicalComponent(
                component_id=left_id,
                display_name="Left Store",
                canonical_type="vector_store",
                layer="retrieval",
                status="detected",
                activation="enabled",
                metadata={"legacy_slot": "vector_store"},
            ),
            CanonicalComponent(
                component_id=right_id,
                display_name="Right Store",
                canonical_type="vector_store",
                layer="retrieval",
                status="detected",
                activation="enabled",
                metadata={"legacy_slot": "vector_store"},
            ),
        ],
        edges=[
            CanonicalEdge(
                edge_id="edge:query_answer:left:right",
                source=left_id,
                target=right_id,
                relationship="writes_to",
                status="undetermined",
                undetermined_reason="synthetic slug-collision fixture",
            ),
        ],
    )

    # When
    graph = GraphProjectionService().project(system_map)

    # Then: graph ids stay injective; topology edge is not a false self-loop
    by_source = {
        node.source_id: node for node in graph.nodes if node.source_id
    }
    left_node = by_source[left_id]
    right_node = by_source[right_id]
    assert left_node.id != right_node.id
    assert "~" in left_node.id and "~" in right_node.id
    assert len({node.id for node in graph.nodes}) == len(graph.nodes)
    edge = graph.edges[0]
    assert edge.from_id == left_node.id
    assert edge.to == right_node.id
    assert edge.from_id != edge.to


def test_graph_node_ids_are_stable_across_repeated_projections(
    canonical_map: AiSystemMapV2,
) -> None:
    # When
    first = GraphProjectionService().project(canonical_map)
    second = GraphProjectionService().project(canonical_map)

    # Then
    assert [node.id for node in first.nodes] == [
        node.id for node in second.nodes
    ]
    assert [edge.id for edge in first.edges] == [
        edge.id for edge in second.edges
    ]


def test_endpoint_risks_attach_to_component_from_qdrant_fixture() -> None:
    # Given: real fixture produces endpoint-targeted docker port risks
    canonical_map = _canonical_map_from_rag_fixture("basic_qdrant_ollama_rag")
    endpoint_risks = [
        risk
        for risk in canonical_map.risk_hints
        if risk.rule_id == "docker_published_port_exposure"
        and risk.target_type == "endpoint"
    ]
    assert len(endpoint_risks) == 2
    endpoint_by_id = {
        endpoint.endpoint_id: endpoint for endpoint in canonical_map.endpoints
    }

    # When
    graph = GraphProjectionService().project(canonical_map)

    # Then: risks stay in details AND mount onto owning component nodes/edges
    nodes_by_source = {
        node.source_id: node for node in graph.nodes if node.source_id
    }
    risk_filter = next(
        item
        for item in graph.filters.available
        if item.id == "filter:risk:has_risk"
    )
    for risk in endpoint_risks:
        assert risk.risk_id in graph.details.risk_hints_by_id
        endpoint = endpoint_by_id[risk.target]
        assert endpoint.component_id is not None
        node = nodes_by_source[endpoint.component_id]
        assert risk.risk_id in node.risk_hint_ids
        assert node.id in risk_filter.matches_node_ids
        related_edges = [
            edge
            for edge in graph.edges
            if edge.from_id == node.id or edge.to == node.id
        ]
        assert all(
            risk.risk_id in edge.risk_hint_ids for edge in related_edges
        )
