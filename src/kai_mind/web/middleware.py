"""Local API hardening middleware."""

from __future__ import annotations

import logging
from typing import Any, Final

from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from kai_mind.core.providers.local_json_state_errors import (
    InvalidStateIdError,
    ProjectStateBusyError,
)
from kai_mind.core.services.logging_service import safe_log_event

DEFAULT_MAX_REQUEST_BODY_BYTES: Final = 1_000_000
HTTP_BODYLESS_METHODS: Final = {"GET", "HEAD", "OPTIONS"}
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
            or scope.get("method") in HTTP_BODYLESS_METHODS
        ):
            await self.app(scope, receive, send)
            return

        declared = _declared_content_length(scope)
        if declared is not None and declared > self._max_request_body_bytes:
            await _json_response(
                {"detail": "request_too_large"},
                status_code=413,
                scope=scope,
                receive=receive,
                send=send,
            )
            return

        buffered: list[Message] = []
        total_bytes = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] != "http.request":
                # After http.disconnect the ASGI server keeps returning
                # the same message forever; not breaking here starves the
                # event loop. Let the downstream app handle the disconnect.
                break
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
    """Return stable masked errors for unexpected local API failures.

    行為對齊 Starlette 的 ServerErrorMiddleware：
    - response 已開始時不再送第二個 http.response.start
    - 遮蔽回應送出後仍 re-raise，讓 uvicorn / TestClient 看得到死因
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except InvalidStateIdError as exc:
            await self._mask(
                {"detail": "resource_not_found"},
                status_code=404,
                started=response_started,
                exception_type=exc.__class__.__name__,
                scope=scope,
                receive=receive,
                send=send,
            )
        except ProjectStateBusyError as exc:
            await self._mask(
                {"detail": "project_state_busy"},
                status_code=503,
                started=response_started,
                exception_type=exc.__class__.__name__,
                scope=scope,
                receive=receive,
                send=send,
            )
        except ClientDisconnect:
            # 對方走了：送遮蔽回應沒有收件人，re-raise 只會讓 uvicorn 把
            # 一次正常的中斷印成 ERROR traceback。掛 guard 的那幾條 route
            # 有 body field，FastAPI 會先讀 body 並自行轉成 400；這一支
            # 接的是任何自己讀 raw stream 的路徑（例如未來的 streaming
            # 上傳），讓中途 Ctrl+C 不要變成 ERROR + 假的 500。
            safe_log_event(
                logger,
                logging.DEBUG,
                "local_api_client_disconnected",
                stage="local_api",
                request_method=scope.get("method"),
                request_path=scope.get("path"),
            )
        except Exception as exc:
            # exc_info 讓預設 logging 設定印得出例外類別與 file/line；
            # safe_log_event 會把 traceback render 成遮罩過的文字才寫出去，
            # raw 例外物件不會進 record.exc_info。
            safe_log_event(
                logger,
                logging.ERROR,
                "local_api_unhandled_exception",
                stage="local_api",
                exception_type=exc.__class__.__name__,
                request_method=scope.get("method"),
                request_path=scope.get("path"),
                exc_info=exc,
            )
            await self._mask(
                {"detail": "internal_server_error"},
                status_code=500,
                started=response_started,
                exception_type=exc.__class__.__name__,
                scope=scope,
                receive=receive,
                send=send,
            )
            raise

    @staticmethod
    async def _mask(
        content: dict[str, Any],
        *,
        status_code: int,
        started: bool,
        exception_type: str,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if started:
            # response 已經開始，遮蔽回應送不出去了。404/503 兩個分支
            # 吃掉例外而且不 re-raise，不留 log 就等於無聲失敗 ——
            # 所以固定留一筆 WARNING 說明「本來要送什麼」。
            # 500 分支也會走到這裡，那邊的例外已經另外記了 ERROR 又
            # re-raise，這一筆對它是重複的；照樣留著是因為它記的是
            # 「遮蔽回應沒送出去，client 收到的是先前那個已開始的
            # response」，那件事從 ERROR 那筆看不出來。重複無害。
            safe_log_event(
                logger,
                logging.WARNING,
                "masked_response_suppressed",
                stage="local_api",
                status_code=status_code,
                exception_type=exception_type,
                request_method=scope.get("method"),
                request_path=scope.get("path"),
            )
            return
        await _json_response(
            content,
            status_code=status_code,
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


def _declared_content_length(scope: Scope) -> int | None:
    """Read Content-Length from the raw ASGI scope headers."""
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name.lower() != b"content-length":
            continue
        if not raw_value.isdigit():
            # Signs, spaces and junk are not a usable declaration; fall
            # back to counting the streamed body instead.
            return None
        try:
            return int(raw_value)
        except ValueError:
            # Absurdly long digit runs exceed CPython's int() limit.
            return None
    return None


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
