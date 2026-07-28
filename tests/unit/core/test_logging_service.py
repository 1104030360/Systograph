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


def test_exc_info_reaches_logging_without_entering_event_data() -> None:
    """exc_info 是獨立通道，不可以被 **fields 吸進 event_data。"""
    logger = logging.getLogger("test.exc-info-channel")
    logger.setLevel(logging.ERROR)
    logger.propagate = False
    handler = RecordingHandler()
    logger.addHandler(handler)
    failure = RuntimeError("provider exploded")

    try:
        safe_log_event(
            logger,
            logging.ERROR,
            "provider_failed",
            stage="unit",
            exc_info=failure,
        )
    finally:
        logger.removeHandler(handler)

    assert len(handler.records) == 1
    assert handler.records[0].exc_info is not None
    assert handler.records[0].exc_info[1] is failure
    event_data = cast(StructuredLogRecord, handler.records[0]).event_data
    assert event_data == {"event": "provider_failed", "stage": "unit"}
