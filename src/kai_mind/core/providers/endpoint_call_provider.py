"""Bounded HTTP caller for explicit query trace runs."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict

from kai_mind.core.models.system_map import Endpoint

EndpointCallStatus = Literal[
    "ok",
    "timeout",
    "connection_error",
    "request_error",
    "http_error",
    "invalid_response",
    "unsupported_endpoint",
]


class EndpointCallResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EndpointCallStatus
    query_sent: bool
    status_code: int | None = None
    body: Any | None = None
    latency_ms: float | None = None
    error_type: str | None = None
    error_message: str | None = None


class EndpointCallProvider:
    """Call one validated endpoint without instrumenting the target process."""

    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client()

    def call(
        self,
        *,
        endpoint: Endpoint,
        query: str,
        timeout_seconds: float,
    ) -> EndpointCallResult:
        method = (endpoint.method or "POST").upper()
        unsupported_result = self._endpoint_preflight_result(endpoint.value)
        if unsupported_result is not None:
            return unsupported_result

        started_at = perf_counter()
        try:
            response = self._request(
                method=method,
                url=endpoint.value,
                query=query,
                timeout_seconds=timeout_seconds,
            )
        except httpx.TimeoutException:
            return EndpointCallResult(
                status="timeout",
                query_sent=True,
                error_type="timeout",
                error_message=f"Timeout after {timeout_seconds:g}s",
            )
        except httpx.TransportError:
            return EndpointCallResult(
                status="connection_error",
                query_sent=True,
                error_type="connection_error",
                error_message="Endpoint request failed",
            )
        except httpx.InvalidURL:
            return EndpointCallResult(
                status="request_error",
                query_sent=False,
                error_type="invalid_url",
                error_message="Endpoint URL is invalid",
            )
        except httpx.HTTPError as error:
            return EndpointCallResult(
                status="request_error",
                query_sent=True,
                error_type=self._error_type(error),
                error_message="Endpoint request failed",
            )

        latency_ms = (perf_counter() - started_at) * 1000
        body = self._response_body(response)
        if not response.is_success:
            return EndpointCallResult(
                status="http_error",
                query_sent=True,
                status_code=response.status_code,
                body=body,
                latency_ms=latency_ms,
                error_type="http_error",
                error_message=f"HTTP {response.status_code}",
            )

        return EndpointCallResult(
            status="ok",
            query_sent=True,
            status_code=response.status_code,
            body=body,
            latency_ms=latency_ms,
        )

    def _request(
        self,
        *,
        method: str,
        url: str,
        query: str,
        timeout_seconds: float,
    ) -> httpx.Response:
        if method == "GET":
            return self._client.request(
                method,
                url,
                params={"query": query},
                timeout=timeout_seconds,
            )
        return self._client.request(
            method,
            url,
            json={"query": query},
            timeout=timeout_seconds,
        )

    def _response_body(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return {"content_type": response.headers.get("content-type")}

    def _endpoint_preflight_result(
        self,
        url: str,
    ) -> EndpointCallResult | None:
        try:
            scheme = urlsplit(url).scheme.lower()
        except ValueError:
            return EndpointCallResult(
                status="request_error",
                query_sent=False,
                error_type="invalid_url",
                error_message="Endpoint URL is invalid",
            )

        if scheme in {"http", "https"}:
            return None

        return EndpointCallResult(
            status="unsupported_endpoint",
            query_sent=False,
            error_type="unsupported_endpoint",
            error_message=(
                f"Unsupported endpoint scheme: {scheme or 'missing'}"
            ),
        )

    def _error_type(self, error: httpx.HTTPError) -> str:
        name = type(error).__name__
        parts: list[str] = []
        word_start = 0
        for index, char in enumerate(name):
            if index > 0 and char.isupper():
                parts.append(name[word_start:index].lower())
                word_start = index
        parts.append(name[word_start:].lower())
        return "_".join(parts)
