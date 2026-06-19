from __future__ import annotations

import json

import httpx

from kai_mind.core.models.system_map import Endpoint
from kai_mind.core.providers.endpoint_call_provider import EndpointCallProvider


def test_endpoint_call_provider_posts_query_and_returns_json_body() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"answer": "ok"})

    provider = EndpointCallProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:chat",
            value="http://rag.local/chat",
            endpoint_type="local",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=2,
    )

    assert result.status == "ok"
    assert result.query_sent is True
    assert result.status_code == 200
    assert result.body == {"answer": "ok"}
    assert len(seen) == 1
    assert seen[0].method == "POST"
    assert json.loads(seen[0].content) == {"query": "hello"}


def test_endpoint_call_provider_get_sends_query_as_param() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"answer": "ok"})

    provider = EndpointCallProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:chat",
            value="http://rag.local/chat",
            endpoint_type="local",
            method="GET",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=2,
    )

    assert result.status == "ok"
    assert result.query_sent is True
    assert seen[0].url.params["query"] == "hello"


def test_endpoint_call_provider_wraps_timeout_as_typed_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("request timed out", request=request)

    provider = EndpointCallProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:slow",
            value="http://rag.local/slow",
            endpoint_type="local",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=0.01,
    )

    assert result.status == "timeout"
    assert result.query_sent is True
    assert result.error_type == "timeout"
    assert result.body is None


def test_endpoint_call_provider_wraps_httpx_request_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TooManyRedirects("too many redirects", request=request)

    provider = EndpointCallProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:redirect-loop",
            value="http://rag.local/redirect-loop",
            endpoint_type="local",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=2,
    )

    assert result.status == "request_error"
    assert result.query_sent is True
    assert result.error_type == "too_many_redirects"
    assert result.error_message == "Endpoint request failed"


def test_endpoint_call_provider_wraps_invalid_url_errors() -> None:
    provider = EndpointCallProvider()

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:invalid-url",
            value="http://[::1",
            endpoint_type="local",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=2,
    )

    assert result.status == "request_error"
    assert result.query_sent is False
    assert result.error_type == "invalid_url"
    assert result.error_message == "Endpoint URL is invalid"


def test_endpoint_call_provider_wraps_httpx_invalid_url_errors() -> None:
    provider = EndpointCallProvider()

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:invalid-url",
            value="http://example.com/" + chr(0),
            endpoint_type="local",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=2,
    )

    assert result.status == "request_error"
    assert result.query_sent is False
    assert result.error_type == "invalid_url"
    assert result.error_message == "Endpoint URL is invalid"


def test_endpoint_call_provider_rejects_non_http_endpoint_without_query() -> (
    None
):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"answer": "ok"})

    provider = EndpointCallProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler))
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:vector-store",
            value="postgresql://localhost:5432/rag",
            endpoint_type="local",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=2,
    )

    assert result.status == "unsupported_endpoint"
    assert result.query_sent is False
    assert result.error_type == "unsupported_endpoint"
    assert result.error_message == "Unsupported endpoint scheme: postgresql"
    assert seen == []
