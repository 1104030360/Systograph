from __future__ import annotations

import hashlib
import json
from pathlib import Path

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.analysis_history import (
    ArtifactManifestEntry,
    MapBuildManifest,
)
from systograph.core.models.execution_artifact import (
    ArtifactEdge,
    CallGraphArtifact,
    DataflowHintsArtifact,
    EvidenceTableArtifact,
    ExecutionPathsArtifact,
)
from systograph.core.models.map_build import MapBuildResult
from systograph.core.models.profile_signal import ProfileInferenceResult
from systograph.core.models.readiness_report import ReadinessReport
from systograph.core.services.canonical_map_loader import CanonicalMapLoader
from systograph.core.services.profile_signal_validation_service import (
    ProfileSignalValidationService,
)

PATH_FIELDS = {
    "ai_system_map.json": "map_json_path",
    "profile_signals.json": "profile_signals_path",
    "readiness_report.json": "readiness_report_path",
    "call_graph.json": "call_graph_path",
    "dataflow_hints.json": "dataflow_hints_path",
    "execution_paths.json": "execution_paths_path",
    "evidence_table.json": "evidence_table_path",
    "ai_system_map.md": "map_markdown_path",
    "system_map.mmd": "system_map_mermaid_path",
    "execution_map.mmd": "execution_map_mermaid_path",
}


def required_artifact_paths(result: MapBuildResult) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, field in PATH_FIELDS.items():
        value = getattr(result, field)
        if value is None or not value.is_file():
            raise ValueError(f"required build artifact is missing: {name}")
        if value.name != name:
            raise ValueError(f"artifact path mismatch: {name}")
        paths[name] = value
    return paths


def validate_artifact_scope(
    result: MapBuildResult,
    paths: dict[str, Path],
) -> None:
    lineage = result.lineage
    system_map = result.ai_system_map
    if lineage is None or system_map is None:
        raise ValueError("lineage is required")
    expected = {
        "build_id": lineage.build_id,
        "scan_id": lineage.scan_id,
        "environment_id": system_map.environment_id,
        "artifact_set_version": system_map.artifact_set_version,
        "generated_from_build_id": lineage.build_id,
    }
    if result.active_schema_version == "ai-system-map/v2":
        _require_scope(paths["ai_system_map.json"], expected)
    for name in (
        "profile_signals.json",
        "readiness_report.json",
        "call_graph.json",
        "dataflow_hints.json",
        "execution_paths.json",
        "evidence_table.json",
    ):
        _require_scope(paths[name], expected)
    for name in (
        "ai_system_map.md",
        "system_map.mmd",
        "execution_map.mmd",
    ):
        _require_render_scope(paths[name], expected)
    _validate_json_schemas(result, paths)
    validate_artifact_references(result, paths)


def validate_artifact_references(
    result: MapBuildResult,
    paths: dict[str, Path],
) -> None:
    system_map = result.ai_system_map
    if system_map is None:
        raise ValueError("canonical map is required")
    known_evidence = {item.evidence_id for item in system_map.evidence}
    for name in (
        "profile_signals.json",
        "readiness_report.json",
        "call_graph.json",
        "dataflow_hints.json",
        "execution_paths.json",
        "evidence_table.json",
    ):
        payload = json.loads(paths[name].read_text(encoding="utf-8"))
        unknown = _evidence_references(payload) - known_evidence
        if unknown:
            raise ValueError(f"artifact evidence reference mismatch: {name}")
    call_graph = json.loads(
        paths["call_graph.json"].read_text(encoding="utf-8")
    )
    known_components = {item.component_id for item in system_map.components}
    node_ids = {
        item.get("node_id")
        for item in call_graph.get("nodes", [])
        if isinstance(item, dict)
    }
    if node_ids - known_components:
        raise ValueError("call graph references unknown component")
    for edge in call_graph.get("edges", []):
        if not isinstance(edge, dict):
            raise ValueError("call graph edge is invalid")
        if (
            edge.get("source") not in known_components
            or edge.get("target") not in known_components
        ):
            raise ValueError("call graph edge references unknown component")
    dataflow = json.loads(
        paths["dataflow_hints.json"].read_text(encoding="utf-8")
    )
    for edge in dataflow.get("hints", []):
        if (
            edge.get("source") not in known_components
            or edge.get("target") not in known_components
        ):
            raise ValueError("dataflow hint references unknown component")
    execution = json.loads(
        paths["execution_paths.json"].read_text(encoding="utf-8")
    )
    for edge in execution.get("paths", []):
        if not isinstance(edge, dict):
            raise ValueError("execution path edge is invalid")
        if (
            edge.get("source") not in known_components
            or edge.get("target") not in known_components
        ):
            raise ValueError("execution path references unknown component")


def artifact_manifest_entry(path: Path) -> ArtifactManifestEntry:
    schema_version: str | None = None
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"artifact JSON root is invalid: {path.name}")
        value = payload.get("schema_version")
        schema_version = value if isinstance(value, str) else None
    return ArtifactManifestEntry(
        digest=digest(path),
        size_bytes=path.stat().st_size,
        schema_version=schema_version,
    )


def _require_scope(path: Path, expected: dict[str, str]) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or any(
        payload.get(field) != value for field, value in expected.items()
    ):
        raise ValueError(f"artifact scope mismatch: {path.name}")


def _require_render_scope(path: Path, expected: dict[str, str]) -> None:
    content = path.read_text(encoding="utf-8")
    if any(value not in content for value in expected.values()):
        raise ValueError(f"render artifact scope mismatch: {path.name}")


def _validate_json_schemas(
    result: MapBuildResult,
    paths: dict[str, Path],
) -> None:
    map_payload = _json_object(paths["ai_system_map.json"])
    loaded = CanonicalMapLoader().load(map_payload)
    if loaded.active_schema_version != result.active_schema_version:
        raise ValueError("canonical artifact schema does not match build")
    profile = ProfileInferenceResult.model_validate(
        _json_object(paths["profile_signals.json"])
    )
    if result.ai_system_map is None:
        raise ValueError("canonical map is required")
    ProfileSignalValidationService().validate(
        profile,
        system_map=result.ai_system_map,
    )
    ReadinessReport.model_validate(
        _json_object(paths["readiness_report.json"])
    )
    call_graph = CallGraphArtifact.model_validate(
        _json_object(paths["call_graph.json"])
    )
    dataflow_hints = DataflowHintsArtifact.model_validate(
        _json_object(paths["dataflow_hints.json"])
    )
    execution_paths = ExecutionPathsArtifact.model_validate(
        _json_object(paths["execution_paths.json"])
    )
    validate_static_edge_parity(
        loaded.normalized,
        call_graph=call_graph,
        dataflow_hints=dataflow_hints,
        execution_paths=execution_paths,
    )
    EvidenceTableArtifact.model_validate(
        _json_object(paths["evidence_table.json"])
    )


def validate_static_edge_parity(
    system_map: AiSystemMapV2,
    *,
    call_graph: CallGraphArtifact,
    dataflow_hints: DataflowHintsArtifact,
    execution_paths: ExecutionPathsArtifact,
) -> None:
    expected = tuple(
        ArtifactEdge(
            edge_id=edge.edge_id,
            source=edge.source,
            target=edge.target,
            relationship=edge.relationship,
            status=edge.status,
            undetermined_reason=edge.undetermined_reason,
            evidence_ids=tuple(edge.evidence_ids),
        )
        for edge in system_map.edges
    )
    siblings = (
        ("call_graph.json", call_graph.edges),
        ("dataflow_hints.json", dataflow_hints.hints),
        ("execution_paths.json", execution_paths.paths),
    )
    for name, edges in siblings:
        if edges != expected:
            raise ValueError(f"static artifact edge mismatch: {name}")


def _json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact JSON root is invalid: {path.name}")
    return payload


def _evidence_references(payload: object) -> set[str]:
    references: set[str] = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "evidence_id" and isinstance(value, str):
                references.add(value)
            elif key.endswith("evidence_ids") and isinstance(value, list):
                references.update(
                    item for item in value if isinstance(item, str)
                )
            else:
                references.update(_evidence_references(value))
    elif isinstance(payload, list):
        for item in payload:
            references.update(_evidence_references(item))
    return references


def existing_path(path: Path) -> Path | None:
    return path if path.is_file() else None


def digest_matches(
    manifest: MapBuildManifest,
    name: str,
    path: Path,
) -> bool:
    expected = manifest.artifact_digests.get(name)
    return bool(expected and path.is_file() and expected == digest(path))


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
