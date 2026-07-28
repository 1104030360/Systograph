from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from kai_mind.core.providers.local_json_state_errors import (
    ProjectStateBusyError,
)
from kai_mind.web.app import create_app
from kai_mind.web.middleware import (
    RequestSizeLimitMiddleware,
    _declared_content_length,
)


def test_large_request_returns_413_with_cors_header() -> None:
    client = TestClient(
        create_app(max_request_body_bytes=32),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/api/map/build",
        headers={
            "Origin": "http://localhost:5173",
            "Content-Type": "application/json",
        },
        content=b'{"project_path":"' + (b"x" * 80) + b'"}',
    )

    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.json() == {"detail": "request_too_large"}


def test_unhandled_error_response_is_masked_and_keeps_cors_header() -> None:
    router = APIRouter()

    @router.get("/api/debug/boom")
    def boom() -> None:
        raise RuntimeError(
            "failed at /Users/linjunting/Local_AI_Health_Doctor/.env "
            "with OPENAI_API_KEY=sk-live-secret-value"
        )

    app = create_app()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(
        "/api/debug/boom",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.json() == {"detail": "internal_server_error"}
    assert "sk-live-secret-value" not in response.text
    assert "/Users/linjunting" not in response.text


def test_project_lock_timeout_returns_stable_503() -> None:
    router = APIRouter()

    @router.post("/api/debug/busy")
    def busy() -> None:
        raise ProjectStateBusyError("private lock detail")

    app = create_app()
    app.include_router(router)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/debug/busy",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 503
    assert response.headers["access-control-allow-origin"] == (
        "http://localhost:5173"
    )
    assert response.json() == {"detail": "project_state_busy"}
    assert "private lock detail" not in response.text


@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("GET", "/api/map-builds/not-a-build", None),
        ("GET", "/api/projects/not-a-project/map-builds/latest", None),
        ("GET", "/api/mappings?project_id=not-a-project", None),
        (
            "POST",
            "/api/map-builds/not-a-build/apply",
            {"mapping_ids": ["mapping:m1"]},
        ),
    ],
)
def test_malformed_state_ids_return_stable_404(
    method: str,
    path: str,
    json_payload: dict[str, object] | None,
) -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.request(method, path, json=json_payload)

    assert response.status_code == 404
    assert response.json() == {"detail": "resource_not_found"}


def test_request_size_limit_stops_on_client_disconnect() -> None:
    """Client disconnect must not spin the size-limit receive loop."""
    calls = 0

    async def receive() -> Message:
        # A spinning loop never yields, so an asyncio timeout would never
        # fire; fail loudly instead of hanging the suite on a regression.
        nonlocal calls
        calls += 1
        if calls > 5:
            raise AssertionError(
                "receive() spun: size-limit loop did not break"
            )
        return {"type": "http.disconnect"}

    async def downstream(
        scope_: Scope,
        receive_: Receive,
        send_: Send,
    ) -> None:
        return None

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = RequestSizeLimitMiddleware(downstream)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/scans",
        "headers": [],
    }

    asyncio.run(middleware(scope, receive, send))

    assert calls == 1
    assert sent == []


def test_oversized_content_length_is_rejected_without_reading_body() -> None:
    """A declared oversized body is rejected before the body is read."""
    calls = 0

    async def receive() -> Message:
        nonlocal calls
        calls += 1
        return {"type": "http.request", "body": b"x", "more_body": False}

    async def downstream(
        scope_: Scope,
        receive_: Receive,
        send_: Send,
    ) -> None:
        raise AssertionError("downstream must not be reached")

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = RequestSizeLimitMiddleware(
        downstream,
        max_request_body_bytes=10,
    )
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/scans",
        "headers": [(b"content-length", b"999999")],
    }

    asyncio.run(middleware(scope, receive, send))

    assert calls == 0
    assert sent[0]["status"] == 413


def test_streamed_body_over_limit_is_rejected_without_content_length() -> None:
    """No Content-Length: the streamed byte counter is the only guard."""
    chunks: list[Message] = [
        {"type": "http.request", "body": b"x" * 8, "more_body": True},
        {"type": "http.request", "body": b"y" * 8, "more_body": False},
    ]
    received: list[Message] = []

    async def receive() -> Message:
        message = chunks.pop(0)
        received.append(message)
        return message

    async def downstream(
        scope_: Scope,
        receive_: Receive,
        send_: Send,
    ) -> None:
        raise AssertionError("downstream must not be reached")

    sent: list[Message] = []

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = RequestSizeLimitMiddleware(
        downstream,
        max_request_body_bytes=10,
    )
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/scans",
        "headers": [],
    }

    asyncio.run(middleware(scope, receive, send))

    # First chunk stays under the limit, so the loop must read the second.
    assert len(received) == 2
    assert sent[0]["status"] == 413
    assert json.loads(sent[1]["body"]) == {"detail": "request_too_large"}


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ([(b"content-length", b"999999")], 999999),
        ([(b"Content-Length", b"12")], 12),
        ([(b"content-length", b" 42 ")], None),
        ([(b"content-length", b"-1")], None),
        ([(b"content-length", b"+7")], None),
        ([(b"content-length", b"abc")], None),
        ([(b"content-length", b"\xff\xfe")], None),
        ([(b"content-length", b"9" * 5000)], None),
        ([(b"content-type", b"application/json")], None),
        ([], None),
    ],
)
def test_declared_content_length_falls_back_on_hostile_values(
    headers: list[tuple[bytes, bytes]],
    expected: int | None,
) -> None:
    """Unusable declarations degrade to None, never raise."""
    scope: Scope = {"type": "http", "headers": headers}

    assert _declared_content_length(scope) == expected
