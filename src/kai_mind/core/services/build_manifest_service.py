# 這個檔案負責：把成功的 MapBuildResult 存成 MapBuildManifest（含 artifact
# digests），
# 以及依 manifest「同一條路徑」reload 回 MapBuildResult（再走
# CanonicalMapLoader + Viewer）。
#
# 呼叫鏈：
#   persist：ApplyConfirmations / history 流程 →
# BuildManifestService.persist(result)
#            → 算 digests → repository.save_build_manifest
#   load：依 manifest 讀磁碟 artifacts → validate/digest →
#         CanonicalMapLoader.load → ViewerSessionService.build_loaded →
#         MapBuildResult
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
    artifact_manifest_entry,
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
from kai_mind.core.services.viewer_session_service import ViewerSessionService


# 做什麼：寫入 MapBuildManifest 的 repository 協定。
# 被誰用：BuildManifestService.persist。
# 自己呼叫：實作方（storage）提供 save_build_manifest。
class BuildManifestWriter(Protocol):
    def save_build_manifest(
        self,
        manifest: MapBuildManifest,
    ) -> MapBuildManifest: ...


# 做什麼：reload 時必要 artifact 無效或 map 無法載入時丟出。
# 被誰用：load / _require_valid_digest。
class BuildArtifactLoadError(ValueError):
    pass


# 做什麼：persist（存 manifest）與 load（依 manifest 重載同一套 artifacts）。
# 被誰用：ApplyConfirmations / history / query 需要「重開舊 build」的路徑。
# 自己呼叫：CanonicalMapLoader、ViewerSessionService、digest helpers。
class BuildManifestService:
    # 做什麼：注入 repository、canonical loader、viewer。
    # 被誰呼叫：DI / 測試。
    # 自己呼叫：預設 CanonicalMapLoader、ViewerSessionService。
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

    # 做什麼：成功 build 後寫入 manifest（output_dir + 各 artifact digest）。
    # 被誰呼叫：ApplyConfirmations / 需要記錄 lineage 的流程。
    # 自己呼叫：required_artifact_paths、validate_artifact_scope、digest、
    #           repository.save_build_manifest。
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
        system_map = result.ai_system_map
        if system_map is None:
            raise ValueError("canonical map is missing")
        artifacts = {
            name: artifact_manifest_entry(path) for name, path in paths.items()
        }
        manifest = MapBuildManifest(
            lineage=result.lineage,
            output_dir=str(result.output_run_dir),
            artifact_set_version=system_map.artifact_set_version,
            environment_id=system_map.environment_id,
            artifact_digests={
                name: entry.digest for name, entry in artifacts.items()
            },
            artifacts=artifacts,
            active_schema_version=result.active_schema_version,
            requested_schema_version=result.requested_schema_version,
            source_schema_version=result.source_schema_version,
            operator_rollback_active=result.operator_rollback_active,
            migration_warnings=tuple(result.migration_warnings),
            detail_scan_results=tuple(result.detail_scan_results),
            apply_request_digest=apply_request_digest,
        )
        return self._repository.save_build_manifest(manifest)

    # 做什麼：依 manifest 從磁碟 reload 同一套 build（同路徑驗證 digest）。
    # 被誰呼叫：需要重開歷史 build / query service。
    # 自己呼叫：
    #   1. 驗 ai_system_map.json digest → CanonicalMapLoader
    #   2. _load_profiles / _load_readiness（可降級成 warning）
    #   3. 其他 optional artifacts digest 不符 → warning
    #   4. ViewerSessionService.build_loaded → MapBuildResult
    def load(self, manifest: MapBuildManifest) -> MapBuildResult:
        output_dir = Path(manifest.output_dir)
        paths = {name: output_dir / name for name in PATH_FIELDS}
        map_path = paths["ai_system_map.json"]
        self._require_valid_digest(manifest, "ai_system_map.json", map_path)
        try:
            map_payload = json.loads(map_path.read_text(encoding="utf-8"))
            loaded = self._canonical_loader.load(map_payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise BuildArtifactLoadError("canonical map is invalid") from exc
        if loaded.active_schema_version != manifest.active_schema_version:
            raise BuildArtifactLoadError(
                "manifest schema version does not match artifact"
            )
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
        viewer = self._viewer.build_loaded(
            loaded.with_normalized(normalized),
            map_json_path=map_path,
            profile_result=profiles,
        )
        return MapBuildResult(
            status="ok",
            project_name=normalized.project.name,
            output_run_dir=output_dir,
            viewer_load_result=viewer,
            ai_system_map=normalized,
            profile_inference_result=profiles,
            readiness_report=readiness,
            lineage=manifest.lineage,
            active_schema_version=manifest.active_schema_version,
            requested_schema_version=manifest.requested_schema_version,
            source_schema_version=(
                manifest.source_schema_version
                or normalized.source_schema_version
                or normalized.schema_version
            ),
            operator_rollback_active=manifest.operator_rollback_active,
            migration_warnings=list(manifest.migration_warnings),
            detail_scan_results=list(manifest.detail_scan_results),
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

    # 做什麼：載入並驗證 profile_signals.json（digest + schema + scope）。
    # 被誰呼叫：load()。
    # 自己呼叫：digest_matches、ProfileInferenceResult.model_validate_json、
    #           ProfileSignalValidationService.validate、_scope_matches。
    # 失敗：寫 warning、回 None（不擋整個 reload）。
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

    # 做什麼：載入並驗證 readiness_report.json（digest + schema + scope）。
    # 被誰呼叫：load()。
    # 自己呼叫：digest_matches、ReadinessReport.model_validate_json、
    # _scope_matches。
    # 失敗：寫 warning、回 None。
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

    # 做什麼：確認 artifact 的 build_id/scan_id 與 manifest.lineage 一致。
    # 被誰呼叫：_load_profiles / _load_readiness。
    # 自己呼叫：getattr。
    @staticmethod
    def _scope_matches(manifest: MapBuildManifest, item: object) -> bool:
        return bool(
            getattr(item, "build_id", None) == manifest.lineage.build_id
            and getattr(item, "scan_id", None) == manifest.lineage.scan_id
        )

    # 做什麼：必要 artifact digest 不符就丟 BuildArtifactLoadError。
    # 被誰呼叫：load()（對 ai_system_map.json）。
    # 自己呼叫：digest_matches。
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
