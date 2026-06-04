"""Derive initial RAG flows from template slot order and components."""

from __future__ import annotations

import re
from typing import Final

from kai_mind.core.models.system_map import (
    ComponentInstance,
    Edge,
    Flow,
)
from kai_mind.core.models.template import RagTemplate, TemplateFlow
from kai_mind.core.services.component_detection_service import (
    ComponentDetectionResult,
)

RELATIONSHIPS: Final = {
    ("data_sources", "document_loader"): "loads_documents",
    ("document_loader", "chunking"): "splits_documents",
    ("chunking", "embedding_model"): "passes_chunks",
    ("embedding_model", "vector_store"): "stores_vectors",
    ("app_api_or_orchestrator", "query_processing"): "passes_query",
    ("query_processing", "retriever"): "passes_processed_query",
    ("retriever", "vector_store"): "queries_vector_store",
    ("vector_store", "prompt_builder"): "provides_retrieved_context",
    ("prompt_builder", "llm"): "prompts_llm",
    ("llm", "citation_or_response_composer"): "generates_answer",
    ("citation_or_response_composer", "guardrails"): "passes_response",
    ("guardrails", "observability"): "emits_trace",
}


class FlowDerivationService:
    """Build flow edges only when both endpoint slots are detected."""

    def derive(
        self,
        *,
        template: RagTemplate,
        components: ComponentDetectionResult,
    ) -> list[Flow]:
        flows: list[Flow] = []
        for template_flow in template.flows:
            flow_id = f"flow:{template_flow.id}"
            flows.append(
                Flow(
                    id=flow_id,
                    name=_flow_name(template_flow.id),
                    flow_type=template_flow.id,
                    edges=self._derive_edges(
                        flow_id=flow_id,
                        template_flow=template_flow,
                        components=components,
                    ),
                )
            )
        return flows

    def _derive_edges(
        self,
        *,
        flow_id: str,
        template_flow: TemplateFlow,
        components: ComponentDetectionResult,
    ) -> list[Edge]:
        edges: list[Edge] = []
        pairs = zip(
            template_flow.slot_order,
            template_flow.slot_order[1:],
            strict=False,
        )
        for from_slot, to_slot in pairs:
            from_component = _first_component(components, from_slot)
            to_component = _first_component(components, to_slot)
            if from_component is None or to_component is None:
                continue
            flow_key = _flow_key(flow_id)
            edges.append(
                Edge(
                    id=f"edge:{flow_key}:{from_slot}:{to_slot}",
                    flow_id=flow_id,
                    from_slot=from_slot,
                    to_slot=to_slot,
                    from_component_id=from_component.id,
                    to_component_id=to_component.id,
                    relationship=RELATIONSHIPS.get(
                        (from_slot, to_slot),
                        "connects_to",
                    ),
                    evidence_ids=_edge_evidence_ids(
                        from_component,
                        to_component,
                    ),
                )
            )
        return edges


def _first_component(
    components: ComponentDetectionResult,
    slot_id: str,
) -> ComponentInstance | None:
    slot = components.components_by_slot.get(slot_id)
    if slot is None or slot.status != "detected" or not slot.instances:
        return None
    return sorted(slot.instances, key=lambda item: item.id)[0]


def _edge_evidence_ids(
    from_component: ComponentInstance,
    to_component: ComponentInstance,
) -> list[str]:
    return sorted(
        set(from_component.evidence_ids) | set(to_component.evidence_ids)
    )


def _flow_key(flow_id: str) -> str:
    return flow_id.removeprefix("flow:")


def _flow_name(flow_id: str) -> str:
    return re.sub(r"[_-]+", " ", flow_id).title()
