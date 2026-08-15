from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from systograph.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
)
from systograph.core.services import ua_sidecar_result_builder
from systograph.core.services.ua_sidecar_result_builder import (
    UnderstandAnythingResultValidator,
)
from systograph.core.services.ua_sidecar_runtime import UaAnalysisError
from systograph.core.services.ua_sidecar_script_models import (
    UaBatchScriptOutput,
    UaImportScriptOutput,
    UaImportScriptStats,
    UaNamedSpan,
    UaStructureScriptOutput,
)


def write_structure(tmp_path: Path, payload: object) -> Path:
    target = tmp_path / "structure-1.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def structure_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "scriptCompleted": True,
        "filesAnalyzed": 1,
        "filesSkipped": [],
        "results": [
            {
                "path": "src/app.py",
                "functions": [{"name": "main", "startLine": 1, "endLine": 5}],
                "callGraph": [
                    {"caller": "main", "callee": "run", "lineNumber": 2}
                ],
            }
        ],
    }
    payload.update(overrides)
    return payload


def test_clean_output_loads_without_warnings(tmp_path: Path) -> None:
    # Given: a structure output that matches the contract exactly.
    target = write_structure(tmp_path, structure_payload())

    # When
    loaded = UnderstandAnythingResultValidator().load_structure(target)

    # Then: the strict fast path applies and nothing is quarantined.
    assert loaded.warnings == ()
    assert loaded.output.results[0].path == "src/app.py"


def test_garbage_entry_is_quarantined_with_warning(tmp_path: Path) -> None:
    # Given: one garbage callGraph entry (a whole source expression
    # captured as the callee) among valid entries.
    payload = structure_payload()
    payload["results"][0]["callGraph"].append(
        {"caller": "main", "callee": "x" * 600, "lineNumber": 3}
    )
    target = write_structure(tmp_path, payload)

    # When
    loaded = UnderstandAnythingResultValidator().load_structure(target)

    # Then: valid entries survive, the garbage entry is dropped, and the
    # drop is recorded loudly instead of failing the whole scan closed.
    row = loaded.output.results[0]
    assert [item.callee for item in row.call_graph] == ["run"]
    assert [item.name for item in row.functions] == ["main"]
    assert len(loaded.warnings) == 1
    assert loaded.warnings[0].stage == "validate-structure"
    assert "callGraph" in loaded.warnings[0].message
    assert "src/app.py" in loaded.warnings[0].message


@pytest.mark.parametrize(
    ("section", "entry"),
    [
        ("endpoints", {"path": "/x", "endLine": 7}),
        ("endpoints", {"path": "/x", "method": "", "line": 1}),
        ("functions", {"name": "f", "startLine": 9, "endLine": 2}),
        ("resources", {"name": "db", "kind": "pg", "endLine": 7}),
        ("services", {"name": "db", "startLine": 3}),
    ],
)
def test_span_garbage_is_quarantined_not_leaked(
    tmp_path: Path,
    section: str,
    entry: dict[str, Any],
) -> None:
    # Given: an entry that satisfies the loose upstream shape but would
    # violate the downstream contract row models (mixed/inverted spans,
    # empty method). It must be caught here, not crash the projection.
    payload = structure_payload()
    payload["results"][0][section] = [entry]
    target = write_structure(tmp_path, payload)

    # When
    loaded = UnderstandAnythingResultValidator().load_structure(target)

    # Then: the entry is quarantined with a warning, like any garbage.
    assert getattr(loaded.output.results[0], section) == ()
    assert len(loaded.warnings) == 1
    assert loaded.warnings[0].stage == "validate-structure"
    assert section in loaded.warnings[0].message


def test_snake_case_call_graph_garbage_is_quarantined(
    tmp_path: Path,
) -> None:
    # Given: the models accept the field-name spelling too, so garbage
    # under "call_graph" must be quarantined exactly like "callGraph".
    payload = structure_payload()
    del payload["results"][0]["callGraph"]
    payload["results"][0]["call_graph"] = [
        {"caller": "main", "callee": "run", "lineNumber": 2},
        {"caller": "main", "callee": "x" * 600, "lineNumber": 3},
    ]
    target = write_structure(tmp_path, payload)

    # When
    loaded = UnderstandAnythingResultValidator().load_structure(target)

    # Then
    row = loaded.output.results[0]
    assert [item.callee for item in row.call_graph] == ["run"]
    assert len(loaded.warnings) == 1
    assert loaded.warnings[0].stage == "validate-structure"


def test_path_violation_stays_fatal(tmp_path: Path) -> None:
    # Given: a result row whose path escapes the approved project root.
    payload = structure_payload()
    payload["results"][0]["path"] = "../escape.py"
    target = write_structure(tmp_path, payload)

    # When/Then: boundary violations are never quarantined.
    with pytest.raises(UaAnalysisError) as excinfo:
        UnderstandAnythingResultValidator().load_structure(target)
    assert excinfo.value.code == "ua_path_not_approved"


def test_envelope_corruption_stays_fatal(tmp_path: Path) -> None:
    # Given: the envelope itself is broken, not an individual entry.
    target = write_structure(tmp_path, structure_payload(results="junk"))

    # When/Then
    with pytest.raises(UaAnalysisError) as excinfo:
        UnderstandAnythingResultValidator().load_structure(target)
    assert excinfo.value.code == "ua_result_invalid"


def test_non_object_json_stays_fatal(tmp_path: Path) -> None:
    # Given: the output parses as JSON but is not an object at all.
    target = write_structure(tmp_path, [1, 2, 3])

    # When/Then
    with pytest.raises(UaAnalysisError) as excinfo:
        UnderstandAnythingResultValidator().load_structure(target)
    assert excinfo.value.code == "ua_result_invalid"


def test_missing_output_stays_fatal(tmp_path: Path) -> None:
    # When/Then: an absent stage output keeps its dedicated error code.
    with pytest.raises(UaAnalysisError) as excinfo:
        UnderstandAnythingResultValidator().load_structure(
            tmp_path / "absent.json"
        )
    assert excinfo.value.code == "ua_output_missing"


def test_projection_contract_error_is_typed_not_raw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a hypothetical parity gap where an entry passes the inbound
    # gate yet fails contract-row construction inside the projection.
    def exploding_projection(*args: object, **kwargs: object) -> object:
        return UaNamedSpan.model_validate({})

    monkeypatch.setattr(
        ua_sidecar_result_builder,
        "project_structure_rows",
        exploding_projection,
    )
    validator = UnderstandAnythingResultValidator()

    # When/Then: the failure surfaces as the typed fail-closed error, not
    # a raw pydantic ValidationError leaking through the service boundary.
    with pytest.raises(UaAnalysisError) as excinfo:
        validator.build(
            inventory=FileInventory(
                source=FileInventorySource.RECURSIVE,
                project_root="/project",
                files=[],
            ),
            import_output=UaImportScriptOutput(
                scriptCompleted=True,
                stats=UaImportScriptStats(
                    filesScanned=0,
                    filesWithImports=0,
                    totalEdges=0,
                ),
                importMap={},
            ),
            batch_output=UaBatchScriptOutput(
                schemaVersion=1,
                algorithm="count-fallback",
                totalFiles=0,
                totalBatches=0,
                batches=(),
            ),
            structure_outputs=(
                (
                    1,
                    UaStructureScriptOutput(
                        scriptCompleted=True,
                        filesAnalyzed=0,
                        filesSkipped=(),
                        results=(),
                    ),
                ),
            ),
            warnings=(),
        )
    assert excinfo.value.code == "ua_result_invalid"
