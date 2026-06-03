from __future__ import annotations

from pathlib import Path

from kai_mind.core.models.filesystem import (
    FileInventory,
    FileInventorySource,
    FileRecord,
)
from kai_mind.core.providers.dependency_manifest_provider import (
    DependencyManifestProvider,
)


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


def test_collect_reads_dependency_manifests_from_inventory_only(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "qdrant-client==1.12.1\n",
        encoding="utf-8",
    )
    (project_root / "notes.txt").write_text(
        "openai==1.59.7\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "requirements.txt", "notes.txt")

    result = DependencyManifestProvider().collect(inventory)

    assert {fact.file for fact in result.facts} == {"requirements.txt"}
    assert not result.issues


def test_collect_parses_requirements_and_emits_known_rag_candidate_facts(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "\n".join(
            [
                "# comments are ignored",
                "qdrant_client==1.12.1",
                "openai[embeddings]>=1.59; python_version >= '3.11'",
                "langchain~=0.3",
                "requests==2.32.3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "requirements.txt")

    result = DependencyManifestProvider().collect(inventory)

    fact_by_value = {fact.value: fact for fact in result.facts}
    assert fact_by_value["qdrant-client"].kind == "dependency_candidate"
    assert (
        fact_by_value["qdrant-client"].rule_id
        == "dependency_vector_store_client_qdrant"
    )
    assert (
        fact_by_value["openai"].rule_id
        == "dependency_external_llm_embedding_openai"
    )
    assert (
        fact_by_value["langchain"].rule_id
        == "dependency_rag_framework_langchain"
    )
    assert "requests" not in fact_by_value
    assert {evidence.value for evidence in result.evidence} == {
        "qdrant-client",
        "openai",
        "langchain",
    }


def test_collect_parses_pyproject_pep621_and_poetry_dependency_sections(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'dependencies = ["llama-index>=0.12", "chromadb==0.5.0"]',
                "",
                "[project.optional-dependencies]",
                'local = ["ollama>=0.4"]',
                "",
                "[tool.poetry.dependencies]",
                'python = ">=3.11,<4.0"',
                'openai = "^1.59.7"',
                "",
                "[tool.poetry.group.dev.dependencies]",
                'langchain = "^0.3.0"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "pyproject.toml")

    result = DependencyManifestProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    assert (
        fact_by_path["project.dependencies[0]"].rule_id
        == "dependency_rag_framework_llama_index"
    )
    assert (
        fact_by_path["project.dependencies[1]"].rule_id
        == "dependency_vector_store_client_chromadb"
    )
    assert (
        fact_by_path["project.optional-dependencies.local[0]"].rule_id
        == "dependency_local_llm_provider_ollama"
    )
    assert (
        fact_by_path["tool.poetry.dependencies.openai"].rule_id
        == "dependency_external_llm_embedding_openai"
    )
    assert (
        fact_by_path["tool.poetry.group.dev.dependencies.langchain"].rule_id
        == "dependency_rag_framework_langchain"
    )
    assert "python" not in {fact.value for fact in result.facts}


def test_collect_parses_package_json_dependencies_and_dev_dependencies(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "package.json").write_text(
        "\n".join(
            [
                "{",
                '  "dependencies": {',
                '    "langchain": "^0.3.0",',
                '    "@scope/ignored": "1.0.0"',
                "  },",
                '  "devDependencies": {',
                '    "openai": "^4.0.0"',
                "  }",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "package.json")

    result = DependencyManifestProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    assert (
        fact_by_path["dependencies.langchain"].rule_id
        == "dependency_rag_framework_langchain"
    )
    assert (
        fact_by_path["devDependencies.openai"].rule_id
        == "dependency_external_llm_embedding_openai"
    )
    assert "@scope/ignored" not in {fact.value for fact in result.facts}


def test_collect_detects_scoped_langchain_package_json_dependencies(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "package.json").write_text(
        "\n".join(
            [
                "{",
                '  "dependencies": {',
                '    "@langchain/core": "^1.0.0",',
                '    "@langchain/openai": "^1.0.0"',
                "  },",
                '  "devDependencies": {',
                '    "@langchain/community": "^1.0.0"',
                "  }",
                "}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "package.json")

    result = DependencyManifestProvider().collect(inventory)

    fact_by_path = {fact.path: fact for fact in result.facts}
    assert (
        fact_by_path["dependencies.@langchain/core"].rule_id
        == "dependency_rag_framework_langchain"
    )
    assert (
        fact_by_path["dependencies.@langchain/openai"].rule_id
        == "dependency_rag_framework_langchain"
    )
    assert (
        fact_by_path["devDependencies.@langchain/community"].rule_id
        == "dependency_rag_framework_langchain"
    )
    assert {
        fact_by_path["dependencies.@langchain/core"].value,
        fact_by_path["dependencies.@langchain/openai"].value,
        fact_by_path["devDependencies.@langchain/community"].value,
    } == {
        "@langchain/core",
        "@langchain/openai",
        "@langchain/community",
    }


def test_collect_uses_injected_dependency_rule_catalog(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    catalog_path = tmp_path / "dependency_manifest_rules.toml"
    catalog_path.write_text(
        "\n".join(
            [
                "[[python]]",
                'package = "custom-rag"',
                'rule_id = "dependency_custom_rag_detected"',
                "match_prefix = false",
                "",
                "[[node]]",
                'package = "custom-node-rag"',
                'rule_id = "dependency_custom_node_rag_detected"',
                "match_prefix = false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (project_root / "requirements.txt").write_text(
        "custom-rag==1.0.0\nopenai==1.59.7\n",
        encoding="utf-8",
    )
    (project_root / "package.json").write_text(
        '{"dependencies": {"custom-node-rag": "1.0.0", "openai": "4.0.0"}}',
        encoding="utf-8",
    )
    inventory = build_inventory(
        project_root,
        "requirements.txt",
        "package.json",
    )

    result = DependencyManifestProvider(
        rule_catalog_path=catalog_path,
    ).collect(inventory)

    assert {fact.rule_id for fact in result.facts} == {
        "dependency_custom_rag_detected",
        "dependency_custom_node_rag_detected",
    }
    assert "openai" not in {fact.value for fact in result.facts}


def test_collect_keeps_other_manifests_when_one_manifest_is_malformed(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "package.json").write_text(
        '{"dependencies": {"openai": }}',
        encoding="utf-8",
    )
    (project_root / "requirements.txt").write_text(
        "ollama==0.4.2\n",
        encoding="utf-8",
    )
    inventory = build_inventory(
        project_root,
        "package.json",
        "requirements.txt",
    )

    result = DependencyManifestProvider().collect(inventory)

    assert {fact.value for fact in result.facts} == {"ollama"}
    assert len(result.issues) == 1
    assert result.issues[0].provider == "dependency_manifest"
    assert result.issues[0].scan_stage == "dependency_manifest_parse"
    assert result.issues[0].file == "package.json"
    parse_error_evidence = [
        evidence
        for evidence in result.evidence
        if evidence.kind == "parse_error"
    ]
    assert len(parse_error_evidence) == 1
    assert parse_error_evidence[0].file == "package.json"


def test_collect_reports_unsupported_requirements_without_expanding_scope(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "requirements.txt").write_text(
        "\n".join(
            [
                "-r private-requirements.txt",
                "-e git+https://example.invalid/repo.git#egg=openai",
                "git+https://example.invalid/repo.git#egg=qdrant-client",
                "--index-url https://example.invalid/simple",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    inventory = build_inventory(project_root, "requirements.txt")

    result = DependencyManifestProvider().collect(inventory)

    assert result.facts == []
    assert len(result.issues) == 4
    assert all(issue.file == "requirements.txt" for issue in result.issues)
    assert all(
        issue.scan_stage == "dependency_manifest_parse"
        for issue in result.issues
    )
    assert {evidence.kind for evidence in result.evidence} == {"parse_error"}
