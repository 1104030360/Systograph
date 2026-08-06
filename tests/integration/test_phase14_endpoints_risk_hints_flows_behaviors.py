from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from systograph.core.services.system_map_validation_service import (
    SystemMapValidationService,
)

# Static ai-system-map/v1 artifacts captured from the corresponding
# tests/fixtures/rag_projects scans. The v1 writer is gone (refactor 06),
# so these frozen payloads are the input to the retained v1 read path;
# the v2 derivation of the same projects is covered by the v2 build tests.
V1_FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "ai_system_map"


def load_phase14_map(fixture_name: str) -> dict[str, Any]:
    path = V1_FIXTURE_DIR / f"{fixture_name}.v1.json"
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def test_basic_qdrant_fixture_derives_valid_endpoint_risk_and_flow() -> None:
    system_map = load_phase14_map("basic_qdrant_ollama_rag")

    validated = SystemMapValidationService().validate(system_map)

    assert any(
        endpoint.value == "http://localhost:6333"
        and endpoint.slot == "vector_store"
        for endpoint in validated.endpoints
    )
    assert any(
        risk.rule_id == "docker_published_port_exposure"
        for risk in validated.risk_hints
    )
    assert any(
        edge.from_slot == "retriever" and edge.to_slot == "vector_store"
        for flow in validated.flows
        for edge in flow.edges
    )


def test_openai_fixture_derives_external_endpoint_no_secret_leak() -> None:
    system_map = load_phase14_map("openai_external_provider_rag")

    validated = SystemMapValidationService().validate(system_map)

    openai_endpoints = [
        endpoint
        for endpoint in validated.endpoints
        if endpoint.endpoint_type == "external"
    ]
    assert openai_endpoints
    assert all("sk-" not in endpoint.value for endpoint in openai_endpoints)
    assert any(
        risk.rule_id == "external_provider_detected"
        for risk in validated.risk_hints
    )
