# 這個檔案負責：從 normalized AiSystemMapV2 組出靜態 execution artifacts
# （call_graph / dataflow_hints / execution_paths / evidence_table / mermaid）
# 。
# 不做 runtime replay；只從 map 的 components/edges/evidence + manual mappings
# 推導。
#
# 呼叫鏈：
#   MapBuildPipeline._complete()
#     → StaticExecutionArtifactService.build(normalized, manual_mappings)
#         → StaticExecutionArtifacts
#     → BuildArtifactPublisher.publish 寫到磁碟
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.execution_artifact import (
    ArtifactEdge,
    ArtifactNode,
    CallGraphArtifact,
    DataflowHintsArtifact,
    EvidenceTableArtifact,
    EvidenceTableRow,
    ExecutionPathsArtifact,
)
from systograph.core.models.mapping import (
    ManualMapping,
    ManualMappingDecision,
)

EvidenceReviewState = Literal[
    "confirmed",
    "rejected",
    "needs_confirmation",
    "not_required",
]


# 做什麼：一次靜態 execution 產物集合（給 publisher 寫檔）。
# 被誰用：MapBuildPipeline → BuildArtifactPublisher。
# 自己呼叫：無；純資料。
@dataclass(frozen=True, slots=True)
class StaticExecutionArtifacts:
    call_graph: CallGraphArtifact
    dataflow_hints: DataflowHintsArtifact
    execution_paths: ExecutionPathsArtifact
    evidence_table: EvidenceTableArtifact
    execution_map_mermaid: str


# 做什麼：從 canonical map 組靜態 execution artifacts。
# 被誰用：MapBuildPipeline._complete。
# 自己呼叫：_review_states、_mermaid、_id。
class StaticExecutionArtifactService:
    # 做什麼：入口；要求 map 已有 build_id/scan_id，再組 nodes/edges/evidence
    # rows。
    # 被誰呼叫：MapBuildPipeline._complete。
    # 自己呼叫：
    #   components → ArtifactNode
    #   edges → ArtifactEdge / paths / dataflow hints
    #   _review_states → EvidenceTableRow.review_state
    #   _mermaid → execution_map_mermaid
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
                status=item.status,
                undetermined_reason=item.undetermined_reason,
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
                trace_kind="static_inferred",
                runtime_verified=False,
                nodes=nodes,
                edges=edges,
            ),
            dataflow_hints=DataflowHintsArtifact(
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
                generated_from_build_id=build_id,
                trace_kind="static_inferred",
                runtime_verified=False,
                hints=edges,
            ),
            execution_paths=ExecutionPathsArtifact(
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
                generated_from_build_id=build_id,
                trace_kind="static_inferred",
                runtime_verified=False,
                paths=edges,
            ),
            evidence_table=EvidenceTableArtifact(
                build_id=build_id,
                scan_id=scan_id,
                environment_id=environment_id,
                generated_from_build_id=build_id,
                trace_kind="static_inferred",
                runtime_verified=False,
                rows=rows,
            ),
            execution_map_mermaid=self._mermaid(
                "Execution map",
                nodes,
                edges,
                system_map=system_map,
            ),
        )

    # 做什麼：依 unmapped evidence + manual mapping decisions 算 review_state。
    # 被誰呼叫：build()。
    # 自己呼叫：掃 unmapped_components.evidence_ids（預設 needs_confirmation）
    # ，
    #           再用 ManualMapping.decision 覆寫。
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

    # 做什麼：把 nodes/edges 渲成簡單 flowchart LR mermaid 字串。
    # 被誰呼叫：build()（execution_map_mermaid）。
    # 自己呼叫：_id。
    @staticmethod
    def _mermaid(
        title: str,
        nodes: tuple[ArtifactNode, ...],
        edges: tuple[ArtifactEdge, ...],
        *,
        system_map: AiSystemMapV2,
    ) -> str:
        lines = [
            f"---\ntitle: {title}\n---",
            "%% "
            f"build={system_map.build_id or 'unscoped'} "
            f"scan={system_map.scan_id or 'unscoped'} "
            f"environment={system_map.environment_id} "
            f"artifact_set={system_map.artifact_set_version}",
            "flowchart LR",
        ]
        for node in nodes:
            node_id = StaticExecutionArtifactService._id(node.node_id)
            lines.append(f'  {node_id}["{node.kind}"]')
        for edge in edges:
            source = StaticExecutionArtifactService._id(edge.source)
            target = StaticExecutionArtifactService._id(edge.target)
            lines.append(f"  {source} -->|{edge.relationship}| {target}")
        return "\n".join(lines) + "\n"

    # 做什麼：把任意 id 壓成 mermaid 安全的 node_* 識別字。
    # 被誰呼叫：_mermaid。
    # 自己呼叫：字元過濾。
    @staticmethod
    def _id(value: str) -> str:
        return "node_" + "".join(
            char if char.isalnum() else "_" for char in value
        )
