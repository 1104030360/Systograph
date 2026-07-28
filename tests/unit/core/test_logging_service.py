from __future__ import annotations

import logging
from typing import Protocol, cast

from kai_mind.core.services.logging_service import safe_log_event


class StructuredLogRecord(Protocol):
    event_data: object


class RecordingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_structured_log_masks_url_credentials() -> None:
    raw_url = "postgresql://demo:synthetic-pass-138@db.example:5432/app"
    logger = logging.getLogger("test.secret-masking")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = RecordingHandler()
    logger.addHandler(handler)

    try:
        safe_log_event(
            logger,
            logging.ERROR,
            "provider_failed",
            error=f"Could not connect to {raw_url}",
            context={"database_url": raw_url},
        )
    finally:
        logger.removeHandler(handler)

    assert len(handler.records) == 1
    record = cast(StructuredLogRecord, handler.records[0])
    event_data = str(record.event_data)
    assert raw_url not in event_data
    assert "synthetic-pass-138" not in event_data
    assert "[MASKED]" in event_data


def test_exc_info_is_rendered_as_masked_text_not_raw_exception() -> None:
    """例外只以遮罩過的文字進 log；raw exc_info 永遠不轉給 logging。"""
    logger = logging.getLogger("test.exc-info-channel")
    logger.setLevel(logging.ERROR)
    logger.propagate = False
    handler = RecordingHandler()
    logger.addHandler(handler)
    secret = "sk-live-secret-value"
    local_path = "/Users/linjunting/Local_AI_Health_Doctor/.env"

    try:
        try:
            raise RuntimeError(
                f"failed at {local_path} with OPENAI_API_KEY={secret}"
            )
        except RuntimeError as exc:
            safe_log_event(
                logger,
                logging.ERROR,
                "provider_failed",
                stage="unit",
                exc_info=exc,
            )
    finally:
        logger.removeHandler(handler)

    assert len(handler.records) == 1
    record = handler.records[0]
    # raw 例外物件不進 record：pytest 會把它展開進 failure report。
    assert record.exc_info is None
    message = record.getMessage()
    assert message.startswith("provider_failed\n")
    assert "Traceback (most recent call last)" in message
    assert "RuntimeError" in message
    assert secret not in message
    assert local_path not in message
    assert "<LOCAL_PATH>/.env" in message
    # exc_info 仍不可以被 **fields 吸進 event_data。
    event_data = cast(StructuredLogRecord, record).event_data
    assert event_data == {"event": "provider_failed", "stage": "unit"}
