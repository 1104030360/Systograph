from __future__ import annotations

from systograph.core.models.viewer import (
    GraphEndpointModel,
    GraphViewModel,
)
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)

_NETWORK_EXPOSURE_TYPES = frozenset({"network_exposure", "external_provider"})


class GraphMarkdownRenderer:
    def __init__(
        self,
        *,
        masking_service: SecretMaskingService | None = None,
    ) -> None:
        self._masking_service = masking_service or SecretMaskingService()

    def render(self, graph: GraphViewModel) -> str:
        lines = [
            "# Systograph System Map",
            "",
            f"- Graph schema: `{graph.schema_version or 'unknown'}`",
            f"- Source schema: `{graph.source_schema_version or 'unknown'}`",
            f"- Scan: `{graph.scan_id or 'unscoped'}`",
            f"- Build: `{graph.build_id or 'unscoped'}`",
            f"- Environment: `{graph.environment_id or 'unscoped'}`",
            f"- Artifact set: `{graph.artifact_set_version or 'unscoped'}`",
            f"- Reference map: `{graph.reference_map_version or 'unknown'}`",
        ]
        completeness = graph.mapping_completeness
        if completeness is None:
            lines.append("- Mapping Completeness: unavailable")
        else:
            lines.extend(
                (
                    "- Mapping Completeness: "
                    f"{completeness.numerator}/{completeness.denominator} "
                    f"({completeness.value:.1%})",
                    "- Mapping status counts: "
                    + ", ".join(
                        f"{key}={value}"
                        for key, value in (
                            completeness.status_counts.model_dump()
                        ).items()
                    ),
                )
            )
        lines.extend(
            (
                "",
                "## Slot Coverage",
                "",
                "| Slot | Status | Activation | Graph ID |",
                "|---|---|---|---|",
            )
        )
        lines.extend(
            "| "
            + " | ".join(
                (
                    _cell(node.slot),
                    _cell(node.status),
                    _cell(node.activation),
                    _cell(node.id),
                )
            )
            + " |"
            for node in graph.nodes
            if node.slot is not None
        )
        lines.extend(
            (
                "",
                "## Nodes",
                "",
                "| Graph ID | Kind | Plane | Status | Activation | Label |",
                "|---|---|---|---|---|---|",
            )
        )
        lines.extend(
            "| "
            + " | ".join(
                (
                    _cell(node.id),
                    _cell(node.semantic_kind),
                    _cell(node.plane_id),
                    _cell(node.status),
                    _cell(node.activation),
                    _cell(node.label),
                )
            )
            + " |"
            for node in graph.nodes
        )
        lines.extend(
            (
                "",
                "## Topology Edges",
                "",
                "| Graph ID | From | To | Relationship |",
                "|---|---|---|---|",
            )
        )
        lines.extend(
            "| "
            + " | ".join(
                (
                    _cell(edge.id),
                    _cell(edge.from_id),
                    _cell(edge.to),
                    _cell(edge.relationship),
                )
            )
            + " |"
            for edge in graph.edges
        )
        lines.extend(
            (
                "",
                "## Semantic Relationships",
                "",
                "These relationships are static mapping metadata, "
                "not runtime traversal.",
                "",
                "| ID | Kind | Source | Target |",
                "|---|---|---|---|",
            )
        )
        lines.extend(
            "| "
            + " | ".join(
                (
                    _cell(relation.id),
                    _cell(relation.kind),
                    _cell(relation.source_node_id),
                    _cell(relation.target_node_id),
                )
            )
            + " |"
            for relation in graph.relationships
        )
        lines.extend(
            self._render_endpoint_section(
                "Local Endpoints",
                [
                    endpoint
                    for endpoint in graph.endpoints
                    if endpoint.endpoint_type == "local"
                ],
            )
        )
        lines.extend(
            self._render_endpoint_section(
                "External Endpoints",
                [
                    endpoint
                    for endpoint in graph.endpoints
                    if endpoint.endpoint_type == "external"
                ],
            )
        )
        lines.extend(self._render_network_exposure(graph))
        lines.extend(self._render_recommended_next_checks(graph))
        return "\n".join(lines).rstrip() + "\n"

    def _render_endpoint_section(
        self,
        title: str,
        endpoints: list[GraphEndpointModel],
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

    def _render_network_exposure(self, graph: GraphViewModel) -> list[str]:
        risks = [
            risk
            for risk in graph.details.risk_hints_by_id.values()
            if str(risk.get("type", "")) in _NETWORK_EXPOSURE_TYPES
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
            severity = risk.get("severity_hint") or risk.get("severity") or "-"
            lines.append(
                "| "
                f"{self._safe(str(severity))} | "
                f"{self._safe(str(risk.get('type', '-')))} | "
                f"{self._safe(str(risk.get('target', '-')))} | "
                f"{self._safe(str(risk.get('rationale', '-')))} | "
                f"{self._safe(str(risk.get('uncertainty') or '-'))} |"
            )
        lines.append("")
        return lines

    def _render_recommended_next_checks(
        self,
        graph: GraphViewModel,
    ) -> list[str]:
        lines = ["## Recommended Next Checks", ""]
        if graph.recommended_next_checks:
            for check in graph.recommended_next_checks:
                lines.append(
                    "- [ ] "
                    f"{self._safe(check.action)}: "
                    f"{self._safe(check.reason)} "
                    f"(target: {self._safe(check.target)})"
                )
            lines.append("")
            return lines

        profile_checks = [
            (node.id, check)
            for node in graph.nodes
            for check in node.recommended_next_checks
        ]
        if profile_checks:
            lines.extend(
                f"- [ ] `{_cell(node_id)}`: {_cell(check)}"
                for node_id, check in profile_checks
            )
            lines.append("")
            return lines

        lines.extend(["- No backend-provided next checks.", ""])
        return lines

    def _safe(self, value: str) -> str:
        return self._masking_service.mask_text(value).replace("\n", " ")


def _cell(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")
