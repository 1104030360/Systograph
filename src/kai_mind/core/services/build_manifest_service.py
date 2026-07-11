from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.analysis_history import MapBuildManifest
from kai_mind.core.models.map_build import MapBuildResult
from kai_mind.core.models.profile_signal import ProfileInferenceResult
from kai_mind.core.models.readiness_report import ReadinessReport
from kai_mind.core.services.build_manifest_artifacts import (
    PATH_FIELDS,
    digest,
    digest_matches,
    existing_path,
    required_artifact_paths,
    validate_artifact_scope,
)
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.profile_signal_validation_service import (
    ProfileSignalValidationError,
    ProfileSignalValidationService,
)
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)
from kai_mind.core.services.viewer_session_service import ViewerSessionService


class BuildManifestWriter(Protocol):
    def save_build_manifest(
        self,
        manifest: MapBuildManifest,
    ) -> MapBuildManifest: ...


class BuildArtifactLoadError(ValueError):
    pass


class BuildManifestService:
    def __init__(
        self,
        *,
        repository: BuildManifestWriter,
        canonical_loader: CanonicalMapLoader | None = None,
        viewer_service: ViewerSessionService | None = None,
    ) -> None:
        self._repository = repository
        self._canonical_loader = canonical_loader or CanonicalMapLoader()
        self._viewer = viewer_service or ViewerSessionService()

    def persist(
        self,
        result: MapBuildResult,
        *,
        apply_request_digest: str | None = None,
    ) -> MapBuildManifest:
        if result.status != "ok" or result.lineage is None:
            raise ValueError("only successful project builds can be persisted")
        if result.output_run_dir is None:
            raise ValueError("build output directory is missing")
        paths = required_artifact_paths(result)
        validate_artifact_scope(result, paths)
        manifest = MapBuildManifest(
            lineage=result.lineage,
            output_dir=str(result.output_run_dir),
            artifact_digests={
                name: digest(path) for name, path in paths.items()
            },
            active_schema_version=result.active_schema_version,
            requested_schema_version=result.requested_schema_version,
            migration_warnings=tuple(result.migration_warnings),
            apply_request_digest=apply_request_digest,
        )
        return self._repository.save_build_manifest(manifest)

    def load(self, manifest: MapBuildManifest) -> MapBuildResult:
        output_dir = Path(manifest.output_dir)
        paths = {name: output_dir / name for name in PATH_FIELDS}
        map_path = paths["ai_system_map.json"]
        self._require_valid_digest(manifest, "ai_system_map.json", map_path)
        try:
            map_payload = json.loads(map_path.read_text(encoding="utf-8"))
            system_map = SystemMapValidationService().validate(map_payload)
            loaded = self._canonical_loader.load(map_payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise BuildArtifactLoadError("canonical map is invalid") from exc
        normalized = loaded.normalized.model_copy(
            update={
                "scan_id": manifest.lineage.scan_id,
                "build_id": manifest.lineage.build_id,
                "generated_from_build_id": manifest.lineage.build_id,
            }
        )
        warnings: list[str] = []
        profiles = self._load_profiles(
            manifest,
            paths["profile_signals.json"],
            normalized=normalized,
            warnings=warnings,
        )
        readiness = self._load_readiness(
            manifest,
            paths["readiness_report.json"],
            warnings=warnings,
        )
        for name in PATH_FIELDS:
            if name in {
                "ai_system_map.json",
                "profile_signals.json",
                "readiness_report.json",
            }:
                continue
            if not digest_matches(manifest, name, paths[name]):
                warnings.append(f"optional_artifact_invalid:{name}")
        viewer = self._viewer.build(system_map, map_json_path=map_path)
        return MapBuildResult(
            status="ok",
            project_name=system_map.project.name,
            output_run_dir=output_dir,
            viewer_load_result=viewer,
            ai_system_map=system_map,
            normalized_ai_system_map=normalized,
            profile_inference_result=profiles,
            readiness_report=readiness,
            lineage=manifest.lineage,
            active_schema_version=manifest.active_schema_version,
            requested_schema_version=manifest.requested_schema_version,
            migration_warnings=list(manifest.migration_warnings),
            warnings=warnings,
            map_json_path=existing_path(paths["ai_system_map.json"]),
            profile_signals_path=existing_path(paths["profile_signals.json"]),
            readiness_report_path=existing_path(
                paths["readiness_report.json"]
            ),
            call_graph_path=existing_path(paths["call_graph.json"]),
            dataflow_hints_path=existing_path(paths["dataflow_hints.json"]),
            execution_paths_path=existing_path(paths["execution_paths.json"]),
            evidence_table_path=existing_path(paths["evidence_table.json"]),
            map_markdown_path=existing_path(paths["ai_system_map.md"]),
            system_map_mermaid_path=existing_path(paths["system_map.mmd"]),
            execution_map_mermaid_path=existing_path(
                paths["execution_map.mmd"]
            ),
        )

    def _load_profiles(
        self,
        manifest: MapBuildManifest,
        path: Path,
        *,
        normalized: AiSystemMapV2,
        warnings: list[str],
    ) -> ProfileInferenceResult | None:
        if not digest_matches(manifest, "profile_signals.json", path):
            warnings.append("profile_signals_missing_or_invalid")
            return None
        try:
            result = ProfileInferenceResult.model_validate_json(
                path.read_text(encoding="utf-8")
            )
            ProfileSignalValidationService().validate(
                result,
                system_map=normalized,
            )
        except (
            OSError,
            ValidationError,
            ProfileSignalValidationError,
        ):
            warnings.append("profile_signals_missing_or_invalid")
            return None
        if not self._scope_matches(manifest, result):
            warnings.append("profile_signals_scope_mismatch")
            return None
        return result

    def _load_readiness(
        self,
        manifest: MapBuildManifest,
        path: Path,
        *,
        warnings: list[str],
    ) -> ReadinessReport | None:
        if not digest_matches(manifest, "readiness_report.json", path):
            warnings.append("readiness_report_missing_or_invalid")
            return None
        try:
            report = ReadinessReport.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError):
            warnings.append("readiness_report_missing_or_invalid")
            return None
        if not self._scope_matches(manifest, report):
            warnings.append("readiness_report_scope_mismatch")
            return None
        return report

    @staticmethod
    def _scope_matches(manifest: MapBuildManifest, item: object) -> bool:
        return bool(
            getattr(item, "build_id", None) == manifest.lineage.build_id
            and getattr(item, "scan_id", None) == manifest.lineage.scan_id
        )

    def _require_valid_digest(
        self,
        manifest: MapBuildManifest,
        name: str,
        path: Path,
    ) -> None:
        if not digest_matches(manifest, name, path):
            raise BuildArtifactLoadError(
                f"required artifact is invalid: {name}"
            )
