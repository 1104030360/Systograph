from __future__ import annotations

import inspect
import json
from pathlib import Path

from kai_mind.core.models.system_map import RagSystemMap
from kai_mind.core.services.markdown_summary_service import (
    MarkdownSummaryService,
)

FIXTURE_DIR = Path(__file__).parents[2] / "fixtures" / "ai_system_map"


def load_system_map(
    name: str = "valid_rich_frontend_sample.v1.json",
) -> RagSystemMap:
    return RagSystemMap.model_validate_json(
        (FIXTURE_DIR / name).read_text(encoding="utf-8")
    )


def test_render_uses_validated_map_and_returns_markdown_string() -> None:
    signature = inspect.signature(MarkdownSummaryService.render)

    assert "project_path" not in signature.parameters
    markdown = MarkdownSummaryService().render(load_system_map())

    assert isinstance(markdown, str)
    assert markdown.startswith("# KAI-Mind System Map\n")
    assert "sample-health-rag" in markdown
    assert "ai-system-map/v1" in markdown


def test_render_includes_required_sections_in_deterministic_order() -> None:
    markdown = MarkdownSummaryService().render(load_system_map())
    sections = [
        "## System Overview",
        "## Slot Coverage",
        "## Detected And Missing Slots",
        "## Indexing Flow",
        "## Query Answer Flow",
        "## Local Endpoints",
        "## External Endpoints",
        "## Network Exposure",
        "## Recommended Next Checks",
    ]

    positions = [markdown.index(section) for section in sections]

    assert positions == sorted(positions)


def test_render_summarizes_slots_flows_endpoints_and_risks() -> None:
    markdown = MarkdownSummaryService().render(load_system_map())

    assert "| data_sources | required | detected | docs/ |" in markdown
    assert "| guardrails | optional | missing | - |" in markdown
    assert "- data_sources -> document_loader: loads_documents" in markdown
    assert "- prompt_builder -> llm: sends_grounded_prompt" in markdown
    assert "| local | GET | http://localhost:6333 | vector_store |" in markdown
    assert (
        "| local | POST | http://localhost:8000/query | "
        "app_api_or_orchestrator |"
    ) in markdown
    assert "| external | POST | https://api.openai.com/v1 | llm |" in markdown
    assert (
        "Epic 1 does not run full port security or firewall checks."
        in markdown
    )


def test_render_uses_github_task_list_for_recommended_next_checks() -> None:
    markdown = MarkdownSummaryService().render(load_system_map())

    assert (
        "- [ ] review_network_exposure: Published vector database port may "
        "affect release readiness. (target: component:vector_store:qdrant)"
        in markdown
    )
    assert "manual_mapping_confirmation" in markdown
    assert "run_query_trace" in markdown


def test_render_does_not_emit_unmasked_secret_values() -> None:
    data = json.loads(
        (FIXTURE_DIR / "valid_rich_frontend_sample.v1.json").read_text(
            encoding="utf-8"
        )
    )
    data["risk_hints"][0]["rationale"] = (
        "Raw secret accidentally reached a report field: "
        "OPENAI_API_KEY=sk-test-regression-secret"
    )
    system_map = RagSystemMap.model_validate(data)

    markdown = MarkdownSummaryService().render(system_map)

    assert "sk-test-regression-secret" not in markdown
    assert "[MASKED]" in markdown or "sk-t...cret" in markdown
