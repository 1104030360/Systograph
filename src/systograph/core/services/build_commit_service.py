from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Literal, Protocol

from systograph.core.models.analysis_history import (
    LatestBuildPointer,
    MapBuildManifest,
)
from systograph.core.models.map_build import MapBuildResult
from systograph.core.models.scan import OutputRun
from systograph.core.providers.local_json_state_errors import (
    StateConflictError,
)
from systograph.core.services.build_manifest_artifacts import (
    PATH_FIELDS,
    required_artifact_paths,
    validate_artifact_scope,
)
from systograph.core.services.build_manifest_service import (
    BuildManifestService,
)

BuildCommitErrorCode = Literal[
    "build_output_conflict",
    "build_artifact_set_invalid",
    "atomic_artifact_publish_unavailable",
    "build_manifest_persist_failed",
    "stale_latest_revision",
]
BuildOperation = Callable[[OutputRun], MapBuildResult]


class BuildCommitRepository(Protocol):
    def get_build_manifest(
        self,
        project_id: str,
        build_id: str,
    ) -> MapBuildManifest | None: ...

    def get_latest_pointer(
        self,
        project_id: str,
    ) -> LatestBuildPointer | None: ...

    def promote_latest_build(
        self,
        *,
        project_id: str,
        build_id: str,
        expected_latest_build_id: str | None,
        expected_revision: int,
    ) -> LatestBuildPointer: ...


class BuildCommitError(RuntimeError):
    def __init__(
        self,
        code: BuildCommitErrorCode,
        *,
        committed_result: MapBuildResult | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.committed_result = committed_result


class BuildCommitService:
    def __init__(
        self,
        *,
        repository: BuildCommitRepository,
        manifest_service: BuildManifestService,
    ) -> None:
        self._repository = repository
        self._manifest = manifest_service

    def commit(
        self,
        *,
        project_id: str,
        build_id: str,
        final_output_dir: Path,
        expected_latest_build_id: str | None,
        expected_revision: int,
        build: BuildOperation,
        apply_request_digest: str | None = None,
    ) -> MapBuildResult:
        final_dir = final_output_dir.absolute()
        staging_dir = final_dir.with_name(f"{final_dir.name}.staging")
        self._prepare_staging(final_dir, staging_dir)
        published = False
        result: MapBuildResult | None = None
        try:
            result = build(OutputRun(root_dir=staging_dir))
            self._validate_result(
                result,
                project_id=project_id,
                build_id=build_id,
                staging_dir=staging_dir,
            )
            self._publish_directory(staging_dir, final_dir)
            published = True
        finally:
            if not published:
                self._remove_staging(staging_dir)
        if result is None:
            raise BuildCommitError("build_artifact_set_invalid")
        committed = self._rebase_result(result, final_dir)
        try:
            self._manifest.persist(
                committed,
                apply_request_digest=apply_request_digest,
            )
        except (OSError, ValueError, StateConflictError) as exc:
            raise BuildCommitError(
                "build_manifest_persist_failed",
                committed_result=committed,
            ) from exc
        try:
            self._repository.promote_latest_build(
                project_id=project_id,
                build_id=build_id,
                expected_latest_build_id=expected_latest_build_id,
                expected_revision=expected_revision,
            )
        except StateConflictError as exc:
            raise BuildCommitError(
                "stale_latest_revision",
                committed_result=committed,
            ) from exc
        return committed

    def discard_orphan_artifact_set(
        self,
        *,
        project_id: str,
        build_id: str,
        final_output_dir: Path,
    ) -> None:
        final_dir = final_output_dir.absolute()
        pointer = self._repository.get_latest_pointer(project_id)
        manifest = self._repository.get_build_manifest(project_id, build_id)
        if (
            final_dir.name != build_id.replace(":", "_")
            or manifest is not None
            or (pointer is not None and pointer.latest_build_id == build_id)
            or final_dir.is_symlink()
            or (final_dir.exists() and not final_dir.is_dir())
        ):
            raise BuildCommitError("build_output_conflict")
        if final_dir.is_dir():
            shutil.rmtree(final_dir)

    @staticmethod
    def _prepare_staging(final_dir: Path, staging_dir: Path) -> None:
        final_dir.parent.mkdir(parents=True, exist_ok=True)
        if final_dir.exists() or final_dir.is_symlink():
            raise BuildCommitError("build_output_conflict")
        BuildCommitService._remove_staging(staging_dir)
        staging_dir.mkdir()
        if staging_dir.stat().st_dev != final_dir.parent.stat().st_dev:
            BuildCommitService._remove_staging(staging_dir)
            raise BuildCommitError("atomic_artifact_publish_unavailable")

    @staticmethod
    def _validate_result(
        result: MapBuildResult,
        *,
        project_id: str,
        build_id: str,
        staging_dir: Path,
    ) -> None:
        lineage = result.lineage
        if (
            result.status != "ok"
            or result.output_run_dir != staging_dir
            or lineage is None
            or lineage.project_id != project_id
            or lineage.build_id != build_id
        ):
            raise BuildCommitError("build_artifact_set_invalid")
        try:
            paths = required_artifact_paths(result)
            validate_artifact_scope(result, paths)
        except (OSError, ValueError) as exc:
            raise BuildCommitError("build_artifact_set_invalid") from exc
        if any(path.parent != staging_dir for path in paths.values()):
            raise BuildCommitError("build_artifact_set_invalid")

    @staticmethod
    def _publish_directory(staging_dir: Path, final_dir: Path) -> None:
        if final_dir.exists() or final_dir.is_symlink():
            raise BuildCommitError("build_output_conflict")
        try:
            os.rename(staging_dir, final_dir)
        except OSError as exc:
            code: BuildCommitErrorCode = (
                "build_output_conflict"
                if final_dir.exists() or final_dir.is_symlink()
                else "atomic_artifact_publish_unavailable"
            )
            raise BuildCommitError(code) from exc

    @staticmethod
    def _rebase_result(
        result: MapBuildResult,
        final_dir: Path,
    ) -> MapBuildResult:
        updates: dict[str, Path] = {"output_run_dir": final_dir}
        for name, field in PATH_FIELDS.items():
            updates[field] = final_dir / name
        return result.model_copy(update=updates)

    @staticmethod
    def _remove_staging(staging_dir: Path) -> None:
        try:
            if staging_dir.is_symlink() or staging_dir.is_file():
                staging_dir.unlink(missing_ok=True)
            elif staging_dir.is_dir():
                shutil.rmtree(staging_dir)
        except OSError:
            pass
