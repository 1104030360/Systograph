from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from kai_mind.core.models.analysis_history import ScanSnapshot
from kai_mind.core.models.apply_confirmations import ApplyConfirmationsResult
from kai_mind.core.models.map_build import MapBuildRequest, MapBuildResult
from kai_mind.core.models.mapping import ManualMapping, ManualMappingDecision
from kai_mind.core.models.scan import OutputRun
from kai_mind.core.services.apply_confirmations_contracts import (
    ApplyBuildError,
    ApplyRepository,
    ApplyValidationError,
    BaseBuildNotLatestError,
    BuildIdFactory,
    BuildNotFoundError,
    MappingNotFoundError,
)
from kai_mind.core.services.build_commit_service import (
    BuildCommitError,
    BuildCommitService,
)
from kai_mind.core.services.build_manifest_service import BuildManifestService
from kai_mind.core.services.map_build_service import MapBuildService

__all__ = [
    "ApplyBuildError",
    "ApplyConfirmationsService",
    "ApplyValidationError",
    "BaseBuildNotLatestError",
    "BuildNotFoundError",
    "MappingNotFoundError",
]


class ApplyConfirmationsService:
    def __init__(
        self,
        *,
        repository: ApplyRepository,
        map_build_service: MapBuildService,
        manifest_service: BuildManifestService,
        build_commit_service: BuildCommitService | None = None,
        build_id_factory: BuildIdFactory | None = None,
    ) -> None:
        self._repository = repository
        self._map_build_service = map_build_service
        self._manifest_service = manifest_service
        self._build_commit = build_commit_service or BuildCommitService(
            repository=repository,
            manifest_service=manifest_service,
        )
        self._build_id_factory = build_id_factory or (
            lambda: f"build:{uuid4()}"
        )

    def apply(
        self,
        *,
        base_build_id: str,
        mapping_ids: tuple[str, ...],
    ) -> ApplyConfirmationsResult:
        self._validate_ids(mapping_ids)
        base = self._repository.find_build_manifest(base_build_id)
        if base is None:
            raise BuildNotFoundError(base_build_id)
        project_id = base.lineage.project_id
        snapshot = self._repository.get_snapshot(
            project_id,
            base.lineage.scan_id,
        )
        if snapshot is None:
            raise ApplyValidationError("source scan snapshot is missing")
        mappings = self._resolve_mappings(
            project_id=project_id,
            mapping_ids=mapping_ids,
            snapshot=snapshot,
        )
        request_digest = self._request_digest(base_build_id, mappings)
        existing = self._idempotent_result(
            project_id,
            base_build_id=base_build_id,
            request_digest=request_digest,
        )
        if existing is not None:
            return existing
        latest = self._repository.get_latest_pointer(project_id)
        if latest is None or latest.latest_build_id != base_build_id:
            raise BaseBuildNotLatestError("base_build_not_latest")
        project = self._repository.get_project(project_id)
        if project is None:
            raise ApplyValidationError("project state is missing")

        build_id = self._build_id_factory()
        output_root = Path(base.output_dir).parent
        output_dir = output_root / build_id.replace(":", "_")

        def build(output_run: OutputRun) -> MapBuildResult:
            return self._map_build_service.build_from_snapshot(
                snapshot,
                request=MapBuildRequest(
                    project_path=Path(project.canonical_path),
                    output=output_root,
                    system_map_schema_version=base.requested_schema_version,
                ),
                output_run=output_run,
                build_id=build_id,
                based_on_build_id=base_build_id,
                build_reason="apply_confirmations",
                mapping_ids=tuple(sorted(mapping_ids)),
            )

        try:
            result = self._build_commit.commit(
                project_id=project_id,
                build_id=build_id,
                final_output_dir=output_dir,
                expected_latest_build_id=base_build_id,
                expected_revision=latest.revision,
                build=build,
                apply_request_digest=request_digest,
            )
            if result.status != "ok" or result.viewer_load_result is None:
                raise ApplyBuildError("apply build did not complete")
        except BuildCommitError as exc:
            if exc.code != "stale_latest_revision":
                raise ApplyBuildError(exc.code) from exc
            winner = self._idempotent_result(
                project_id,
                base_build_id=base_build_id,
                request_digest=request_digest,
            )
            if winner is not None:
                return winner
            raise BaseBuildNotLatestError("base_build_not_latest") from exc
        return self._result(result)

    @staticmethod
    def _validate_ids(mapping_ids: tuple[str, ...]) -> None:
        if not mapping_ids:
            raise ApplyValidationError("mapping_ids must not be empty")
        if len(mapping_ids) != len(set(mapping_ids)):
            raise ApplyValidationError("mapping_ids must be unique")

    def _resolve_mappings(
        self,
        *,
        project_id: str,
        mapping_ids: tuple[str, ...],
        snapshot: ScanSnapshot,
    ) -> tuple[ManualMapping, ...]:
        evidence_ids = {item.id for item in snapshot.scan_result.evidence}
        mappings: list[ManualMapping] = []
        for mapping_id in sorted(mapping_ids):
            mapping = self._repository.get(mapping_id)
            if mapping is None:
                raise MappingNotFoundError(mapping_id)
            if mapping.project_id != project_id:
                raise ApplyValidationError(
                    "mapping belongs to another project"
                )
            if mapping.decision != ManualMappingDecision.CONFIRMED:
                raise ApplyValidationError("mapping must be confirmed")
            if not set(mapping.evidence_ids).issubset(evidence_ids):
                raise ApplyValidationError(
                    "mapping evidence is not present in source snapshot"
                )
            mappings.append(mapping)
        return tuple(mappings)

    def _idempotent_result(
        self,
        project_id: str,
        *,
        base_build_id: str,
        request_digest: str,
    ) -> ApplyConfirmationsResult | None:
        latest = self._repository.get_latest_pointer(project_id)
        if latest is None:
            return None
        for manifest in self._repository.list_build_manifests(project_id):
            if (
                manifest.lineage.based_on_build_id == base_build_id
                and manifest.apply_request_digest == request_digest
                and manifest.lineage.build_id == latest.latest_build_id
            ):
                return self._result(self._manifest_service.load(manifest))
        return None

    @staticmethod
    def _request_digest(
        base_build_id: str,
        mappings: tuple[ManualMapping, ...],
    ) -> str:
        payload = {
            "base_build_id": base_build_id,
            "mappings": [
                [item.mapping_id, item.mapping_digest] for item in mappings
            ],
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return "sha256:" + hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _result(result: MapBuildResult) -> ApplyConfirmationsResult:
        lineage = result.lineage
        viewer = result.viewer_load_result
        if (
            lineage is None
            or lineage.based_on_build_id is None
            or viewer is None
        ):
            raise ApplyBuildError("persisted apply result is incomplete")
        return ApplyConfirmationsResult(
            project_id=lineage.project_id,
            scan_id=lineage.scan_id,
            build_id=lineage.build_id,
            based_on_build_id=lineage.based_on_build_id,
            applied_mapping_ids=lineage.applied_mapping_ids,
            build_result=result,
            viewer_load_result=viewer,
        )
