"""Viewer projection models derived from ai-system-map/v1."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ViewerModel(BaseModel):
    """Base model for frontend-facing viewer payloads."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class GraphNodeModel(ViewerModel):
    id: str
    source_id: str | None = None
    type: str | None = None
    slot: str | None = None
    status: str | None = None
    label: str
    subtitle: str | None = None
    badges: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    risk_hint_ids: list[str] = Field(default_factory=list)


class GraphEdgeModel(ViewerModel):
    id: str
    source_id: str | None = None
    flow_id: str | None = None
    from_id: str = Field(
        serialization_alias="from",
        validation_alias="from",
    )
    to: str
    relationship: str | None = None
    label: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    risk_hint_ids: list[str] = Field(default_factory=list)


class GraphFilterModel(ViewerModel):
    id: str
    label: str
    kind: str
    matches_node_ids: list[str] = Field(default_factory=list)
    matches_edge_ids: list[str] = Field(default_factory=list)


class GraphDetailsModel(ViewerModel):
    evidence_by_id: dict[str, dict[str, Any]] = Field(default_factory=dict)
    risk_hints_by_id: dict[str, dict[str, Any]] = Field(default_factory=dict)


class GraphFiltersModel(ViewerModel):
    available: list[GraphFilterModel] = Field(default_factory=list)
    behavior: str | None = None


class GraphViewModel(ViewerModel):
    schema_version: str | None = None
    source_schema_version: str | None = None
    map_json: str | None = None
    summary: dict[str, Any] | None = None
    nodes: list[GraphNodeModel]
    edges: list[GraphEdgeModel]
    details: GraphDetailsModel
    filters: GraphFiltersModel


class ViewerLoadResult(ViewerModel):
    loaded: bool
    error_reason: str | None = None
    map_json: str | None = None
    ai_system_map: dict[str, Any]
    graph_view_model: GraphViewModel


class ViewerPayload(ViewerModel):
    viewer_load_result: ViewerLoadResult
