"""Small structured logging helpers with masking and path redaction."""

from __future__ import annotations

import logging
import traceback
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from kai_mind.core.services.path_safety_service import redact_local_paths
from kai_mind.core.services.secret_masking_service import SecretMaskingService


def safe_log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    workspace_root: Path | None = None,
    masking_service: SecretMaskingService | None = None,
    exc_info: BaseException | None = None,
    **fields: Any,
) -> None:
    """Emit a structured log event without raw secrets or local paths.

    政策（唯一一條，適用所有呼叫端）：**例外細節只以遮罩過的文字進 log，
    永遠不以 raw exc_info 進。** logging 自己的 traceback 格式化不經過遮罩，
    而它的輸出會流進預設 stream、pytest 的 failure report 與 CI/PR 頻道，
    等於把 `str(exc)` 裡的 secret 與 traceback 的絕對路徑一起外送。

    所以這個 `exc_info` 參數收到的例外會在這裡被 render 成字串、跑過
    `mask_text` + `redact_local_paths`，再接到 message 後面（欄位放
    `extra["event_data"]`，預設 Formatter 不印，所以 message 是唯一能讓
    預設設定看到例外類別與 file/line 的通道）。`record.exc_info` 一律是
    None，呼叫端不需要、也不應該自己先遮罩。
    """

    service = masking_service or SecretMaskingService()
    event_data = {
        "event": event,
        **{
            key: _safe_log_value(
                value,
                workspace_root=workspace_root,
                masking_service=service,
            )
            for key, value in fields.items()
        },
    }
    message = event
    if exc_info is not None:
        rendered = _masked_traceback(
            exc_info,
            workspace_root=workspace_root,
            masking_service=service,
        )
        message = f"{event}\n{rendered}"
    logger.log(level, message, extra={"event_data": event_data})


def _masked_traceback(
    exc: BaseException,
    *,
    workspace_root: Path | None,
    masking_service: SecretMaskingService,
) -> str:
    """Render a traceback as text with secrets and local paths removed."""

    rendered = "".join(traceback.format_exception(exc))
    return redact_local_paths(
        masking_service.mask_text(rendered),
        workspace_root=workspace_root,
    )


def _safe_log_value(
    value: Any,
    *,
    workspace_root: Path | None,
    masking_service: SecretMaskingService,
) -> Any:
    masked = masking_service.mask_json_like(value)
    return _redact_value(masked, workspace_root=workspace_root)


def _redact_value(value: Any, *, workspace_root: Path | None) -> Any:
    if isinstance(value, str):
        return redact_local_paths(value, workspace_root=workspace_root)

    if isinstance(value, Mapping):
        return {
            key: _redact_value(child, workspace_root=workspace_root)
            for key, child in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(
        value,
        bytes | bytearray,
    ):
        return [
            _redact_value(child, workspace_root=workspace_root)
            for child in value
        ]

    return value
