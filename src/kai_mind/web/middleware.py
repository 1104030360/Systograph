"""Local API hardening middleware."""

from __future__ import annotations

import logging
from typing import Any, Final

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from kai_mind.core.services.logging_service import safe_log_event

DEFAULT_MAX_REQUEST_BODY_BYTES: Final = 1_000_000
HTTP_BODY_METHODS: Final = {"POST", "PUT", "PATCH"}
logger = logging.getLogger(__name__)


class RequestSizeLimitMiddleware:
    """Reject oversized local API request bodies before route handlers run."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_request_body_bytes: int = DEFAULT_MAX_REQUEST_BODY_BYTES,
    ) -> None:
        self.app = app
        self._max_request_body_bytes = max_request_body_bytes

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if (
            scope["type"] != "http"
            or scope.get("method") not in HTTP_BODY_METHODS
        ):
            await self.app(scope, receive, send)
            return

        buffered: list[Message] = []
        total_bytes = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] != "http.request":
                continue
            total_bytes += len(message.get("body", b""))
            if total_bytes > self._max_request_body_bytes:
                await _json_response(
                    {"detail": "request_too_large"},
                    status_code=413,
                    scope=scope,
                    receive=receive,
                    send=send,
                )
                return
            if not message.get("more_body", False):
                break

        replay = _ReplayReceive(buffered)
        await self.app(scope, replay, send)


class SafeUnhandledExceptionMiddleware:
    """Return stable masked 500 errors for unexpected local API failures."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        try:
            await self.app(scope, receive, send)
        except Exception as exc:  # noqa: BLE001
            safe_log_event(
                logger,
                logging.ERROR,
                "local_api_unhandled_exception",
                stage="local_api",
                exception_type=exc.__class__.__name__,
            )
            if scope["type"] != "http":
                raise
            await _json_response(
                {"detail": "internal_server_error"},
                status_code=500,
                scope=scope,
                receive=receive,
                send=send,
            )


class _ReplayReceive:
    def __init__(self, messages: list[Message]) -> None:
        self._messages = list(messages)

    async def __call__(self) -> Message:
        if self._messages:
            return self._messages.pop(0)
        return {"type": "http.request", "body": b"", "more_body": False}


async def _json_response(
    content: dict[str, Any],
    *,
    status_code: int,
    scope: Scope,
    receive: Receive,
    send: Send,
) -> None:
    response = JSONResponse(content, status_code=status_code)
    await response(scope, receive, send)
