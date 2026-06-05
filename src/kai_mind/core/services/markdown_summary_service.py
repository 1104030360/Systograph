"""Render human-readable Markdown from a validated system map."""

from __future__ import annotations

from collections.abc import Iterable

from kai_mind.core.models.system_map import (
    ComponentSlot,
    Endpoint,
    Flow,
    RagSystemMap,
    RiskHint,
)
from kai_mind.core.services.secret_masking_service import SecretMaskingService


class MarkdownSummaryService:
    """Render an ai-system-map/v1 report without file I/O."""

    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()

    def render(self, system_map: RagSystemMap) -> str:
        """Return a deterministic Markdown report for a validated map."""

        sections = [
            "# KAI-Mind System Map",
            "",
            *self._render_system_overview(system_map),
            *self._render_slot_coverage(system_map),
            *self._render_detected_and_missing_slots(system_map),
            *self._render_flow_section(
                "Indexing Flow",
                self._find_flow(system_map.flows, "indexing"),
            ),
            *self._render_flow_section(
                "Query Answer Flow",
                self._find_flow(system_map.flows, "query_answer"),
            ),
            *self._render_endpoint_section(
                "External Endpoints",
                [
                    endpoint
                    for endpoint in system_map.endpoints
                    if endpoint.endpoint_type == "external"
                ],
            ),
            *self._render_network_exposure(system_map),
            *self._render_recommended_next_checks(system_map),
        ]
        return "\n".join(sections).rstrip() + "\n"

    def _render_system_overview(self, system_map: RagSystemMap) -> list[str]:
        summary = system_map.scan_summary
        lines = [
            "## System Overview",
            "",
            f"- Project: {self._safe(system_map.project.name)}",
            f"- Schema version: {system_map.schema_version}",
            f"- System type: {system_map.system_type}",
            "- Reference architecture: "
            f"{system_map.reference_architecture.id}",
        ]
        if summary is not None:
            lines.extend(
                [
                    f"- Scan status: {self._safe(summary.status)}",
                    f"- Files scanned: {summary.files_scanned}",
                    f"- Files skipped: {summary.files_skipped}",
                    "- Secret masking applied: "
                    f"{str(summary.secret_masking_applied).lower()}",
                ]
            )
        lines.append("")
        return lines

    def _render_slot_coverage(self, system_map: RagSystemMap) -> list[str]:
        lines = [
            "## Slot Coverage",
            "",
            "| Slot | Required | Status | Instances |",
            "|---|---|---|---|",
        ]
        for slot in self._ordered_slots(system_map):
            lines.append(
                "| "
                f"{self._safe(slot.slot)} | "
                f"{'required' if slot.required_for_rag else 'optional'} | "
                f"{slot.status} | "
                f"{self._instance_names(slot)} |"
            )
        lines.append("")
        return lines

    def _render_detected_and_missing_slots(
        self, system_map: RagSystemMap
    ) -> list[str]:
        lines = [
            "## Detected And Missing Slots",
            "",
            "### Detected Slots",
            "",
        ]
        detected = [
            slot
            for slot in self._ordered_slots(system_map)
            if slot.status == "detected"
        ]
        lines.extend(self._render_slot_bullets(detected))
        lines.extend(["", "### Missing Or Not Configured Slots", ""])
        missing = [
            slot
            for slot in self._ordered_slots(system_map)
            if slot.status != "detected"
        ]
        lines.extend(self._render_slot_bullets(missing))
        lines.append("")
        return lines

    def _render_slot_bullets(
        self, slots: Iterable[ComponentSlot]
    ) -> list[str]:
        rendered = [
            f"- {self._safe(slot.slot)}: {slot.status}"
            f" ({self._instance_names(slot)})"
            for slot in slots
        ]
        if rendered:
            return rendered
        return ["- None"]

    def _render_flow_section(
        self,
        title: str,
        flow: Flow | None,
    ) -> list[str]:
        lines = [f"## {title}", ""]
        if flow is None or not flow.edges:
            lines.extend(["- Not detected", ""])
            return lines

        for edge in flow.edges:
            lines.append(
                "- "
                f"{self._safe(edge.from_slot)} -> "
                f"{self._safe(edge.to_slot)}: "
                f"{self._safe(edge.relationship)}"
            )
        lines.append("")
        return lines

    def _render_endpoint_section(
        self,
        title: str,
        endpoints: list[Endpoint],
    ) -> list[str]:
        lines = [
            f"## {title}",
            "",
            "| Type | Method | Value | Slot |",
            "|---|---|---|---|",
        ]
        if not endpoints:
            lines.append("| - | - | Not detected | - |")
        for endpoint in endpoints:
            lines.append(
                "| "
                f"{endpoint.endpoint_type} | "
                f"{self._safe(endpoint.method or '-')} | "
                f"{self._safe(endpoint.value)} | "
                f"{self._safe(endpoint.slot or '-')} |"
            )
        lines.append("")
        return lines

    def _render_network_exposure(self, system_map: RagSystemMap) -> list[str]:
        risks = [
            risk
            for risk in system_map.risk_hints
            if risk.type in {"network_exposure", "external_provider"}
        ]
        lines = [
            "## Network Exposure",
            "",
            "| Severity | Type | Target | Rationale | Uncertainty |",
            "|---|---|---|---|---|",
        ]
        if not risks:
            lines.append("| - | - | - | Not detected | - |")
        for risk in risks:
            lines.append(self._risk_row(risk))
        lines.append("")
        return lines

    def _render_recommended_next_checks(
        self, system_map: RagSystemMap
    ) -> list[str]:
        lines = ["## Recommended Next Checks", ""]
        if not system_map.recommended_next_checks:
            lines.extend(["- [ ] No recommended next checks detected.", ""])
            return lines

        for check in system_map.recommended_next_checks:
            lines.append(
                "- [ ] "
                f"{self._safe(check.action)}: {self._safe(check.reason)} "
                f"(target: {self._safe(check.target)})"
            )
        lines.append("")
        return lines

    def _ordered_slots(self, system_map: RagSystemMap) -> list[ComponentSlot]:
        ordered = []
        for slot_name in system_map.reference_architecture.slots:
            slot = system_map.components_by_slot.get(slot_name)
            if slot is not None:
                ordered.append(slot)
        extra_names = sorted(
            set(system_map.components_by_slot)
            - set(system_map.reference_architecture.slots)
        )
        for slot_name in extra_names:
            ordered.append(system_map.components_by_slot[slot_name])
        return ordered

    def _find_flow(
        self,
        flows: list[Flow],
        flow_type: str,
    ) -> Flow | None:
        for flow in flows:
            if flow.flow_type == flow_type or flow.id.endswith(flow_type):
                return flow
        return None

    def _instance_names(self, slot: ComponentSlot) -> str:
        names = [self._safe(instance.name) for instance in slot.instances]
        if not names:
            return "-"
        return ", ".join(names)

    def _risk_row(self, risk: RiskHint) -> str:
        return (
            "| "
            f"{self._safe(risk.severity_hint or '-')} | "
            f"{self._safe(risk.type)} | "
            f"{self._safe(risk.target)} | "
            f"{self._safe(risk.rationale)} | "
            f"{self._safe(risk.uncertainty or '-')} |"
        )

    def _safe(self, value: str) -> str:
        return self._masking_service.mask_text(value).replace("\n", " ")
