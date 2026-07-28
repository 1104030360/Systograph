from __future__ import annotations

import inspect
import json
from pathlib import Path

import systograph.core.services.viewer_session_service as viewer_session_module
from systograph.core.services.canonical_map_loader import CanonicalMapLoader
from systograph.core.services.graph_projection_service import (
    _component_node_id,
    _unmapped_node_id,
)
from systograph.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from systograph.core.services.system_map_validation_service import (
    SystemMapValidationService,
)
from systograph.core.services.viewer_session_service import (
    ViewerSessionService,
)

FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)
INVALID_FIXTURE_PATH = Path(
    "tests/fixtures/ai_system_map/invalid_confidence.v1.json"
)
V2_FIXTURE_PATH = Path("tests/fixtures/ai_system_map/v2/grounded_rag.v2.json")


def test_v1_viewer_characterization_preserves_order_and_public_shape() -> None:
    # Given
    service = ViewerSessionService()

    # When
    result = service.load_map(FIXTURE_PATH)
    payload = result.model_dump(mode="json", by_alias=True)

    # Then
    legacy_result_keys = [
        "loaded",
        "error_reason",
        "map_json",
        "ai_system_map",
        "graph_view_model",
    ]
    assert [key for key in payload if key in legacy_result_keys] == (
        legacy_result_keys
    )
    legacy_graph_keys = [
        "schema_version",
        "source_schema_version",
        "map_json",
        "summary",
        "nodes",
        "edges",
        "details",
        "filters",
    ]
    graph_payload = payload["graph_view_model"]
    assert [key for key in graph_payload if key in legacy_graph_keys] == (
        legacy_graph_keys
    )
    assert {
        "project_id",
        "scan_id",
        "build_id",
        "environment_id",
        "generated_from_build_id",
    } <= set(graph_payload)
    graph = result.graph_view_model
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
    assert len(reference_nodes) == 52
    assert [node.source_id for node in base_nodes] == [
        "component:app_api_or_orchestrator:fastapi-chat-api",
        "component:chunking:recursive-character-splitter",
        "component:slot_placeholder:citation_or_response_composer",
        "component:data_sources:docs-folder",
        "component:document_loader:langchain-directory-loader",
        "component:embedding_model:openai-embeddings",
        "component:slot_placeholder:guardrails",
        "component:llm:openai-chat",
        "component:slot_placeholder:observability",
        "component:prompt_builder:context-prompt-template",
        "component:query_processing:query-rewrite",
        "component:retriever:qdrant-retriever",
        "component:vector_store:qdrant",
        "extension:cache:redis-response-cache",
        "unmapped:src-rag-rerank",
    ]
    assert [node.id for node in base_nodes] == [
        (
            _unmapped_node_id(node.source_id or "")
            if node.semantic_kind == "unmapped_component"
            else _component_node_id(
                node.component_id or node.source_id or "",
                node.slot,
            )
        )
        for node in base_nodes
    ]
    assert len({node.id for node in graph.nodes}) == len(graph.nodes)
    assert [edge.id for edge in graph.edges] == [
        "graph:edge:indexing:data_sources:document_loader",
        "graph:edge:indexing:document_loader:chunking",
        "graph:edge:indexing:chunking:embedding_model",
        "graph:edge:indexing:embedding_model:vector_store",
        "graph:edge:query_answer:app_api_or_orchestrator:query_processing",
        "graph:edge:query_answer:query_processing:retriever",
        "graph:edge:query_answer:retriever:vector_store",
        "graph:edge:query_answer:retriever:prompt_builder",
        "graph:edge:query_answer:prompt_builder:llm",
    ]


def test_v1_viewer_characterization_preserves_recommended_next_checks() -> (
    None
):
    result = ViewerSessionService().load_map(FIXTURE_PATH)

    assert [
        check.model_dump(mode="json")
        for check in result.graph_view_model.recommended_next_checks
    ] == [
        {
            "id": "next_check:confirm-reranker",
            "target_type": "unmapped_component",
            "target": "unmapped:src-rag-rerank",
            "reason": (
                "Confirm whether rerank.py should appear as a retriever "
                "extension in the graph."
            ),
            "action": "manual_mapping_confirmation",
        },
        {
            "id": "next_check:review-qdrant-port",
            "target_type": "component_instance",
            "target": "component:vector_store:qdrant",
            "reason": (
                "Published vector database port may affect release readiness."
            ),
            "action": "review_network_exposure",
        },
        {
            "id": "next_check:run-query-trace",
            "target_type": "endpoint",
            "target": "endpoint:local:chat-query",
            "reason": (
                "A local query endpoint was detected and can be used for "
                "opt-in replay."
            ),
            "action": "run_query_trace",
        },
    ]


def test_load_map_projects_full_graph_without_layout_or_second_truth() -> None:
    load_result = ViewerSessionService().load_map(FIXTURE_PATH)

    assert load_result.loaded is True
    assert load_result.error_reason is None
    assert load_result.ai_system_map["schema_version"] == "ai-system-map/v1"
    assert "viewer_load_result" not in load_result.ai_system_map
    assert "graph_view_model" not in load_result.ai_system_map

    graph = load_result.graph_view_model
    graph_data = graph.model_dump(mode="json", by_alias=True)
    source_ids = {node.source_id for node in graph.nodes}
    node_by_source = {
        node.source_id: node for node in graph.nodes if node.source_id
    }

    assert graph.schema_version == "graph-view-model/v1"
    assert graph.source_schema_version == "ai-system-map/v1"
    assert graph.nodes
    assert graph.edges
    assert "component:vector_store:qdrant" in source_ids
    assert "extension:cache:redis-response-cache" in source_ids
    assert "unmapped:src-rag-rerank" in source_ids

    for node in graph_data["nodes"]:
        assert {"x", "y", "position"}.isdisjoint(node)
    for edge in graph_data["edges"]:
        assert {"x", "y", "position"}.isdisjoint(edge)

    unmapped = node_by_source["unmapped:src-rag-rerank"]
    assert unmapped.status == "needs_confirmation"
    assert "unmapped" in unmapped.badges
    assert unmapped.evidence_ids == [
        "evidence:code_pattern:reranker-ambiguous"
    ]

    extension = node_by_source["extension:cache:redis-response-cache"]
    assert extension.status == "confirmed"
    assert extension.evidence_ids == ["evidence:dependency:redis"]

    retriever = node_by_source["component:retriever:qdrant-retriever"]
    vector_store = node_by_source["component:vector_store:qdrant"]
    edge = next(
        item
        for item in graph.edges
        if item.source_id == "edge:query_answer:retriever:vector_store"
    )
    assert edge.from_id == retriever.id
    assert edge.to == vector_store.id
    assert edge.flow_id == "flow:query_answer"
    assert edge.risk_hint_ids == [
        "risk:docker_published_port_exposure:component-vector-store-qdrant"
    ]

    assert "evidence:docker:qdrant-port" in graph.details.evidence_by_id
    risk = graph.details.risk_hints_by_id[
        "risk:docker_published_port_exposure:component-vector-store-qdrant"
    ]
    assert risk["target"] == "component:vector_store:qdrant"
    assert risk["severity_hint"] == "high"


def test_load_map_returns_error_payload_for_invalid_map() -> None:
    load_result = ViewerSessionService().load_map(INVALID_FIXTURE_PATH)

    assert load_result.loaded is False
    assert load_result.error_reason is not None
    assert "confidence" in load_result.error_reason
    assert load_result.ai_system_map == {}
    assert load_result.graph_view_model.nodes == []
    assert load_result.graph_view_model.edges == []
    assert load_result.graph_view_model.details.evidence_by_id == {}
    assert load_result.graph_view_model.details.risk_hints_by_id == {}


def test_native_v2_load_has_no_projection_schema_branch() -> None:
    # Given
    service = ViewerSessionService()

    # When
    result = service.load_map(V2_FIXTURE_PATH)

    # Then
    assert result.loaded is True
    assert result.ai_system_map["schema_version"] == "ai-system-map/v2"
    assert result.graph_view_model.source_schema_version == "ai-system-map/v2"
    assert result.graph_view_model.nodes
    semantic_kinds = {
        node.semantic_kind for node in result.graph_view_model.nodes
    }
    assert semantic_kinds <= {
        "reference_capability",
        "repo_component",
        "unmapped_component",
    }
    assert "reference_capability" in semantic_kinds


def test_project_to_graph_filters_highlight_and_dim_without_removing() -> None:
    system_map = SystemMapValidationService().validate(
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    )

    graph = ViewerSessionService().project_to_graph(system_map)

    filters = {item.id: item for item in graph.filters.available}
    query_filter = filters["filter:flow:query_answer"]
    unmapped_filter = filters["filter:status:needs_confirmation"]
    risk_filter = filters["filter:risk:has_risk"]

    assert graph.filters.behavior == "highlight_and_dim"
    assert graph.nodes
    assert graph.edges
    assert query_filter.matches_edge_ids
    assert query_filter.matches_node_ids
    assert unmapped_filter.matches_node_ids == [
        next(
            node.id
            for node in graph.nodes
            if node.source_id == "unmapped:src-rag-rerank"
        )
    ]
    assert risk_filter.matches_node_ids
    assert risk_filter.matches_edge_ids


def test_slot_only_edges_route_to_existing_component_nodes() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    target_edge = data["flows"][1]["edges"][2]
    assert target_edge["id"] == "edge:query_answer:retriever:vector_store"
    target_edge["from_component_id"] = None
    target_edge["to_component_id"] = None
    system_map = SystemMapValidationService().validate(data)

    graph = ViewerSessionService().project_to_graph(system_map)

    node_ids = {node.id for node in graph.nodes}
    node_by_source = {
        node.source_id: node for node in graph.nodes if node.source_id
    }
    edge = next(
        item
        for item in graph.edges
        if item.source_id == "edge:query_answer:retriever:vector_store"
    )
    assert edge.from_id in node_ids
    assert edge.to in node_ids
    assert (
        edge.from_id
        == node_by_source["component:retriever:qdrant-retriever"].id
    )
    assert edge.to == node_by_source["component:vector_store:qdrant"].id


def test_viewer_session_service_is_pure_projection_boundary() -> None:
    source = inspect.getsource(viewer_session_module)

    assert "fastapi" not in source.lower()
    assert "ProjectScanService" not in source
    assert "FilesystemProvider" not in source
    assert "ConfigParseProvider" not in source
    assert "DockerComposeProvider" not in source


def test_viewer_projection_indexes_canonical_evidence_and_risks() -> None:
    system_map = SystemMapValidationService().validate(
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    )

    viewer_load_result = ViewerSessionService().build(
        system_map,
        map_json_path=Path("outputs/ai_system_map.json"),
    )

    graph = viewer_load_result.graph_view_model
    assert viewer_load_result.loaded
    assert viewer_load_result.error_reason is None
    assert graph.source_schema_version == "ai-system-map/v1"
    assert graph.nodes
    assert graph.edges
    assert graph.details.evidence_by_id == {
        evidence.id: evidence.model_dump(mode="json")
        for evidence in system_map.evidence
    }
    assert graph.details.risk_hints_by_id.keys() == {
        risk.id for risk in system_map.risk_hints
    }
    assert graph.filters.available

    vector_node = next(
        node
        for node in graph.nodes
        if node.source_id == "component:vector_store:qdrant"
    )
    assert vector_node.slot == "vector_store"
    assert vector_node.evidence_ids
    assert vector_node.risk_hint_ids


def test_v1_compatibility_details_preserve_profile_projection_details() -> (
    None
):
    # Given
    system_map = SystemMapValidationService().validate(
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    )
    normalized = (
        CanonicalMapLoader()
        .load(system_map.model_dump(mode="json"))
        .normalized
    )
    profile_result = ProfileInferenceService().infer(
        normalized,
        build_id="build:viewer-details",
        scan_id="scan:viewer-details",
        environment_id=normalized.environment_id,
    )

    # When
    graph = (
        ViewerSessionService()
        .build(
            system_map,
            normalized_system_map=normalized,
            profile_result=profile_result,
        )
        .graph_view_model
    )

    # Then
    assert graph.details.reference_assessments_by_id
    assert graph.details.profile_findings_by_id
    assert graph.details.reference_assessments_by_id.keys() == {
        item.reference_node_id
        for item in profile_result.reference_capability_assessments
    }
    assert graph.details.profile_findings_by_id.keys() == {
        item.profile_id for item in profile_result.profiles
    }


def test_viewer_projection_does_not_mutate_canonical_map() -> None:
    system_map = SystemMapValidationService().validate(
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    )

    ViewerSessionService().build(
        system_map,
        map_json_path=Path("outputs/ai_system_map.json"),
    )

    data = system_map.model_dump(mode="json")
    assert "viewer_load_result" not in data
    assert "graph_view_model" not in data


def test_v1_viewer_keeps_public_map_with_normalized_projection() -> None:
    # Given
    service = ViewerSessionService()

    # When
    result = service.load_map(FIXTURE_PATH)

    # Then
    assert result.ai_system_map["schema_version"] == "ai-system-map/v1"
    assert result.graph_view_model.source_schema_version == "ai-system-map/v1"
    assert result.graph_view_model.nodes
    semantic_kinds = {
        node.semantic_kind for node in result.graph_view_model.nodes
    }
    assert semantic_kinds <= {
        "reference_capability",
        "repo_component",
        "unmapped_component",
    }
    assert "reference_capability" in semantic_kinds
