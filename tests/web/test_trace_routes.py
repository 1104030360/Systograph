from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient
from tests.unit.core.test_detail_scan_service import (
    base_map,
    build_router_project,
)

from systograph.core.models.ai_system_map_v2 import CanonicalEndpoint
from systograph.core.models.map_build import MapBuildResult
from systograph.core.providers.endpoint_call_provider import EndpointCallResult
from systograph.core.services.query_trace_service import QueryTraceService
from systograph.web.app import create_app
from systograph.web.session_store import InMemorySessionStore


@dataclass
class RecordingEndpointProvider:
    result: EndpointCallResult
    calls: list[tuple[CanonicalEndpoint, str, float]] = field(
        default_factory=list
    )

    def call(
        self,
        *,
        endpoint: CanonicalEndpoint,
        query: str,
        timeout_seconds: float,
    ) -> EndpointCallResult:
        self.calls.append((endpoint, query, timeout_seconds))
        return self.result


def test_trace_route_returns_endpoint_not_found_without_writing_map(
    tmp_path: Path,
) -> None:
    client, project_id, store, provider = create_trace_test_client(tmp_path)

    response = client.post(
        "/api/trace",
        json={
            "project_id": project_id,
            "endpoint_id": "endpoint:missing",
            "query": "patient secret query",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "endpoint_not_found"
    assert payload["query_sent"] is False
    assert provider.calls == []
    build_result = store.build_result(project_id)
    assert build_result is not None
    assert build_result.ai_system_map is not None
    assert build_result.ai_system_map.endpoints[0].endpoint_id == (
        "endpoint:chat"
    )


def test_trace_route_masks_success_response(tmp_path: Path) -> None:
    raw_query = "patient said sk-test-1234567890"
    raw_answer = "answer with sk-test-1234567890"
    client, project_id, _store, provider = create_trace_test_client(
        tmp_path,
        provider_result=EndpointCallResult(
            status="ok",
            query_sent=True,
            body={"answer": raw_answer, "retrieved_chunks": ["private chunk"]},
        ),
    )

    response = client.post(
        "/api/trace",
        json={
            "project_id": project_id,
            "endpoint_id": "endpoint:chat",
            "query": raw_query,
            "timeout_seconds": 3,
        },
    )

    assert response.status_code == 200
    payload_text = response.text
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["query_sent"] is True
    assert provider.calls[0][2] == 3
    assert raw_query not in payload_text
    assert raw_answer not in payload_text
    assert "private chunk" not in payload_text
    assert "[MASKED]" in payload_text


def test_trace_route_returns_unsent_blocked_endpoint_result(
    tmp_path: Path,
) -> None:
    client, project_id, _store, _provider = create_trace_test_client(
        tmp_path,
        provider_result=EndpointCallResult(
            status="blocked_endpoint",
            query_sent=False,
            error_type="egress_policy_blocked",
            error_message=(
                "Endpoint blocked by query trace egress policy: "
                "private_network_blocked"
            ),
        ),
    )

    response = client.post(
        "/api/trace",
        json={
            "project_id": project_id,
            "endpoint_id": "endpoint:chat",
            "query": "private query",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["query_sent"] is False
    assert payload["error_reason"] == "egress_policy_blocked"
    assert [event["event_type"] for event in payload["events"]] == ["error"]
    assert payload["events"][0]["status"] == "blocked"


def test_trace_route_uses_project_pyproject_chunk_keys(
    tmp_path: Path,
) -> None:
    client, project_id, _store, _provider = create_trace_test_client(
        tmp_path,
        provider_result=EndpointCallResult(
            status="ok",
            query_sent=True,
            body={
                "answer": "ok",
                "docs": ["private custom docs chunk"],
            },
        ),
        pyproject_text="""
[tool.systograph.trace]
retrieved_chunks_keys = ["docs", "retrieved_docs"]
""",
    )

    response = client.post(
        "/api/trace",
        json={
            "project_id": project_id,
            "endpoint_id": "endpoint:chat",
            "query": "hello",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["events"][1]["retrieved_chunks"] is not None
    assert "private custom docs chunk" not in response.text


def test_trace_route_requires_loaded_project_map(tmp_path: Path) -> None:
    store = InMemorySessionStore()
    project = store.import_project(
        project_path=build_router_project(tmp_path),
        source_type="local_path",
    )
    client = TestClient(create_app(session_store=store))

    missing_project = client.post(
        "/api/trace",
        json={
            "project_id": "project:missing",
            "endpoint_id": "endpoint:chat",
            "query": "hello",
        },
    )
    missing_map = client.post(
        "/api/trace",
        json={
            "project_id": project.project_id,
            "endpoint_id": "endpoint:chat",
            "query": "hello",
        },
    )

    assert missing_project.status_code == 404
    assert missing_project.json()["detail"] == "project_not_found"
    assert missing_map.status_code == 404
    assert missing_map.json()["detail"] == "map_not_loaded"


def create_trace_test_client(
    tmp_path: Path,
    *,
    provider_result: EndpointCallResult | None = None,
    pyproject_text: str | None = None,
) -> tuple[
    TestClient,
    str,
    InMemorySessionStore,
    RecordingEndpointProvider,
]:
    project_root = build_router_project(tmp_path)
    if pyproject_text is not None:
        (project_root / "pyproject.toml").write_text(
            pyproject_text,
            encoding="utf-8",
        )
    system_map = base_map().model_copy(
        update={
            "endpoints": [
                CanonicalEndpoint(
                    endpoint_id="endpoint:chat",
                    value="http://rag.local/chat",
                    endpoint_type="local",
                    method="POST",
                    evidence_ids=["evidence:l1-router"],
                )
            ]
        }
    )
    store = InMemorySessionStore()
    project = store.import_project(
        project_path=project_root,
        source_type="local_path",
    )
    store.save_build_result(
        MapBuildResult(
            status="ok",
            project_name=project_root.name,
            ai_system_map=system_map,
        ),
        project_id=project.project_id,
    )
    provider = RecordingEndpointProvider(
        provider_result
        or EndpointCallResult(
            status="ok",
            query_sent=True,
            body={"answer": "ok"},
        )
    )
    app = create_app(
        session_store=store,
        query_trace_service=QueryTraceService(endpoint_call_provider=provider),
    )
    return TestClient(app), project.project_id, store, provider
