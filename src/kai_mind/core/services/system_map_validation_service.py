"""Runtime validation for ai-system-map/v1 cross-reference invariants."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from pydantic import ValidationError

from kai_mind.core.models.system_map import RagSystemMap

WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")


class SystemMapValidationError(ValueError):
    """Raised when an ai-system-map/v1 document violates runtime invariants."""


class SystemMapValidationService:
    """Validate schema-level shape and cross-reference invariants."""

    def validate(self, data: Mapping[str, Any]) -> RagSystemMap:
        self._reject_confidence(data)

        try:
            system_map = RagSystemMap.model_validate(data)
        except ValidationError as exc:
            raise SystemMapValidationError(str(exc)) from exc

        self._validate_evidence_paths(system_map)
        self._validate_components(system_map)
        self._validate_endpoints(system_map)
        self._validate_flows(system_map)
        self._validate_extensions(system_map)
        self._validate_unmapped_components(system_map)
        self._validate_risk_hints(system_map)
        self._validate_detail_scans(system_map)
        self._validate_query_trace_events(system_map)
        return system_map

    def _reject_confidence(self, value: Any, path: str = "$") -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key == "confidence":
                    raise SystemMapValidationError(
                        f"Field 'confidence' is not allowed at {child_path}"
                    )
                self._reject_confidence(child, child_path)
            return

        if isinstance(value, list):
            for index, child in enumerate(value):
                self._reject_confidence(child, f"{path}[{index}]")

    def _validate_evidence_paths(self, system_map: RagSystemMap) -> None:
        for evidence in system_map.evidence:
            if evidence.file and not self._is_project_relative_posix_path(
                evidence.file
            ):
                raise SystemMapValidationError(
                    "Evidence.file must be a project-relative POSIX path: "
                    f"{evidence.id}"
                )

    def _validate_components(self, system_map: RagSystemMap) -> None:
        evidence_ids = self._evidence_ids(system_map)
        slots = set(system_map.components_by_slot)

        for slot_key, slot in system_map.components_by_slot.items():
            if slot.slot != slot_key:
                raise SystemMapValidationError(
                    f"Component slot key '{slot_key}' must match "
                    f"slot '{slot.slot}'"
                )

            if slot.status == "detected" and not slot.instances:
                raise SystemMapValidationError(
                    f"Detected slot '{slot.slot}' must include "
                    "component evidence"
                )

            for instance in slot.instances:
                if instance.slot != slot.slot:
                    raise SystemMapValidationError(
                        f"Component instance '{instance.id}' references "
                        "wrong slot"
                    )
                if instance.slot not in slots:
                    raise SystemMapValidationError(
                        f"Component instance '{instance.id}' references "
                        "unknown slot"
                    )
                if slot.status == "detected" and not instance.evidence_ids:
                    raise SystemMapValidationError(
                        f"Detected component '{instance.id}' must "
                        "include evidence"
                    )
                self._validate_evidence_ids(
                    instance.evidence_ids,
                    evidence_ids,
                    f"Component '{instance.id}'",
                )

    def _validate_endpoints(self, system_map: RagSystemMap) -> None:
        evidence_ids = self._evidence_ids(system_map)
        component_ids = self._component_ids(system_map)
        slots = set(system_map.components_by_slot)

        for endpoint in system_map.endpoints:
            if endpoint.evidence_id not in evidence_ids:
                raise SystemMapValidationError(
                    f"Endpoint '{endpoint.id}' references missing evidence"
                )
            if endpoint.slot and endpoint.slot not in slots:
                raise SystemMapValidationError(
                    f"Endpoint '{endpoint.id}' references unknown slot"
                )
            if (
                endpoint.component_instance_id
                and endpoint.component_instance_id not in component_ids
            ):
                raise SystemMapValidationError(
                    f"Endpoint '{endpoint.id}' references missing component"
                )

    def _validate_flows(self, system_map: RagSystemMap) -> None:
        evidence_ids = self._evidence_ids(system_map)
        component_ids = self._component_ids(system_map)
        slots = set(system_map.components_by_slot)

        for flow in system_map.flows:
            for edge in flow.edges:
                if edge.flow_id != flow.id:
                    raise SystemMapValidationError(
                        f"Edge '{edge.id}' references wrong flow"
                    )
                if edge.from_slot not in slots:
                    raise SystemMapValidationError(
                        f"Edge '{edge.id}' references unknown slot"
                    )
                if edge.to_slot not in slots:
                    raise SystemMapValidationError(
                        f"Edge '{edge.id}' references unknown slot"
                    )
                if (
                    edge.from_component_id
                    and edge.from_component_id not in component_ids
                ):
                    raise SystemMapValidationError(
                        f"Edge '{edge.id}' references missing component"
                    )
                if (
                    edge.to_component_id
                    and edge.to_component_id not in component_ids
                ):
                    raise SystemMapValidationError(
                        f"Edge '{edge.id}' references missing component"
                    )
                self._validate_evidence_ids(
                    edge.evidence_ids,
                    evidence_ids,
                    f"Edge '{edge.id}'",
                )

    def _validate_risk_hints(self, system_map: RagSystemMap) -> None:
        evidence_ids = self._evidence_ids(system_map)
        target_ids_by_type = {
            "component_instance": self._component_ids(system_map),
            "endpoint": {endpoint.id for endpoint in system_map.endpoints},
            "component_slot": set(system_map.components_by_slot),
            "evidence": evidence_ids,
            "file": {
                evidence.file
                for evidence in system_map.evidence
                if evidence.file is not None
            },
        }

        for risk_hint in system_map.risk_hints:
            if risk_hint.evidence_id not in evidence_ids:
                raise SystemMapValidationError(
                    f"RiskHint '{risk_hint.id}' references missing evidence"
                )
            valid_targets = target_ids_by_type[risk_hint.target_type]
            if risk_hint.target not in valid_targets:
                raise SystemMapValidationError(
                    f"RiskHint '{risk_hint.id}' references missing "
                    f"{risk_hint.target_type} target"
                )

    def _validate_extensions(self, system_map: RagSystemMap) -> None:
        evidence_ids = self._evidence_ids(system_map)

        for extension in system_map.extensions:
            if not extension.evidence_ids and not extension.confirmed_by_user:
                raise SystemMapValidationError(
                    f"ExtensionComponent '{extension.id}' must include "
                    "evidence or user confirmation"
                )
            self._validate_evidence_ids(
                extension.evidence_ids,
                evidence_ids,
                f"ExtensionComponent '{extension.id}'",
            )

    def _validate_unmapped_components(self, system_map: RagSystemMap) -> None:
        evidence_ids = self._evidence_ids(system_map)

        for component in system_map.unmapped_components:
            if component.status != "needs_confirmation":
                raise SystemMapValidationError(
                    f"UnmappedComponent '{component.id}' must have "
                    "needs_confirmation status"
                )
            if not component.evidence_ids:
                raise SystemMapValidationError(
                    f"UnmappedComponent '{component.id}' must include evidence"
                )
            self._validate_evidence_ids(
                component.evidence_ids,
                evidence_ids,
                f"UnmappedComponent '{component.id}'",
            )

    def _validate_detail_scans(self, system_map: RagSystemMap) -> None:
        evidence_ids = self._evidence_ids(system_map)
        slots = set(system_map.components_by_slot)
        component_ids = self._component_ids(system_map)
        unmapped_ids = {
            component.id for component in system_map.unmapped_components
        }
        extension_ids = {extension.id for extension in system_map.extensions}
        edge_ids = {
            edge.id for flow in system_map.flows for edge in flow.edges
        }
        evidence_ids = self._evidence_ids(system_map)

        valid_targets = (
            slots
            | component_ids
            | unmapped_ids
            | extension_ids
            | edge_ids
            | evidence_ids
        )
        for detail_scan in system_map.detail_scans:
            if detail_scan.target not in valid_targets:
                raise SystemMapValidationError(
                    f"Detail scan '{detail_scan.id}' references missing target"
                )
            for finding in detail_scan.findings:
                self._validate_evidence_ids(
                    finding.evidence_ids,
                    evidence_ids,
                    f"Detail scan '{detail_scan.id}'",
                )

    def _validate_query_trace_events(self, system_map: RagSystemMap) -> None:
        slots = set(system_map.components_by_slot)
        edge_ids = {
            edge.id for flow in system_map.flows for edge in flow.edges
        }
        component_ids = self._component_ids(system_map)

        for event in system_map.query_trace_events:
            if event.slot and event.slot not in slots:
                raise SystemMapValidationError(
                    f"QueryTraceEvent '{event.id}' references unknown slot"
                )
            if event.edge_id and event.edge_id not in edge_ids:
                raise SystemMapValidationError(
                    f"QueryTraceEvent '{event.id}' references missing edge"
                )
            if event.component_id and event.component_id not in component_ids:
                raise SystemMapValidationError(
                    f"QueryTraceEvent '{event.id}' references "
                    "missing component"
                )

    def _validate_evidence_ids(
        self, candidate_ids: list[str], evidence_ids: set[str], owner: str
    ) -> None:
        for evidence_id in candidate_ids:
            if evidence_id not in evidence_ids:
                raise SystemMapValidationError(
                    f"{owner} references missing evidence '{evidence_id}'"
                )

    def _evidence_ids(self, system_map: RagSystemMap) -> set[str]:
        return {evidence.id for evidence in system_map.evidence}

    def _component_ids(self, system_map: RagSystemMap) -> set[str]:
        return {
            instance.id
            for slot in system_map.components_by_slot.values()
            for instance in slot.instances
        }

    def _is_project_relative_posix_path(self, value: str) -> bool:
        path = PurePosixPath(value)
        return (
            "\\" not in value
            and not path.is_absolute()
            and ".." not in path.parts
            and not WINDOWS_ABSOLUTE_PATH_RE.match(value)
        )
