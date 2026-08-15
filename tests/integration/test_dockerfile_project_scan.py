from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from systograph.cli import main as cli_main

# A trailing-newline Dockerfile triggers both known upstream quirks at
# once: services without "kind" and a last-stage end line one past EOF.
DOCKERFILE = 'FROM python:3.13\nCMD ["python", "app.py"]\n'


def test_project_with_dockerfile_scans_end_to_end(tmp_path: Path) -> None:
    # Given: a minimal project whose Dockerfile used to 503 the scan.
    project_root = tmp_path / "project"
    (project_root / "src").mkdir(parents=True)
    (project_root / "src" / "app.py").write_text(
        "from qdrant_client import QdrantClient\n"
        'client = QdrantClient(url="http://localhost:6333")\n',
        encoding="utf-8",
    )
    (project_root / "requirements.txt").write_text(
        "qdrant-client\n", encoding="utf-8"
    )
    (project_root / "Dockerfile").write_text(DOCKERFILE, encoding="utf-8")
    output = tmp_path / "output"

    # When
    result = CliRunner().invoke(
        cli_main.app,
        [
            "map",
            str(project_root),
            "--output",
            str(output),
            "--state-dir",
            str(tmp_path / "state"),
        ],
        env={"SYSTOGRAPH_TEMPLATE_FLOW_EDGES": "off"},
    )

    # Then: the scan completes and publishes the full artifact set.
    assert result.exit_code == 0, result.stdout
    system_map = cast(
        "dict[str, Any]",
        json.loads(
            (output / "ai_system_map.json").read_text(encoding="utf-8")
        ),
    )
    assert (output / "readiness_report.json").is_file()
    assert (output / "profile_signals.json").is_file()
    dockerfile_evidence = [
        item
        for item in system_map["evidence"]
        if item["location"]["path"] == "Dockerfile"
    ]
    assert dockerfile_evidence
