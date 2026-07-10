"""Emit workflow components/edges from validated workflow JSON shapes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final, Literal

from kai_mind.core.models.filesystem import FileInventory
from kai_mind.core.models.scan import ParseIssue, ProviderScanResult, ScanFact
from kai_mind.core.models.system_map import Evidence
from kai_mind.core.services.secret_masking_service import SecretMaskingService

WORKFLOW_JSON_SCAN_STAGE: Literal["workflow_json_parse"] = (
    "workflow_json_parse"
)
WORKFLOW_JSON_PROVIDER_NAME: Final[str] = "workflow_json"
WORKFLOW_NODE_RULE_ID: Final[str] = "workflow_json_node"
WORKFLOW_EDGE_RULE_ID: Final[str] = "workflow_json_edge"
INVALID_JSON_RULE_ID: Final[str] = "workflow_json_invalid"
DUPLICATE_NODE_RULE_ID: Final[str] = "workflow_json_duplicate_node_id"
DUPLICATE_EDGE_RULE_ID: Final[str] = "workflow_json_duplicate_edge_id"
DEFAULT_MAX_FILE_SIZE_BYTES: Final[int] = 250_000


class WorkflowJsonProvider:
    """Read workflow JSON files and emit deterministic workflow facts.

    Only validated object shapes with an explicit node list and edge endpoints
    are accepted. Platform names are never inferred from free-text blobs.
    """

    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()
        self._max_file_size_bytes = max_file_size_bytes

    def collect(self, inventory: FileInventory) -> ProviderScanResult:
        result = ProviderScanResult()
        project_root = Path(inventory.project_root).resolve()

        for record in inventory.files:
            if not record.path.endswith(".json"):
                continue
            if record.size_bytes > self._max_file_size_bytes:
                continue

            file_path = project_root / record.path
            if not file_path.is_file():
                continue

            try:
                raw = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                result.issues.append(
                    ParseIssue(
                        provider=WORKFLOW_JSON_PROVIDER_NAME,
                        scan_stage=WORKFLOW_JSON_SCAN_STAGE,
                        file=record.path,
                        message=self._masking_service.mask_text(str(exc)),
                        rule_id=INVALID_JSON_RULE_ID,
                    )
                )
                continue

            if not self._is_workflow_shape(raw):
                continue

            self._emit_workflow_facts(
                result,
                relative_path=record.path,
                payload=raw,
            )

        return result

    @staticmethod
    def _is_workflow_shape(payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        nodes = payload.get("nodes")
        edges = payload.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, list):
            return False
        if not nodes or not edges:
            return False
        for node in nodes:
            if not isinstance(node, dict) or not isinstance(
                node.get("id"),
                str,
            ):
                return False
        for edge in edges:
            if not isinstance(edge, dict):
                return False
            if not isinstance(edge.get("source"), str):
                return False
            if not isinstance(edge.get("target"), str):
                return False
        return True

    def _emit_workflow_facts(
        self,
        result: ProviderScanResult,
        *,
        relative_path: str,
        payload: dict[str, Any],
    ) -> None:
        nodes = payload["nodes"]
        edges = payload["edges"]
        node_ids = [node["id"] for node in nodes]
        if len(node_ids) != len(set(node_ids)):
            result.issues.append(
                ParseIssue(
                    provider=WORKFLOW_JSON_PROVIDER_NAME,
                    scan_stage=WORKFLOW_JSON_SCAN_STAGE,
                    file=relative_path,
                    message="Duplicate node id within workflow JSON",
                    rule_id=DUPLICATE_NODE_RULE_ID,
                )
            )
            return

        edge_ids: list[str] = []
        for edge in edges:
            edge_id = edge.get("id")
            if not isinstance(edge_id, str) or not edge_id:
                edge_id = f"{edge['source']}->{edge['target']}"
            edge_ids.append(edge_id)
        if len(edge_ids) != len(set(edge_ids)):
            result.issues.append(
                ParseIssue(
                    provider=WORKFLOW_JSON_PROVIDER_NAME,
                    scan_stage=WORKFLOW_JSON_SCAN_STAGE,
                    file=relative_path,
                    message="Duplicate edge id within workflow JSON",
                    rule_id=DUPLICATE_EDGE_RULE_ID,
                )
            )
            return

        known_node_ids = set(node_ids)
        for index, node in enumerate(nodes):
            node_id = node["id"]
            component_id = f"component:workflow:{relative_path}:{node_id}"
            pointer = f"/nodes/{index}"
            label = None
            data = node.get("data")
            if isinstance(data, dict) and isinstance(data.get("label"), str):
                label = self._masking_service.mask_text(data["label"])
            result.facts.append(
                ScanFact(
                    kind="workflow_component",
                    file=relative_path,
                    path=pointer,
                    value=component_id,
                    rule_id=WORKFLOW_NODE_RULE_ID,
                    provider=WORKFLOW_JSON_PROVIDER_NAME,
                )
            )
            result.evidence.append(
                Evidence(
                    id=f"evidence:workflow:{relative_path}:{node_id}",
                    kind="workflow_node",
                    file=relative_path,
                    path=pointer,
                    value=label or node_id,
                    rule_id=WORKFLOW_NODE_RULE_ID,
                )
            )

        for index, edge in enumerate(edges):
            source = edge["source"]
            target = edge["target"]
            if source not in known_node_ids or target not in known_node_ids:
                continue
            edge_id = edge_ids[index]
            pointer = f"/edges/{index}"
            canonical_edge_id = f"edge:workflow:{relative_path}:{edge_id}"
            result.facts.append(
                ScanFact(
                    kind="workflow_edge",
                    file=relative_path,
                    path=pointer,
                    value=canonical_edge_id,
                    rule_id=WORKFLOW_EDGE_RULE_ID,
                    provider=WORKFLOW_JSON_PROVIDER_NAME,
                )
            )
            result.evidence.append(
                Evidence(
                    id=(f"evidence:workflow-edge:{relative_path}:{edge_id}"),
                    kind="workflow_edge",
                    file=relative_path,
                    path=pointer,
                    value=f"{source}->{target}",
                    rule_id=WORKFLOW_EDGE_RULE_ID,
                )
            )
