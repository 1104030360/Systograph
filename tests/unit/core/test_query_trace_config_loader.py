from __future__ import annotations

from pathlib import Path

import pytest

from systograph.core.services.query_trace_config_loader import (
    DEFAULT_RETRIEVED_CHUNKS_KEYS,
    QueryTraceConfigError,
    QueryTraceConfigLoader,
)


def test_query_trace_config_loader_reads_pyproject_tool_section(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.systograph.trace]
retrieved_chunks_keys = ["docs", "retrieved_docs", "context"]
""",
        encoding="utf-8",
    )

    config = QueryTraceConfigLoader().load_project_config(tmp_path)

    assert config.retrieved_chunks_keys == (
        "docs",
        "retrieved_docs",
        "context",
    )


def test_query_trace_config_loader_defaults_when_pyproject_is_missing(
    tmp_path: Path,
) -> None:
    config = QueryTraceConfigLoader().load_project_config(tmp_path)

    assert config.retrieved_chunks_keys == DEFAULT_RETRIEVED_CHUNKS_KEYS


@pytest.mark.parametrize(
    "content",
    [
        "",
        "[tool]\nother = 'value'\n",
        "[tool]\n'systograph' = 'disabled'\n",
        "[tool.systograph]\nname = 'project'\n",
        "[tool.systograph.trace]\nenabled = true\n",
    ],
)
def test_query_trace_config_loader_defaults_when_optional_keys_are_absent(
    tmp_path: Path,
    content: str,
) -> None:
    # Given
    (tmp_path / "pyproject.toml").write_text(content, encoding="utf-8")

    # When
    config = QueryTraceConfigLoader().load_project_config(tmp_path)

    # Then
    assert config.retrieved_chunks_keys == DEFAULT_RETRIEVED_CHUNKS_KEYS


def test_query_trace_config_loader_rejects_malformed_toml(
    tmp_path: Path,
) -> None:
    # Given
    (tmp_path / "pyproject.toml").write_text("[tool", encoding="utf-8")

    # When / Then
    with pytest.raises(QueryTraceConfigError, match="Failed to parse"):
        QueryTraceConfigLoader().load_project_config(tmp_path)


def test_query_trace_config_loader_rejects_non_table_trace_section(
    tmp_path: Path,
) -> None:
    # Given
    (tmp_path / "pyproject.toml").write_text(
        "[tool.systograph]\ntrace = 'enabled'\n",
        encoding="utf-8",
    )

    # When / Then
    with pytest.raises(
        QueryTraceConfigError,
        match="tool.systograph.trace must be a table",
    ):
        QueryTraceConfigLoader().load_project_config(tmp_path)


@pytest.mark.parametrize(
    ("raw_value", "match"),
    [
        ("[]", "must be a string list"),
        ("'docs'", "must be a string list"),
        ("['docs', 1]", r"retrieved_chunks_keys\[1\]"),
        ("['docs', ' docs ']", "duplicate retrieved_chunks_keys: docs"),
    ],
)
def test_query_trace_config_loader_rejects_invalid_chunk_key_lists(
    tmp_path: Path,
    raw_value: str,
    match: str,
) -> None:
    # Given
    (tmp_path / "pyproject.toml").write_text(
        f"[tool.systograph.trace]\nretrieved_chunks_keys = {raw_value}\n",
        encoding="utf-8",
    )

    # When / Then
    with pytest.raises(QueryTraceConfigError, match=match):
        QueryTraceConfigLoader().load_project_config(tmp_path)


def test_query_trace_config_loader_rejects_empty_chunk_key(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.systograph.trace]
retrieved_chunks_keys = ["docs", ""]
""",
        encoding="utf-8",
    )

    with pytest.raises(
        QueryTraceConfigError,
        match="retrieved_chunks_keys\\[1\\] must be a non-empty string",
    ):
        QueryTraceConfigLoader().load_project_config(tmp_path)


def test_scanned_project_cannot_enable_local_dev_egress_policy(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.systograph.trace]
retrieved_chunks_keys = ["docs"]

[tool.systograph.trace.security]
mode = "local-dev"
allow_loopback = true
allowed_hosts = ["localhost"]
allowed_ports = [11434]
""",
        encoding="utf-8",
    )

    config = QueryTraceConfigLoader().load_project_config(tmp_path)

    assert config.retrieved_chunks_keys == ("docs",)
    assert not hasattr(config, "egress_policy")
