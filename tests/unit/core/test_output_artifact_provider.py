from __future__ import annotations

import json
from pathlib import Path

import pytest

from systograph.core.models.scan import OutputRun
from systograph.core.models.system_map import RagSystemMap
from systograph.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from systograph.core.services.system_map_validation_service import (
    SystemMapValidationService,
)


def test_write_json_writes_validated_ai_system_map_artifact(
    tmp_path: Path,
) -> None:
    system_map = SystemMapValidationService().validate(
        json.loads(
            Path(
                "tests/fixtures/ai_system_map/valid_minimal.v1.json"
            ).read_text(encoding="utf-8")
        )
    )
    provider = OutputArtifactProvider()

    artifact_path = provider.write_json(
        system_map,
        output_run=OutputRun(root_dir=tmp_path),
    )

    assert artifact_path == tmp_path / "ai_system_map.json"
    written = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert RagSystemMap.model_validate(written).schema_version == (
        "ai-system-map/v1"
    )
    assert "viewer_load_result" not in written
    assert "graph_view_model" not in written


def test_write_markdown_writes_summary_artifact(tmp_path: Path) -> None:
    provider = OutputArtifactProvider()

    artifact_path = provider.write_markdown(
        "# Systograph System Map\n",
        output_run=OutputRun(root_dir=tmp_path),
    )

    assert artifact_path == tmp_path / "ai_system_map.md"
    assert artifact_path.read_text(encoding="utf-8") == (
        "# Systograph System Map\n"
    )


def test_output_run_exposes_phase2_sibling_paths(tmp_path: Path) -> None:
    output_run = OutputRun(root_dir=tmp_path)

    assert output_run.profile_signals_path == tmp_path / "profile_signals.json"
    assert (
        output_run.readiness_report_path == tmp_path / "readiness_report.json"
    )
    assert output_run.system_map_mermaid_path == tmp_path / "system_map.mmd"


def test_profile_sidecar_collision_creates_timestamped_run(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "profile_signals.json").write_text("{}", encoding="utf-8")

    run = OutputArtifactProvider().prepare_output_run(output_dir)

    assert run.root_dir != output_dir
    assert run.root_dir.parent == output_dir


def test_public_map_writers_use_atomic_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    system_map = SystemMapValidationService().validate(
        json.loads(
            Path(
                "tests/fixtures/ai_system_map/valid_minimal.v1.json"
            ).read_text(encoding="utf-8")
        )
    )

    def reject_direct_write(
        _path: Path,
        _data: str,
        *args: object,
        **kwargs: object,
    ) -> int:
        raise AssertionError("public artifact used Path.write_text directly")

    monkeypatch.setattr(Path, "write_text", reject_direct_write)
    provider = OutputArtifactProvider()
    output_run = OutputRun(root_dir=tmp_path)

    provider.write_json(system_map, output_run=output_run)
    provider.write_markdown("# Summary\n", output_run=output_run)

    assert output_run.map_json_path.is_file()
    assert output_run.map_markdown_path.is_file()
