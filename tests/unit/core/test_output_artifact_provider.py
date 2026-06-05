from __future__ import annotations

import json
from pathlib import Path

from kai_mind.core.models.scan import OutputRun
from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.providers.output_artifact_provider import (
    OutputArtifactProvider,
)
from kai_mind.core.services.system_map_validation_service import (
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
        "# KAI-Mind System Map\n",
        output_run=OutputRun(root_dir=tmp_path),
    )

    assert artifact_path == tmp_path / "ai_system_map.md"
    assert artifact_path.read_text(encoding="utf-8") == (
        "# KAI-Mind System Map\n"
    )
