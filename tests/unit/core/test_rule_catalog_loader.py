from __future__ import annotations

from pathlib import Path

import pytest

from kai_mind.core.services.rule_catalog_loader import (
    RuleCatalogError,
    RuleCatalogLoader,
)


def write_catalog(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_dependency_rules_from_valid_catalog(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "\n".join(
            [
                "[[python]]",
                'package = "langchain"',
                'rule_id = "dependency_rag_framework_langchain"',
                "match_prefix = true",
                "",
                "[[node]]",
                'package = "@langchain/"',
                'rule_id = "dependency_rag_framework_langchain"',
                "match_prefix = true",
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_dependency_rules(catalog_path)

    assert [rule.package for rule in rules.python] == ["langchain"]
    assert rules.python[0].match_prefix is True
    assert [rule.package for rule in rules.node] == ["@langchain/"]


def test_dependency_catalog_rejects_missing_required_field(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "\n".join(
            [
                "[[python]]",
                'package = "openai"',
                "match_prefix = false",
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="rule_id"):
        RuleCatalogLoader().load_dependency_rules(catalog_path)


def test_dependency_catalog_rejects_duplicate_package(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "\n".join(
            [
                "[[python]]",
                'package = "openai"',
                'rule_id = "dependency_external_llm_embedding_openai"',
                "match_prefix = false",
                "",
                "[[python]]",
                'package = "openai"',
                'rule_id = "dependency_duplicate_openai"',
                "match_prefix = false",
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate package"):
        RuleCatalogLoader().load_dependency_rules(catalog_path)


def test_dependency_catalog_requires_explicit_prefix_match(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "\n".join(
            [
                "[[python]]",
                'package = "openai"',
                'rule_id = "dependency_external_llm_embedding_openai"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="match_prefix"):
        RuleCatalogLoader().load_dependency_rules(catalog_path)


def test_load_docker_image_rules_from_valid_catalog(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "docker_image_rules.toml",
        "\n".join(
            [
                "[[images]]",
                'repository = "qdrant/qdrant"',
                'rule_id = "docker_qdrant_image_detected"',
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_docker_image_rules(catalog_path)

    assert rules[0].repository == "qdrant/qdrant"
    assert rules[0].rule_id == "docker_qdrant_image_detected"


def test_docker_image_catalog_rejects_duplicate_repository(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "docker_image_rules.toml",
        "\n".join(
            [
                "[[images]]",
                'repository = "ollama/ollama"',
                'rule_id = "docker_ollama_image_detected"',
                "",
                "[[images]]",
                'repository = "ollama/ollama"',
                'rule_id = "docker_duplicate_ollama"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate repository"):
        RuleCatalogLoader().load_docker_image_rules(catalog_path)


def test_docker_image_catalog_rejects_duplicate_rule_id(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "docker_image_rules.toml",
        "\n".join(
            [
                "[[images]]",
                'repository = "ollama/ollama"',
                'rule_id = "docker_shared"',
                "",
                "[[images]]",
                'repository = "qdrant/qdrant"',
                'rule_id = "docker_shared"',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate rule_id"):
        RuleCatalogLoader().load_docker_image_rules(catalog_path)


def test_load_code_pattern_rules_from_valid_catalog(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_custom_qdrant"',
                'kind = "vector_store_client"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "\\\\bQdrantClient\\\\b"',
                'snippet_group = ""',
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_code_pattern_rules(catalog_path)

    assert rules[0].rule_id == "code_custom_qdrant"
    assert rules[0].regex.search("QdrantClient")
    assert rules[0].snippet_group == ""


def test_code_pattern_catalog_rejects_regex_compile_failure(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "code_pattern_rules.toml",
        "\n".join(
            [
                "[[patterns]]",
                'rule_id = "code_broken"',
                'kind = "code_pattern"',
                'languages = ["python"]',
                'extensions = [".py"]',
                'regex = "["',
                'snippet_group = ""',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="regex"):
        RuleCatalogLoader().load_code_pattern_rules(catalog_path)


def test_catalog_loader_rejects_malformed_toml(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "dependency_rules.toml",
        "[[python]\n",
    )

    with pytest.raises(RuleCatalogError, match="Failed to parse"):
        RuleCatalogLoader().load_dependency_rules(catalog_path)
