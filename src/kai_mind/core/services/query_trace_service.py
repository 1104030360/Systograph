"""Build transient replay events for explicit query trace runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from kai_mind.core.models.system_map import (
    Endpoint,
    QueryTraceEvent,
    RagSystemMap,
)
from kai_mind.core.models.trace import TraceRunResult
from kai_mind.core.providers.endpoint_call_provider import (
    EndpointCallProvider,
    EndpointCallResult,
)
from kai_mind.core.services.query_trace_config_loader import (
    DEFAULT_RETRIEVED_CHUNKS_KEYS,
)
from kai_mind.core.services.secret_masking_service import (
    MASK,
    SecretMaskingService,
)


class EndpointCaller(Protocol):
    def call(
        self,
        *,
        endpoint: Endpoint,
        query: str,
        timeout_seconds: float,
    ) -> EndpointCallResult: ...


class QueryTraceService:
    """Run one opt-in black-box endpoint trace without mutating the map."""

    def __init__(
        self,
        *,
        endpoint_call_provider: EndpointCaller | None = None,
        masking_service: SecretMaskingService | None = None,
        retrieved_chunks_keys: Sequence[str] | None = None,
    ) -> None:
        self._endpoint_call_provider = (
            endpoint_call_provider or EndpointCallProvider()
        )
        self._masking_service = masking_service or SecretMaskingService()
        self._retrieved_chunks_keys = self._normalize_retrieved_chunks_keys(
            retrieved_chunks_keys
        )

    def trace(
        self,
        *,
        system_map: RagSystemMap,
        endpoint_id: str,
        query: str,
        timeout_seconds: float = 30.0,
        retrieved_chunks_keys: Sequence[str] | None = None,
    ) -> TraceRunResult:
        trace_id = f"trace:{uuid4()}"
        active_retrieved_chunks_keys = (
            self._normalize_retrieved_chunks_keys(retrieved_chunks_keys)
            if retrieved_chunks_keys is not None
            else self._retrieved_chunks_keys
        )
        endpoint = self._find_endpoint(system_map, endpoint_id)
        if endpoint is None:
            return TraceRunResult(
                trace_id=trace_id,
                status="endpoint_not_found",
                query_sent=False,
                endpoint_id=endpoint_id,
                error_reason="endpoint_not_found",
                events=[
                    self._event(
                        trace_id=trace_id,
                        sequence_index=0,
                        event_type="endpoint_not_found",
                        endpoint_id=endpoint_id,
                        query_sent=False,
                        status="endpoint_not_found",
                        error={
                            "type": "endpoint_not_found",
                            "message": "Endpoint id was not found in the map",
                        },
                    )
                ],
            )

        request_event = self._event(
            trace_id=trace_id,
            sequence_index=0,
            event_type="request_sent",
            endpoint_id=endpoint.id,
            query_sent=True,
            status="sent",
            slot=endpoint.slot,
            component_id=endpoint.component_instance_id,
            input={"query": self._masked_payload(query)},
        )
        call_result = self._endpoint_call_provider.call(
            endpoint=endpoint,
            query=query,
            timeout_seconds=timeout_seconds,
        )

        if call_result.status != "ok":
            error_type = self._masking_service.mask_text(
                call_result.error_type or call_result.status
            )
            error_message = self._masking_service.mask_text(
                call_result.error_message or "Endpoint request failed"
            )
            events = [request_event] if call_result.query_sent else []
            events.append(
                self._event(
                    trace_id=trace_id,
                    sequence_index=len(events),
                    event_type="error",
                    endpoint_id=endpoint.id,
                    query_sent=call_result.query_sent,
                    status="partial",
                    slot=endpoint.slot,
                    component_id=endpoint.component_instance_id,
                    latency_ms=call_result.latency_ms,
                    error={
                        "type": error_type,
                        "message": error_message,
                    },
                )
            )
            return TraceRunResult(
                trace_id=trace_id,
                status="partial",
                query_sent=call_result.query_sent,
                endpoint_id=endpoint.id,
                error_reason=error_type,
                events=events,
            )

        response_event = self._response_event(
            system_map=system_map,
            endpoint=endpoint,
            trace_id=trace_id,
            call_result=call_result,
            retrieved_chunks_keys=active_retrieved_chunks_keys,
        )
        return TraceRunResult(
            trace_id=trace_id,
            status="completed",
            query_sent=True,
            endpoint_id=endpoint.id,
            events=[request_event, response_event],
            warnings=response_event.warnings,
        )

    def _response_event(
        self,
        *,
        system_map: RagSystemMap,
        endpoint: Endpoint,
        trace_id: str,
        call_result: EndpointCallResult,
        retrieved_chunks_keys: tuple[str, ...],
    ) -> QueryTraceEvent:
        warnings: list[str] = []
        step_type: str | None = None
        unmapped_component_id: str | None = None
        body = call_result.body
        if isinstance(body, Mapping):
            candidate = body.get("unmapped_component_id")
            known_unmapped_ids = {
                component.id for component in system_map.unmapped_components
            }
            if isinstance(candidate, str) and candidate in known_unmapped_ids:
                step_type = "unknown"
                unmapped_component_id = candidate
                warnings.append("needs_mapping_confirmation")

        return self._event(
            trace_id=trace_id,
            sequence_index=1,
            event_type="response_received",
            endpoint_id=endpoint.id,
            query_sent=True,
            status="completed",
            slot=endpoint.slot,
            component_id=endpoint.component_instance_id,
            step_type=step_type,
            unmapped_component_id=unmapped_component_id,
            warnings=warnings,
            output=self._masked_payload(body),
            retrieved_chunks=self._retrieved_chunks(
                body,
                retrieved_chunks_keys=retrieved_chunks_keys,
            ),
            latency_ms=call_result.latency_ms,
        )

    def _retrieved_chunks(
        self,
        body: Any,
        *,
        retrieved_chunks_keys: tuple[str, ...],
    ) -> Any | None:
        if not isinstance(body, Mapping):
            return None
        for key in retrieved_chunks_keys:
            if key in body:
                return self._masked_payload(body[key])
        return None

    def _normalize_retrieved_chunks_keys(
        self,
        keys: Sequence[str] | None,
    ) -> tuple[str, ...]:
        if keys is None:
            return DEFAULT_RETRIEVED_CHUNKS_KEYS
        if isinstance(keys, str) or not keys:
            raise ValueError("retrieved_chunks_keys must be a string list")

        normalized: list[str] = []
        for index, key in enumerate(keys):
            if not isinstance(key, str) or not key.strip():
                raise ValueError(
                    "retrieved_chunks_keys"
                    f"[{index}] must be a non-empty string"
                )
            normalized.append(key.strip())
        return tuple(normalized)

    def _masked_payload(self, value: Any) -> Any:
        masked = self._masking_service.mask_json_like(value)
        return self._summary(masked)

    def _summary(self, value: Any) -> Any:
        if isinstance(value, str):
            return {
                "type": "string",
                "length": len(value),
                "masked": MASK,
            }
        if isinstance(value, Mapping):
            return {
                str(key): self._summary(child) for key, child in value.items()
            }
        if isinstance(value, list | tuple):
            return {
                "type": "list",
                "length": len(value),
                "items": [self._summary(child) for child in value[:5]],
            }
        if value is None:
            return {"type": "null"}
        if isinstance(value, bool):
            return {"type": "bool"}
        if isinstance(value, int | float):
            return {"type": "number"}
        return {"type": type(value).__name__}

    def _event(
        self,
        *,
        trace_id: str,
        sequence_index: int,
        event_type: str,
        endpoint_id: str,
        query_sent: bool,
        status: str,
        slot: str | None = None,
        component_id: str | None = None,
        step_type: str | None = None,
        unmapped_component_id: str | None = None,
        warnings: list[str] | None = None,
        input: Any | None = None,
        output: Any | None = None,
        retrieved_chunks: Any | None = None,
        latency_ms: float | None = None,
        error: Any | None = None,
    ) -> QueryTraceEvent:
        return QueryTraceEvent(
            id=f"{trace_id}:event:{sequence_index}",
            trace_id=trace_id,
            sequence_index=sequence_index,
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            slot=slot,
            component_id=component_id,
            event_type=event_type,
            endpoint_id=endpoint_id,
            query_sent=query_sent,
            status=status,
            step_type=step_type,
            unmapped_component_id=unmapped_component_id,
            warnings=warnings or [],
            input=input,
            output=output,
            latency_ms=latency_ms,
            error=error,
            retrieved_chunks=retrieved_chunks,
        )

    def _find_endpoint(
        self,
        system_map: RagSystemMap,
        endpoint_id: str,
    ) -> Endpoint | None:
        for endpoint in system_map.endpoints:
            if endpoint.id == endpoint_id:
                return endpoint
        return None
