"""Unit tests for CanonicalMapLoader dual-read boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from systograph.core.models.ai_system_map_v2 import AiSystemMapV2
from systograph.core.services.canonical_map_loader import (
    CanonicalMapLoader,
    CanonicalMapLoadError,
    CanonicalMapLoadResult,
)

V1_FIXTURE = Path(
    "tests/fixtures/ai_system_map/valid_rich_frontend_sample.v1.json"
)
V2_FIXTURE = Path("tests/fixtures/ai_system_map/v2/grounded_rag.v2.json")


def test_loader_adapts_v1_payload_into_normalized_v2_view() -> None:
    payload = json.loads(V1_FIXTURE.read_text(encoding="utf-8"))

    result = CanonicalMapLoader().load(payload)

    assert isinstance(result, CanonicalMapLoadResult)
    assert result.active_schema_version == "ai-system-map/v1"
    assert result.normalized.schema_version == "ai-system-map/v2"
    assert result.normalized.system_type == "ai_system"
    assert result.normalized.source_schema_version == "ai-system-map/v1"
    assert result.migration_warnings
    assert "release_verdict" not in result.normalized.model_dump(mode="json")
    evidence_ids = {item.evidence_id for item in result.normalized.evidence}
    assert evidence_ids == {item["id"] for item in payload["evidence"]}


def test_loader_validates_native_v2_payload_without_adapter() -> None:
    payload = json.loads(V2_FIXTURE.read_text(encoding="utf-8"))

    result = CanonicalMapLoader().load(payload)

    assert result.active_schema_version == "ai-system-map/v2"
    assert result.normalized.source_schema_version in {
        None,
        "ai-system-map/v2",
    }
    assert isinstance(result.normalized, AiSystemMapV2)
    assert result.migration_warnings == []


def test_loader_is_the_only_schema_branch_owner_for_unknown_versions() -> None:
    with pytest.raises(
        CanonicalMapLoadError,
        match="unsupported_system_map_schema_version",
    ):
        CanonicalMapLoader().load(
            {
                "schema_version": "ai-system-map/v9",
                "system_type": "ai_system",
            }
        )


@pytest.mark.parametrize(
    "invalid_json",
    ["[]", "null", '"not-a-map"', "42"],
    ids=["array", "null", "string", "number"],
)
def test_loader_rejects_non_object_json_root(invalid_json: str) -> None:
    payload = json.loads(invalid_json)

    with pytest.raises(
        CanonicalMapLoadError,
        match="canonical map JSON root must be an object",
    ):
        CanonicalMapLoader().load(payload)


def test_loader_rejects_confidence_in_either_schema() -> None:
    payload = json.loads(V2_FIXTURE.read_text(encoding="utf-8"))
    payload["confidence"] = 0.42

    with pytest.raises(CanonicalMapLoadError, match="confidence"):
        CanonicalMapLoader().load(payload)


@pytest.mark.parametrize("missing_field", ["schema_version", "system_type"])
def test_loader_rejects_native_v2_payload_missing_individual_badge(
    missing_field: str,
) -> None:
    payload = json.loads(V2_FIXTURE.read_text(encoding="utf-8"))
    del payload[missing_field]

    with pytest.raises(CanonicalMapLoadError):
        CanonicalMapLoader().load(payload)
