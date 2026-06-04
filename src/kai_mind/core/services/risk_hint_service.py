"""Derive evidence-backed risk hints from endpoints and scan results."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final

from kai_mind.core.models.scan import ParseIssue, ScanFact
from kai_mind.core.models.system_map import (
    ComponentInstance,
    Endpoint,
    Evidence,
    RiskHint,
)
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)

PUBLISHED_PORT_RULE_ID: Final = "docker_published_port_detected"
SECRET_MARKERS: Final = {
    "api_key",
    "apikey",
    "secret",
    "token",
    "password",
    "passwd",
    "credential",
}
CHROMA_HTTP_RULE_IDS: Final = {
    "code_pattern_vector_store_chroma_http",
    "code_pattern_vector_store_chroma_async_http",
}


class RiskHintService:
    """Build conservative risk hints with valid evidence references."""

    def derive(
        self,
        *,
        facts: Sequence[ScanFact],
        evidence: Sequence[Evidence],
        issues: Sequence[ParseIssue],
        components: ComponentDetectionResult,
        endpoints: Sequence[Endpoint],
    ) -> list[RiskHint]:
        evidence_lookup = EvidenceLookup(evidence)
        component_lookup = ComponentLookup(components)
        hints: dict[str, RiskHint] = {}

        for endpoint in endpoints:
            source_evidence = evidence_lookup.by_id(endpoint.evidence_id)
            if source_evidence is None:
                continue
            component = component_lookup.by_id(endpoint.component_instance_id)
            if source_evidence.rule_id == PUBLISHED_PORT_RULE_ID:
                self._add_hint(
                    hints,
                    self._published_port_hint(endpoint, source_evidence),
                )
                if _is_chroma_component(component):
                    self._add_hint(
                        hints,
                        self._chroma_server_port_hint(
                            endpoint,
                            source_evidence,
                        ),
                    )
            if endpoint.endpoint_type == "external":
                self._add_hint(
                    hints,
                    self._external_provider_hint(endpoint),
                )
            if endpoint.slot == "vector_store" and _is_chroma_http_component(
                component
            ):
                self._add_hint(
                    hints,
                    self._chroma_http_endpoint_hint(endpoint),
                )

        for issue in issues:
            hint = self._parse_issue_hint(issue, evidence_lookup)
            self._add_hint(hints, hint)

        for fact in facts:
            evidence_id = evidence_lookup.id_for_fact(fact)
            if evidence_id is None:
                continue
            if self._is_secret_like_config(fact):
                self._add_hint(
                    hints,
                    self._secret_like_config_hint(fact, evidence_id),
                )

        context_evidence_id = evidence_lookup.first_id()
        if context_evidence_id is not None:
            for slot in components.components_by_slot.values():
                if slot.required_for_rag and slot.status == "missing":
                    self._add_hint(
                        hints,
                        self._missing_required_slot_hint(
                            slot.slot,
                            context_evidence_id,
                        ),
                    )

        for component in component_lookup.instances:
            if component.provider == "chroma_persistent":
                evidence_id = _first(component.evidence_ids)
                if evidence_id is None:
                    continue
                self._add_hint(
                    hints,
                    self._chroma_local_persistence_hint(
                        component,
                        evidence_id,
                    ),
                )

        return sorted(hints.values(), key=lambda item: item.id)

    def _published_port_hint(
        self,
        endpoint: Endpoint,
        evidence: Evidence,
    ) -> RiskHint:
        local_bound = _is_loopback_binding(evidence.value)
        severity = "low" if local_bound else "medium"
        rationale = (
            "Docker published port is bound to loopback; review whether this "
            "local-only endpoint is expected."
            if local_bound
            else (
                "Docker published port may expose a service endpoint beyond "
                "the container network."
            )
        )
        return RiskHint(
            id=f"risk:docker_published_port_exposure:{_slug(endpoint.id)}",
            type="network_exposure",
            target=endpoint.id,
            target_type="endpoint",
            evidence_id=evidence.id,
            rule_id="docker_published_port_exposure",
            rationale=rationale,
            uncertainty=(
                "Compose port binding does not prove firewall, runtime "
                "reachability, or public network exposure."
            ),
            severity_hint=severity,
        )

    def _external_provider_hint(self, endpoint: Endpoint) -> RiskHint:
        return RiskHint(
            id=f"risk:external_provider_detected:{_slug(endpoint.id)}",
            type="external_provider",
            target=endpoint.id,
            target_type="endpoint",
            evidence_id=endpoint.evidence_id,
            rule_id="external_provider_detected",
            rationale=(
                "External provider endpoint detected; review data egress, "
                "retention, and provider configuration."
            ),
            uncertainty=(
                "Static scan identifies provider configuration but does not "
                "observe actual runtime requests or payload contents."
            ),
            severity_hint="medium",
        )

    def _parse_issue_hint(
        self,
        issue: ParseIssue,
        evidence_lookup: EvidenceLookup,
    ) -> RiskHint | None:
        evidence = evidence_lookup.parse_evidence_for_issue(issue)
        if evidence is None or evidence.file is None:
            return None
        return RiskHint(
            id=f"risk:{_slug(issue.rule_id)}:{_slug(issue.file)}",
            type="partial_scan",
            target=evidence.file,
            target_type="file",
            evidence_id=evidence.id,
            rule_id=issue.rule_id,
            rationale=(
                "A configuration or manifest parse error may make the system "
                "map incomplete."
            ),
            uncertainty=(
                "Static scan can only derive facts from files that parsed "
                "successfully."
            ),
            severity_hint="medium",
        )

    def _secret_like_config_hint(
        self,
        fact: ScanFact,
        evidence_id: str,
    ) -> RiskHint:
        return RiskHint(
            id=f"risk:secret_like_config_key_detected:{_slug(evidence_id)}",
            type="secret_config",
            target=evidence_id,
            target_type="evidence",
            evidence_id=evidence_id,
            rule_id="secret_like_config_key_detected",
            rationale=(
                "Secret-like configuration key detected; ensure masking, "
                "storage, and access controls are reviewed."
            ),
            uncertainty=(
                "Key name is a heuristic and does not prove whether the value "
                "is a live credential."
            ),
            severity_hint="medium",
        )

    def _missing_required_slot_hint(
        self,
        slot: str,
        evidence_id: str,
    ) -> RiskHint:
        return RiskHint(
            id=f"risk:missing_required_slot:{_slug(slot)}",
            type="missing_component",
            target=slot,
            target_type="component_slot",
            evidence_id=evidence_id,
            rule_id="missing_required_slot",
            rationale=(
                f"Required rag-core-v1 slot '{slot}' was not detected in the "
                "available evidence."
            ),
            uncertainty=(
                "Missing detection may mean the project lacks this component "
                "or the current static scan rules did not recognize it."
            ),
            severity_hint="medium",
        )

    def _chroma_http_endpoint_hint(self, endpoint: Endpoint) -> RiskHint:
        return RiskHint(
            id=f"risk:chroma_http_endpoint_detected:{_slug(endpoint.id)}",
            type="vector_store_endpoint",
            target=endpoint.id,
            target_type="endpoint",
            evidence_id=endpoint.evidence_id,
            rule_id="chroma_http_endpoint_detected",
            rationale=(
                "Chroma vector store appears to be accessed over HTTP/server "
                "mode."
            ),
            uncertainty="Static scan does not verify runtime reachability.",
            severity_hint="low",
        )

    def _chroma_local_persistence_hint(
        self,
        component: ComponentInstance,
        evidence_id: str,
    ) -> RiskHint:
        return RiskHint(
            id=f"risk:chroma_local_persistence_detected:{_slug(component.id)}",
            type="local_persistence",
            target=component.id,
            target_type="component_instance",
            evidence_id=evidence_id,
            rule_id="chroma_local_persistence_detected",
            rationale=(
                "Local Chroma persistence may store embeddings, metadata, or "
                "documents on disk."
            ),
            uncertainty=(
                "Static scan does not inspect stored data contents or local "
                "filesystem permissions."
            ),
            severity_hint="medium",
        )

    def _chroma_server_port_hint(
        self,
        endpoint: Endpoint,
        evidence: Evidence,
    ) -> RiskHint:
        return RiskHint(
            id=f"risk:chroma_server_published_port:{_slug(endpoint.id)}",
            type="vector_store_network_exposure",
            target=endpoint.id,
            target_type="endpoint",
            evidence_id=evidence.id,
            rule_id="chroma_server_published_port",
            rationale=(
                "Published Chroma port may expose vector store service beyond "
                "localhost."
            ),
            uncertainty=(
                "Compose port binding does not prove firewall or runtime "
                "exposure."
            ),
            severity_hint="medium",
        )

    def _is_secret_like_config(self, fact: ScanFact) -> bool:
        if fact.kind not in {"config_value", "docker_environment"}:
            return False
        normalized_path = re.sub(r"[^a-zA-Z0-9]+", "_", fact.path.lower())
        return any(marker in normalized_path for marker in SECRET_MARKERS)

    def _add_hint(
        self,
        hints: dict[str, RiskHint],
        hint: RiskHint | None,
    ) -> None:
        if hint is None:
            return
        hints[hint.id] = hint


class EvidenceLookup:
    """Find evidence records by id, fact, or parse issue."""

    def __init__(self, evidence: Sequence[Evidence]) -> None:
        self._evidence = tuple(evidence)
        self._by_id = {item.id: item for item in self._evidence}

    def by_id(self, evidence_id: str) -> Evidence | None:
        return self._by_id.get(evidence_id)

    def first_id(self) -> str | None:
        if not self._evidence:
            return None
        return sorted(item.id for item in self._evidence)[0]

    def id_for_fact(self, fact: ScanFact) -> str | None:
        matches = [
            item.id
            for item in self._evidence
            if item.file == fact.file
            and item.path == fact.path
            and item.kind == fact.kind
            and item.rule_id == fact.rule_id
        ]
        if not matches:
            return None
        return sorted(matches)[0]

    def parse_evidence_for_issue(self, issue: ParseIssue) -> Evidence | None:
        matches = [
            item
            for item in self._evidence
            if item.file == issue.file
            and item.kind == "parse_error"
            and item.rule_id == issue.rule_id
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item.id)[0]


class ComponentLookup:
    """Locate component instances by id."""

    def __init__(self, components: ComponentDetectionResult) -> None:
        self.instances = tuple(
            instance
            for slot in components.components_by_slot.values()
            for instance in slot.instances
        )
        self._by_id = {instance.id: instance for instance in self.instances}

    def by_id(self, component_id: str | None) -> ComponentInstance | None:
        if component_id is None:
            return None
        return self._by_id.get(component_id)


def _is_loopback_binding(value: str | None) -> bool:
    if not value:
        return False
    if value.startswith("host_ip="):
        match = re.search(r"(?:^|,)host_ip=([^,]+)", value)
        return match is not None and match.group(1) in {
            "127.0.0.1",
            "localhost",
            "::1",
        }
    return value.startswith(("127.0.0.1:", "localhost:"))


def _is_chroma_component(component: ComponentInstance | None) -> bool:
    return component is not None and (component.provider or "").startswith(
        "chroma"
    )


def _is_chroma_http_component(component: ComponentInstance | None) -> bool:
    return component is not None and component.provider == "chroma_http"


def _first(values: list[str]) -> str | None:
    if not values:
        return None
    return sorted(values)[0]


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"
