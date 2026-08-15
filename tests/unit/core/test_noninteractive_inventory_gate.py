from __future__ import annotations

from pathlib import Path

import pytest

from systograph.core.models.errors import (
    InventorySelectionError,
    InventorySelectionErrorCode,
)
from systograph.core.services.noninteractive_inventory_gate import (
    NonInteractiveInventoryGate,
)


def test_default_policy_materializes_inventory_without_prompt(
    tmp_path: Path,
) -> None:
    # Given: a project whose default policy needs no operator decision.
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "app.py").write_text("print('ok')\n", encoding="utf-8")

    # When: the CLI-style noninteractive gate runs.
    result = NonInteractiveInventoryGate().select(
        project_id="project:cli",
        project_root=project_root,
    )

    # Then: the final allowlist is enriched for deterministic providers.
    assert [item.path for item in result.files] == ["app.py"]
    assert result.files[0].language == "python"
    assert result.files[0].size_lines == 1
    assert result.final_inventory_digest is not None


def test_required_review_fails_closed_and_points_to_web_flow(
    tmp_path: Path,
) -> None:
    # Given: a sensitive file whose policy requires an operator decision.
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text("TOKEN=fixture\n", encoding="utf-8")

    # When/Then: noninteractive selection refuses to guess.
    with pytest.raises(InventorySelectionError) as exc_info:
        NonInteractiveInventoryGate().select(
            project_id="project:cli",
            project_root=project_root,
        )

    assert exc_info.value.code == (
        InventorySelectionErrorCode.NON_INTERACTIVE_REVIEW_REQUIRED
    )
    assert exc_info.value.context == {"resolution": "use_web_review_flow"}
