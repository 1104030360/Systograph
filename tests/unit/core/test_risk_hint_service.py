from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest

from systograph.core.models.scan import ParseIssue, ScanFact
from systograph.core.models.system_map import Endpoint, Evidence, RiskHint
from systograph.core.services.component_detection_service import (
    ComponentDetectionResult,
    ComponentDetectionService,
)
from systograph.core.services.endpoint_detection_service import (
    EndpointDetectionService,
)
from systograph.core.services.rag_template_service import RagTemplateService
from systograph.core.services.risk_hint_service import (
    RiskHintMetadataError,
    RiskHintService,
)

ParseStage = Literal[
    "config_parse",
    "docker_compose_parse",
    "dependency_manifest_parse",
    "code_pattern_scan",
    "project_scan",
]


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


def parse_evidence(
    *,
    file: str,
    rule_id: str = "config_parse_error",
) -> Evidence:
    return Evidence(
        id=f"evidence:{rule_id}:{file}:parse".replace("/", "_"),
        kind="parse_error",
        file=file,
        path="$parse_error",
        value="Failed to parse file",
        rule_id=rule_id,
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
    components: ComponentDetectionResult,
) -> list[Endpoint]:
    return EndpointDetectionService().detect(
        facts=[fact for fact, _evidence in pairs],
        evidence=[evidence for _fact, evidence in pairs],
        components=components,
    )


def derive_risks(
    pairs: list[tuple[ScanFact, Evidence]],
    *,
    issues: list[ParseIssue] | None = None,
    service: RiskHintService | None = None,
) -> list[RiskHint]:
    components = detect_components(pairs)
    endpoints = detect_endpoints(pairs, components)
    return (service or RiskHintService()).derive(
        facts=[fact for fact, _evidence in pairs],
        evidence=[evidence for _fact, evidence in pairs],
        issues=issues or [],
        components=components,
        endpoints=endpoints,
    )


def write_catalog(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def minimal_risk_catalog(
    *,
    include_missing_required_slot: bool = True,
) -> str:
    entries = [
        (
            "[[risk_hints]]\n"
            'rule_id = "docker_published_port_exposure"\n'
            'type = "catalog_network_exposure"\n'
            'default_severity_hint = "catalog-medium"\n'
            'rationale = "Catalog published port rationale."\n'
            'uncertainty = "Catalog published port uncertainty."\n'
        )
    ]
    if include_missing_required_slot:
        entries.append(
            "[[risk_hints]]\n"
            'rule_id = "missing_required_slot"\n'
            'type = "catalog_missing_component"\n'
            'default_severity_hint = "catalog-medium"\n'
            'rationale = "Catalog missing slot rationale."\n'
            'uncertainty = "Catalog missing slot uncertainty."\n'
        )
    return "\n".join(entries)


def test_published_port_creates_network_exposure_hint() -> None:
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

    risks = derive_risks([qdrant_image, qdrant_port])

    published_risk = next(
        risk
        for risk in risks
        if risk.rule_id == "docker_published_port_exposure"
    )
    assert published_risk.target_type == "endpoint"
    assert published_risk.target.startswith("endpoint:docker:qdrant")
    assert published_risk.evidence_id == qdrant_port[1].id
    assert published_risk.severity_hint == "medium"
    assert "firewall" in (published_risk.uncertainty or "").lower()


def test_published_port_hint_uses_catalog_metadata(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "risk_hint_rules.toml",
        minimal_risk_catalog(),
    )
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

    risks = derive_risks(
        [qdrant_image, qdrant_port],
        service=RiskHintService(rule_catalog_path=catalog_path),
    )

    published_risk = next(
        risk
        for risk in risks
        if risk.rule_id == "docker_published_port_exposure"
    )
    assert published_risk.type == "catalog_network_exposure"
    assert published_risk.severity_hint == "catalog-medium"
    assert published_risk.rationale == "Catalog published port rationale."
    assert published_risk.uncertainty == "Catalog published port uncertainty."


def test_unknown_emitted_rule_id_fails_loudly(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "risk_hint_rules.toml",
        minimal_risk_catalog(include_missing_required_slot=False),
    )
    qdrant_image = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.qdrant.image",
        value="qdrant/qdrant:v1.12.1",
        rule_id="docker_qdrant_image_detected",
    )

    with pytest.raises(RiskHintMetadataError, match="missing_required_slot"):
        derive_risks(
            [qdrant_image],
            service=RiskHintService(rule_catalog_path=catalog_path),
        )


def test_loopback_published_port_uses_local_bound_wording() -> None:
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

    risks = derive_risks([qdrant_image, loopback_port])

    published_risk = next(
        risk
        for risk in risks
        if risk.rule_id == "docker_published_port_exposure"
    )
    assert published_risk.severity_hint == "low"
    assert "loopback" in published_risk.rationale.lower()


def test_internal_endpoint_does_not_create_published_port_risk() -> None:
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

    risks = derive_risks([qdrant_image, api_env])

    assert {risk.rule_id for risk in risks}.isdisjoint(
        {"docker_published_port_exposure"}
    )


def test_openai_external_endpoint_creates_provider_hint_no_secret() -> None:
    openai_key = fact_with_evidence(
        kind="config_value",
        file=".env",
        path="OPENAI_API_KEY",
        value="sk-...masked",
        rule_id="config_env_value_detected",
    )

    risks = derive_risks([openai_key])

    external_risk = next(
        risk for risk in risks if risk.rule_id == "external_provider_detected"
    )
    assert external_risk.target_type == "endpoint"
    assert external_risk.target.startswith("endpoint:external:openai")
    assert "sk-" not in external_risk.rationale
    assert "sk-" not in (external_risk.uncertainty or "")


def test_parse_issue_creates_config_parse_error_hint() -> None:
    evidence = parse_evidence(file="settings.yaml")
    issue = ParseIssue(
        provider="config",
        scan_stage="config_parse",
        file="settings.yaml",
        message="Failed to parse YAML file",
        rule_id="config_parse_error",
    )

    risks = RiskHintService().derive(
        facts=[],
        evidence=[evidence],
        issues=[issue],
        components=detect_components([]),
        endpoints=[],
    )

    parse_risk = next(
        risk for risk in risks if risk.rule_id == "config_parse_error"
    )
    assert parse_risk.target_type == "file"
    assert parse_risk.target == "settings.yaml"
    assert parse_risk.evidence_id == evidence.id


@pytest.mark.parametrize(
    ("provider", "scan_stage", "file", "rule_id"),
    [
        (
            "docker_compose",
            "docker_compose_parse",
            "docker-compose.yml",
            "docker_compose_parse_error",
        ),
        (
            "dependency_manifest",
            "dependency_manifest_parse",
            "package.json",
            "dependency_manifest_parse_error",
        ),
        (
            "code_pattern",
            "code_pattern_scan",
            "src/app.py",
            "code_pattern_read_error",
        ),
    ],
)
def test_provider_parse_issue_rule_ids_create_partial_scan_hints(
    provider: str,
    scan_stage: ParseStage,
    file: str,
    rule_id: str,
) -> None:
    evidence = parse_evidence(file=file, rule_id=rule_id)
    issue = ParseIssue(
        provider=provider,
        scan_stage=scan_stage,
        file=file,
        message="Provider parse/read issue",
        rule_id=rule_id,
    )

    risks = RiskHintService().derive(
        facts=[],
        evidence=[evidence],
        issues=[issue],
        components=detect_components([]),
        endpoints=[],
    )

    parse_risk = next(risk for risk in risks if risk.rule_id == rule_id)
    assert parse_risk.type == "partial_scan"
    assert parse_risk.target_type == "file"
    assert parse_risk.target == file
    assert parse_risk.evidence_id == evidence.id


def test_secret_like_config_key_creates_evidence_hint_without_value() -> None:
    secret = fact_with_evidence(
        kind="config_value",
        file=".env",
        path="CHROMA_API_KEY",
        value="***REDACTED***",
        rule_id="config_env_value_detected",
    )

    risks = derive_risks([secret])

    secret_risk = next(
        risk
        for risk in risks
        if risk.rule_id == "secret_like_config_key_detected"
    )
    assert secret_risk.target_type == "evidence"
    assert secret_risk.target == secret[1].id
    assert "***REDACTED***" not in secret_risk.rationale


def test_missing_required_slot_creates_component_slot_hint() -> None:
    qdrant_image = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.qdrant.image",
        value="qdrant/qdrant:v1.12.1",
        rule_id="docker_qdrant_image_detected",
    )

    risks = derive_risks([qdrant_image])

    missing_slots = {
        risk.target
        for risk in risks
        if risk.rule_id == "missing_required_slot"
    }
    assert "llm" in missing_slots
    assert "vector_store" not in missing_slots


def test_chroma_hints_cover_http_persistence_and_server_port() -> None:
    chroma_http = fact_with_evidence(
        kind="vector_store_client",
        file="src/vector.py",
        path="line[3]",
        value="chromadb.HttpClient(",
        rule_id="code_pattern_vector_store_chroma_http",
        snippet='client = chromadb.HttpClient(host="localhost", port=8000)',
    )
    chroma_persistent = fact_with_evidence(
        kind="vector_store_client",
        file="src/local_vector.py",
        path="line[7]",
        value="chromadb.PersistentClient(",
        rule_id="code_pattern_vector_store_chroma_persistent",
        snippet='client = chromadb.PersistentClient(path="./chroma")',
    )
    chroma_image = fact_with_evidence(
        kind="docker_service",
        file="docker-compose.yml",
        path="services.chroma.image",
        value="chromadb/chroma:latest",
        rule_id="docker_chromadb_chroma_image_detected",
    )
    chroma_port = fact_with_evidence(
        kind="published_port",
        file="docker-compose.yml",
        path="services.chroma.ports[0]",
        value="8000:8000",
        rule_id="docker_published_port_detected",
    )

    risks = derive_risks(
        [chroma_http, chroma_persistent, chroma_image, chroma_port]
    )

    rule_ids = {risk.rule_id for risk in risks}
    assert "chroma_http_endpoint_detected" in rule_ids
    assert "chroma_local_persistence_detected" in rule_ids
    assert "chroma_server_published_port" in rule_ids
