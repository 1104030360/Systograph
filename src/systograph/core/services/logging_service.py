"""Small structured logging helpers with masking and path redaction."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from systograph.core.services.path_safety_service import redact_local_paths
from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)


def safe_log_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    workspace_root: Path | None = None,
    masking_service: SecretMaskingService | None = None,
    **fields: Any,
) -> None:
    """Emit a structured log event without raw secrets or local paths."""

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
    logger.log(level, event, extra={"event_data": event_data})


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
