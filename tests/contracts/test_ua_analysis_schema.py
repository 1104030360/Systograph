from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from systograph.core.models.ua_analysis import (
    JSON_SCHEMA_DRAFT,
    UA_REQUEST_SCHEMA_ID,
    UA_RESULT_SCHEMA_ID,
    UaAnalysisRequest,
    UaAnalysisResult,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUEST_SCHEMA_PATH = (
    REPO_ROOT / "schemas/systograph-ua-request.v1.schema.json"
)
RESULT_SCHEMA_PATH = REPO_ROOT / "schemas/systograph-ua-result.v1.schema.json"


def _generated_schema(
    model: type[BaseModel], schema_id: str
) -> dict[str, object]:
    schema: dict[str, object] = model.model_json_schema()
    schema["$schema"] = JSON_SCHEMA_DRAFT
    schema["$id"] = schema_id
    return schema


def _load_schema(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _property_names(value: object) -> set[str]:
    if isinstance(value, dict):
        names: set[str] = set()
        properties = value.get("properties")
        if isinstance(properties, dict):
            names.update(str(name) for name in properties)
        for child in value.values():
            names.update(_property_names(child))
        return names
    if isinstance(value, list):
        nested_names: set[str] = set()
        for child in value:
            nested_names.update(_property_names(child))
        return nested_names
    return set()


def test_checked_in_request_schema_matches_pydantic_contract() -> None:
    assert _load_schema(REQUEST_SCHEMA_PATH) == _generated_schema(
        UaAnalysisRequest,
        UA_REQUEST_SCHEMA_ID,
    )


def test_checked_in_result_schema_matches_pydantic_contract() -> None:
    assert _load_schema(RESULT_SCHEMA_PATH) == _generated_schema(
        UaAnalysisResult,
        UA_RESULT_SCHEMA_ID,
    )


def test_request_schema_forbids_unknown_fields_at_every_typed_layer() -> None:
    schema = _generated_schema(UaAnalysisRequest, UA_REQUEST_SCHEMA_ID)
    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    assert schema["additionalProperties"] is False
    for definition in definitions.values():
        assert isinstance(definition, dict)
        if definition.get("type") == "object":
            assert definition.get("additionalProperties") is False


def test_result_schema_has_typed_stats_and_only_one_open_object() -> None:
    schema = _generated_schema(UaAnalysisResult, UA_RESULT_SCHEMA_ID)
    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    stats = definitions["UaAnalysisStats"]
    assert isinstance(stats, dict)
    assert set(stats["required"]) == {
        "filesScanned",
        "filesWithImports",
        "totalEdges",
        "totalBatches",
        "algorithm",
        "filesAnalyzed",
        "batchCompletion",
    }
    for name, definition in definitions.items():
        if name == "JsonValue":
            continue
        assert isinstance(definition, dict)
        if definition.get("type") == "object":
            assert definition.get("additionalProperties") is False
    extra_schema = schema["properties"]
    assert isinstance(extra_schema, dict)
    extra = extra_schema["extra"]
    assert isinstance(extra, dict)
    assert "additionalProperties" in extra


def test_result_schema_has_no_raw_source_or_inferred_conclusion_fields() -> (
    None
):
    schema = _generated_schema(UaAnalysisResult, UA_RESULT_SCHEMA_ID)
    forbidden = {
        "raw_source",
        "source_code",
        "plane_id",
        "reference_node_id",
        "profile_status",
        "confidence",
        "runtime_truth",
    }

    assert _property_names(schema).isdisjoint(forbidden)
