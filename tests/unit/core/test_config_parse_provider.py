from __future__ import annotations

import json
from pathlib import Path

import pytest

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
)
from kai_mind.core.providers.config_parse_provider import ConfigParseProvider
from kai_mind.core.services.secret_masking_service import SecretMaskingService


def build_inventory(project_root: Path, *paths: str) -> FileInventory:
    return FileInventory(
        source=FileInventorySource.RECURSIVE,
        project_root=str(project_root),
        files=[
            FileRecord(
                path=path,
                size_bytes=(project_root / path).stat().st_size,
            )
            for path in paths
        ],
    )


def test_collect_masks_env_values_and_skips_non_config_yaml_names(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    env_file = project_root / ".env"
    env_file.write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=sk-test-example",
                "OPENAI_BASE_URL=https://api.openai.example/v1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    compose_file = project_root / "docker-compose.yml"
    compose_file.write_text(
        "services:\n  app:\n    image: demo\n",
        encoding="utf-8",
    )
    inventory = build_inventory(
        project_root,
        ".env",
        "docker-compose.yml",
    )

    result = ConfigParseProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    evidence_by_path = {
        evidence.path: evidence for evidence in result.evidence
    }
    masker = SecretMaskingService()
    assert set(fact_by_path) == {"OPENAI_API_KEY", "OPENAI_BASE_URL"}
    assert fact_by_path["OPENAI_API_KEY"].value == masker.mask_value(
        "sk-test-example",
        key="OPENAI_API_KEY",
    )
    assert (
        fact_by_path["OPENAI_BASE_URL"].value
        == "https://api.openai.example/v1"
    )
    assert all(fact.file == ".env" for fact in result.facts)
    assert all(evidence.file == ".env" for evidence in result.evidence)
    assert evidence_by_path["OPENAI_API_KEY"].kind == "config_value"
    assert not result.issues


@pytest.mark.parametrize(
    ("relative_path", "contents", "expected_path", "expected_value"),
    [
        (
            "config.json",
            json.dumps(
                {
                    "providers": {
                        "llm": {
                            "provider": "openai-compatible",
                            "base_url": "https://api.openai.example/v1",
                        }
                    }
                }
            ),
            "providers.llm.base_url",
            "https://api.openai.example/v1",
        ),
        (
            "config.yaml",
            "\n".join(
                [
                    "providers:",
                    "  embedding:",
                    "    provider: openai",
                    "    model: text-embedding-3-small",
                ]
            )
            + "\n",
            "providers.embedding.model",
            "text-embedding-3-small",
        ),
        (
            "pyproject.toml",
            "\n".join(
                [
                    "[tool.kai_mind]",
                    'default_model = "gpt-4o-mini"',
                ]
            )
            + "\n",
            "tool.kai_mind.default_model",
            "gpt-4o-mini",
        ),
    ],
)
def test_collect_flattens_json_yaml_and_toml_scalars(
    tmp_path: Path,
    relative_path: str,
    contents: str,
    expected_path: str,
    expected_value: str,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / relative_path
    target_file.write_text(contents, encoding="utf-8")
    inventory = build_inventory(project_root, relative_path)

    result = ConfigParseProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    evidence_by_path = {
        evidence.path: evidence for evidence in result.evidence
    }
    assert fact_by_path[expected_path].value == expected_value
    assert evidence_by_path[expected_path].rule_id is not None
    assert not result.issues


@pytest.mark.parametrize(
    ("relative_path", "contents"),
    [
        (
            "config.json",
            json.dumps(
                {
                    "environment": [
                        {
                            "key": "PASSWORD",
                            "value": "correct horse battery staple",
                        }
                    ]
                }
            ),
        ),
        (
            "config.yaml",
            "\n".join(
                [
                    "environment:",
                    "  - key: PASSWORD",
                    "    value: correct horse battery staple",
                ]
            )
            + "\n",
        ),
    ],
)
def test_collect_masks_structured_key_value_secret_entries(
    tmp_path: Path,
    relative_path: str,
    contents: str,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    target_file = project_root / relative_path
    target_file.write_text(contents, encoding="utf-8")
    inventory = build_inventory(project_root, relative_path)

    result = ConfigParseProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    expected_masked_value = SecretMaskingService().mask_value(
        "correct horse battery staple",
        key="PASSWORD",
    )
    assert fact_by_path["environment[0].key"].value == "PASSWORD"
    assert fact_by_path["environment[0].value"].value == expected_masked_value
    assert "correct horse battery staple" not in {
        fact.value for fact in result.facts
    }
    assert "correct horse battery staple" not in {
        evidence.value for evidence in result.evidence
    }


def test_collect_keeps_other_files_when_json_is_malformed_and_reports_issue(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "broken.json").write_text(
        '{"providers": {"llm": }',
        encoding="utf-8",
    )
    (project_root / "config.yaml").write_text(
        "providers:\n  llm:\n    provider: ollama\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "broken.json", "config.yaml")

    result = ConfigParseProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    assert fact_by_path["providers.llm.provider"].value == "ollama"
    assert len(result.issues) == 1
    assert result.issues[0].file == "broken.json"
    assert result.issues[0].scan_stage == "config_parse"
    parse_error_evidence = [
        evidence
        for evidence in result.evidence
        if evidence.kind == "parse_error"
    ]
    assert len(parse_error_evidence) == 1
    assert parse_error_evidence[0].file == "broken.json"
    assert parse_error_evidence[0].rule_id == "config_parse_error"


def test_collect_reports_env_line_errors_without_leaking_secret_values(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".env").write_text(
        "\n".join(
            [
                "OPENAI_API_KEY=sk-test-example",
                "BROKEN LINE sk-very-secret",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, ".env")

    result = ConfigParseProvider().collect(inventory)

    assert len(result.issues) == 1
    assert "sk-very-secret" not in result.issues[0].message
    assert "sk-very-secret" not in (result.evidence[-1].value or "")
    fact_by_path = {fact.path: fact for fact in result.facts}
    assert fact_by_path["OPENAI_API_KEY"].value != "sk-test-example"


def test_collect_returns_empty_result_for_empty_config_file(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "config.yaml").write_text("", encoding="utf-8")
    inventory = build_inventory(project_root, "config.yaml")

    result = ConfigParseProvider().collect(inventory)

    assert result.facts == []
    assert result.evidence == []
    assert result.issues == []
