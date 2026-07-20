from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from kai_mind.core.models.analysis_history import (
    LatestBuildPointer,
    MapBuildManifest,
    ProjectState,
    ScanSnapshot,
)
from kai_mind.core.models.mapping import ManualMapping

BuildIdFactory = Callable[[], str]


class ApplyRepository(Protocol):
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

    def get_snapshot(
        self, project_id: str, scan_id: str
    ) -> ScanSnapshot | None: ...

    def get_project(self, project_id: str) -> ProjectState | None: ...

    def get(self, mapping_id: str) -> ManualMapping | None: ...

    def promote_latest_build(
        self,
        *,
        project_id: str,
        build_id: str,
        expected_latest_build_id: str | None,
        expected_revision: int,
    ) -> LatestBuildPointer: ...

    def discard_unpublished_build(
        self, project_id: str, build_id: str
    ) -> None: ...


class ApplyConfirmationsError(RuntimeError):
    pass


class BuildNotFoundError(ApplyConfirmationsError):
    pass


class MappingNotFoundError(ApplyConfirmationsError):
    pass


class BaseBuildNotLatestError(ApplyConfirmationsError):
    pass


class ApplyValidationError(ApplyConfirmationsError):
    pass


class ApplyBuildError(ApplyConfirmationsError):
    pass
