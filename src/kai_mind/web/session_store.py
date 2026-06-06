"""In-memory session state for the local development API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from kai_mind.core.models.map_build import MapBuildResult
from kai_mind.core.models.viewer import ViewerPayload
from kai_mind.core.services.viewer_session_service import ViewerSessionService


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    project_path: Path
    project_name: str
    source_type: str


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

    def save_build_result(self, result: MapBuildResult) -> None:
        self._latest_build_result = result
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
