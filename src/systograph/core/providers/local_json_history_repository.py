from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from systograph.core.models.analysis_history import (
    LatestBuildPointer,
    MapBuildManifest,
    ProjectState,
    ScanSnapshot,
    ScanSnapshotManifest,
)
from systograph.core.providers.local_json_snapshot_safety import (
    LocalJsonSnapshotSafety,
)
from systograph.core.providers.local_json_state_errors import (
    StateConflictError,
)
from systograph.core.providers.local_json_state_storage import (
    LocalJsonStateStorage,
)


class ProjectLookup(Protocol):
    def get_project(self, project_id: str) -> ProjectState | None: ...


class LocalJsonHistoryRepository:
    def __init__(
        self,
        storage: LocalJsonStateStorage,
        *,
        snapshot_safety: LocalJsonSnapshotSafety,
        project_lookup: ProjectLookup,
    ) -> None:
        self._storage = storage
        self._snapshot_safety = snapshot_safety
        self._project_lookup = project_lookup

    def save_snapshot(self, snapshot: ScanSnapshot) -> ScanSnapshot:
        self._storage.validate_id(snapshot.project_id, "project")
        self._storage.validate_id(snapshot.scan_id, "scan")
        project = self._project_lookup.get_project(snapshot.project_id)
        workspace = Path(project.canonical_path) if project else None
        safe = self._snapshot_safety.sanitize(
            snapshot,
            workspace_root=workspace,
        )
        with self._storage.project_lock(snapshot.project_id):
            path = self._storage.snapshot_file(
                snapshot.project_id,
                snapshot.scan_id,
            )
            if path.exists():
                existing = self._storage.read_model(path, ScanSnapshot)
                if existing != safe:
                    raise StateConflictError("scan snapshot is immutable")
                return safe
            self._storage.write_model(path, safe)
            self._storage.write_model(
                path.with_name("manifest.json"),
                ScanSnapshotManifest(
                    project_id=safe.project_id,
                    scan_id=safe.scan_id,
                    generated_at=safe.generated_at,
                    inventory_digest=safe.inventory_digest,
                    inventory_provenance_status=(
                        safe.inventory_provenance_status
                    ),
                    inventory_policy_schema_version=(
                        safe.inventory_policy_schema_version
                    ),
                    inventory_policy_digest=safe.inventory_policy_digest,
                    candidate_set_digest=safe.candidate_set_digest,
                    filesystem_safety_version=(safe.filesystem_safety_version),
                    boundary_decision_digest=(safe.boundary_decision_digest),
                    final_inventory_digest=safe.final_inventory_digest,
                    inventory_run_digest=safe.inventory_run_digest,
                    inventory_source_mode=safe.inventory_source_mode,
                    inventory_selection_summary=(
                        safe.inventory_selection_summary
                    ),
                    ua_analysis_available=safe.ua_analysis_result is not None,
                ),
            )
        return safe

    def get_snapshot(
        self,
        project_id: str,
        scan_id: str,
    ) -> ScanSnapshot | None:
        self._storage.validate_id(project_id, "project")
        self._storage.validate_id(scan_id, "scan")
        return self._storage.read_model(
            self._storage.snapshot_file(project_id, scan_id),
            ScanSnapshot,
        )

    def save_build_manifest(
        self,
        manifest: MapBuildManifest,
    ) -> MapBuildManifest:
        project_id = manifest.lineage.project_id
        build_id = manifest.lineage.build_id
        self._storage.validate_id(project_id, "project")
        self._storage.validate_id(build_id, "build")
        with self._storage.project_lock(project_id):
            path = self._storage.build_file(project_id, build_id)
            if path.exists():
                existing = self._storage.read_model(path, MapBuildManifest)
                if existing != manifest:
                    raise StateConflictError("build manifest is immutable")
                return manifest
            self._storage.write_model(path, manifest)
        return manifest

    def get_build_manifest(
        self,
        project_id: str,
        build_id: str,
    ) -> MapBuildManifest | None:
        self._storage.validate_id(project_id, "project")
        self._storage.validate_id(build_id, "build")
        return self._storage.read_model(
            self._storage.build_file(project_id, build_id),
            MapBuildManifest,
        )

    def find_build_manifest(
        self,
        build_id: str,
    ) -> MapBuildManifest | None:
        self._storage.validate_id(build_id, "build")
        return self._storage.find_model(
            "builds",
            self._storage.segment(build_id),
            MapBuildManifest,
            nested_name="manifest.json",
        )

    def list_build_manifests(
        self,
        project_id: str,
    ) -> tuple[MapBuildManifest, ...]:
        self._storage.validate_id(project_id, "project")
        directory = self._storage.project_dir(project_id) / "builds"
        manifests = tuple(
            item
            for path in sorted(directory.glob("*/manifest.json"))
            if (item := self._storage.read_model(path, MapBuildManifest))
            is not None
        )
        return tuple(
            sorted(
                manifests,
                key=lambda item: (
                    item.lineage.generated_at,
                    item.lineage.build_id,
                ),
            )
        )

    def get_latest_pointer(
        self,
        project_id: str,
    ) -> LatestBuildPointer | None:
        self._storage.validate_id(project_id, "project")
        return self._storage.read_model(
            self._storage.project_dir(project_id) / "latest.json",
            LatestBuildPointer,
        )

    def discard_unpublished_build(
        self,
        project_id: str,
        build_id: str,
    ) -> None:
        self._storage.validate_id(project_id, "project")
        self._storage.validate_id(build_id, "build")
        with self._storage.project_lock(project_id):
            current = self.get_latest_pointer(project_id)
            if current is not None and current.latest_build_id == build_id:
                raise StateConflictError("cannot discard latest build")
            build_dir = self._storage.build_file(project_id, build_id).parent
            if build_dir.is_dir():
                shutil.rmtree(build_dir)

    def get_latest_build_id(self, project_id: str) -> str | None:
        pointer = self.get_latest_pointer(project_id)
        return pointer.latest_build_id if pointer is not None else None

    def promote_latest_build(
        self,
        *,
        project_id: str,
        build_id: str,
        expected_latest_build_id: str | None,
        expected_revision: int,
    ) -> LatestBuildPointer:
        self._storage.validate_id(project_id, "project")
        self._storage.validate_id(build_id, "build")
        if self.get_build_manifest(project_id, build_id) is None:
            raise StateConflictError("cannot promote unknown build")
        with self._storage.project_lock(project_id):
            current = self.get_latest_pointer(project_id)
            current_id = current.latest_build_id if current else None
            current_revision = current.revision if current else 0
            if (
                current_id != expected_latest_build_id
                or current_revision != expected_revision
            ):
                raise StateConflictError("stale latest revision")
            pointer = LatestBuildPointer(
                project_id=project_id,
                latest_build_id=build_id,
                revision=current_revision + 1,
                updated_at=datetime.now(UTC),
            )
            self._storage.write_model(
                self._storage.project_dir(project_id) / "latest.json",
                pointer,
            )
            return pointer
