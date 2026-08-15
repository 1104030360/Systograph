from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from systograph.core.models.ai_system_map_v2 import CanonicalEdge
from systograph.core.models.system_map import Flow


@dataclass(frozen=True, slots=True)
class CallPriorityEdgeMergeResult:
    edges: tuple[CanonicalEdge, ...]
    discarded_lower_tier: int


class CallPriorityEdgeMergeService:
    def merge(
        self,
        *,
        structural_edges: Sequence[CanonicalEdge],
        template_flows: Sequence[Flow],
    ) -> CallPriorityEdgeMergeResult:
        candidates = [*structural_edges, *self._template_edges(template_flows)]
        grouped: dict[tuple[str, str, str], list[CanonicalEdge]] = defaultdict(
            list
        )
        for edge in candidates:
            grouped[(edge.source, edge.target, edge.relationship)].append(edge)

        merged: list[CanonicalEdge] = []
        discarded = 0
        for key in sorted(grouped):
            group = sorted(grouped[key], key=self._sort_key)
            priority = self._priority(group[0])
            winners = [
                edge for edge in group if self._priority(edge) == priority
            ]
            discarded += len(group) - len(winners)
            first = winners[0]
            merged.append(
                first.model_copy(
                    update={
                        "evidence_ids": sorted(
                            {
                                evidence_id
                                for winner in winners
                                for evidence_id in winner.evidence_ids
                            }
                        )
                    }
                )
            )
        return CallPriorityEdgeMergeResult(
            edges=tuple(sorted(merged, key=self._sort_key)),
            discarded_lower_tier=discarded,
        )

    @staticmethod
    def _template_edges(flows: Sequence[Flow]) -> list[CanonicalEdge]:
        return [
            CanonicalEdge(
                edge_id=edge.id,
                source=edge.from_component_id,
                target=edge.to_component_id,
                relationship=edge.relationship,
                status=edge.status,
                evidence_ids=sorted(edge.evidence_ids),
                undetermined_reason=edge.undetermined_reason,
            )
            for flow in flows
            for edge in flow.edges
            if edge.from_component_id is not None
            and edge.to_component_id is not None
        ]

    @staticmethod
    def _priority(edge: CanonicalEdge) -> int:
        if edge.status == "observed":
            return 0
        if edge.undetermined_reason == "template_adjacency_only":
            return 2
        return 1

    @classmethod
    def _sort_key(
        cls,
        edge: CanonicalEdge,
    ) -> tuple[int, str, str, str, str]:
        return (
            cls._priority(edge),
            edge.source,
            edge.target,
            edge.relationship,
            edge.edge_id,
        )
