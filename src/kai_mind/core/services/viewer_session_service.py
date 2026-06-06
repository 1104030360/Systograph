"""Load validated system maps into frontend viewer payloads."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Mapping
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from kai_mind.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Edge,
    Endpoint,
    ExtensionComponent,
    Flow,
    RagSystemMap,
    RiskHint,
    UnmappedComponent,
)
from kai_mind.core.models.viewer import (
    GraphDetailsModel,
    GraphEdgeModel,
    GraphFilterModel,
    GraphFiltersModel,
    GraphNodeModel,
    GraphViewModel,
    ViewerLoadResult,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationError,
    SystemMapValidationService,
)

GRAPH_SCHEMA_VERSION = "graph-view-model/v1"


class ViewerSessionService:
    """Convert validated canonical maps into frontend graph payloads."""

    def __init__(
        self,
        *,
        validation_service: SystemMapValidationService | None = None,
    ) -> None:
        self._validation_service = (
            validation_service or SystemMapValidationService()
        )

    def load_map(self, map_json_path: Path) -> ViewerLoadResult:
        """Read, validate, and project one ai_system_map.json file."""

        try:
            raw = map_json_path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            if not isinstance(parsed, Mapping):
                return self.empty(error_reason="map_json_must_be_object")
            system_map = self._validation_service.validate(parsed)
        except OSError as exc:
            return self.empty(error_reason=f"map_read_failed: {exc}")
        except JSONDecodeError as exc:
            return self.empty(error_reason=f"invalid_json: {exc.msg}")
        except SystemMapValidationError as exc:
            return self.empty(error_reason=f"invalid_map: {exc}")

        return self.build(system_map, map_json_path=map_json_path)

    def build(
        self,
        system_map: RagSystemMap,
        *,
        map_json_path: Path | None = None,
    ) -> ViewerLoadResult:
        """Return a complete viewer load result for a validated map."""

        graph = self.project_to_graph(system_map, map_json_path=map_json_path)
        system_map_data = system_map.model_dump(mode="json")
        return ViewerLoadResult(
            loaded=True,
            error_reason=None,
            map_json=json.dumps(system_map_data, ensure_ascii=False),
            ai_system_map=system_map_data,
            graph_view_model=graph,
        )

    def project_to_graph(
        self,
        system_map: RagSystemMap,
        *,
        map_json_path: Path | None = None,
    ) -> GraphViewModel:
        """Project canonical facts into semantic graph data only."""

        risk_index = RiskHintIndex(system_map.risk_hints, system_map.endpoints)
        node_builder = _GraphNodeBuilder(risk_index)
        nodes = node_builder.build_nodes(system_map)
        node_ids_by_source = {
            node.source_id: node.id for node in nodes if node.source_id
        }
        edges = [
            self._edge_for_graph(
                edge=edge,
                node_ids_by_source=node_ids_by_source,
                risk_index=risk_index,
            )
            for flow in system_map.flows
            for edge in flow.edges
        ]

        return GraphViewModel(
            schema_version=GRAPH_SCHEMA_VERSION,
            source_schema_version=system_map.schema_version,
            map_json=str(map_json_path) if map_json_path is not None else None,
            summary=_summary(system_map, nodes=nodes, edges=edges),
            nodes=nodes,
            edges=edges,
            details=GraphDetailsModel(
                evidence_by_id={
                    evidence.id: evidence.model_dump(mode="json")
                    for evidence in system_map.evidence
                },
                risk_hints_by_id={
                    risk.id: _risk_detail(risk)
                    for risk in system_map.risk_hints
                },
            ),
            filters=_filters(system_map.flows, nodes, edges),
        )

    def empty(
        self, *, error_reason: str = "no_map_loaded"
    ) -> ViewerLoadResult:
        """Return a contract-compatible empty viewer load result."""

        return ViewerLoadResult(
            loaded=False,
            error_reason=error_reason,
            map_json=None,
            ai_system_map={},
            graph_view_model=GraphViewModel(
                schema_version=GRAPH_SCHEMA_VERSION,
                source_schema_version=None,
                map_json=None,
                summary=None,
                nodes=[],
                edges=[],
                details=GraphDetailsModel(),
                filters=GraphFiltersModel(
                    available=[],
                    behavior="highlight",
                ),
            ),
        )

    def _edge_for_graph(
        self,
        *,
        edge: Edge,
        node_ids_by_source: dict[str, str],
        risk_index: RiskHintIndex,
    ) -> GraphEdgeModel:
        return GraphEdgeModel(
            id=_graph_edge_id(edge.id),
            source_id=edge.id,
            flow_id=edge.flow_id,
            from_id=_edge_endpoint_id(edge, "from", node_ids_by_source),
            to=_edge_endpoint_id(edge, "to", node_ids_by_source),
            relationship=edge.relationship,
            label=_humanize(edge.relationship),
            evidence_ids=sorted(edge.evidence_ids),
            risk_hint_ids=risk_index.ids_for_edge(edge),
        )


class _GraphNodeBuilder:
    def __init__(self, risk_index: RiskHintIndex) -> None:
        self._risk_index = risk_index

    def build_nodes(self, system_map: RagSystemMap) -> list[GraphNodeModel]:
        nodes: list[GraphNodeModel] = []
        for slot in system_map.components_by_slot.values():
            nodes.extend(self._nodes_for_slot(slot))
        nodes.extend(
            self._node_for_extension(extension, system_map.risk_hints)
            for extension in system_map.extensions
        )
        nodes.extend(
            self._node_for_unmapped(component, system_map.risk_hints)
            for component in system_map.unmapped_components
        )
        return nodes

    def _nodes_for_slot(self, slot: ComponentSlot) -> list[GraphNodeModel]:
        if not slot.instances:
            return [self._placeholder_node_for_slot(slot)]

        return [
            self._node_for_instance(slot, instance)
            for instance in _sorted_instances(slot.instances)
        ]

    def _node_for_instance(
        self,
        slot: ComponentSlot,
        instance: ComponentInstance,
    ) -> GraphNodeModel:
        evidence_ids = sorted(instance.evidence_ids)
        return GraphNodeModel(
            id=_component_node_id(instance.id),
            source_id=instance.id,
            type=instance.kind,
            slot=slot.slot,
            status=slot.status,
            label=instance.name,
            subtitle=instance.description or _humanize(slot.slot),
            badges=_clean_badges(
                [slot.status, instance.provider, instance.kind]
            ),
            evidence_ids=evidence_ids,
            risk_hint_ids=self._risk_index.ids_for_slot(slot, evidence_ids),
        )

    def _placeholder_node_for_slot(
        self,
        slot: ComponentSlot,
    ) -> GraphNodeModel:
        evidence_ids: list[str] = []
        return GraphNodeModel(
            id=_slot_node_id(slot.slot),
            source_id=slot.slot,
            type="component_slot",
            slot=slot.slot,
            status=slot.status,
            label=_humanize(slot.slot),
            subtitle=None,
            badges=_clean_badges([slot.status]),
            evidence_ids=evidence_ids,
            risk_hint_ids=self._risk_index.ids_for_slot(slot, evidence_ids),
        )

    def _node_for_extension(
        self,
        extension: ExtensionComponent,
        risk_hints: list[RiskHint],
    ) -> GraphNodeModel:
        evidence_ids = sorted(extension.evidence_ids)
        return GraphNodeModel(
            id=f"node:extension:{_slug(extension.id)}",
            source_id=extension.id,
            type=extension.kind,
            slot=None,
            status=extension.status,
            label=extension.name,
            subtitle=extension.description,
            badges=_clean_badges(
                [extension.status, "extension", extension.kind]
            ),
            evidence_ids=evidence_ids,
            risk_hint_ids=_risk_ids_for_evidence(risk_hints, evidence_ids),
        )

    def _node_for_unmapped(
        self,
        component: UnmappedComponent,
        risk_hints: list[RiskHint],
    ) -> GraphNodeModel:
        evidence_ids = sorted(component.evidence_ids)
        return GraphNodeModel(
            id=f"node:unmapped:{_slug(component.id)}",
            source_id=component.id,
            type=component.observed_kind,
            slot=None,
            status=component.status,
            label=_humanize(component.observed_kind),
            subtitle=component.reason,
            badges=_clean_badges(
                [component.status, "unmapped", component.observed_kind]
            ),
            evidence_ids=evidence_ids,
            risk_hint_ids=_risk_ids_for_evidence(risk_hints, evidence_ids),
        )


class RiskHintIndex:
    """Index risk hints by canonical targets used in graph projection."""

    def __init__(
        self,
        risk_hints: list[RiskHint],
        endpoints: list[Endpoint],
    ) -> None:
        self._risk_hints = tuple(risk_hints)
        self._endpoints_by_id = {
            endpoint.id: endpoint for endpoint in endpoints
        }

    def ids_for_slot(
        self,
        slot: ComponentSlot,
        evidence_ids: list[str],
    ) -> list[str]:
        instance_ids = {instance.id for instance in slot.instances}
        evidence_id_set = set(evidence_ids)
        ids = [
            risk.id
            for risk in self._risk_hints
            if (
                risk.target_type == "component_slot"
                and risk.target == slot.slot
            )
            or (
                risk.target_type == "component_instance"
                and risk.target in instance_ids
            )
            or (
                risk.target_type == "endpoint"
                and self._endpoint_component_id(risk.target) in instance_ids
            )
            or (
                risk.target_type == "evidence"
                and risk.target in evidence_id_set
            )
            or risk.evidence_id in evidence_id_set
        ]
        return sorted(ids)

    def ids_for_edge(self, edge: Edge) -> list[str]:
        evidence_ids = set(edge.evidence_ids)
        component_ids = {
            value
            for value in (edge.from_component_id, edge.to_component_id)
            if value is not None
        }
        ids = [
            risk.id
            for risk in self._risk_hints
            if (
                risk.target_type == "component_instance"
                and risk.target in component_ids
            )
            or (
                risk.target_type == "endpoint"
                and self._endpoint_component_id(risk.target) in component_ids
            )
            or (risk.target_type == "evidence" and risk.target in evidence_ids)
            or risk.evidence_id in evidence_ids
        ]
        return sorted(ids)

    def _endpoint_component_id(self, endpoint_id: str) -> str | None:
        endpoint = self._endpoints_by_id.get(endpoint_id)
        if endpoint is None:
            return None
        return endpoint.component_instance_id


def _edge_endpoint_id(
    edge: Edge,
    side: str,
    node_ids_by_source: dict[str, str],
) -> str:
    if side == "from":
        candidates = [edge.from_component_id, edge.from_slot]
    else:
        candidates = [edge.to_component_id, edge.to_slot]

    for candidate in candidates:
        if candidate and candidate in node_ids_by_source:
            return node_ids_by_source[candidate]

    return _slot_node_id(candidates[-1] or "unknown")


def _filters(
    flows: list[Flow],
    nodes: list[GraphNodeModel],
    edges: list[GraphEdgeModel],
) -> GraphFiltersModel:
    filters: list[GraphFilterModel] = []
    node_ids_by_status: dict[str, list[str]] = defaultdict(list)
    node_ids_by_type: dict[str, list[str]] = defaultdict(list)

    for node in nodes:
        if node.status:
            node_ids_by_status[node.status].append(node.id)
        if node.type:
            node_ids_by_type[node.type].append(node.id)

    filters.extend(
        GraphFilterModel(
            id=f"filter:status:{status}",
            label=f"Status: {_humanize(status)}",
            kind="status",
            matches_node_ids=sorted(ids),
            matches_edge_ids=[],
        )
        for status, ids in sorted(node_ids_by_status.items())
        if ids
    )
    filters.extend(
        GraphFilterModel(
            id=f"filter:type:{_slug(node_type)}",
            label=f"Type: {_humanize(node_type)}",
            kind="type",
            matches_node_ids=sorted(ids),
            matches_edge_ids=[],
        )
        for node_type, ids in sorted(node_ids_by_type.items())
        if ids
    )

    edge_ids_by_flow_id = _edge_ids_by_flow_id(edges)
    node_ids_by_edge_id = {edge.id: {edge.from_id, edge.to} for edge in edges}
    for flow in flows:
        edge_ids = edge_ids_by_flow_id.get(flow.id, [])
        if not edge_ids:
            continue
        node_ids = sorted(
            {
                node_id
                for edge_id in edge_ids
                for node_id in node_ids_by_edge_id.get(edge_id, set())
            }
        )
        flow_slug = flow.flow_type or flow.id.removeprefix("flow:")
        filters.append(
            GraphFilterModel(
                id=f"filter:flow:{flow_slug}",
                label=flow.name or _humanize(flow_slug),
                kind="flow",
                matches_node_ids=node_ids,
                matches_edge_ids=edge_ids,
            )
        )

    risk_node_ids = sorted(node.id for node in nodes if node.risk_hint_ids)
    risk_edge_ids = sorted(edge.id for edge in edges if edge.risk_hint_ids)
    if risk_node_ids or risk_edge_ids:
        filters.append(
            GraphFilterModel(
                id="filter:risk:has_risk",
                label="Has Risk Hint",
                kind="risk",
                matches_node_ids=risk_node_ids,
                matches_edge_ids=risk_edge_ids,
            )
        )

    return GraphFiltersModel(available=filters, behavior="highlight")


def _edge_ids_by_flow_id(
    edges: list[GraphEdgeModel],
) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.flow_id:
            grouped[edge.flow_id].append(edge.id)
    return {key: sorted(value) for key, value in grouped.items()}


def _summary(
    system_map: RagSystemMap,
    *,
    nodes: list[GraphNodeModel],
    edges: list[GraphEdgeModel],
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "project_name": system_map.project.name,
        "schema_version": system_map.schema_version,
        "scan_depth": system_map.scan_depth,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
    if system_map.scan_summary is not None:
        summary.update(system_map.scan_summary.model_dump(mode="json"))
    return summary


def _risk_detail(risk: RiskHint) -> dict[str, Any]:
    detail = risk.model_dump(mode="json")
    detail["title"] = _humanize(risk.type)
    detail["severity"] = risk.severity_hint or "review"
    detail["description"] = risk.rationale
    return detail


def _risk_ids_for_evidence(
    risk_hints: list[RiskHint],
    evidence_ids: list[str],
) -> list[str]:
    evidence_id_set = set(evidence_ids)
    return sorted(
        risk.id
        for risk in risk_hints
        if risk.evidence_id in evidence_id_set
        or (risk.target_type == "evidence" and risk.target in evidence_id_set)
    )


def _sorted_instances(
    instances: list[ComponentInstance],
) -> list[ComponentInstance]:
    return sorted(instances, key=lambda item: item.id)


def _component_node_id(component_id: str) -> str:
    return f"node:component:{_slug(component_id)}"


def _slot_node_id(slot: str) -> str:
    return f"node:slot:{_slug(slot)}"


def _graph_edge_id(edge_id: str) -> str:
    return f"graph:{edge_id}"


def _clean_badges(values: list[str | None]) -> list[str]:
    return [value for value in values if value]


def _humanize(value: str) -> str:
    return re.sub(r"[_:-]+", " ", value).title()


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "unknown"
