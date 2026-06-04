from __future__ import annotations

from pathlib import Path

import pytest

from kai_mind.core.services.rule_catalog_loader import (
    RuleCatalogError,
    RuleCatalogLoader,
)

TASK14_RISK_RULE_IDS = {
    "docker_published_port_exposure",
    "external_provider_detected",
    "config_parse_error",
    "secret_like_config_key_detected",
    "missing_required_slot",
    "chroma_http_endpoint_detected",
    "chroma_local_persistence_detected",
    "chroma_server_published_port",
}
PROVIDER_PARSE_RISK_RULE_IDS = {
    "config_parse_error",
    "docker_compose_parse_error",
    "dependency_manifest_parse_error",
    "code_pattern_read_error",
    "project_scan_provider_failed",
}
RECOMMENDED_NEXT_CHECK_IDS = {
    "runtime_readiness",
    "privacy_exposure",
    "rag_knowledge_trust",
}


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


def test_load_risk_hint_rules_from_valid_catalog(tmp_path: Path) -> None:
    catalog_path = write_catalog(
        tmp_path / "risk_hint_rules.toml",
        "\n".join(
            [
                "[[risk_hints]]",
                'rule_id = "docker_published_port_exposure"',
                'type = "network_exposure"',
                'default_severity_hint = "medium"',
                (
                    'rationale = "Docker published port may expose a '
                    'service endpoint."'
                ),
                (
                    'uncertainty = "Static scan does not verify runtime '
                    'reachability."'
                ),
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_risk_hint_rules(catalog_path)

    assert rules[0].rule_id == "docker_published_port_exposure"
    assert rules[0].type == "network_exposure"
    assert rules[0].default_severity_hint == "medium"
    assert "Docker published port" in rules[0].rationale
    assert "Static scan" in rules[0].uncertainty


def test_risk_hint_catalog_rejects_duplicate_rule_id(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "risk_hint_rules.toml",
        "\n".join(
            [
                "[[risk_hints]]",
                'rule_id = "external_provider_detected"',
                'type = "external_provider"',
                'default_severity_hint = "medium"',
                'rationale = "External provider detected."',
                'uncertainty = "Static scan only."',
                "",
                "[[risk_hints]]",
                'rule_id = "external_provider_detected"',
                'type = "external_provider"',
                'default_severity_hint = "medium"',
                'rationale = "Duplicate external provider detected."',
                'uncertainty = "Static scan only."',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate rule_id"):
        RuleCatalogLoader().load_risk_hint_rules(catalog_path)


@pytest.mark.parametrize("missing_field", ["rationale", "uncertainty"])
def test_risk_hint_catalog_requires_wording_fields(
    tmp_path: Path,
    missing_field: str,
) -> None:
    fields = {
        "rule_id": 'rule_id = "config_parse_error"',
        "type": 'type = "partial_scan"',
        "default_severity_hint": 'default_severity_hint = "medium"',
        "rationale": 'rationale = "Config parse error may make map partial."',
        "uncertainty": 'uncertainty = "Only parsed files produce facts."',
    }
    del fields[missing_field]
    catalog_path = write_catalog(
        tmp_path / "risk_hint_rules.toml",
        "\n".join(["[[risk_hints]]", *fields.values()]) + "\n",
    )

    with pytest.raises(RuleCatalogError, match=missing_field):
        RuleCatalogLoader().load_risk_hint_rules(catalog_path)


def test_default_risk_hint_catalog_covers_task14_rule_ids() -> None:
    rules = RuleCatalogLoader().load_default_risk_hint_rules()

    assert {rule.rule_id for rule in rules} >= TASK14_RISK_RULE_IDS


def test_default_risk_hint_catalog_covers_provider_parse_rule_ids() -> None:
    rules = RuleCatalogLoader().load_default_risk_hint_rules()

    assert {rule.rule_id for rule in rules} >= PROVIDER_PARSE_RISK_RULE_IDS


def test_load_recommended_next_check_rules_from_valid_catalog(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "recommended_next_check_rules.toml",
        "\n".join(
            [
                "[[recommended_next_checks]]",
                'id = "runtime_readiness"',
                'default_target_type = "system"',
                'reason = "Static scan found runtime-dependent services."',
                (
                    'action = "Verify services start and endpoints are '
                    'reachable."'
                ),
            ]
        )
        + "\n",
    )

    rules = RuleCatalogLoader().load_recommended_next_check_rules(catalog_path)

    assert rules[0].id == "runtime_readiness"
    assert rules[0].default_target_type == "system"
    assert "runtime-dependent" in rules[0].reason
    assert "endpoints" in rules[0].action


def test_recommended_next_check_catalog_rejects_duplicate_id(
    tmp_path: Path,
) -> None:
    catalog_path = write_catalog(
        tmp_path / "recommended_next_check_rules.toml",
        "\n".join(
            [
                "[[recommended_next_checks]]",
                'id = "runtime_readiness"',
                'default_target_type = "system"',
                'reason = "Static scan found runtime-dependent services."',
                'action = "Verify services start."',
                "",
                "[[recommended_next_checks]]",
                'id = "runtime_readiness"',
                'default_target_type = "system"',
                'reason = "Duplicate runtime check."',
                'action = "Duplicate action."',
            ]
        )
        + "\n",
    )

    with pytest.raises(RuleCatalogError, match="duplicate id"):
        RuleCatalogLoader().load_recommended_next_check_rules(catalog_path)


@pytest.mark.parametrize("missing_field", ["reason", "action"])
def test_recommended_next_check_catalog_requires_wording_fields(
    tmp_path: Path,
    missing_field: str,
) -> None:
    fields = {
        "id": 'id = "runtime_readiness"',
        "default_target_type": 'default_target_type = "system"',
        "reason": 'reason = "Static scan found runtime services."',
        "action": 'action = "Verify runtime services."',
    }
    del fields[missing_field]
    catalog_path = write_catalog(
        tmp_path / "recommended_next_check_rules.toml",
        "\n".join(["[[recommended_next_checks]]", *fields.values()]) + "\n",
    )

    with pytest.raises(RuleCatalogError, match=missing_field):
        RuleCatalogLoader().load_recommended_next_check_rules(catalog_path)


def test_default_recommended_next_check_catalog_covers_initial_ids() -> None:
    rules = RuleCatalogLoader().load_default_recommended_next_check_rules()

    assert {rule.id for rule in rules} == RECOMMENDED_NEXT_CHECK_IDS
