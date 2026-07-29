from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import pytest

from kai_mind.core.models.viewer import (
    GraphDetailsModel,
    GraphEndpointModel,
    GraphFiltersModel,
    GraphNodeModel,
    GraphRecommendedNextCheckModel,
    GraphViewModel,
)
from kai_mind.core.services.graph_markdown_renderer import (
    GraphMarkdownRenderer,
)
from kai_mind.core.services.graph_mermaid_renderer import (
    GraphMermaidRenderer,
)
from kai_mind.core.services.graph_projection_service import (
    GraphProjectionService,
)
from kai_mind.core.services.profile_inference_service import (
    ProfileInferenceService,
)
from kai_mind.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationService,
)

V2_FIXTURE = Path("tests/fixtures/ai_system_map/v2/grounded_rag.v2.json")
V2_FIXTURE_DIR = V2_FIXTURE.parent


@pytest.mark.parametrize(
    ("module_name", "type_name"),
    [
        (
            "kai_mind.core.services.graph_mermaid_renderer",
            "GraphMermaidRenderer",
        ),
        (
            "kai_mind.core.services.graph_markdown_renderer",
            "GraphMarkdownRenderer",
        ),
    ],
)
def test_graph_renderer_contract_is_available(
    module_name: str,
    type_name: str,
) -> None:
    # Given / When
    try:
        module = import_module(module_name)
    except ModuleNotFoundError:
        pytest.fail(f"{type_name} module is not implemented", pytrace=False)

    # Then
    assert hasattr(module, type_name)


def test_renderers_share_graph_ids_without_semantic_topology_edges() -> None:
    # Given
    system_map = SystemMapV2ValidationService().validate(
        json.loads(V2_FIXTURE.read_text(encoding="utf-8"))
    )
    profile_result = ProfileInferenceService().infer(
        system_map,
        build_id=system_map.build_id or "build:fixture",
        scan_id=system_map.scan_id or "scan:fixture",
        environment_id=system_map.environment_id,
    )
    graph = GraphProjectionService().project(
        system_map,
        profile_result=profile_result,
    )

    # When
    mermaid = GraphMermaidRenderer().render(graph)
    markdown = GraphMarkdownRenderer().render(graph)

    # Then
    assert mermaid.startswith("flowchart LR\n")
    assert mermaid.count(" -->") == len(graph.edges)
    assert all(node.id in mermaid for node in graph.nodes)
    assert all(edge.id in mermaid for edge in graph.edges)
    assert all(node.id in markdown for node in graph.nodes)
    assert all(edge.id in markdown for edge in graph.edges)
    assert "Mapping Completeness" in markdown
    assert "## Slot Coverage" in markdown
    assert "## Local Endpoints" in markdown
    assert "## External Endpoints" in markdown
    assert "## Network Exposure" in markdown
    assert "## Recommended Next Checks" in markdown
    assert "confidence" not in markdown.lower()


def test_markdown_renders_graph_endpoints_and_canonical_next_checks() -> None:
    # Given
    graph = GraphViewModel(
        schema_version="graph-view-model/v1",
        nodes=[
            GraphNodeModel(
                id="node:component:qdrant",
                label="Qdrant",
                semantic_kind="repo_component",
            )
        ],
        edges=[],
        endpoints=[
            GraphEndpointModel(
                endpoint_id="endpoint:docker:qdrant:6333",
                value="http://localhost:6333",
                endpoint_type="local",
                method=None,
                component_id="component:vector_store:qdrant",
                slot="vector_store",
            )
        ],
        recommended_next_checks=[
            GraphRecommendedNextCheckModel(
                id="check:1",
                target_type="endpoint",
                target="endpoint:docker:qdrant:6333",
                reason="Confirm whether the published port is intentional.",
                action="review_published_port",
            )
        ],
        details=GraphDetailsModel(
            risk_hints_by_id={
                "risk:1": {
                    "type": "network_exposure",
                    "target": "endpoint:docker:qdrant:6333",
                    "rationale": "Docker published port detected.",
                    "severity_hint": "medium",
                    "uncertainty": "unknown",
                }
            }
        ),
        filters=GraphFiltersModel(),
    )

    # When
    markdown = GraphMarkdownRenderer().render(graph)

    # Then
    assert "## Local Endpoints" in markdown
    assert "http://localhost:6333" in markdown
    assert "vector_store" in markdown
    assert "## Network Exposure" in markdown
    assert "network_exposure" in markdown
    assert "## Recommended Next Checks" in markdown
    assert (
        "- [ ] review_published_port: Confirm whether the published port "
        "is intentional. (target: endpoint:docker:qdrant:6333)"
    ) in markdown
    assert "- No scan-fact checks." not in markdown


def _next_check(
    *,
    check_id: str = "check:1",
    target: str = "component:vector_store:qdrant",
) -> GraphRecommendedNextCheckModel:
    return GraphRecommendedNextCheckModel(
        id=check_id,
        target_type="component_instance",
        target=target,
        reason="Confirm whether the published port is intentional.",
        action="review_published_port",
    )


def _graph_with_next_checks(
    *,
    graph_checks: list[GraphRecommendedNextCheckModel] | None = None,
    node_checks: list[str] | None = None,
) -> GraphViewModel:
    return GraphViewModel(
        schema_version="graph-view-model/v1",
        nodes=[
            GraphNodeModel(
                id="node:reference:grounding",
                label="Grounding",
                semantic_kind="reference_capability",
                recommended_next_checks=list(node_checks or []),
            )
        ],
        edges=[],
        recommended_next_checks=list(graph_checks or []),
        details=GraphDetailsModel(),
        filters=GraphFiltersModel(),
    )


def test_markdown_renders_both_next_check_sections() -> None:
    # Given
    graph = _graph_with_next_checks(
        graph_checks=[_next_check()],
        node_checks=["Review the retrieval grounding evidence."],
    )

    # When
    markdown = GraphMarkdownRenderer().render(graph)

    # Then
    assert "## Recommended Next Checks" in markdown
    assert "### Scan-fact checks" in markdown
    assert "### Capability review checks" in markdown
    assert markdown.index("### Scan-fact checks") < markdown.index(
        "### Capability review checks"
    )
    assert (
        "- [ ] review_published_port: Confirm whether the published port "
        "is intentional. (target: component:vector_store:qdrant)"
    ) in markdown
    assert (
        "- [ ] `node:reference:grounding`: "
        "Review the retrieval grounding evidence."
    ) in markdown


def test_markdown_marks_capability_section_empty_when_scan_only() -> None:
    # Given
    graph = _graph_with_next_checks(graph_checks=[_next_check()])

    # When
    markdown = GraphMarkdownRenderer().render(graph)

    # Then
    assert "### Scan-fact checks" in markdown
    assert "### Capability review checks" in markdown
    assert "- [ ] review_published_port: " in markdown
    assert "- No scan-fact checks." not in markdown
    assert "- No capability review checks." in markdown


def test_markdown_marks_scan_fact_section_empty_when_profile_only() -> None:
    # Given
    graph = _graph_with_next_checks(
        node_checks=["Review the retrieval grounding evidence."]
    )

    # When
    markdown = GraphMarkdownRenderer().render(graph)

    # Then
    assert "### Scan-fact checks" in markdown
    assert "### Capability review checks" in markdown
    assert "- No scan-fact checks." in markdown
    assert "- No capability review checks." not in markdown
    assert (
        "- [ ] `node:reference:grounding`: "
        "Review the retrieval grounding evidence."
    ) in markdown


def test_markdown_reports_both_next_check_sections_as_empty() -> None:
    # Given
    graph = _graph_with_next_checks()

    # When
    markdown = GraphMarkdownRenderer().render(graph)

    # Then
    assert "- No scan-fact checks." in markdown
    assert "- No capability review checks." in markdown
    assert "- [ ]" not in markdown


def test_markdown_deduplicates_next_checks_within_each_section() -> None:
    # Given
    duplicate_check = "Review the retrieval grounding evidence."
    graph = _graph_with_next_checks(
        graph_checks=[_next_check(), _next_check(check_id="check:2")],
        node_checks=[duplicate_check, duplicate_check],
    )

    # When
    markdown = GraphMarkdownRenderer().render(graph)

    # Then
    duplicate_line = f"- [ ] `node:reference:grounding`: {duplicate_check}"
    assert markdown.count("- [ ] review_published_port: ") == 1
    assert markdown.count(duplicate_line) == 1


@pytest.mark.parametrize(
    ("fixture_name", "expected_component_types"),
    [
        ("non_grounded_llm_app.v2.json", {"api_input", "llm"}),
        ("tool_using_agent.v2.json", {"agent_loop", "tool", "llm"}),
        ("grounded_rag.v2.json", {"api_input", "retriever", "llm"}),
        (
            "grounded_agent.v2.json",
            {"agent_loop", "retriever", "tool", "llm"},
        ),
        ("workflow_graph.v2.json", {"workflow_node"}),
    ],
)
def test_supported_system_scenarios_render_non_empty_semantic_mermaid(
    fixture_name: str,
    expected_component_types: set[str],
) -> None:
    # Given
    fixture_path = V2_FIXTURE_DIR / fixture_name
    system_map = SystemMapV2ValidationService().validate(
        json.loads(fixture_path.read_text(encoding="utf-8"))
    )

    # When
    graph = GraphProjectionService().project(system_map)
    mermaid = GraphMermaidRenderer().render(graph)

    # Then
    repo_nodes = [
        node for node in graph.nodes if node.semantic_kind == "repo_component"
    ]
    assert repo_nodes
    assert {node.type for node in repo_nodes} == expected_component_types
    assert len(graph.edges) == len(system_map.edges)
    assert mermaid.startswith("flowchart LR\n")
    assert all(node.id in mermaid for node in repo_nodes)
    assert all(edge.id in mermaid for edge in graph.edges)
