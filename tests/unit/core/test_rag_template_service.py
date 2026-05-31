import json
from pathlib import Path

import pytest

from kai_mind.core.services.rag_template_service import (
    RagTemplateService,
    RagTemplateValidationError,
)

EXPECTED_SLOT_IDS = [
    "data_sources",
    "document_loader",
    "chunking",
    "embedding_model",
    "vector_store",
    "app_api_or_orchestrator",
    "query_processing",
    "retriever",
    "prompt_builder",
    "llm",
    "citation_or_response_composer",
    "guardrails",
    "observability",
]

EXPECTED_ALLOWED_STATUSES = [
    "detected",
    "missing",
    "not_configured",
    "not_applicable",
]


def test_loads_builtin_rag_core_v1_template() -> None:
    template = RagTemplateService.load("rag-core-v1")

    assert template.id == "rag-core-v1"
    assert template.system_type == "rag"
    assert template.version == "1.0.0"
    assert [slot.id for slot in template.slots] == EXPECTED_SLOT_IDS
    assert template.allowed_statuses == EXPECTED_ALLOWED_STATUSES


def test_template_flows_use_bare_ids_and_known_slots() -> None:
    template = RagTemplateService.load("rag-core-v1")
    slot_ids = {slot.id for slot in template.slots}

    assert [flow.id for flow in template.flows] == [
        "indexing",
        "query_answer",
    ]
    assert all(not flow.id.startswith("flow:") for flow in template.flows)
    for flow in template.flows:
        assert flow.slot_order
        assert set(flow.slot_order).issubset(slot_ids)


def test_requiredness_hints_do_not_mark_every_slot_required() -> None:
    template = RagTemplateService.load("rag-core-v1")
    requiredness_by_slot = {
        slot.id: slot.required_for_rag_hint for slot in template.slots
    }

    assert requiredness_by_slot["retriever"] is True
    assert requiredness_by_slot["llm"] is True
    assert requiredness_by_slot["guardrails"] is False
    assert requiredness_by_slot["observability"] is False
    assert not all(requiredness_by_slot.values())


def test_rejects_unknown_template_id() -> None:
    with pytest.raises(RagTemplateValidationError, match="Unknown template"):
        RagTemplateService.load("missing-template")


def test_rejects_duplicate_template_slots(tmp_path: Path) -> None:
    write_template(
        tmp_path,
        {
            "id": "rag-core-v1",
            "version": "1.0.0",
            "system_type": "rag",
            "allowed_statuses": EXPECTED_ALLOWED_STATUSES,
            "slots": [
                {
                    "id": "retriever",
                    "label": "Retriever",
                    "required_for_rag_hint": True,
                },
                {
                    "id": "retriever",
                    "label": "Retriever duplicate",
                    "required_for_rag_hint": True,
                },
            ],
            "flows": [
                {
                    "id": "query_answer",
                    "slot_order": ["retriever"],
                }
            ],
        },
    )

    with pytest.raises(RagTemplateValidationError, match="Duplicate slot"):
        RagTemplateService.load("rag-core-v1", template_dir=tmp_path)


def test_rejects_flow_referencing_unknown_slot(tmp_path: Path) -> None:
    write_template(
        tmp_path,
        {
            "id": "rag-core-v1",
            "version": "1.0.0",
            "system_type": "rag",
            "allowed_statuses": EXPECTED_ALLOWED_STATUSES,
            "slots": [
                {
                    "id": "retriever",
                    "label": "Retriever",
                    "required_for_rag_hint": True,
                }
            ],
            "flows": [
                {
                    "id": "query_answer",
                    "slot_order": ["retriever", "missing_slot"],
                }
            ],
        },
    )

    with pytest.raises(RagTemplateValidationError, match="unknown slot"):
        RagTemplateService.load("rag-core-v1", template_dir=tmp_path)


def test_rejects_status_drift_from_system_map_contract(
    tmp_path: Path,
) -> None:
    write_template(
        tmp_path,
        {
            "id": "rag-core-v1",
            "version": "1.0.0",
            "system_type": "rag",
            "allowed_statuses": ["detected", "missing", "archived"],
            "slots": [
                {
                    "id": "retriever",
                    "label": "Retriever",
                    "required_for_rag_hint": True,
                }
            ],
            "flows": [
                {
                    "id": "query_answer",
                    "slot_order": ["retriever"],
                }
            ],
        },
    )

    with pytest.raises(RagTemplateValidationError, match="Allowed statuses"):
        RagTemplateService.load("rag-core-v1", template_dir=tmp_path)


def test_rejects_prefixed_template_flow_id(tmp_path: Path) -> None:
    write_template(
        tmp_path,
        {
            "id": "rag-core-v1",
            "version": "1.0.0",
            "system_type": "rag",
            "allowed_statuses": EXPECTED_ALLOWED_STATUSES,
            "slots": [
                {
                    "id": "retriever",
                    "label": "Retriever",
                    "required_for_rag_hint": True,
                }
            ],
            "flows": [
                {
                    "id": "flow:query_answer",
                    "slot_order": ["retriever"],
                }
            ],
        },
    )

    with pytest.raises(RagTemplateValidationError, match="bare flow id"):
        RagTemplateService.load("rag-core-v1", template_dir=tmp_path)


def write_template(template_dir: Path, data: object) -> None:
    template_dir.mkdir(parents=True, exist_ok=True)
    template_path = template_dir / "rag-core-v1.json"
    template_path.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )
