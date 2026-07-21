from __future__ import annotations

from dataclasses import dataclass, field

from tests.unit.core.test_detail_scan_service import base_map

from kai_mind.core.models.ai_system_map_v2 import (
    AiSystemMapV2,
    CanonicalEndpoint,
)
from kai_mind.core.providers.endpoint_call_provider import EndpointCallResult
from kai_mind.core.services.query_trace_service import QueryTraceService


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


def test_query_trace_endpoint_not_found_does_not_send_request() -> None:
    provider = RecordingEndpointProvider(
        EndpointCallResult(status="ok", query_sent=True, body={"answer": "ok"})
    )

    result = QueryTraceService(endpoint_call_provider=provider).trace(
        system_map=_map_with_endpoint(),
        endpoint_id="endpoint:missing",
        query="patient secret query",
    )

    assert result.status == "endpoint_not_found"
    assert result.query_sent is False
    assert result.endpoint_id == "endpoint:missing"
    assert provider.calls == []
    assert result.events[0].event_type == "endpoint_not_found"
    assert result.events[0].query_sent is False


def test_query_trace_masks_query_output_and_retrieved_chunks() -> None:
    raw_query = "patient said sk-test-1234567890 and private symptom"
    raw_answer = "answer contains sk-test-1234567890 and diagnosis detail"
    provider = RecordingEndpointProvider(
        EndpointCallResult(
            status="ok",
            query_sent=True,
            status_code=200,
            latency_ms=12.5,
            body={
                "answer": raw_answer,
                "retrieved_chunks": ["chunk with private symptom"],
            },
        )
    )

    result = QueryTraceService(endpoint_call_provider=provider).trace(
        system_map=_map_with_endpoint(),
        endpoint_id="endpoint:chat",
        query=raw_query,
    )

    serialized = str(result.model_dump(mode="json"))
    assert result.status == "completed"
    assert result.query_sent is True
    assert provider.calls[0][1] == raw_query
    assert raw_query not in serialized
    assert raw_answer not in serialized
    assert "chunk with private symptom" not in serialized
    assert "[MASKED]" in serialized
    assert result.events[0].event_type == "request_sent"
    assert result.events[1].event_type == "response_received"
    assert result.events[1].retrieved_chunks is not None


def test_query_trace_uses_configured_retrieved_chunk_keys() -> None:
    provider = RecordingEndpointProvider(
        EndpointCallResult(
            status="ok",
            query_sent=True,
            body={
                "answer": "ok",
                "docs": ["custom RAG framework chunk"],
            },
        )
    )

    result = QueryTraceService(
        endpoint_call_provider=provider,
        retrieved_chunks_keys=("docs",),
    ).trace(
        system_map=_map_with_endpoint(),
        endpoint_id="endpoint:chat",
        query="hello",
    )

    serialized = str(result.model_dump(mode="json"))
    assert result.status == "completed"
    assert result.events[1].retrieved_chunks is not None
    assert "custom RAG framework chunk" not in serialized


def test_query_trace_timeout_keeps_partial_replay_events() -> None:
    provider = RecordingEndpointProvider(
        EndpointCallResult(
            status="timeout",
            query_sent=True,
            error_type="timeout",
            error_message="Timeout after 30s",
        )
    )

    result = QueryTraceService(endpoint_call_provider=provider).trace(
        system_map=_map_with_endpoint(),
        endpoint_id="endpoint:chat",
        query="hello",
        timeout_seconds=30,
    )

    assert result.status == "partial"
    assert result.query_sent is True
    assert [event.event_type for event in result.events] == [
        "request_sent",
        "error",
    ]
    assert result.events[1].status == "partial"
    assert result.events[1].error == {
        "type": "timeout",
        "message": "Timeout after 30s",
    }
    assert result.error_reason == "timeout"


def test_query_trace_masks_url_credentials_in_error_fields() -> None:
    raw_url = "postgresql://demo:synthetic-pass-138@db.example:5432/app"
    provider = RecordingEndpointProvider(
        EndpointCallResult(
            status="connection_error",
            query_sent=True,
            error_type=f"connection_error:{raw_url}",
            error_message=f"Could not connect to {raw_url}",
        )
    )

    result = QueryTraceService(endpoint_call_provider=provider).trace(
        system_map=_map_with_endpoint(),
        endpoint_id="endpoint:chat",
        query="hello",
    )

    serialized = str(result.model_dump(mode="json"))
    assert raw_url not in serialized
    assert "synthetic-pass-138" not in serialized
    assert "[MASKED]" in serialized
    assert result.error_reason is not None
    assert raw_url not in result.error_reason


def test_query_trace_unsupported_endpoint_does_not_emit_request_sent() -> None:
    provider = RecordingEndpointProvider(
        EndpointCallResult(
            status="unsupported_endpoint",
            query_sent=False,
            error_type="unsupported_endpoint",
            error_message="Unsupported endpoint scheme: postgresql",
        )
    )

    result = QueryTraceService(endpoint_call_provider=provider).trace(
        system_map=_map_with_endpoint(
            value="postgresql://localhost:5432/rag",
        ),
        endpoint_id="endpoint:chat",
        query="hello",
    )

    assert result.status == "partial"
    assert result.query_sent is False
    assert [event.event_type for event in result.events] == ["error"]
    assert result.events[0].query_sent is False
    assert result.events[0].error == {
        "type": "unsupported_endpoint",
        "message": "Unsupported endpoint scheme: postgresql",
    }
    assert result.error_reason == "unsupported_endpoint"


def test_query_trace_blocked_endpoint_emits_one_blocked_error_event() -> None:
    provider = RecordingEndpointProvider(
        EndpointCallResult(
            status="blocked_endpoint",
            query_sent=False,
            error_type="egress_policy_blocked",
            error_message=(
                "Endpoint blocked by query trace egress policy: "
                "metadata_blocked"
            ),
        )
    )

    result = QueryTraceService(endpoint_call_provider=provider).trace(
        system_map=_map_with_endpoint(
            value="http://169.254.169.254/latest/meta-data/"
        ),
        endpoint_id="endpoint:chat",
        query="hello",
    )

    assert result.status == "partial"
    assert result.query_sent is False
    assert result.error_reason == "egress_policy_blocked"
    assert [event.event_type for event in result.events] == ["error"]
    assert result.events[0].query_sent is False
    assert result.events[0].status == "blocked"
    assert result.events[0].error == {
        "type": "egress_policy_blocked",
        "message": (
            "Endpoint blocked by query trace egress policy: metadata_blocked"
        ),
    }


def test_query_trace_marks_unmapped_evidence_without_mutating_map() -> None:
    system_map = _map_with_endpoint()
    original = system_map.model_dump(mode="json")
    provider = RecordingEndpointProvider(
        EndpointCallResult(
            status="ok",
            query_sent=True,
            body={
                "answer": "ok",
                "unmapped_component_id": "unmapped:router",
            },
        )
    )

    result = QueryTraceService(endpoint_call_provider=provider).trace(
        system_map=system_map,
        endpoint_id="endpoint:chat",
        query="hello",
    )

    assert system_map.model_dump(mode="json") == original
    assert result.events[1].step_type == "unknown"
    assert result.events[1].unmapped_component_id == "unmapped:router"
    assert "needs_mapping_confirmation" in result.events[1].warnings


def _map_with_endpoint(
    value: str = "http://rag.local/chat",
) -> AiSystemMapV2:
    system_map = base_map()
    return system_map.model_copy(
        update={
            "endpoints": [
                CanonicalEndpoint(
                    endpoint_id="endpoint:chat",
                    value=value,
                    endpoint_type="local",
                    method="POST",
                    evidence_ids=["evidence:l1-router"],
                )
            ]
        }
    )
