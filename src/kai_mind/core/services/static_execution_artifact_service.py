from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.execution_artifact import (
    ArtifactEdge,
    ArtifactNode,
    CallGraphArtifact,
    DataflowHintsArtifact,
    EvidenceTableArtifact,
    EvidenceTableRow,
    ExecutionPathsArtifact,
)
from kai_mind.core.models.mapping import (
    ManualMapping,
    ManualMappingDecision,
)

EvidenceReviewState = Literal[
    "confirmed",
    "rejected",
    "needs_confirmation",
    "not_required",
]


@dataclass(frozen=True, slots=True)
class StaticExecutionArtifacts:
    call_graph: CallGraphArtifact
    dataflow_hints: DataflowHintsArtifact
    execution_paths: ExecutionPathsArtifact
    evidence_table: EvidenceTableArtifact
    system_map_mermaid: str
    execution_map_mermaid: str


class StaticExecutionArtifactService:
    def build(
        self,
        system_map: AiSystemMapV2,
        *,
        manual_mappings: tuple[ManualMapping, ...] = (),
    ) -> StaticExecutionArtifacts:
        if system_map.build_id is None or system_map.scan_id is None:
            raise ValueError("normalized map requires build and scan scope")
        build_id = system_map.build_id
        scan_id = system_map.scan_id
        environment_id = system_map.environment_id
        nodes = tuple(
            ArtifactNode(
                node_id=item.component_id,
                kind=item.canonical_type,
            )
            for item in system_map.components
        )
        edges = tuple(
            ArtifactEdge(
                edge_id=item.edge_id,
                source=item.source,
                target=item.target,
                relationship=item.relationship,
                evidence_ids=tuple(item.evidence_ids),
            )
            for item in system_map.edges
        )
        review_states = self._review_states(system_map, manual_mappings)
        rows = tuple(
            EvidenceTableRow(
                evidence_id=item.evidence_id,
                artifact_type=item.artifact_type,
                evidence_kind=item.evidence_kind,
                review_state=review_states.get(
                    item.evidence_id,
                    "not_required",
                ),
                relative_path=item.location.path,
                rule_id=item.rule_id,
                summary=item.extract_summary,
            )
            for item in system_map.evidence
        )
        return StaticExecutionArtifacts(
            call_graph=CallGraphArtifact(
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
                generated_from_build_id=build_id,
                nodes=nodes,
                edges=edges,
            ),
            dataflow_hints=DataflowHintsArtifact(
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
                generated_from_build_id=build_id,
                hints=edges,
            ),
            execution_paths=ExecutionPathsArtifact(
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
                generated_from_build_id=build_id,
                paths=tuple((item.source, item.target) for item in edges),
            ),
            evidence_table=EvidenceTableArtifact(
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
                generated_from_build_id=build_id,
                rows=rows,
            ),
            system_map_mermaid=self._mermaid("System map", nodes, edges),
            execution_map_mermaid=self._mermaid("Execution map", nodes, edges),
        )

    @staticmethod
    def _review_states(
        system_map: AiSystemMapV2,
        manual_mappings: tuple[ManualMapping, ...],
    ) -> dict[str, EvidenceReviewState]:
        states: dict[str, EvidenceReviewState] = {
            evidence_id: "needs_confirmation"
            for item in system_map.unmapped_components
            for evidence_id in item.evidence_ids
        }
        decision_states: dict[ManualMappingDecision, EvidenceReviewState] = {
            ManualMappingDecision.CONFIRMED: "confirmed",
            ManualMappingDecision.REJECTED: "rejected",
            ManualMappingDecision.SKIP_FOR_NOW: "needs_confirmation",
            ManualMappingDecision.NOT_APPLICABLE: "not_required",
        }
        for mapping in manual_mappings:
            state = decision_states[mapping.decision]
            for evidence_id in mapping.evidence_ids:
                states[evidence_id] = state
        return states

    @staticmethod
    def _mermaid(
        title: str,
        nodes: tuple[ArtifactNode, ...],
        edges: tuple[ArtifactEdge, ...],
    ) -> str:
        lines = [f"---\ntitle: {title}\n---", "flowchart LR"]
        for node in nodes:
            node_id = StaticExecutionArtifactService._id(node.node_id)
            lines.append(f'  {node_id}["{node.kind}"]')
        for edge in edges:
            source = StaticExecutionArtifactService._id(edge.source)
            target = StaticExecutionArtifactService._id(edge.target)
            lines.append(f"  {source} -->|{edge.relationship}| {target}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _id(value: str) -> str:
        return "node_" + "".join(
            char if char.isalnum() else "_" for char in value
        )
