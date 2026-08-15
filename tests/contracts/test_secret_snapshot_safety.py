from __future__ import annotations

from pathlib import Path

import pytest

from systograph.core.providers.filesystem_provider import FilesystemProvider
from systograph.core.services.snapshot_safety_service import (
    SnapshotSafetyError,
    SnapshotSafetyService,
)


def test_snapshot_scanner_rejects_fake_full_secret() -> None:
    scanner = SnapshotSafetyService()

    with pytest.raises(SnapshotSafetyError, match="unmasked_secret"):
        scanner.assert_safe_text(
            '{"OPENAI_API_KEY": "sk-live-secret-value"}',
            source="snapshot.json",
        )


def test_snapshot_scanner_rejects_url_credentials() -> None:
    scanner = SnapshotSafetyService()

    with pytest.raises(SnapshotSafetyError, match="unmasked_secret"):
        scanner.assert_safe_text(
            (
                '{"database_url": '
                '"postgresql://demo:synthetic-pass-138@db.example/app"}'
            ),
            source="snapshot.json",
        )


def test_snapshot_scanner_rejects_workspace_absolute_path() -> None:
    scanner = SnapshotSafetyService(
        workspace_root=Path("/Users/linjunting/Systograph")
    )

    with pytest.raises(SnapshotSafetyError, match="local_path"):
        scanner.assert_safe_text(
            ("map_json_path=/Users/linjunting/Systograph/outputs/map.json"),
            source="snapshot.md",
        )


def test_snapshot_scanner_accepts_masked_secret_and_posix_relative_path() -> (
    None
):
    scanner = SnapshotSafetyService()

    findings = scanner.scan_json_like(
        {
            "file": "src/rag/app.py",
            "api_key": "[MASKED]",
            "message": "OPENAI_API_KEY=[MASKED]",
        },
        source="ai_system_map.json",
    )

    assert findings == []


def test_json_escaped_newline_is_not_a_windows_path() -> None:
    # Given: a captured multi-line value (e.g. a Dockerfile heredoc) whose
    # "as f:" + newline serializes to the JSON text `f:\n` — which must
    # not be mistaken for a Windows drive path.
    payload = {
        "value": (
            'with open("pyproject.toml", "rb") as f:\n'
            "    print(tomllib.load(f))"
        )
    }

    # When/Then: scanning the JSON-like payload finds nothing.
    assert (
        SnapshotSafetyService().scan_json_like(
            payload,
            source="snapshot.json",
        )
        == []
    )


def test_dict_key_containing_local_path_is_detected() -> None:
    # Given: a local absolute path smuggled as a mapping key, which the
    # sanitizer does not rewrite — detection must still fail closed.
    payload = {"/Users/someone/data": "value"}

    # When
    findings = SnapshotSafetyService().scan_json_like(
        payload,
        source="snapshot.json",
    )

    # Then
    assert [item.kind for item in findings] == ["local_path"]


def test_enriched_inventory_snapshot_contains_digest_not_raw_source(
    tmp_path: Path,
) -> None:
    # Given: an eligible source file contains a secret-shaped synthetic value.
    project_root = tmp_path / "project"
    project_root.mkdir()
    raw_source = "API_TOKEN=synthetic-secret-value-123\n"
    (project_root / "settings.py").write_text(raw_source, encoding="utf-8")

    # When: inventory enrichment is serialized for snapshot-safe metadata.
    inventory = FilesystemProvider().build_inventory(project_root)
    payload = [record.model_dump(mode="json") for record in inventory.files]
    serialized = str(payload)

    # Then: only metadata and a digest cross the boundary.
    assert raw_source.strip() not in serialized
    assert "sha256:" in serialized
    assert (
        SnapshotSafetyService().scan_json_like(
            payload,
            source="snapshot.json",
        )
        == []
    )
