"""Small structured logging helpers with masking and path redaction."""

from __future__ import annotations

import logging
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

    exc_info 刻意是 keyword-only、跟 **fields 分開的第二條通道：欄位會
    被遮罩後放進 extra["event_data"]（預設 Formatter 不會印），而 exc_info
    交給 logging 自己的 traceback 格式化，是讓預設設定看得到 file/line 的
    唯一途徑。它不經過遮罩，所以要不要帶由呼叫端自己判斷。
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
    logger.log(
        level,
        event,
        extra={"event_data": event_data},
        exc_info=exc_info,
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
