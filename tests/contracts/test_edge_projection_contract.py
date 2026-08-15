from __future__ import annotations

from systograph.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalComponent,
    CanonicalEdge,
    CanonicalProject,
)
from systograph.core.models.execution_artifact import ArtifactEdge
from systograph.core.models.viewer import GraphEdgeModel
from systograph.core.services.graph_projection_service import (
    GraphProjectionService,
)


def test_graph_edge_preserves_canonical_status_and_reason() -> None:
    # Given: an import-only canonical edge remains explicitly undetermined.
    source_id = "component:retrieval:retriever"
    target_id = "component:generation:llm"
    system_map = AiSystemMapV2(
        schema_version="ai-system-map/v2",
        system_type="ai_system",
        project=CanonicalProject(name="edge-status-projection"),
        components=[
            CanonicalComponent(
                component_id=source_id,
                display_name="Retriever",
                canonical_type="retriever",
                layer="retrieval",
                status="detected",
                activation="enabled",
            ),
            CanonicalComponent(
                component_id=target_id,
                display_name="LLM",
                canonical_type="llm",
                layer="generation",
                status="detected",
                activation="enabled",
            ),
        ],
        edges=[
            CanonicalEdge(
                edge_id="edge:retriever:llm:context_flow",
                source=source_id,
                target=target_id,
                relationship="context_flow",
                status="undetermined",
                undetermined_reason="import_only_no_call_site",
            )
        ],
    )

    # When: the canonical map is serialized through GraphViewModel.
    payload = (
        GraphProjectionService()
        .project(system_map)
        .model_dump(
            mode="json",
            by_alias=True,
        )
    )

    # Then: the API projection does not promote or erase edge uncertainty.
    edge_payload = payload["edges"][0]
    assert edge_payload["status"] == "undetermined"
    assert edge_payload["undetermined_reason"] == "import_only_no_call_site"


def test_downstream_edge_schemas_expose_canonical_uncertainty() -> None:
    # Given: viewer and static edge models are downstream canonical consumers.
    graph_schema = GraphEdgeModel.model_json_schema()
    artifact_schema = ArtifactEdge.model_json_schema()

    # When: their serialized model contracts are inspected.
    graph_properties = graph_schema["properties"]
    artifact_properties = artifact_schema["properties"]

    # Then: both contracts carry typed status and nullable reason fields.
    assert {"status", "undetermined_reason"} <= set(graph_properties)
    assert {"status", "undetermined_reason"} <= set(artifact_properties)
    assert set(artifact_properties["status"]["enum"]) == {
        "observed",
        "detected",
        "undetermined",
    }
    assert "status" in artifact_schema["required"]
    assert "status" not in graph_schema.get("required", [])
