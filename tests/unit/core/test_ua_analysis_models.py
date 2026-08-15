from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from systograph.core.models.analysis_history import ScanSnapshot
from systograph.core.models.scan import ParseIssue, ProjectScanResult
from systograph.core.models.ua_analysis import (
    UaAnalysisRequest,
    UaAnalysisResult,
    UaCallRow,
    UaEndpointRow,
    UaImportRow,
    UaResourceRow,
    UaSymbolRow,
)


def _request_payload() -> dict[str, object]:
    return {
        "schema_version": "systograph-ua-request/v1",
        "project_root": "/workspace/demo",
        "inventory_digest": "sha256:" + "a" * 64,
        "work_dir": {
            "location": "system_temporary_directory",
            "cleanup": "after_analysis",
        },
        "files": [
            {
                "path": "src/app.py",
                "language": "python",
                "size_lines": 8,
                "file_category": "code",
                "digest": "sha256:" + "b" * 64,
            }
        ],
    }


def _result_payload() -> dict[str, object]:
    return {
        "schema_version": "systograph-ua-result/v1",
        "status": "completed",
        "structural": {
            "imports": [
                {
                    "source_file": "src/app.py",
                    "target_file": "src/service.py",
                }
            ],
            "symbols": [
                {
                    "file": "src/app.py",
                    "name": "main",
                    "kind": "function",
                    "line_start": 3,
                    "line_end": 7,
                }
            ],
            "calls": [
                {
                    "file": "src/app.py",
                    "caller": "main",
                    "callee": "serve",
                    "line_number": 6,
                }
            ],
            "resources": [
                {
                    "file": "infra/main.tf",
                    "name": "aws_s3_bucket.main",
                    "kind": "aws_s3_bucket",
                    "line_start": 1,
                    "line_end": 5,
                }
            ],
            "endpoints": [
                {
                    "file": "src/app.py",
                    "method": "GET",
                    "path": "/health",
                    "line_start": 9,
                    "line_end": 11,
                }
            ],
        },
        "semantic": None,
        "warnings": [
            {"stage": "compute_batches", "message": "neighbor list truncated"}
        ],
        "stats": {
            "filesScanned": 2,
            "filesWithImports": 1,
            "totalEdges": 0,
            "totalBatches": 1,
            "algorithm": "louvain",
            "filesAnalyzed": 2,
            "batchCompletion": [
                {
                    "batchIndex": 1,
                    "scriptCompleted": True,
                    "outputPresent": True,
                    "filesAnalyzed": 2,
                }
            ],
        },
        "extra": {"vendor_note": {"version": 1}},
    }


def test_request_accepts_only_absolute_root_and_project_relative_files() -> (
    None
):
    # Given: the local sidecar request has one allowlisted relative file.
    payload = _request_payload()

    # When: the typed contract validates and serializes the request.
    request = UaAnalysisRequest.model_validate(payload)
    serialized = request.model_dump(mode="json")

    # Then: safe work-dir policy and content binding stay explicit.
    assert serialized == payload
    assert request.files[0].path == "src/app.py"


@pytest.mark.parametrize(
    "unsafe_path",
    ["/tmp/app.py", "../app.py", r"C:\repo\app.py", r"src\app.py"],
)
def test_request_rejects_non_relative_or_non_posix_file_paths(
    unsafe_path: str,
) -> None:
    # Given: a request file escapes or bypasses the POSIX allowlist spelling.
    payload = _request_payload()
    files = payload["files"]
    assert isinstance(files, list)
    file_payload = files[0]
    assert isinstance(file_payload, dict)
    file_payload["path"] = unsafe_path

    # When / Then: validation fails closed at the request boundary.
    with pytest.raises(ValidationError, match="project-relative POSIX"):
        UaAnalysisRequest.model_validate(payload)


def test_request_rejects_unknown_file_fields() -> None:
    # Given: raw source attempts to enter an allowlisted file row.
    payload = _request_payload()
    files = payload["files"]
    assert isinstance(files, list)
    file_payload = files[0]
    assert isinstance(file_payload, dict)
    file_payload["raw_source"] = "print('not allowed')"

    # When / Then: the request contract rejects the untyped side channel.
    with pytest.raises(
        ValidationError, match="Extra inputs are not permitted"
    ):
        UaAnalysisRequest.model_validate(payload)


def test_result_preserves_typed_structural_rows_and_legal_zero_edges() -> None:
    # Given: deterministic structural output with zero internal import edges.
    payload = _result_payload()

    # When: the result wrapper validates.
    result = UaAnalysisResult.model_validate(payload)

    # Then: rows stay typed, semantic stays deferred, and zero is legal.
    assert isinstance(result.structural.imports[0], UaImportRow)
    assert isinstance(result.structural.symbols[0], UaSymbolRow)
    assert isinstance(result.structural.calls[0], UaCallRow)
    assert isinstance(result.structural.resources[0], UaResourceRow)
    assert isinstance(result.structural.endpoints[0], UaEndpointRow)
    assert result.stats.total_edges == 0
    assert result.semantic is None
    assert result.extra == {"vendor_note": {"version": 1}}
    assert result.model_dump(mode="json") == payload


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("root", "raw_source", "print('secret')"),
        ("structural", "plane_id", "plane:rag"),
        ("structural", "confidence", 0.99),
        ("stats", "runtime_truth", True),
    ],
)
def test_result_rejects_untyped_or_conclusion_fields(
    section: str,
    field: str,
    value: object,
) -> None:
    # Given: data attempts to enter outside the sole open `extra` object.
    payload = _result_payload()
    target = payload if section == "root" else payload[section]
    assert isinstance(target, dict)
    target[field] = value

    # When / Then: every typed layer rejects unknown fields.
    with pytest.raises(
        ValidationError, match="Extra inputs are not permitted"
    ):
        UaAnalysisResult.model_validate(payload)


def test_result_rejects_absolute_structural_path_and_invalid_line_range() -> (
    None
):
    # Given: one endpoint escapes inventory and reverses its line range.
    payload = _result_payload()
    structural = payload["structural"]
    assert isinstance(structural, dict)
    endpoints = structural["endpoints"]
    assert isinstance(endpoints, list)
    endpoint = endpoints[0]
    assert isinstance(endpoint, dict)
    endpoint.update(
        {"file": "/Users/demo/app.py", "line_start": 12, "line_end": 4}
    )

    # When / Then: both unsafe shapes are rejected by typed core validation.
    with pytest.raises(ValidationError):
        UaAnalysisResult.model_validate(payload)


def test_symbol_rows_require_a_direct_line_range() -> None:
    # Given: UA emits a symbol without the required direct evidence range.
    payload = _result_payload()
    structural = payload["structural"]
    assert isinstance(structural, dict)
    symbols = structural["symbols"]
    assert isinstance(symbols, list)
    symbol = symbols[0]
    assert isinstance(symbol, dict)
    symbol.pop("line_start")
    symbol.pop("line_end")

    # When / Then: the typed result rejects the ungrounded symbol.
    with pytest.raises(ValidationError, match="Field required"):
        UaAnalysisResult.model_validate(payload)


def test_result_models_are_frozen() -> None:
    # Given: a validated sidecar result.
    result = UaAnalysisResult.model_validate(_result_payload())

    # When / Then: callers cannot replace contract fields after validation.
    field_name = "status"
    with pytest.raises(ValidationError, match="frozen"):
        setattr(result, field_name, "completed")


def test_scan_snapshot_round_trips_typed_nullable_ua_result() -> None:
    # Given: a snapshot with the optional typed UA wrapper populated.
    snapshot = ScanSnapshot(
        project_id="project:demo",
        scan_id="scan:s1",
        generated_at=datetime(2026, 8, 11, tzinfo=UTC),
        inventory_digest="sha256:inventory",
        scan_result=ProjectScanResult(files_scanned=2),
        ua_analysis_result=UaAnalysisResult.model_validate(_result_payload()),
    )

    # When: the snapshot crosses its JSON persistence boundary.
    restored = ScanSnapshot.model_validate_json(snapshot.model_dump_json())

    # Then: the slot remains typed rather than becoming an open dictionary.
    assert isinstance(restored.ua_analysis_result, UaAnalysisResult)
    assert restored.ua_analysis_result.stats.total_edges == 0


def test_scan_snapshot_keeps_ua_result_nullable() -> None:
    # Given / When: an initial or Apply snapshot does not run UA.
    snapshot = ScanSnapshot(
        project_id="project:demo",
        scan_id="scan:s1",
        generated_at=datetime(2026, 8, 11, tzinfo=UTC),
        inventory_digest="sha256:inventory",
        scan_result=ProjectScanResult(files_scanned=0),
    )

    # Then: the reserved integration slot remains explicitly nullable.
    assert snapshot.ua_analysis_result is None


def test_parse_issue_accepts_the_ua_structural_scan_stage() -> None:
    # Given / When: a structured UA warning becomes a scanner issue.
    issue = ParseIssue(
        provider="UnderstandAnythingAnalysisService",
        scan_stage="ua_structural_scan",
        file="$ua-sidecar",
        message="neighbor list truncated",
        rule_id="ua_warning",
    )

    # Then: the dedicated stage survives typed validation.
    assert issue.scan_stage == "ua_structural_scan"
