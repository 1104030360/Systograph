from __future__ import annotations

from tests.helpers.fixtures import fixture_file_text

from systograph.core.services.secret_masking_service import (
    SecretMaskingService,
)


def test_report_markdown_and_trace_outputs_share_one_masking_policy() -> None:
    service = SecretMaskingService()
    env_text = fixture_file_text(
        "openai_external_provider_rag", ".env.example"
    )
    github_token = "ghp_abcdefghijklmnopqrstuvwxyz1234567890"
    gitlab_token = "glpat-abcdefghijklmnopqrstuvwxyz123456"
    aws_access_key_id = "AKIAABCDEFGHIJKLMNOP"
    slack_webhook = (
        "https://hooks.slack.com/services/"
        "T00000000/B00000000/abcdefghijklmnopqrstuvwx"
    )
    private_key_body = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC"
    report_like_payload = {
        "markdown": (
            f"## Provider config\n\n```env\n{env_text}\n```\n"
            f"GITHUB_TOKEN={github_token}\n"
            f"GITLAB_TOKEN={gitlab_token}\n"
            f"AWS_ACCESS_KEY_ID={aws_access_key_id}\n"
            f"SLACK_WEBHOOK={slack_webhook}\n"
            "-----BEGIN PRIVATE KEY-----\n"
            f"{private_key_body}\n"
            "-----END PRIVATE KEY-----"
        ),
        "evidence": {
            "key": "OPENAI_API_KEY",
            "value": "ordinary-value",
        },
        "query_trace": [
            "Authorization: Bearer trace-token-value-1234567890",
            "slack=xoxb-123456789012-123456789012-secretvalue",
            "QDRANT_URL=http://localhost:6333",
            "OLLAMA_EMBED_MODEL=nomic-embed-text",
            "route=health_docs",
        ],
    }

    masked = service.mask_json_like(report_like_payload)

    assert "sk-test-example" not in str(masked)
    assert "ordinary-value" not in str(masked)
    assert "trace-token-value-1234567890" not in str(masked)
    assert github_token not in str(masked)
    assert gitlab_token not in str(masked)
    assert aws_access_key_id not in str(masked)
    assert slack_webhook not in str(masked)
    assert private_key_body not in str(masked)
    assert "OPENAI_API_KEY" in str(masked)
    assert "QDRANT_URL=http://localhost:6333" in str(masked)
    assert "OLLAMA_EMBED_MODEL=nomic-embed-text" in str(masked)
    assert "route=health_docs" in str(masked)
