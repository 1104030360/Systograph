from __future__ import annotations

from kai_mind.core.models.system_map import (
    ComponentInstance,
    ComponentSlot,
    Flow,
)
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)
from kai_mind.core.services.flow_derivation_service import (
    FlowDerivationService,
)
from kai_mind.core.services.rag_template_service import RagTemplateService


def component(
    *,
    slot: str,
    provider: str | None = None,
    evidence_id: str | None = None,
) -> ComponentInstance:
    name = provider or slot
    return ComponentInstance(
        id=f"component:{slot}:{name}",
        slot=slot,
        kind=name,
        name=name,
        provider=provider,
        evidence_ids=[evidence_id or f"evidence:{slot}"],
    )


def components_with_slots(
    instances: list[ComponentInstance],
) -> ComponentDetectionResult:
    template = RagTemplateService.load("rag-core-v1")
    instances_by_slot = {instance.slot: [instance] for instance in instances}
    components_by_slot: dict[str, ComponentSlot] = {}
    for slot in template.slots:
        slot_instances = instances_by_slot.get(slot.id, [])
        components_by_slot[slot.id] = ComponentSlot(
            slot=slot.id,
            required_for_rag=slot.required_for_rag_hint,
            status=(
                "detected"
                if slot_instances
                else (
                    "missing"
                    if slot.required_for_rag_hint
                    else "not_applicable"
                )
            ),
            instances=slot_instances,
        )
    return ComponentDetectionResult(
        components_by_slot=components_by_slot,
        unmapped_components=[],
    )


def derive_flows(instances: list[ComponentInstance]) -> list[Flow]:
    template = RagTemplateService.load("rag-core-v1")
    return FlowDerivationService().derive(
        template=template,
        components=components_with_slots(instances),
    )


def test_derives_indexing_edge_only_between_detected_adjacent_slots() -> None:
    embedding = component(
        slot="embedding_model",
        provider="openai",
        evidence_id="evidence:embedding",
    )
    vector_store = component(
        slot="vector_store",
        provider="qdrant",
        evidence_id="evidence:vector_store",
    )

    flows = derive_flows([embedding, vector_store])

    indexing = next(flow for flow in flows if flow.id == "flow:indexing")
    assert [edge.id for edge in indexing.edges] == [
        "edge:indexing:embedding_model:vector_store"
    ]
    edge = indexing.edges[0]
    assert edge.relationship == "stores_vectors"
    assert edge.from_component_id == embedding.id
    assert edge.to_component_id == vector_store.id
    assert edge.evidence_ids == ["evidence:embedding", "evidence:vector_store"]


def test_derives_query_answer_edges_without_dangling_missing_slots() -> None:
    retriever = component(slot="retriever", evidence_id="evidence:retriever")
    vector_store = component(
        slot="vector_store",
        provider="qdrant",
        evidence_id="evidence:vector_store",
    )
    prompt = component(
        slot="prompt_builder",
        evidence_id="evidence:prompt_builder",
    )
    llm = component(
        slot="llm",
        provider="openai",
        evidence_id="evidence:llm",
    )

    flows = derive_flows([retriever, vector_store, prompt, llm])

    query_answer = next(
        flow for flow in flows if flow.id == "flow:query_answer"
    )
    assert [(edge.from_slot, edge.to_slot) for edge in query_answer.edges] == [
        ("retriever", "vector_store"),
        ("vector_store", "prompt_builder"),
        ("prompt_builder", "llm"),
    ]
    assert all(edge.from_component_id for edge in query_answer.edges)
    assert all(edge.to_component_id for edge in query_answer.edges)


def test_always_returns_template_flows_even_when_edges_are_empty() -> None:
    flows = derive_flows([])

    assert [flow.id for flow in flows] == [
        "flow:indexing",
        "flow:query_answer",
    ]
    assert all(flow.edges == [] for flow in flows)
