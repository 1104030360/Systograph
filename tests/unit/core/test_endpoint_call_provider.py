from __future__ import annotations

import json
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any

import httpx
import pytest

from kai_mind.core.models.system_map import Endpoint
from kai_mind.core.providers.endpoint_call_provider import (
    EndpointCallProvider,
)
from kai_mind.core.security.egress_policy import (
    EgressDecision,
    EgressPolicy,
    IPAddress,
)


class AllowAllPolicy:
    def evaluate(self, url: str) -> EgressDecision:
        del url
        return EgressDecision(allowed=True)


class BlockAllPolicy:
    def evaluate(self, url: str) -> EgressDecision:
        del url
        return EgressDecision(
            allowed=False,
            reason="loopback_blocked",
            normalized_host="127.0.0.1",
            port=8000,
            resolved_ips=("127.0.0.1",),
        )


@dataclass(frozen=True)
class StaticResolver:
    hostname: str
    addresses: tuple[str, ...]

    def resolve(
        self,
        hostname: str,
        port: int,
    ) -> tuple[IPAddress, ...]:
        del port
        if hostname != self.hostname:
            raise OSError("DNS resolution failed")
        return tuple(ip_address(value) for value in self.addresses)


def test_endpoint_call_provider_posts_query_and_returns_json_body() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"answer": "ok"})

    provider = EndpointCallProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        egress_policy=AllowAllPolicy(),
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


def test_public_endpoint_passes_real_policy_before_mock_transport() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"answer": "ok"})

    provider = EndpointCallProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        egress_policy=EgressPolicy(
            resolver=StaticResolver(
                hostname="example.com",
                addresses=("93.184.216.34",),
            )
        ),
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:public",
            value="https://example.com/chat",
            endpoint_type="external",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=2,
    )

    assert result.status == "ok"
    assert result.query_sent is True
    assert len(seen) == 1


def test_endpoint_call_provider_get_sends_query_as_param() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"answer": "ok"})

    provider = EndpointCallProvider(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        egress_policy=AllowAllPolicy(),
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
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        egress_policy=AllowAllPolicy(),
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
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        egress_policy=AllowAllPolicy(),
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
    provider = EndpointCallProvider(egress_policy=AllowAllPolicy())

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
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        egress_policy=AllowAllPolicy(),
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


def test_blocked_endpoint_is_unsent_without_calling_client() -> None:
    class FailingClient:
        def request(self, *args: Any, **kwargs: Any) -> httpx.Response:
            raise AssertionError("HTTP client must not be called")

    provider = EndpointCallProvider(
        client=FailingClient(),
        egress_policy=BlockAllPolicy(),
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:ssrf",
            value="http://127.0.0.1:8000/admin",
            endpoint_type="local",
            method="POST",
            evidence_id="evidence:endpoint",
        ),
        query="private query",
        timeout_seconds=1,
    )

    assert result.status == "blocked_endpoint"
    assert result.query_sent is False
    assert result.error_type == "egress_policy_blocked"
    assert result.error_message == (
        "Endpoint blocked by query trace egress policy: loopback_blocked"
    )


def test_injected_client_cannot_follow_redirect_to_blocked_target() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) > 1:
            raise AssertionError("Redirect target must not be requested")
        return httpx.Response(
            302,
            headers={"location": "http://169.254.169.254/latest/meta-data/"},
        )

    provider = EndpointCallProvider(
        client=httpx.Client(
            transport=httpx.MockTransport(handler),
            follow_redirects=True,
        ),
        egress_policy=AllowAllPolicy(),
    )

    result = provider.call(
        endpoint=Endpoint(
            id="endpoint:redirect",
            value="https://example.com/redirect",
            endpoint_type="external",
            method="GET",
            evidence_id="evidence:endpoint",
        ),
        query="hello",
        timeout_seconds=2,
    )

    assert result.status == "http_error"
    assert result.status_code == 302
    assert len(seen) == 1


def test_default_client_disables_redirects_and_environment_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class CapturingClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(httpx, "Client", CapturingClient)

    EndpointCallProvider()

    assert captured["follow_redirects"] is False
    assert captured["trust_env"] is False
