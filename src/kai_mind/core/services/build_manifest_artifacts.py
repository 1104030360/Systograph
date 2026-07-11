from __future__ import annotations

import hashlib
import json
from pathlib import Path

from kai_mind.core.models.analysis_history import MapBuildManifest
from kai_mind.core.models.map_build import MapBuildResult

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
    if lineage is None:
        raise ValueError("lineage is required")
    for name in (
        "profile_signals.json",
        "readiness_report.json",
        "call_graph.json",
        "dataflow_hints.json",
        "execution_paths.json",
        "evidence_table.json",
    ):
        payload = json.loads(paths[name].read_text(encoding="utf-8"))
        if (
            payload.get("build_id") != lineage.build_id
            or payload.get("scan_id") != lineage.scan_id
            or payload.get("generated_from_build_id") != lineage.build_id
        ):
            raise ValueError(f"artifact scope mismatch: {name}")


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
