from __future__ import annotations

from pathlib import Path

from tests.helpers.web import app_mapping_proposal_service

from kai_mind.core.providers.llm_proposal_provider import (
    NvidiaNimProposalProvider,
)
from kai_mind.web.app import create_app


def test_app_does_not_wire_nvidia_provider_without_explicit_flag(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("NVIDIA_API_KEY=nvapi-from-dotenv\n", encoding="utf-8")

    app = create_app(env_file=env_file)

    service = app_mapping_proposal_service(app)
    assert service.provider is None


def test_app_wires_nvidia_provider_when_enabled_from_dotenv(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS=true",
                "NVIDIA_API_KEY=nvapi-from-dotenv",
            ]
        ),
        encoding="utf-8",
    )

    app = create_app(env_file=env_file)

    service = app_mapping_proposal_service(app)
    assert isinstance(service.provider, NvidiaNimProposalProvider)
