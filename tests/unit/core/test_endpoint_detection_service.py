from __future__ import annotations

from kai_mind.core.models.scan import ScanFact
from kai_mind.core.models.system_map import Endpoint, Evidence
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from kai_mind.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from kai_mind.core.services.rag_template_service import RagTemplateService


def fact_with_evidence(
    *,
    kind: str,
    file: str,
    path: str,
    value: str | None,
    rule_id: str,
    snippet: str | None = None,
) -> tuple[ScanFact, Evidence]:
    evidence_id = f"evidence:{rule_id}:{file}:{path}".replace("/", "_")
    return (
        ScanFact(
            kind=kind,
            file=file,
            path=path,
            value=value,
            rule_id=rule_id,
        ),
        Evidence(
            id=evidence_id,
            kind=kind,
            file=file,
            path=path,
            value=value,
            rule_id=rule_id,
            snippet=snippet,
        ),
    )


def detect_components(
    pairs: list[tuple[ScanFact, Evidence]],
) -> ComponentDetectionResult:
    template = RagTemplateService.load("rag-core-v1")
    return ComponentDetectionService().detect(
        template=template,
        facts=[fact for fact, _evidence in pairs],
        evidence=[evidence for _fact, evidence in pairs],
    )


def detect_endpoints(
    pairs: list[tuple[ScanFact, Evidence]],
) -> list[Endpoint]:
    return EndpointDetectionService().detect(
        facts=[fact for fact, _evidence in pairs],
        evidence=[evidence for _fact, evidence in pairs],
        components=detect_components(pairs),
    )


def test_docker_short_port_creates_qdrant_host_published_endpoint() -> None:
    qdrant_image = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.qdrant.image",
        value="qdrant/qdrant:v1.12.1",
        rule_id="docker_qdrant_image_detected",
    )
    qdrant_port = fact_with_evidence(
        kind="published_port",
        file="docker-compose.yml",
        path="services.qdrant.ports[0]",
        value="6333:6333",
        rule_id="docker_published_port_detected",
    )

    endpoints = detect_endpoints([qdrant_image, qdrant_port])

    assert len(endpoints) == 1
    endpoint = endpoints[0]
    assert endpoint.value == "http://localhost:6333"
    assert endpoint.endpoint_type == "local"
    assert endpoint.slot == "vector_store"
    assert endpoint.component_instance_id == "component:vector_store:qdrant"
    assert endpoint.evidence_id == qdrant_port[1].id


def test_docker_loopback_binding_preserves_loopback_host() -> None:
    qdrant_image = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.qdrant.image",
        value="qdrant/qdrant:v1.12.1",
        rule_id="docker_qdrant_image_detected",
    )
    loopback_port = fact_with_evidence(
        kind="published_port",
        file="docker-compose.yml",
        path="services.qdrant.ports[0]",
        value="127.0.0.1:6333:6333",
        rule_id="docker_published_port_detected",
    )

    endpoints = detect_endpoints([qdrant_image, loopback_port])

    assert endpoints[0].value == "http://127.0.0.1:6333"
    assert endpoints[0].evidence_id == loopback_port[1].id


def test_compose_service_reference_creates_internal_endpoint() -> None:
    qdrant_image = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.qdrant.image",
        value="qdrant/qdrant:v1.12.1",
        rule_id="docker_qdrant_image_detected",
    )
    api_env = fact_with_evidence(
        kind="docker_environment",
        file="docker-compose.yml",
        path="services.api.environment.QDRANT_URL",
        value="http://qdrant:6333",
        rule_id="docker_environment_detected",
    )

    endpoints = detect_endpoints([qdrant_image, api_env])

    assert len(endpoints) == 1
    assert endpoints[0].value == "http://qdrant:6333"
    assert endpoints[0].endpoint_type == "local"
    assert endpoints[0].component_instance_id == (
        "component:vector_store:qdrant"
    )
    assert endpoints[0].evidence_id == api_env[1].id


def test_malformed_internal_service_port_is_skipped() -> None:
    qdrant_image = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.qdrant.image",
        value="qdrant/qdrant:v1.12.1",
        rule_id="docker_qdrant_image_detected",
    )
    api_env = fact_with_evidence(
        kind="docker_environment",
        file="docker-compose.yml",
        path="services.api.environment.QDRANT_URL",
        value="http://qdrant:notaport",
        rule_id="docker_environment_detected",
    )

    endpoints = detect_endpoints([qdrant_image, api_env])

    assert endpoints == []


def test_out_of_range_internal_service_port_is_skipped() -> None:
    qdrant_image = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.qdrant.image",
        value="qdrant/qdrant:v1.12.1",
        rule_id="docker_qdrant_image_detected",
    )
    api_env = fact_with_evidence(
        kind="docker_environment",
        file="docker-compose.yml",
        path="services.api.environment.QDRANT_URL",
        value="http://qdrant:99999",
        rule_id="docker_environment_detected",
    )

    endpoints = detect_endpoints([qdrant_image, api_env])

    assert endpoints == []


def test_openai_config_creates_external_endpoint_no_secret_value() -> None:
    openai_key = fact_with_evidence(
        kind="config_value",
        file=".env",
        path="OPENAI_API_KEY",
        value="sk-...masked",
        rule_id="config_env_value_detected",
    )

    endpoints = detect_endpoints([openai_key])

    assert len(endpoints) == 1
    assert endpoints[0].value == "https://api.openai.com/v1"
    assert endpoints[0].endpoint_type == "external"
    assert endpoints[0].component_instance_id in {
        "component:embedding_model:openai",
        "component:llm:openai",
    }
    assert "sk-" not in endpoints[0].value


def test_chroma_http_client_literal_args_create_endpoint() -> None:
    chroma_http = fact_with_evidence(
        kind="vector_store_client",
        file="src/vector.py",
        path="line[3]",
        value="chromadb.HttpClient(",
        rule_id="code_pattern_vector_store_chroma_http",
        snippet='client = chromadb.HttpClient(host="localhost", port=8000)',
    )

    endpoints = detect_endpoints([chroma_http])

    assert len(endpoints) == 1
    assert endpoints[0].value == "http://localhost:8000"
    assert endpoints[0].slot == "vector_store"
    assert endpoints[0].component_instance_id == (
        "component:vector_store:chroma_http"
    )
    assert endpoints[0].evidence_id == chroma_http[1].id


def test_chroma_persistent_client_does_not_create_external_endpoint() -> None:
    chroma_persistent = fact_with_evidence(
        kind="vector_store_client",
        file="src/vector.py",
        path="line[8]",
        value="chromadb.PersistentClient(",
        rule_id="code_pattern_vector_store_chroma_persistent",
        snippet='client = chromadb.PersistentClient(path="./chroma")',
    )

    endpoints = detect_endpoints([chroma_persistent])

    assert endpoints == []
