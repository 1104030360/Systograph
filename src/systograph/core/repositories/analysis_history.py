from __future__ import annotations

from typing import Protocol

from systograph.core.models.analysis_history import (
    LatestBuildPointer,
    MapBuildManifest,
    ProjectState,
    ScanSnapshot,
)
from systograph.core.models.mapping import ManualMapping


class ProjectRepository(Protocol):
    def save_project(self, project: ProjectState) -> ProjectState: ...

    def get_project(self, project_id: str) -> ProjectState | None: ...

    def find_project_by_path_digest(
        self, path_digest: str
    ) -> ProjectState | None: ...


class ScanSnapshotRepository(Protocol):
    def save_snapshot(self, snapshot: ScanSnapshot) -> ScanSnapshot: ...

    def get_snapshot(
        self, project_id: str, scan_id: str
    ) -> ScanSnapshot | None: ...


class MapBuildRepository(Protocol):
    def save_build_manifest(
        self, manifest: MapBuildManifest
    ) -> MapBuildManifest: ...

    def get_build_manifest(
        self, project_id: str, build_id: str
    ) -> MapBuildManifest | None: ...

    def find_build_manifest(
        self, build_id: str
    ) -> MapBuildManifest | None: ...

    def list_build_manifests(
        self, project_id: str
    ) -> tuple[MapBuildManifest, ...]: ...

    def discard_unpublished_build(
        self, project_id: str, build_id: str
    ) -> None: ...

    def get_latest_pointer(
        self, project_id: str
    ) -> LatestBuildPointer | None: ...

    def promote_latest_build(
        self,
        *,
        project_id: str,
        build_id: str,
        expected_latest_build_id: str | None,
        expected_revision: int,
    ) -> LatestBuildPointer: ...


class ManualMappingRepository(Protocol):
    def save(self, mapping: ManualMapping) -> ManualMapping: ...

    def get(self, mapping_id: str) -> ManualMapping | None: ...

    def list_for_project(self, project_id: str) -> list[ManualMapping]: ...
