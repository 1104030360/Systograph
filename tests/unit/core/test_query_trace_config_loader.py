from __future__ import annotations

from pathlib import Path

import pytest

from kai_mind.core.services.query_trace_config_loader import (
    DEFAULT_RETRIEVED_CHUNKS_KEYS,
    QueryTraceConfigError,
    QueryTraceConfigLoader,
)


def test_query_trace_config_loader_reads_pyproject_tool_section(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.kai-mind.trace]
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


def test_query_trace_config_loader_rejects_empty_chunk_key(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.kai-mind.trace]
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
[tool.kai-mind.trace]
retrieved_chunks_keys = ["docs"]

[tool.kai-mind.trace.security]
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
