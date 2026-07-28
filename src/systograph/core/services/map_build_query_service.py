from __future__ import annotations

from typing import Protocol

from systograph.core.models.analysis_history import (
    LatestBuildPointer,
    MapBuildManifest,
)
from systograph.core.models.map_build import MapBuildResult
from systograph.core.services.build_manifest_service import (
    BuildManifestService,
)


class BuildQueryRepository(Protocol):
    def find_build_manifest(
        self, build_id: str
    ) -> MapBuildManifest | None: ...

    def get_build_manifest(
        self, project_id: str, build_id: str
    ) -> MapBuildManifest | None: ...

    def list_build_manifests(
        self, project_id: str
    ) -> tuple[MapBuildManifest, ...]: ...

    def get_latest_pointer(
        self, project_id: str
    ) -> LatestBuildPointer | None: ...


class MapBuildQueryService:
    def __init__(
        self,
        *,
        repository: BuildQueryRepository,
        manifest_service: BuildManifestService,
    ) -> None:
        self._repository = repository
        self._manifest_service = manifest_service

    def get(self, build_id: str) -> MapBuildResult:
        manifest = self._repository.find_build_manifest(build_id)
        if manifest is None:
            raise KeyError(build_id)
        return self._manifest_service.load(manifest)

    def latest(self, project_id: str) -> MapBuildResult:
        pointer = self._repository.get_latest_pointer(project_id)
        if pointer is None:
            raise KeyError(project_id)
        manifest = self._repository.get_build_manifest(
            project_id,
            pointer.latest_build_id,
        )
        if manifest is None:
            raise KeyError(pointer.latest_build_id)
        return self._manifest_service.load(manifest)

    def list(self, project_id: str) -> tuple[MapBuildManifest, ...]:
        return self._repository.list_build_manifests(project_id)
