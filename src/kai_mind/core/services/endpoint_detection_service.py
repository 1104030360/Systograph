"""Derive endpoint candidates from scanner facts and detected components."""

from __future__ import annotations

import ast
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final
from urllib.parse import ParseResult, urlparse

from kai_mind.core.models.scan import ScanFact
from kai_mind.core.models.system_map import (
    ComponentInstance,
    Endpoint,
    Evidence,
)
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)

PUBLISHED_PORT_RULE_ID: Final = "docker_published_port_detected"
OPENAI_DEFAULT_ENDPOINT: Final = "https://api.openai.com/v1"
HTTP_PORT_PROVIDERS: Final = {"qdrant", "chroma", "chroma_http", "ollama"}
POSTGRES_PORT_PROVIDERS: Final = {"pgvector"}
CHROMA_HTTP_RULE_IDS: Final = {
    "code_pattern_vector_store_chroma_http",
    "code_pattern_vector_store_chroma_async_http",
}


@dataclass(frozen=True)
class DockerPortBinding:
    """Static interpretation of a Compose published port value."""

    host_ip: str | None
    published: str | None
    target: str | None


class EndpointDetectionService:
    """Build deterministic endpoints from facts without runtime probing."""

    def detect(
        self,
        *,
        facts: Sequence[ScanFact],
        evidence: Sequence[Evidence],
        components: ComponentDetectionResult,
    ) -> list[Endpoint]:
        evidence_lookup = EvidenceLookup(evidence)
        component_lookup = ComponentLookup(components)
        service_providers = self._docker_service_providers(facts)

        endpoints: dict[str, Endpoint] = {}
        for fact in facts:
            if fact.rule_id == PUBLISHED_PORT_RULE_ID:
                endpoint = self._endpoint_from_published_port(
                    fact,
                    evidence_lookup,
                    component_lookup,
                    service_providers,
                )
                if endpoint is not None:
                    endpoints[endpoint.id] = endpoint
                continue

            endpoint = self._endpoint_from_internal_service_reference(
                fact,
                evidence_lookup,
                component_lookup,
                service_providers,
            )
            if endpoint is not None:
                endpoints[endpoint.id] = endpoint
                continue

            endpoint = self._endpoint_from_openai_config(
                fact,
                evidence_lookup,
                component_lookup,
            )
            if endpoint is not None:
                endpoints[endpoint.id] = endpoint
                continue

            endpoint = self._endpoint_from_chroma_http_client(
                fact,
                evidence_lookup,
                component_lookup,
            )
            if endpoint is not None:
                endpoints[endpoint.id] = endpoint

        return sorted(endpoints.values(), key=lambda item: item.id)

    def _docker_service_providers(
        self,
        facts: Sequence[ScanFact],
    ) -> dict[str, str]:
        providers: dict[str, str] = {}
        for fact in facts:
            service = _service_name(fact.path)
            if service is None:
                continue
            provider = _provider_from_docker_image_rule(fact.rule_id or "")
            if provider is not None:
                providers[service] = provider
        return providers

    def _endpoint_from_published_port(
        self,
        fact: ScanFact,
        evidence_lookup: EvidenceLookup,
        component_lookup: ComponentLookup,
        service_providers: dict[str, str],
    ) -> Endpoint | None:
        service = _service_name(fact.path)
        if service is None:
            return None
        provider = service_providers.get(service)
        if provider is None:
            return None
        component = component_lookup.first_by_provider(provider)
        if component is None:
            return None

        binding = _parse_docker_port_binding(fact.value)
        if binding.published is None:
            return None

        value = _service_endpoint_value(provider, binding)
        evidence_id = evidence_lookup.id_for_fact(fact)
        if evidence_id is None:
            return None

        return Endpoint(
            id=f"endpoint:docker:{_slug(service)}:{_slug(binding.published)}",
            value=value,
            endpoint_type="local",
            slot=component.slot,
            component_instance_id=component.id,
            evidence_id=evidence_id,
        )

    def _endpoint_from_internal_service_reference(
        self,
        fact: ScanFact,
        evidence_lookup: EvidenceLookup,
        component_lookup: ComponentLookup,
        service_providers: dict[str, str],
    ) -> Endpoint | None:
        if fact.kind != "docker_environment" or not fact.value:
            return None

        parsed_url = _first_url(fact.value)
        if parsed_url is None or parsed_url.hostname is None:
            return None
        port = _safe_url_port(parsed_url)
        if port is None:
            return None

        provider = service_providers.get(parsed_url.hostname)
        if provider is None:
            return None
        component = component_lookup.first_by_provider(provider)
        if component is None:
            return None
        evidence_id = evidence_lookup.id_for_fact(fact)
        if evidence_id is None:
            return None

        return Endpoint(
            id=(
                f"endpoint:docker-internal:{_slug(parsed_url.hostname)}:{port}"
            ),
            value=parsed_url.geturl(),
            endpoint_type="local",
            slot=component.slot,
            component_instance_id=component.id,
            evidence_id=evidence_id,
        )

    def _endpoint_from_openai_config(
        self,
        fact: ScanFact,
        evidence_lookup: EvidenceLookup,
        component_lookup: ComponentLookup,
    ) -> Endpoint | None:
        if fact.kind != "config_value" or "openai" not in fact.path.lower():
            return None

        component = component_lookup.first_by_provider("openai")
        if component is None:
            return None
        evidence_id = evidence_lookup.id_for_fact(fact)
        if evidence_id is None:
            return None

        value = OPENAI_DEFAULT_ENDPOINT
        if "base" in fact.path.lower() and fact.value:
            parsed = urlparse(fact.value)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                value = parsed.geturl()

        return Endpoint(
            id=f"endpoint:external:openai:{_slug(component.slot)}",
            value=value,
            endpoint_type="external",
            slot=component.slot,
            component_instance_id=component.id,
            evidence_id=evidence_id,
        )

    def _endpoint_from_chroma_http_client(
        self,
        fact: ScanFact,
        evidence_lookup: EvidenceLookup,
        component_lookup: ComponentLookup,
    ) -> Endpoint | None:
        if fact.rule_id not in CHROMA_HTTP_RULE_IDS:
            return None

        component = component_lookup.first_by_provider("chroma_http")
        if component is None:
            return None
        evidence_item = evidence_lookup.evidence_for_fact(fact)
        if evidence_item is None:
            return None

        host, port = _parse_chroma_http_literal_args(evidence_item.snippet)
        if host is None and port is None:
            return None
        host = host or "localhost"
        port = port or 8000

        return Endpoint(
            id=f"endpoint:chroma-http:{_slug(host)}:{port}",
            value=f"http://{host}:{port}",
            endpoint_type="local",
            slot=component.slot,
            component_instance_id=component.id,
            evidence_id=evidence_item.id,
        )


class EvidenceLookup:
    """Find evidence records corresponding to raw facts."""

    def __init__(self, evidence: Sequence[Evidence]) -> None:
        self._evidence = tuple(evidence)

    def id_for_fact(self, fact: ScanFact) -> str | None:
        evidence = self.evidence_for_fact(fact)
        if evidence is None:
            return None
        return evidence.id

    def evidence_for_fact(self, fact: ScanFact) -> Evidence | None:
        matches = [
            item
            for item in self._evidence
            if item.file == fact.file
            and item.path == fact.path
            and item.kind == fact.kind
            and item.rule_id == fact.rule_id
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item.id)[0]


class ComponentLookup:
    """Locate detected component instances by provider."""

    def __init__(self, components: ComponentDetectionResult) -> None:
        self._instances = tuple(
            instance
            for slot in components.components_by_slot.values()
            for instance in slot.instances
        )

    def first_by_provider(self, provider: str) -> ComponentInstance | None:
        aliases = _provider_aliases(provider)
        matches = [
            instance
            for instance in self._instances
            if (instance.provider or "") in aliases
        ]
        if not matches:
            return None
        return sorted(matches, key=lambda item: item.id)[0]


def _parse_docker_port_binding(value: str | None) -> DockerPortBinding:
    if not value:
        return DockerPortBinding(host_ip=None, published=None, target=None)

    long_syntax = _parse_normalized_long_syntax(value)
    if long_syntax is not None:
        return long_syntax

    raw_value = value.split("/", maxsplit=1)[0]
    if "[" in raw_value or "]" in raw_value or "-" in raw_value:
        return DockerPortBinding(
            host_ip=None,
            published=raw_value,
            target=None,
        )

    parts = raw_value.split(":")
    if len(parts) == 1:
        return DockerPortBinding(
            host_ip=None,
            published=parts[0],
            target=parts[0],
        )
    if len(parts) == 2:
        return DockerPortBinding(
            host_ip=None,
            published=parts[0],
            target=parts[1],
        )
    if len(parts) == 3:
        return DockerPortBinding(
            host_ip=parts[0],
            published=parts[1],
            target=parts[2],
        )
    return DockerPortBinding(host_ip=None, published=raw_value, target=None)


def _parse_normalized_long_syntax(value: str) -> DockerPortBinding | None:
    if "=" not in value:
        return None

    parts: dict[str, str] = {}
    for item in value.split(","):
        key, separator, raw = item.partition("=")
        if separator:
            parts[key.strip()] = raw.strip()

    if "published" not in parts and "target" not in parts:
        return None
    return DockerPortBinding(
        host_ip=parts.get("host_ip"),
        published=parts.get("published"),
        target=parts.get("target"),
    )


def _service_endpoint_value(
    provider: str,
    binding: DockerPortBinding,
) -> str:
    host = binding.host_ip or "localhost"
    if host == "0.0.0.0":
        host = "localhost"

    if provider in POSTGRES_PORT_PROVIDERS:
        return f"postgresql://{host}:{binding.published}"
    if provider in HTTP_PORT_PROVIDERS:
        return f"http://{host}:{binding.published}"
    return f"{host}:{binding.published}"


def _first_url(value: str) -> ParseResult | None:
    match = re.search(r"https?://[^\s,'\"]+", value)
    if match is None:
        return None
    parsed = urlparse(match.group(0))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed


def _safe_url_port(parsed: ParseResult) -> int | None:
    try:
        return parsed.port
    except ValueError:
        return None


def _parse_chroma_http_literal_args(
    snippet: str | None,
) -> tuple[str | None, int | None]:
    if not snippet:
        return None, None
    try:
        tree = ast.parse(snippet)
    except (SyntaxError, ValueError, RecursionError):
        return None, None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_chroma_http_call(node):
            continue
        host: str | None = None
        port: int | None = None
        for keyword in node.keywords:
            if keyword.arg == "host" and isinstance(
                keyword.value,
                ast.Constant,
            ):
                if isinstance(keyword.value.value, str):
                    host = keyword.value.value
            if keyword.arg == "port" and isinstance(
                keyword.value,
                ast.Constant,
            ):
                if isinstance(keyword.value.value, int):
                    port = keyword.value.value
        return host, port
    return None, None


def _is_chroma_http_call(node: ast.Call) -> bool:
    func = node.func
    return isinstance(func, ast.Attribute) and func.attr in {
        "HttpClient",
        "AsyncHttpClient",
    }


def _service_name(path: str) -> str | None:
    match = re.match(r"services\.([^.[]+)\.", path)
    if match is None:
        return None
    return match.group(1)


def _provider_from_docker_image_rule(rule_id: str) -> str | None:
    if rule_id == "docker_qdrant_image_detected":
        return "qdrant"
    if rule_id == "docker_pgvector_image_detected":
        return "pgvector"
    if rule_id == "docker_chromadb_chroma_image_detected":
        return "chroma"
    if rule_id == "docker_ollama_image_detected":
        return "ollama"
    return None


def _provider_aliases(provider: str) -> set[str]:
    if provider == "chroma":
        return {"chroma", "chroma_http", "chroma_persistent"}
    return {provider}


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown"
