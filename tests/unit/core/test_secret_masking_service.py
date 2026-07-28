from __future__ import annotations

import pytest

from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)


def test_short_secret_value_is_fully_masked() -> None:
    service = SecretMaskingService()

    masked = service.mask_value("abc123", key="API_TOKEN")

    assert masked == "[MASKED]"


def test_long_secret_value_keeps_small_prefix_and_suffix() -> None:
    service = SecretMaskingService()
    secret = "systograph-test-secret-value-1234567890"

    masked = service.mask_value(secret, key="CLIENT_SECRET")

    assert masked == "systograph-...7890"
    assert secret not in masked


def test_secret_key_masks_ordinary_looking_value() -> None:
    service = SecretMaskingService()

    masked = service.mask_value("ordinary-value", key="OPENAI_API_KEY")

    assert masked != "ordinary-value"
    assert masked == "ordi...alue"


def test_non_secret_endpoint_is_not_masked() -> None:
    service = SecretMaskingService()

    masked = service.mask_value("http://localhost:6333", key="QDRANT_URL")

    assert masked == "http://localhost:6333"


def test_secret_key_name_detection_is_available_publicly() -> None:
    service = SecretMaskingService()

    assert service.is_secret_key_name("OPENAI_API_KEY")
    assert service.is_secret_key_name("api_token")
    assert not service.is_secret_key_name("QDRANT_URL")


def test_env_text_masks_fake_openai_key_without_hiding_key_name() -> None:
    service = SecretMaskingService()
    env_text = (
        "OPENAI_API_KEY=sk-test-example\nQDRANT_URL=http://localhost:6333"
    )

    masked = service.mask_text(env_text)

    assert "OPENAI_API_KEY=" in masked
    assert "sk-test-example" not in masked
    assert "QDRANT_URL=http://localhost:6333" in masked


def test_bare_secret_marker_keys_are_masked_in_text() -> None:
    service = SecretMaskingService()
    text = "\n".join(
        [
            "PASSWORD=abc123",
            "TOKEN=plain-token-value",
            "SECRET=plain-secret-value",
        ]
    )

    masked = service.mask_text(text)

    assert "abc123" not in masked
    assert "plain-token-value" not in masked
    assert "plain-secret-value" not in masked
    assert "PASSWORD=[MASKED]" in masked
    assert "TOKEN=plai...alue" in masked
    assert "SECRET=plai...alue" in masked


def test_quoted_secret_text_with_spaces_is_masked() -> None:
    service = SecretMaskingService()
    secret = "correct horse battery staple"
    text = "\n".join(
        [
            f'PASSWORD="{secret}"',
            f"password: '{secret}'",
            f'{{"password": "{secret}"}}',
        ]
    )

    masked = service.mask_text(text)

    assert secret not in masked
    assert 'PASSWORD="corr...aple"' in masked
    assert "password: 'corr...aple'" in masked
    assert '{"password": "corr...aple"}' in masked


def test_authorization_bearer_text_is_masked() -> None:
    service = SecretMaskingService()
    token = "bearer-token-value-1234567890"

    masked = service.mask_text(f"Authorization: Bearer {token}")

    assert token not in masked
    assert masked == "Authorization: Bearer bear...7890"


def test_quoted_json_authorization_bearer_value_is_masked() -> None:
    service = SecretMaskingService()
    token = "serialized-token-value-1234567890"

    masked = service.mask_text(f'{{"Authorization": "Bearer {token}"}}')

    assert token not in masked
    assert masked == '{"Authorization": "Bear...7890"}'


def test_common_token_patterns_are_masked_without_keys() -> None:
    service = SecretMaskingService()
    tokens = {
        "github": "ghp_abcdefghijklmnopqrstuvwxyz1234567890",
        "gitlab": "glpat-abcdefghijklmnopqrstuvwxyz123456",
        "aws": "AKIAABCDEFGHIJKLMNOP",
        "slack_bot": "xoxb-123456789012-123456789012-secretvalue",
        "slack_webhook": (
            "https://hooks.slack.com/services/"
            "T00000000/B00000000/abcdefghijklmnopqrstuvwx"
        ),
    }

    masked = service.mask_text("\n".join(tokens.values()))

    for token in tokens.values():
        assert token not in masked


def test_private_key_block_body_is_masked() -> None:
    service = SecretMaskingService()
    private_key_body = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC"
    private_key = (
        "-----BEGIN PRIVATE KEY-----\n"
        f"{private_key_body}\n"
        "-----END PRIVATE KEY-----"
    )

    masked = service.mask_text(private_key)

    assert private_key_body not in masked
    assert "-----BEGIN PRIVATE KEY-----" in masked
    assert "-----END PRIVATE KEY-----" in masked


def test_common_non_secret_values_are_not_masked() -> None:
    service = SecretMaskingService()
    text = "\n".join(
        [
            "QDRANT_URL=http://localhost:6333",
            "OLLAMA_EMBED_MODEL=nomic-embed-text",
            "route=health_docs",
        ]
    )

    masked = service.mask_text(text)

    assert masked == text


def test_json_like_data_is_masked_recursively() -> None:
    service = SecretMaskingService()
    github_token = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    data = {
        "provider": "openai",
        "OPENAI_API_KEY": "sk-test-example",
        "endpoint": "http://localhost:6333",
        "nested": [
            {"password": "short"},
            {"note": "Authorization: Bearer nested-token-1234567890"},
            {"note": f"github={github_token}"},
        ],
    }

    masked = service.mask_json_like(data)

    assert masked == {
        "provider": "openai",
        "OPENAI_API_KEY": "sk-t...mple",
        "endpoint": "http://localhost:6333",
        "nested": [
            {"password": "[MASKED]"},
            {"note": "Authorization: Bearer nest...7890"},
            {"note": "github=ghp_...7890"},
        ],
    }
    assert github_token not in str(masked)


def test_contains_unmasked_secret_detects_supported_patterns() -> None:
    service = SecretMaskingService()

    assert service.contains_unmasked_secret("sk-live-secret-value")
    assert service.contains_unmasked_secret(
        "github=ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    )
    assert service.contains_unmasked_secret("OPENAI_API_KEY=plain-secret")


def test_contains_unmasked_secret_can_skip_key_value_pair_detection() -> None:
    service = SecretMaskingService()
    structural_id = "risk:secret_like_config_key_detected:openai-api-key"
    embedded_token = (
        "risk:secret_like_config_key_detected:"
        "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    )

    assert not service.contains_unmasked_secret(
        structural_id,
        scan_key_value_pairs=False,
    )
    assert service.contains_unmasked_secret(
        embedded_token,
        scan_key_value_pairs=False,
    )


@pytest.mark.parametrize(
    "key",
    [
        "DB_PASSWD",
        "DB_PWD",
        "MYAPIKEY",
        "ACCESSKEY",
        "PRIVATE-KEY",
        "SERVICE.CREDENTIAL",
    ],
)
def test_secret_key_variants_are_normalized_before_matching(key: str) -> None:
    service = SecretMaskingService()
    raw_value = "synthetic-credential-value-138"

    assert service.is_secret_key_name(key)
    assert raw_value not in service.mask_value(raw_value, key=key)

    masked_text = service.mask_text(f"{key}={raw_value}")
    assert f"{key}=" in masked_text
    assert raw_value not in masked_text


@pytest.mark.parametrize(
    ("raw_url", "expected_url"),
    [
        (
            "postgresql://demo:fake-pass@db.example:5432/app",
            "postgresql://demo:[MASKED]@db.example:5432/app",
        ),
        (
            "redis://:fake-pass@cache.example:6379/0",
            "redis://:[MASKED]@cache.example:6379/0",
        ),
        (
            "mongodb+srv://demo:fake-pass@cluster.example/app?retry=true",
            "mongodb+srv://demo:[MASKED]@cluster.example/app?retry=true",
        ),
        (
            "https://demo:fake-pass@service.example/v1#health",
            "https://demo:[MASKED]@service.example/v1#health",
        ),
        (
            "https://synthetic-token@service.example/v1",
            "https://[MASKED]@service.example/v1",
        ),
        (
            "postgresql://demo:fake%40pass@db.example/app",
            "postgresql://demo:[MASKED]@db.example/app",
        ),
        (
            "postgresql://demo:fake-pass@[2001:db8::1]:5432/app",
            "postgresql://demo:[MASKED]@[2001:db8::1]:5432/app",
        ),
    ],
)
def test_url_userinfo_is_fully_masked(
    raw_url: str,
    expected_url: str,
) -> None:
    service = SecretMaskingService()

    assert service.mask_value(raw_url, key="DATABASE_URL") == expected_url
    assert service.mask_text(f"connection failed for {raw_url}") == (
        f"connection failed for {expected_url}"
    )
    assert service.contains_unmasked_secret(raw_url)


@pytest.mark.parametrize(
    "value",
    [
        "http://localhost:6333",
        "https://service.example/v1?health=true",
        "route=health_docs",
        "model=text-embedding-3-small",
        "component=vector_store",
    ],
)
def test_non_secret_urls_and_identifiers_remain_visible(value: str) -> None:
    service = SecretMaskingService()

    assert service.mask_text(value) == value
