"""Build a minimal frontend graph projection from canonical system maps."""

from __future__ import annotations

import json
import re
from pathlib import Path

from kai_mind.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Edge,
    Endpoint,
    RagSystemMap,
    RiskHint,
)
from kai_mind.core.models.viewer import (
    GraphDetailsModel,
    GraphEdgeModel,
    GraphFiltersModel,
    GraphNodeModel,
    GraphViewModel,
    ViewerLoadResult,
)

GRAPH_SCHEMA_VERSION = "graph-view-model/minimal-v1"


class MinimalViewerProjectionService:
    """Project canonical scanner truth into frontend rendering data."""

    def build(
        self,
        system_map: RagSystemMap,
        *,
        map_json_path: Path | None = None,
    ) -> ViewerLoadResult:
        """Return a viewer payload without mutating the canonical map."""

        node_ids_by_slot = {
            slot_id: _node_id(slot_id)
            for slot_id in system_map.components_by_slot
        }
        risk_index = RiskHintIndex(system_map.risk_hints, system_map.endpoints)
        graph = GraphViewModel(
            schema_version=GRAPH_SCHEMA_VERSION,
            source_schema_version=system_map.schema_version,
            map_json=str(map_json_path) if map_json_path is not None else None,
            summary=(
                system_map.scan_summary.model_dump(mode="json")
                if system_map.scan_summary is not None
                else None
            ),
            nodes=[
                self._node_for_slot(slot, risk_index)
                for slot in system_map.components_by_slot.values()
            ],
            edges=[
                self._edge_for_graph(edge, node_ids_by_slot, risk_index)
                for flow in system_map.flows
                for edge in flow.edges
            ],
            details=GraphDetailsModel(
                evidence_by_id={
                    evidence.id: evidence.model_dump(mode="json")
                    for evidence in system_map.evidence
                },
                risk_hints_by_id={
                    risk.id: risk.model_dump(mode="json")
                    for risk in system_map.risk_hints
                },
            ),
            filters=GraphFiltersModel(available=[]),
        )

        system_map_data = system_map.model_dump(mode="json")
        return ViewerLoadResult(
            loaded=True,
            error_reason=None,
            map_json=json.dumps(system_map_data, ensure_ascii=False),
            ai_system_map=system_map_data,
            graph_view_model=graph,
        )

    def empty(
        self, *, error_reason: str = "no_map_loaded"
    ) -> ViewerLoadResult:
        """Return a contract-compatible empty viewer payload."""

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
                filters=GraphFiltersModel(available=[]),
            ),
        )

    def _node_for_slot(
        self,
        slot: ComponentSlot,
        risk_index: RiskHintIndex,
    ) -> GraphNodeModel:
        evidence_ids = _slot_evidence_ids(slot)
        risk_hint_ids = risk_index.ids_for_slot(slot, evidence_ids)
        return GraphNodeModel(
            id=_node_id(slot.slot),
            source_id=slot.slot,
            type="component_slot",
            slot=slot.slot,
            status=slot.status,
            label=_humanize(slot.slot),
            subtitle=_slot_subtitle(slot),
            badges=_slot_badges(slot),
            evidence_ids=evidence_ids,
            risk_hint_ids=risk_hint_ids,
        )

    def _edge_for_graph(
        self,
        edge: Edge,
        node_ids_by_slot: dict[str, str],
        risk_index: RiskHintIndex,
    ) -> GraphEdgeModel:
        return GraphEdgeModel(
            id=_graph_edge_id(edge.id),
            source_id=edge.id,
            flow_id=edge.flow_id,
            **{"from": node_ids_by_slot[edge.from_slot]},
            to=node_ids_by_slot[edge.to_slot],
            relationship=edge.relationship,
            label=_humanize(edge.relationship),
            evidence_ids=sorted(edge.evidence_ids),
            risk_hint_ids=risk_index.ids_for_edge(edge),
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


def _slot_evidence_ids(slot: ComponentSlot) -> list[str]:
    ids = {
        evidence_id
        for instance in slot.instances
        for evidence_id in instance.evidence_ids
    }
    return sorted(ids)


def _slot_badges(slot: ComponentSlot) -> list[str]:
    providers = {
        instance.provider
        for instance in slot.instances
        if instance.provider is not None
    }
    return [slot.status, *sorted(providers)]


def _slot_subtitle(slot: ComponentSlot) -> str | None:
    if not slot.instances:
        return None
    names = [instance.name for instance in _sorted_instances(slot.instances)]
    return ", ".join(names)


def _sorted_instances(
    instances: list[ComponentInstance],
) -> list[ComponentInstance]:
    return sorted(instances, key=lambda item: item.id)


def _node_id(slot: str) -> str:
    return f"node:slot:{_slug(slot)}"


def _graph_edge_id(edge_id: str) -> str:
    return f"graph:{edge_id}"


def _humanize(value: str) -> str:
    return re.sub(r"[_-]+", " ", value).title()


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower() or "unknown"
