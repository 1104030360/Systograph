from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, cast


def test_measurement_cli_compares_on_and_off_from_one_snapshot(
    tmp_path: Path,
) -> None:
    # Given
    report_path = tmp_path / "measurement.json"
    command = [
        ".venv/bin/python",
        "scripts/measure_template_flow_retirement.py",
        "--fixtures",
        "basic_qdrant_ollama_rag",
        "--output",
        str(report_path),
    ]

    # When
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Then
    assert completed.returncode == 0, completed.stderr
    report = cast(
        "dict[str, Any]",
        json.loads(report_path.read_text(encoding="utf-8")),
    )
    assert report["schema_version"] == "template-flow-retirement/v1"
    fixture = report["fixtures"][0]
    assert fixture["fixture"] == "basic_qdrant_ollama_rag"
    assert fixture["ua_invocations"] == {
        "filesystem_scan": 1,
        "ua_sidecar": 1,
        "parity_providers": 1,
    }
    assert fixture["off"]["l3_template"] == 0
    # Documented baseline adjustment (2026-08-13): the fixture's only
    # L1 candidate is a mirror-pair ambiguity, discarded instead of
    # catalog-directed, so the honest off-mode count is zero.
    assert fixture["off"]["l1_observed"] == 0
    assert fixture["on"]["l1_observed"] == fixture["off"]["l1_observed"]
    assert fixture["off"]["l1_relationships"] == []
    assert len(fixture["off"]["profile_statuses"]) == 15
    assert fixture["off"]["graph_node_count"] >= 52
