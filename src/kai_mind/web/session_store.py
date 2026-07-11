"""In-memory session state for the local development API."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from kai_mind.core.models.analysis_history import ProjectState
from kai_mind.core.models.map_build import MapBuildResult
from kai_mind.core.models.viewer import ViewerPayload
from kai_mind.core.providers.local_json_state_provider import (
    LocalJsonStateProvider,
)
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.viewer_session_service import ViewerSessionService


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    project_path: Path
    project_name: str
    source_type: str
    reused: bool = False


class SessionStore(Protocol):
    def import_project(
        self, *, project_path: Path, source_type: str
    ) -> ProjectRecord: ...

    def project(self, project_id: str) -> ProjectRecord | None: ...

    def save_build_result(
        self, result: MapBuildResult, *, project_id: str | None = None
    ) -> None: ...

    def save_viewer_payload(self, payload: ViewerPayload) -> None: ...

    def latest_viewer_payload(self) -> ViewerPayload: ...

    def latest_build_result(self) -> MapBuildResult | None: ...

    def build_result(self, project_id: str) -> MapBuildResult | None: ...

    def build_results(self) -> tuple[tuple[str, MapBuildResult], ...]: ...


class InMemorySessionStore:
    """Non-persistent local API state for one backend process."""

    def __init__(
        self,
        *,
        projection_service: ViewerSessionService | None = None,
    ) -> None:
        self._projection_service = projection_service or ViewerSessionService()
        self._projects: dict[str, ProjectRecord] = {}
        self._latest_viewer_payload = ViewerPayload(
            viewer_load_result=self._projection_service.empty()
        )
        self._latest_build_result: MapBuildResult | None = None
        self._build_results_by_project: dict[str, MapBuildResult] = {}

    def import_project(
        self,
        *,
        project_path: Path,
        source_type: str,
    ) -> ProjectRecord:
        record = ProjectRecord(
            project_id=f"project:{uuid4()}",
            project_path=project_path,
            project_name=project_path.name or "project",
            source_type=source_type,
        )
        self._projects[record.project_id] = record
        return record

    def project(self, project_id: str) -> ProjectRecord | None:
        return self._projects.get(project_id)

    def save_build_result(
        self,
        result: MapBuildResult,
        *,
        project_id: str | None = None,
    ) -> None:
        self._latest_build_result = result
        if project_id is not None:
            self._build_results_by_project[project_id] = result
        if result.viewer_load_result is not None:
            self.save_viewer_payload(
                ViewerPayload(viewer_load_result=result.viewer_load_result)
            )

    def save_viewer_payload(self, payload: ViewerPayload) -> None:
        self._latest_viewer_payload = payload

    def latest_viewer_payload(self) -> ViewerPayload:
        return self._latest_viewer_payload

    def latest_build_result(self) -> MapBuildResult | None:
        return self._latest_build_result

    def build_result(self, project_id: str) -> MapBuildResult | None:
        return self._build_results_by_project.get(project_id)

    def build_results(self) -> tuple[tuple[str, MapBuildResult], ...]:
        return tuple(self._build_results_by_project.items())


class PersistentSessionStore:
    def __init__(
        self,
        *,
        repository: LocalJsonStateProvider,
        manifest_service: BuildManifestService,
        projection_service: ViewerSessionService | None = None,
    ) -> None:
        self._repository = repository
        self._manifest_service = manifest_service
        self._projection = projection_service or ViewerSessionService()
        self._latest_viewer_payload = ViewerPayload(
            viewer_load_result=self._projection.empty()
        )
        self._latest_build_result: MapBuildResult | None = None

    def import_project(
        self,
        *,
        project_path: Path,
        source_type: str,
    ) -> ProjectRecord:
        resolved = project_path.expanduser().resolve()
        path_digest = (
            "sha256:"
            + hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()
        )
        existing = self._repository.find_project_by_path_digest(path_digest)
        if existing is not None:
            return self._record(existing, reused=True)
        state = ProjectState(
            project_id=f"project:{uuid4()}",
            project_name=resolved.name or "project",
            source_type="local_path",
            canonical_path=str(resolved),
            path_digest=path_digest,
            created_at=datetime.now(UTC),
        )
        self._repository.save_project(state)
        return self._record(state, reused=False)

    def project(self, project_id: str) -> ProjectRecord | None:
        state = self._repository.get_project(project_id)
        return self._record(state, reused=True) if state else None

    def save_build_result(
        self,
        result: MapBuildResult,
        *,
        project_id: str | None = None,
    ) -> None:
        self._latest_build_result = result
        if result.viewer_load_result is not None:
            self.save_viewer_payload(
                ViewerPayload(viewer_load_result=result.viewer_load_result)
            )

    def save_viewer_payload(self, payload: ViewerPayload) -> None:
        self._latest_viewer_payload = payload

    def latest_viewer_payload(self) -> ViewerPayload:
        result = self.latest_build_result()
        if result is not None and result.viewer_load_result is not None:
            return ViewerPayload(viewer_load_result=result.viewer_load_result)
        return self._latest_viewer_payload

    def latest_build_result(self) -> MapBuildResult | None:
        if self._latest_build_result is not None:
            return self._latest_build_result
        candidates = []
        for project in self._repository.list_projects():
            pointer = self._repository.get_latest_pointer(project.project_id)
            if pointer is not None:
                candidates.append(pointer)
        if not candidates:
            return None
        pointer = max(
            candidates,
            key=lambda item: (item.updated_at, item.latest_build_id),
        )
        return self.build_result(pointer.project_id)

    def build_result(self, project_id: str) -> MapBuildResult | None:
        pointer = self._repository.get_latest_pointer(project_id)
        if pointer is None:
            return None
        manifest = self._repository.get_build_manifest(
            project_id,
            pointer.latest_build_id,
        )
        if manifest is None:
            return None
        result = self._manifest_service.load(manifest)
        self._latest_build_result = result
        return result

    def build_results(self) -> tuple[tuple[str, MapBuildResult], ...]:
        results: list[tuple[str, MapBuildResult]] = []
        for project in self._repository.list_projects():
            result = self.build_result(project.project_id)
            if result is not None:
                results.append((project.project_id, result))
        return tuple(results)

    @staticmethod
    def _record(state: ProjectState, *, reused: bool) -> ProjectRecord:
        return ProjectRecord(
            project_id=state.project_id,
            project_path=Path(state.canonical_path),
            project_name=state.project_name,
            source_type=state.source_type,
            reused=reused,
        )
