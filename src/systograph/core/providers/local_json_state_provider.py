from __future__ import annotations

from pathlib import Path

from systograph.core.models.analysis_history import (
    LatestBuildPointer,
    MapBuildManifest,
    ProjectState,
    ScanSnapshot,
)
from systograph.core.models.mapping import ManualMapping
from systograph.core.providers.local_json_history_repository import (
    LocalJsonHistoryRepository,
)
from systograph.core.providers.local_json_project_repository import (
    LocalJsonProjectRepository,
)
from systograph.core.providers.local_json_snapshot_safety import (
    LocalJsonSnapshotSafety,
)
from systograph.core.providers.local_json_state_errors import (
    InvalidStateIdError,
    LocalStateError,
    ProjectStateBusyError,
    StateConflictError,
    StateCorruptionError,
)
from systograph.core.providers.local_json_state_storage import (
    LocalJsonStateStorage,
)
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

__all__ = [
    "InvalidStateIdError",
    "LocalJsonStateProvider",
    "LocalStateError",
    "ProjectStateBusyError",
    "StateConflictError",
    "StateCorruptionError",
]


class LocalJsonStateProvider:
    def __init__(
        self,
        state_root: Path,
        *,
        lock_timeout: float = 5.0,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        storage = LocalJsonStateStorage(
            state_root,
            lock_timeout=lock_timeout,
        )
        self._projects = LocalJsonProjectRepository(storage)
        self._history = LocalJsonHistoryRepository(
            storage,
            snapshot_safety=LocalJsonSnapshotSafety(masking_service),
            project_lookup=self._projects,
        )

    def save_project(self, project: ProjectState) -> ProjectState:
        return self._projects.save_project(project)

    def get_project(self, project_id: str) -> ProjectState | None:
        return self._projects.get_project(project_id)

    def list_projects(self) -> tuple[ProjectState, ...]:
        return self._projects.list_projects()

    def find_project_by_path_digest(
        self,
        path_digest: str,
    ) -> ProjectState | None:
        return self._projects.find_project_by_path_digest(path_digest)

    def save(self, mapping: ManualMapping) -> ManualMapping:
        return self._projects.save(mapping)

    def get(self, mapping_id: str) -> ManualMapping | None:
        return self._projects.get(mapping_id)

    def list_for_project(self, project_id: str) -> list[ManualMapping]:
        return self._projects.list_for_project(project_id)

    def save_snapshot(self, snapshot: ScanSnapshot) -> ScanSnapshot:
        return self._history.save_snapshot(snapshot)

    def get_snapshot(
        self,
        project_id: str,
        scan_id: str,
    ) -> ScanSnapshot | None:
        return self._history.get_snapshot(project_id, scan_id)

    def save_build_manifest(
        self,
        manifest: MapBuildManifest,
    ) -> MapBuildManifest:
        return self._history.save_build_manifest(manifest)

    def get_build_manifest(
        self,
        project_id: str,
        build_id: str,
    ) -> MapBuildManifest | None:
        return self._history.get_build_manifest(project_id, build_id)

    def find_build_manifest(
        self,
        build_id: str,
    ) -> MapBuildManifest | None:
        return self._history.find_build_manifest(build_id)

    def list_build_manifests(
        self,
        project_id: str,
    ) -> tuple[MapBuildManifest, ...]:
        return self._history.list_build_manifests(project_id)

    def get_latest_pointer(
        self,
        project_id: str,
    ) -> LatestBuildPointer | None:
        return self._history.get_latest_pointer(project_id)

    def discard_unpublished_build(
        self,
        project_id: str,
        build_id: str,
    ) -> None:
        self._history.discard_unpublished_build(project_id, build_id)

    def get_latest_build_id(self, project_id: str) -> str | None:
        return self._history.get_latest_build_id(project_id)

    def promote_latest_build(
        self,
        *,
        project_id: str,
        build_id: str,
        expected_latest_build_id: str | None,
        expected_revision: int,
    ) -> LatestBuildPointer:
        return self._history.promote_latest_build(
            project_id=project_id,
            build_id=build_id,
            expected_latest_build_id=expected_latest_build_id,
            expected_revision=expected_revision,
        )
