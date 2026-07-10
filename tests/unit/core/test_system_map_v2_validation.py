"""Unit tests for ai-system-map/v2 runtime validation safety boundaries."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest

from kai_mind.core.services.system_map_v2_validation_service import (
    SystemMapV2ValidationError,
    SystemMapV2ValidationService,
)

FIXTURE_PATH = (
    Path(__file__).parents[2]
    / "fixtures"
    / "ai_system_map"
    / "v2"
    / "non_grounded_llm_app.v2.json"
)


@pytest.fixture
def minimal_v2() -> dict[str, Any]:
    return cast(
        "dict[str, Any]",
        json.loads(FIXTURE_PATH.read_text(encoding="utf-8")),
    )


def test_rejects_absolute_evidence_path(minimal_v2: dict[str, Any]) -> None:
    data = copy.deepcopy(minimal_v2)
    data["evidence"][0]["location"]["path"] = "/Users/demo/app/main.py"

    with pytest.raises(
        SystemMapV2ValidationError,
        match="project-relative POSIX",
    ):
        SystemMapV2ValidationService().validate(data)


def test_rejects_absolute_project_root_path(
    minimal_v2: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_v2)
    data["project"]["root_path"] = "/Users/demo/plain-llm-app"

    with pytest.raises(
        SystemMapV2ValidationError,
        match="root_path",
    ):
        SystemMapV2ValidationService().validate(data)


def test_rejects_unmasked_secret_in_evidence_extract(
    minimal_v2: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_v2)
    data["evidence"][0]["extract_summary"] = "sk-live-secret-value"

    with pytest.raises(SystemMapV2ValidationError, match="Unmasked secret"):
        SystemMapV2ValidationService().validate(data)


def test_rejects_endpoint_with_url_credentials(
    minimal_v2: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_v2)
    raw_url = "postgresql://demo:synthetic-pass-138@db.example:5432/app"
    data["endpoints"][0]["value"] = raw_url

    with pytest.raises(SystemMapV2ValidationError) as exc_info:
        SystemMapV2ValidationService().validate(data)

    message = str(exc_info.value)
    assert "Unmasked secret" in message
    assert raw_url not in message
    assert "synthetic-pass-138" not in message


def test_rejects_observed_edge_without_evidence(
    minimal_v2: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_v2)
    data["edges"][0]["evidence_ids"] = []

    with pytest.raises(
        SystemMapV2ValidationError,
        match="observed edge requires evidence",
    ):
        SystemMapV2ValidationService().validate(data)


def test_rejects_detected_edge_without_evidence(
    minimal_v2: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_v2)
    data["edges"][0]["status"] = "detected"
    data["edges"][0]["evidence_ids"] = []

    with pytest.raises(
        SystemMapV2ValidationError,
        match="detected edge requires evidence",
    ):
        SystemMapV2ValidationService().validate(data)


def test_accepts_undetermined_edge_without_evidence(
    minimal_v2: dict[str, Any],
) -> None:
    data = copy.deepcopy(minimal_v2)
    data["edges"][0]["status"] = "undetermined"
    data["edges"][0]["evidence_ids"] = []
    data["edges"][0]["undetermined_reason"] = "edge_endpoint_unresolved"

    SystemMapV2ValidationService().validate(data)
