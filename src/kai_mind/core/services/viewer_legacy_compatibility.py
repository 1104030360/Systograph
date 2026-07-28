# 這個檔案負責：只放「非得吃 v1 RagSystemMap 不可」的 viewer 相容 helper
# （legacy edge 順序、v1 evidence / risk hint 明細）。
# 版本中立的投影（例如 recommended_next_checks）一律放
# viewer_session_service.py，改吃 normalized AiSystemMapV2。
#
# 呼叫鏈：
#   ViewerSessionService.build_loaded / project_to_graph
#     → _preserve_legacy_edge_order / _with_legacy_details
from __future__ import annotations

from typing import Any

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.system_map import RagSystemMap, RiskHint
from kai_mind.core.models.viewer import GraphViewModel


def _preserve_legacy_edge_order(
    system_map: RagSystemMap,
    normalized: AiSystemMapV2,
) -> AiSystemMapV2:
    edges_by_id = {edge.edge_id: edge for edge in normalized.edges}
    ordered_ids = [edge.id for flow in system_map.flows for edge in flow.edges]
    ordered_edges = [
        edges_by_id[edge_id]
        for edge_id in ordered_ids
        if edge_id in edges_by_id
    ]
    ordered_id_set = set(ordered_ids)
    ordered_edges.extend(
        edge for edge in normalized.edges if edge.edge_id not in ordered_id_set
    )
    return normalized.model_copy(update={"edges": ordered_edges})


def _with_legacy_details(
    graph: GraphViewModel,
    system_map: RagSystemMap,
) -> GraphViewModel:
    return graph.model_copy(
        update={
            "details": graph.details.model_copy(
                update={
                    "evidence_by_id": {
                        evidence.id: evidence.model_dump(mode="json")
                        for evidence in system_map.evidence
                    },
                    "risk_hints_by_id": {
                        risk.id: _risk_detail(risk)
                        for risk in system_map.risk_hints
                    },
                },
            )
        }
    )


def _risk_detail(risk: RiskHint) -> dict[str, Any]:
    detail = risk.model_dump(mode="json")
    detail["title"] = risk.type.replace("_", " ").title()
    detail["severity"] = risk.severity_hint or "review"
    detail["description"] = risk.rationale
    return detail
