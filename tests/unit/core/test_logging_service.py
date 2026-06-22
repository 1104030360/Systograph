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
