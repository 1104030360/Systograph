from __future__ import annotations

import asyncio
import json
import logging

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.types import Message, Receive, Scope, Send

from kai_mind.core.providers.local_json_state_errors import (
    ProjectStateBusyError,
)
from kai_mind.web import middleware as web_middleware
from kai_mind.web.app import LocalApiApp, create_app
from kai_mind.web.middleware import (
    RequestSizeLimitMiddleware,
    SafeUnhandledExceptionMiddleware,
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


def test_streaming_failure_does_not_double_start_response() -> None:
    """response 已開始後才拋例外，不可再送第二個 http.response.start。"""
    sent: list[Message] = []

    async def streaming_then_boom(
        scope_: Scope,
        receive_: Receive,
        send_: Send,
    ) -> None:
        await send_(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/event-stream")],
            }
        )
        await send_(
            {"type": "http.response.body", "body": b"x", "more_body": True}
        )
        raise RuntimeError("db handle died mid-stream")

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = SafeUnhandledExceptionMiddleware(streaming_then_boom)
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/scan/events",
        "headers": [],
    }

    # 死因必須原樣傳出去，不能被 "ASGI protocol violation" 蓋掉。
    with pytest.raises(RuntimeError, match="db handle died mid-stream"):
        asyncio.run(middleware(scope, receive, send))

    starts = [m for m in sent if m["type"] == "http.response.start"]
    assert len(starts) == 1


def test_client_disconnect_is_swallowed_without_error_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """中途斷線不是 server 錯誤：不送回應、不留 ERROR、不 re-raise。"""
    sent: list[Message] = []

    async def guard_style_json_read(
        scope_: Scope,
        receive_: Receive,
        send_: Send,
    ) -> None:
        # 形狀對齊 legacy_mapping_guards.reject_legacy_mapping_type 的
        # raw await request.json()：對方斷線時 starlette 會拋
        # ClientDisconnect。目前那三條掛 guard 的 route 都有 body field，
        # FastAPI 會先讀掉 body 並自行轉成 400，所以這裡直接測 middleware
        # 契約本身，涵蓋任何自己讀 raw stream 的路徑。
        await Request(scope_, receive_).json()

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = SafeUnhandledExceptionMiddleware(guard_style_json_read)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/mappings",
        "headers": [],
    }

    with caplog.at_level(logging.DEBUG, logger=web_middleware.__name__):
        asyncio.run(middleware(scope, receive, send))

    assert sent == []
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


def test_size_limit_middleware_failure_is_masked_as_json(
    local_api_app: LocalApiApp,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """遮蔽層必須包住 size limit —— 它的例外也要回 JSON 而非 plain text。"""
    client = TestClient(local_api_app, raise_server_exceptions=False)

    def boom(scope_: Scope) -> None:
        raise RuntimeError("size limit exploded")

    monkeypatch.setattr(
        "kai_mind.web.middleware._declared_content_length",
        boom,
    )

    response = client.post("/api/scans", json={"project_id": "p"})

    assert response.status_code == 500
    assert response.json() == {"detail": "internal_server_error"}


def test_unhandled_exception_log_carries_route_without_secrets(
    local_api_app: LocalApiApp,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """500 的 log 必須能定位，但結構化欄位不得含 secret 或絕對路徑。"""
    router = APIRouter()

    @router.get("/api/debug/boom-logged")
    def boom() -> None:
        raise RuntimeError(
            "failed at /Users/linjunting/Local_AI_Health_Doctor/.env "
            "with OPENAI_API_KEY=sk-live-secret-value"
        )

    local_api_app.include_router(router)
    client = TestClient(local_api_app, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR, logger=web_middleware.__name__):
        response = client.get("/api/debug/boom-logged")

    assert response.status_code == 500
    records = [
        record
        for record in caplog.records
        if record.name == web_middleware.__name__
        and record.levelno == logging.ERROR
    ]
    assert len(records) == 1
    event_data = getattr(records[0], "event_data", {})
    assert event_data["event"] == "local_api_unhandled_exception"
    assert event_data["stage"] == "local_api"
    assert event_data["request_method"] == "GET"
    assert event_data["request_path"] == "/api/debug/boom-logged"
    assert event_data["exception_type"] == "RuntimeError"
    # exc_info 是唯一能讓預設 Formatter 印出 file/line 的通道；
    # 它走 logging 自己的 traceback 格式化，不經過遮罩，因此
    # 只有結構化欄位與訊息本身在這裡被斷言為乾淨的。
    # （re-raise 之後 uvicorn 本來就會印同一份 traceback。）
    assert records[0].exc_info is not None
    rendered = f"{event_data}{records[0].getMessage()}"
    assert "sk-live-secret-value" not in rendered
    assert "/Users/linjunting" not in rendered
    assert "sk-live-secret-value" not in response.text
    assert "/Users/linjunting" not in response.text
