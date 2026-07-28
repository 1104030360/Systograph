# 這個檔案負責：legacy `rag-core-v1` 13 個 slot → canonical layer 的
# 唯一對照表。純資料、無行為；v1 adapter 與 v2 normalize 共用同一份，
# 讓兩條路徑的 layer 語意等價性由「單一來源」保證，而不是靠兩份複本
# 剛好長得一樣。
# 注意：key 是 legacy `rag-core-v1` template 的 slot 詞彙，不是 v2
# canonical component 詞彙；新的 v2 元件不應該擴充這張表。
#
# 呼叫鏈：
#   system_map_v1_to_v2_adapter._layer_for_slot()
#     → SLOT_LAYER_BY_ID.get(slot, "undetermined")
#   SystemMapV2NormalizeService._components()
#     → SLOT_LAYER_BY_ID.get(slot.slot, "undetermined")
from __future__ import annotations

from typing import Final

from kai_mind.core.models.ai_system_map_v2 import CompatibilityLayer

SLOT_LAYER_BY_ID: Final[dict[str, CompatibilityLayer]] = {
    "app_api_or_orchestrator": "control",
    "data_sources": "ingestion_indexing",
    "document_loader": "ingestion_indexing",
    "chunking": "ingestion_indexing",
    "embedding_model": "ingestion_indexing",
    "vector_store": "retrieval",
    "query_processing": "retrieval",
    "retriever": "retrieval",
    "prompt_builder": "generation",
    "llm": "generation",
    "citation_or_response_composer": "generation",
    "guardrails": "governance_observability",
    "observability": "governance_observability",
}
