from __future__ import annotations

from kai_mind.core.models.analysis_history import ProjectState
from kai_mind.core.models.mapping import ManualMapping
from kai_mind.core.providers.local_json_state_errors import StateConflictError
from kai_mind.core.providers.local_json_state_storage import (
    LocalJsonStateStorage,
)


class LocalJsonProjectRepository:
    def __init__(self, storage: LocalJsonStateStorage) -> None:
        self._storage = storage

    def save_project(self, project: ProjectState) -> ProjectState:
        self._storage.validate_id(project.project_id, "project")
        with self._storage.project_lock(project.project_id):
            existing = self.get_project(project.project_id)
            if existing is not None and existing != project:
                raise StateConflictError("project identity is immutable")
            self._storage.write_model(
                self._storage.project_file(project.project_id),
                project,
            )
        return project

    def get_project(self, project_id: str) -> ProjectState | None:
        self._storage.validate_id(project_id, "project")
        return self._storage.read_model(
            self._storage.project_file(project_id),
            ProjectState,
        )

    def list_projects(self) -> tuple[ProjectState, ...]:
        if not self._storage.projects_root.exists():
            return ()
        projects = tuple(
            project
            for path in sorted(
                self._storage.projects_root.glob("*/project.json")
            )
            if (project := self._storage.read_model(path, ProjectState))
            is not None
        )
        return tuple(sorted(projects, key=lambda item: item.project_id))

    def find_project_by_path_digest(
        self,
        path_digest: str,
    ) -> ProjectState | None:
        return next(
            (
                project
                for project in self.list_projects()
                if project.path_digest == path_digest and project.active
            ),
            None,
        )

    def save(self, mapping: ManualMapping) -> ManualMapping:
        self._storage.validate_id(mapping.project_id, "project")
        self._storage.validate_id(mapping.mapping_id, "mapping")
        existing = self.get(mapping.mapping_id)
        if existing is not None and existing.project_id != mapping.project_id:
            raise StateConflictError("mapping id belongs to another project")
        with self._storage.project_lock(mapping.project_id):
            self._storage.write_model(
                self._storage.mapping_file(
                    mapping.project_id,
                    mapping.mapping_id,
                ),
                mapping,
            )
        return mapping

    def get(self, mapping_id: str) -> ManualMapping | None:
        self._storage.validate_id(mapping_id, "mapping")
        return self._storage.find_model(
            "mappings",
            self._storage.segment(mapping_id) + ".json",
            ManualMapping,
        )

    def list_for_project(self, project_id: str) -> list[ManualMapping]:
        self._storage.validate_id(project_id, "project")
        directory = self._storage.project_dir(project_id) / "mappings"
        mappings = [
            item
            for path in sorted(directory.glob("*.json"))
            if (item := self._storage.read_model(path, ManualMapping))
            is not None
        ]
        return sorted(
            mappings,
            key=lambda item: (item.created_at, item.mapping_id),
        )
