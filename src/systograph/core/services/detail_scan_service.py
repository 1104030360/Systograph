from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.models.system_map import DetailScanResult, ScanDepth
from systograph.core.services.canonical_evidence_service import (
    canonical_evidence_from_scan,
)
from systograph.core.services.code_path_scan_service import CodePathScanService
from systograph.core.services.component_detail_scan_service import (
    ComponentDetailScanService,
    _slug,
)
from systograph.core.services.detail_scan_target_resolver import (
    DetailScanTarget,
    DetailScanTargetError,
    DetailScanTargetResolver,
)
from systograph.core.services.system_map_index import SystemMapIndex
from systograph.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationService,
)

DetailScanTargetType = Literal[
    "component_slot",
    "component_instance",
    "unmapped_component",
    "edge",
    "evidence",
]

TARGET_TYPE_ALIASES: dict[str, DetailScanTargetType] = {
    "slot": "component_slot",
    "component_slot": "component_slot",
    "component": "component_instance",
    "component_instance": "component_instance",
    "unmapped": "unmapped_component",
    "unmapped_component": "unmapped_component",
    "edge": "edge",
    "evidence": "evidence",
}


class DetailScanValidationError(ValueError):
    pass


class DetailScanSnapshotStaleError(ValueError):
    pass


@dataclass(frozen=True)
class DetailScanExecutionResult:
    detail_scan: DetailScanResult
    system_map: AiSystemMapV2


class DetailScanService:
    def __init__(
        self,
        *,
        component_detail_scan_service: (
            ComponentDetailScanService | None
        ) = None,
        code_path_scan_service: CodePathScanService | None = None,
        validation_service: SystemMapV2ValidationService | None = None,
    ) -> None:
        self._component_detail_scan_service = (
            component_detail_scan_service or ComponentDetailScanService()
        )
        self._code_path_scan_service = (
            code_path_scan_service or CodePathScanService()
        )
        self._validation_service = (
            validation_service or SystemMapV2ValidationService()
        )

    def scan(
        self,
        *,
        project_root: Path,
        system_map: AiSystemMapV2,
        target_type: str,
        target: str,
        scan_depth: ScanDepth = "component",
        expected_file_fingerprints: dict[str, str] | None = None,
    ) -> DetailScanExecutionResult:
        if scan_depth not in {"component", "code_path"}:
            raise ValueError("scan_depth must be component or code_path")

        normalized_target_type = self._normalize_target_type(target_type)
        index = SystemMapIndex.from_map(system_map)
        target_ref = self._resolve_target(
            index,
            system_map,
            target_type=normalized_target_type,
            target=target,
        )
        self._validate_fingerprints(
            project_root,
            target_ref.related_files,
            expected_file_fingerprints,
        )
        existing_ids = {item.evidence_id for item in system_map.evidence}
        target_slug = _slug(target)
        component_extraction = self._component_detail_scan_service.scan(
            project_root=project_root,
            relative_files=target_ref.related_files,
            target_slug=target_slug,
            existing_evidence_ids=existing_ids,
        )
        evidence = list(component_extraction.evidence)
        findings = list(component_extraction.findings)
        warnings = list(component_extraction.warnings)
        code_path = []
        context_limits: dict[str, object] = dict(
            component_extraction.context_limits
        )
        context_limits["component"] = component_extraction.context_limits

        if scan_depth == "code_path":
            code_path_extraction = self._code_path_scan_service.scan(
                project_root=project_root,
                relative_files=target_ref.related_files,
                target_slug=target_slug,
                existing_evidence_ids=existing_ids
                | {item.id for item in evidence},
            )
            evidence.extend(code_path_extraction.evidence)
            findings.extend(code_path_extraction.findings)
            code_path.extend(code_path_extraction.code_path)
            warnings.extend(code_path_extraction.warnings)
            context_limits["code_path"] = code_path_extraction.context_limits

        detail_scan = DetailScanResult(
            id=f"detail-scan:{scan_depth}:{normalized_target_type}:{target_slug}",
            target_type=normalized_target_type,
            target=target,
            scan_depth=scan_depth,
            status="completed",
            findings=findings,
            code_path=code_path,
            warnings=_unique(warnings),
            best_effort=True,
            context_limits=context_limits,
        )
        evidence_ids = [item.id for item in evidence]
        updated = self._attach_evidence_ids(
            system_map,
            target_ref,
            evidence_ids,
        ).model_copy(
            update={
                "evidence": [
                    *system_map.evidence,
                    *(
                        canonical_evidence_from_scan(
                            item,
                            no_snippets=False,
                        )
                        for item in evidence
                    ),
                ]
            }
        )
        try:
            validated = self._validation_service.validate(
                updated.model_dump(mode="json")
            )
        except ValueError as exc:
            raise DetailScanValidationError(str(exc)) from exc
        return DetailScanExecutionResult(
            detail_scan=detail_scan,
            system_map=validated,
        )

    @staticmethod
    def _validate_fingerprints(
        project_root: Path,
        relative_files: Sequence[str],
        expected: dict[str, str] | None,
    ) -> None:
        if expected is None:
            return
        for relative_file in relative_files:
            expected_digest = expected.get(relative_file)
            path = project_root / relative_file
            try:
                actual_digest = (
                    "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
                )
            except OSError as exc:
                raise DetailScanSnapshotStaleError(
                    "scan_snapshot_stale"
                ) from exc
            if expected_digest is None or actual_digest != expected_digest:
                raise DetailScanSnapshotStaleError("scan_snapshot_stale")

    @staticmethod
    def _normalize_target_type(target_type: str) -> DetailScanTargetType:
        normalized = TARGET_TYPE_ALIASES.get(target_type)
        if normalized is None:
            raise DetailScanTargetError("target_type_not_supported")
        return normalized

    @staticmethod
    def _resolve_target(
        index: SystemMapIndex,
        system_map: AiSystemMapV2,
        *,
        target_type: DetailScanTargetType,
        target: str,
    ) -> DetailScanTarget:
        if target_type != "component_slot":
            return DetailScanTargetResolver(index).resolve(
                target_type,
                target,
            )
        evidence_ids = [
            evidence_id
            for component in system_map.components
            if component.metadata.get("legacy_slot") == target
            for evidence_id in component.evidence_ids
        ]
        if not evidence_ids:
            raise DetailScanTargetError("target_not_found")
        return DetailScanTarget(
            target_type=target_type,
            target=target,
            related_files=_unique(
                location.path
                for location in index.related_locations_for_evidence_ids(
                    evidence_ids
                )
            ),
        )

    @staticmethod
    def _attach_evidence_ids(
        system_map: AiSystemMapV2,
        target: DetailScanTarget,
        evidence_ids: Sequence[str],
    ) -> AiSystemMapV2:
        if not evidence_ids:
            return system_map
        if target.target_type in {"component_slot", "component_instance"}:
            components = [
                item.model_copy(
                    update={
                        "evidence_ids": _merged(
                            item.evidence_ids,
                            evidence_ids,
                        )
                    }
                )
                if (
                    item.component_id == target.target
                    or item.metadata.get("legacy_slot") == target.target
                )
                else item
                for item in system_map.components
            ]
            return system_map.model_copy(update={"components": components})
        if target.target_type == "unmapped_component":
            unmapped = [
                item.model_copy(
                    update={
                        "evidence_ids": _merged(
                            item.evidence_ids,
                            evidence_ids,
                        )
                    }
                )
                if item.unmapped_id == target.target
                else item
                for item in system_map.unmapped_components
            ]
            return system_map.model_copy(
                update={"unmapped_components": unmapped}
            )
        if target.target_type == "edge":
            edges = [
                item.model_copy(
                    update={
                        "evidence_ids": _merged(
                            item.evidence_ids,
                            evidence_ids,
                        )
                    }
                )
                if item.edge_id == target.target
                else item
                for item in system_map.edges
            ]
            return system_map.model_copy(update={"edges": edges})
        return system_map


def _merged(values: Sequence[str], candidates: Sequence[str]) -> list[str]:
    return list(dict.fromkeys([*values, *candidates]))


def _unique(values: Iterable[str | None]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value is not None))
