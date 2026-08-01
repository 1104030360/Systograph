from __future__ import annotations

from pathlib import Path

import pytest

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
