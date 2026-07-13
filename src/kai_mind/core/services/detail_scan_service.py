"""Append validated bounded detail scan results to a system map."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from kai_mind.core.models.ai_system_map_v2 import AiSystemMapV2
from kai_mind.core.models.system_map import (
    ComponentInstance,
    DetailScanResult,
    Edge,
    ExtensionComponent,
    RagSystemMap,
    ScanDepth,
    UnmappedComponent,
)
from kai_mind.core.services.canonical_map_loader import CanonicalMapLoader
from kai_mind.core.services.code_path_scan_service import (
    CodePathScanService,
)
from kai_mind.core.services.component_detail_scan_service import (
    ComponentDetailScanService,
    _slug,
)
from kai_mind.core.services.detail_scan_target_resolver import (
    DetailScanTarget,
    DetailScanTargetError,
    DetailScanTargetResolver,
)
from kai_mind.core.services.system_map_index import SystemMapIndex
from kai_mind.core.services.system_map_validation_service import (
    SystemMapValidationService,
)

DetailScanTargetType = Literal[
    "component_slot",
    "component_instance",
    "extension",
    "unmapped_component",
    "edge",
    "evidence",
]

TARGET_TYPE_ALIASES: dict[str, DetailScanTargetType] = {
    "slot": "component_slot",
    "component_slot": "component_slot",
    "component": "component_instance",
    "component_instance": "component_instance",
    "extension": "extension",
    "unmapped": "unmapped_component",
    "unmapped_component": "unmapped_component",
    "edge": "edge",
    "evidence": "evidence",
}


class DetailScanValidationError(ValueError):
    """Raised when the updated system map fails contract validation."""


class DetailScanSnapshotStaleError(ValueError):
    pass


@dataclass(frozen=True)
class DetailScanExecutionResult:
    detail_scan: DetailScanResult
    system_map: RagSystemMap


class DetailScanService:
    """Dispatch L2/L3 bounded scans and persist them through validation."""

    def __init__(
        self,
        *,
        component_detail_scan_service: (
            ComponentDetailScanService | None
        ) = None,
        code_path_scan_service: CodePathScanService | None = None,
        validation_service: SystemMapValidationService | None = None,
        canonical_map_loader: CanonicalMapLoader | None = None,
    ) -> None:
        self._component_detail_scan_service = (
            component_detail_scan_service or ComponentDetailScanService()
        )
        self._code_path_scan_service = (
            code_path_scan_service or CodePathScanService()
        )
        self._validation_service = (
            validation_service or SystemMapValidationService()
        )
        self._canonical_map_loader = (
            canonical_map_loader or CanonicalMapLoader()
        )

    def scan(
        self,
        *,
        project_root: Path,
        system_map: RagSystemMap,
        normalized_system_map: AiSystemMapV2 | None = None,
        target_type: str,
        target: str,
        scan_depth: ScanDepth = "component",
        expected_file_fingerprints: dict[str, str] | None = None,
    ) -> DetailScanExecutionResult:
        if scan_depth not in {"component", "code_path"}:
            raise ValueError("scan_depth must be component or code_path")

        normalized_target_type = self._normalize_target_type(target_type)
        normalized = (
            normalized_system_map
            or self._canonical_map_loader.load(
                system_map.model_dump(mode="json")
            ).normalized
        )
        target_ref = self._resolve_read_only_target(
            system_map,
            SystemMapIndex.from_map(normalized),
            target_type=normalized_target_type,
            target=target,
        )
        self._validate_fingerprints(
            project_root,
            target_ref.related_files,
            expected_file_fingerprints,
        )
        updated = system_map.model_copy(deep=True)
        existing_ids = {item.id for item in updated.evidence}
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
            id=self._detail_scan_id(
                target_type=normalized_target_type,
                target=target,
                scan_depth=scan_depth,
                existing_ids={scan.id for scan in updated.detail_scans},
            ),
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

        updated.evidence.extend(evidence)
        self._attach_evidence_ids(
            system_map=updated,
            target=target_ref,
            evidence_ids=[item.id for item in evidence],
        )
        updated.detail_scans.append(detail_scan)
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

    def _normalize_target_type(self, target_type: str) -> DetailScanTargetType:
        normalized = TARGET_TYPE_ALIASES.get(target_type)
        if normalized is None:
            raise DetailScanTargetError("target_type_not_supported")
        return normalized

    def _resolve_read_only_target(
        self,
        system_map: RagSystemMap,
        index: SystemMapIndex,
        *,
        target_type: DetailScanTargetType,
        target: str,
    ) -> DetailScanTarget:
        if target_type in {"component_slot", "extension"}:
            return self._resolve_compatibility_alias_target(
                system_map,
                target_type=target_type,
                target=target,
            )
        return DetailScanTargetResolver(index).resolve(target_type, target)

    def _resolve_compatibility_alias_target(
        self,
        system_map: RagSystemMap,
        *,
        target_type: DetailScanTargetType,
        target: str,
    ) -> DetailScanTarget:
        if target_type == "component_slot":
            slot = system_map.components_by_slot.get(target)
            evidence_ids = (
                [
                    evidence_id
                    for instance in slot.instances
                    for evidence_id in instance.evidence_ids
                ]
                if slot is not None
                else None
            )
        else:
            extension = self._find_compatibility_extension(system_map, target)
            evidence_ids = extension.evidence_ids if extension else None
        if evidence_ids is None:
            raise DetailScanTargetError("target_not_found")
        evidence_by_id = {item.id: item for item in system_map.evidence}
        return DetailScanTarget(
            target_type=target_type,
            target=target,
            related_files=_unique(
                evidence_by_id[evidence_id].file
                for evidence_id in evidence_ids
                if evidence_id in evidence_by_id
            ),
        )

    def _attach_evidence_ids(
        self,
        *,
        system_map: RagSystemMap,
        target: DetailScanTarget,
        evidence_ids: Sequence[str],
    ) -> None:
        if not evidence_ids:
            return

        if target.target_type == "component_slot":
            slot = system_map.components_by_slot[target.target]
            for instance in slot.instances:
                _append_missing(instance.evidence_ids, evidence_ids)
            return

        if target.target_type == "component_instance":
            component = self._find_compatibility_component_for_mutation(
                system_map,
                target.target,
            )
            if component is not None:
                _append_missing(component.evidence_ids, evidence_ids)
            return

        if target.target_type == "extension":
            extension = self._find_compatibility_extension(
                system_map,
                target.target,
            )
            if extension is not None:
                _append_missing(extension.evidence_ids, evidence_ids)
            return

        if target.target_type == "unmapped_component":
            unmapped = self._find_compatibility_unmapped_for_mutation(
                system_map,
                target.target,
            )
            if unmapped is not None:
                _append_missing(unmapped.evidence_ids, evidence_ids)
            return

        if target.target_type == "edge":
            edge = self._find_compatibility_edge_for_mutation(
                system_map,
                target.target,
            )
            if edge is not None:
                _append_missing(edge.evidence_ids, evidence_ids)

    def _detail_scan_id(
        self,
        *,
        target_type: str,
        target: str,
        scan_depth: str,
        existing_ids: set[str],
    ) -> str:
        base = f"detail-scan:{scan_depth}:{target_type}:{_slug(target)}"
        if base not in existing_ids:
            return base
        index = 2
        while f"{base}:{index}" in existing_ids:
            index += 1
        return f"{base}:{index}"

    def _find_compatibility_component_for_mutation(
        self,
        system_map: RagSystemMap,
        component_id: str,
    ) -> ComponentInstance | None:
        for slot in system_map.components_by_slot.values():
            for instance in slot.instances:
                if instance.id == component_id:
                    return instance
        return None

    def _find_compatibility_extension(
        self,
        system_map: RagSystemMap,
        extension_id: str,
    ) -> ExtensionComponent | None:
        for extension in system_map.extensions:
            if extension.id == extension_id:
                return extension
        return None

    def _find_compatibility_unmapped_for_mutation(
        self,
        system_map: RagSystemMap,
        unmapped_id: str,
    ) -> UnmappedComponent | None:
        for unmapped in system_map.unmapped_components:
            if unmapped.id == unmapped_id:
                return unmapped
        return None

    def _find_compatibility_edge_for_mutation(
        self,
        system_map: RagSystemMap,
        edge_id: str,
    ) -> Edge | None:
        for flow in system_map.flows:
            for edge in flow.edges:
                if edge.id == edge_id:
                    return edge
        return None


def _append_missing(values: list[str], candidates: Sequence[str]) -> None:
    existing = set(values)
    for candidate in candidates:
        if candidate not in existing:
            values.append(candidate)
            existing.add(candidate)


def _unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
