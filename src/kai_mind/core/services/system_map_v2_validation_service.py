"""Runtime validation for ai-system-map/v2 cross-reference invariants."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from pydantic import ValidationError

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CapabilityAssessment,
    ReferenceMapCatalog,
)
from kai_mind.core.services.path_safety_service import (
    WINDOWS_DRIVE_RE,
    WINDOWS_UNC_RE,
    is_project_relative_posix_path,
)
from kai_mind.core.services.secret_masking_service import SecretMaskingService
from kai_mind.core.services.secret_validation_service import (
    SecretValidationService,
)
from kai_mind.core.services.system_map_secret_boundary import (
    SystemMapSecretBoundary,
)


class SystemMapV2ValidationError(ValueError):
    """Raised when an ai-system-map/v2 document violates runtime invariants."""


class SystemMapV2ValidationService:
    """Validate schema-level shape and cross-reference invariants for v2."""

    def __init__(
        self,
        secret_masking_service: SecretMaskingService | None = None,
        secret_validation_service: SecretValidationService | None = None,
    ) -> None:
        self._secret_boundary = SystemMapSecretBoundary(
            secret_masking_service=secret_masking_service,
            secret_validation_service=secret_validation_service,
            on_violation=SystemMapV2ValidationError,
        )

    def validate(self, data: Mapping[str, Any]) -> AiSystemMapV2:
        self._reject_confidence(data)
        self._secret_boundary.reject_unmasked_secrets(data)
        try:
            system_map = AiSystemMapV2.model_validate(data)
        except ValidationError as exc:
            raise SystemMapV2ValidationError(str(exc)) from exc

        self._validate_unique_ids(system_map)
        self._validate_project_paths(system_map)
        self._validate_evidence_paths(system_map)
        self._validate_component_refs(system_map)
        self._validate_edge_refs(system_map)
        self._validate_endpoint_refs(system_map)
        self._validate_risk_refs(system_map)
        self._validate_unmapped_refs(system_map)
        return system_map

    def validate_assessment(
        self,
        assessment: CapabilityAssessment,
    ) -> CapabilityAssessment:
        catalog = ReferenceMapCatalog.default()
        known_nodes = {
            node.reference_node_id: node.plane_id for node in catalog.nodes
        }
        if assessment.reference_node_id not in known_nodes:
            raise SystemMapV2ValidationError(
                f"unknown reference_node_id: {assessment.reference_node_id}"
            )
        expected_plane = known_nodes[assessment.reference_node_id]
        if assessment.plane_id != expected_plane:
            raise SystemMapV2ValidationError(
                "assessment plane_id does not match reference catalog: "
                f"{assessment.plane_id} != {expected_plane}"
            )

        if assessment.status == "not_detected":
            if assessment.not_detected_coverage_gate_passed is not True:
                raise SystemMapV2ValidationError(
                    "not_detected requires not_detected_coverage_gate_passed"
                )

        if assessment.status == "detected":
            if not assessment.evidence_ids:
                raise SystemMapV2ValidationError(
                    "detected assessment requires evidence_ids"
                )
            has_direct = any(
                assessment.evidence_kinds.get(evidence_id) == "direct"
                for evidence_id in assessment.evidence_ids
            )
            if not has_direct:
                raise SystemMapV2ValidationError(
                    "detected assessment requires at least one direct evidence"
                )

        if (
            assessment.status == "conflicted"
            and not assessment.conflict_fields
        ):
            raise SystemMapV2ValidationError(
                "conflicted assessment requires field-specific conflict_fields"
            )

        return assessment

    def _reject_confidence(self, value: Any, path: str = "$") -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key == "confidence":
                    raise SystemMapV2ValidationError(
                        f"Field 'confidence' is not allowed at {child_path}"
                    )
                self._reject_confidence(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                self._reject_confidence(child, f"{path}[{index}]")

    def _validate_unique_ids(self, system_map: AiSystemMapV2) -> None:
        self._assert_unique(
            [item.component_id for item in system_map.components],
            "component_id",
        )
        self._assert_unique(
            [item.edge_id for item in system_map.edges],
            "edge_id",
        )
        self._assert_unique(
            [item.evidence_id for item in system_map.evidence],
            "evidence_id",
        )
        self._assert_unique(
            [item.endpoint_id for item in system_map.endpoints],
            "endpoint_id",
        )
        self._assert_unique(
            [item.risk_id for item in system_map.risk_hints],
            "risk_id",
        )
        self._assert_unique(
            [item.unmapped_id for item in system_map.unmapped_components],
            "unmapped_id",
        )
        self._assert_unique(
            [item.candidate_fact_id for item in system_map.candidate_facts],
            "candidate_fact_id",
        )

    def _validate_project_paths(self, system_map: AiSystemMapV2) -> None:
        root_path = system_map.project.root_path
        if root_path is None:
            return
        if self._is_absolute_filesystem_path(root_path):
            raise SystemMapV2ValidationError(
                "project.root_path must not be an absolute filesystem path"
            )

    def _validate_evidence_paths(self, system_map: AiSystemMapV2) -> None:
        for item in system_map.evidence:
            path = item.location.path
            if path is None:
                continue
            if not is_project_relative_posix_path(path):
                raise SystemMapV2ValidationError(
                    f"evidence {item.evidence_id} path must be "
                    f"project-relative POSIX: {path}"
                )

    def _validate_component_refs(self, system_map: AiSystemMapV2) -> None:
        evidence_ids = {item.evidence_id for item in system_map.evidence}
        for component in system_map.components:
            self._assert_evidence_refs(
                component.evidence_ids,
                evidence_ids,
                f"component {component.component_id}",
            )
            if component.status == "detected" and not component.evidence_ids:
                raise SystemMapV2ValidationError(
                    f"detected component requires evidence: "
                    f"{component.component_id}"
                )

    def _validate_edge_refs(self, system_map: AiSystemMapV2) -> None:
        component_ids = {item.component_id for item in system_map.components}
        evidence_ids = {item.evidence_id for item in system_map.evidence}
        for edge in system_map.edges:
            if edge.source not in component_ids:
                raise SystemMapV2ValidationError(
                    f"edge {edge.edge_id} source missing: {edge.source}"
                )
            if edge.target not in component_ids:
                raise SystemMapV2ValidationError(
                    f"edge {edge.edge_id} target missing: {edge.target}"
                )
            self._assert_evidence_refs(
                edge.evidence_ids,
                evidence_ids,
                f"edge {edge.edge_id}",
            )
            if (
                edge.status in {"observed", "detected"}
                and not edge.evidence_ids
            ):
                raise SystemMapV2ValidationError(
                    f"{edge.status} edge requires evidence: {edge.edge_id}"
                )
            if (
                edge.status == "undetermined"
                and not edge.evidence_ids
                and not edge.undetermined_reason
            ):
                raise SystemMapV2ValidationError(
                    f"undetermined edge without evidence requires "
                    f"undetermined_reason: {edge.edge_id}"
                )

    def _validate_endpoint_refs(self, system_map: AiSystemMapV2) -> None:
        component_ids = {item.component_id for item in system_map.components}
        evidence_ids = {item.evidence_id for item in system_map.evidence}
        for endpoint in system_map.endpoints:
            if (
                endpoint.component_id is not None
                and endpoint.component_id not in component_ids
            ):
                raise SystemMapV2ValidationError(
                    f"endpoint {endpoint.endpoint_id} component missing: "
                    f"{endpoint.component_id}"
                )
            self._assert_evidence_refs(
                endpoint.evidence_ids,
                evidence_ids,
                f"endpoint {endpoint.endpoint_id}",
            )

    def _validate_risk_refs(self, system_map: AiSystemMapV2) -> None:
        evidence_ids = {item.evidence_id for item in system_map.evidence}
        for risk in system_map.risk_hints:
            if risk.evidence_id not in evidence_ids:
                raise SystemMapV2ValidationError(
                    f"risk {risk.risk_id} evidence missing: {risk.evidence_id}"
                )

    def _validate_unmapped_refs(self, system_map: AiSystemMapV2) -> None:
        evidence_ids = {item.evidence_id for item in system_map.evidence}
        for item in system_map.unmapped_components:
            self._assert_evidence_refs(
                item.evidence_ids,
                evidence_ids,
                f"unmapped {item.unmapped_id}",
            )
            if item.source_file is not None and not (
                is_project_relative_posix_path(item.source_file)
            ):
                raise SystemMapV2ValidationError(
                    f"unmapped {item.unmapped_id} source_file must be "
                    f"project-relative POSIX: {item.source_file}"
                )

    @staticmethod
    def _is_absolute_filesystem_path(value: str) -> bool:
        if value in {"", ".", "<project_root>"}:
            return False
        if WINDOWS_DRIVE_RE.match(value) or WINDOWS_UNC_RE.match(value):
            return True
        if "\\" in value:
            return PureWindowsPath(value).is_absolute()
        return PurePosixPath(value).is_absolute()

    @staticmethod
    def _assert_unique(values: list[str], label: str) -> None:
        seen: set[str] = set()
        for value in values:
            if value in seen:
                raise SystemMapV2ValidationError(f"duplicate {label}: {value}")
            seen.add(value)

    @staticmethod
    def _assert_evidence_refs(
        refs: list[str],
        known: set[str],
        owner: str,
    ) -> None:
        missing = [ref for ref in refs if ref not in known]
        if missing:
            raise SystemMapV2ValidationError(
                f"{owner} references unknown evidence: {missing}"
            )
