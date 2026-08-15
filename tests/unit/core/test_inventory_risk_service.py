from __future__ import annotations

import pytest

from systograph.core.services.inventory_risk_service import (
    InventoryRiskService,
)


@pytest.mark.parametrize(
    "path",
    [
        "goldenverba/components/chunking/TokenChunker.py",
        "private_gpt/components/llm/tokenizers/estimator.py",
        "packages/graphrag/graphrag/config/tokenizer_config.py",
        "notebooks/token_chunking_example.ipynb",
        "src/auth/PasswordPolicy.ts",
        "internal/credentials_loader.go",
    ],
)
def test_program_source_filenames_are_not_secret_risk(path: str) -> None:
    # Given/When/Then: tokenizer- and credential-shaped NAMES on program
    # source are ordinary AI-system code, not secret-bearing artifacts;
    # source content is covered by secret masking instead.
    assert InventoryRiskService().risk_type(path) is None


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.production",
        "deploy/service-account.key",
        "certs/server.pem",
        "config/api_keys.json",
        "infra/secrets.yaml",
        "ops/db_password.txt",
    ],
)
def test_secret_bearing_artifacts_still_require_review(path: str) -> None:
    # Given/When/Then: config and credential artifacts keep the gate.
    assert InventoryRiskService().risk_type(path) == "secret_like_config"


def test_vector_persistence_detection_is_unchanged() -> None:
    # Given/When/Then: the second risk family is untouched by the
    # source-file exemption.
    service = InventoryRiskService()
    assert service.risk_type("storage/chroma.sqlite3") == (
        "model_or_vector_persistence"
    )
    assert service.risk_type("src/vector_store.py") is None
