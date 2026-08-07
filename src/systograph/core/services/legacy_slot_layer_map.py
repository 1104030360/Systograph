# 這個檔案負責：legacy `rag-core-v1` 13 個 slot → canonical layer 的
# 唯一對照表。純資料、無行為。
# 用途：**migration-only**——只服務 v1→v2 adapter，把只有 slot 詞彙的
# legacy v1 map 讀進來時補出一個 layer。
# active v2 路徑已經不查這張表：`SystemMapV2NormalizeService` 改由
# `CanonicalTypePlaneResolver` 從 canonical_type 推導 layer
# （canonical_type → capability node → node.plane_id）。
# 注意：key 是 legacy `rag-core-v1` template 的 slot 詞彙，不是 v2
# canonical component 詞彙。這張表已凍結在 13 個 legacy slot，不再擴充：
# 新的 canonical type 要落哪一帶，改 `capability_type_node_map.toml`。
#
# 呼叫鏈（唯一消費者）：
#   system_map_v1_to_v2_adapter._layer_for_slot()
#     → SLOT_LAYER_BY_ID.get(slot, "undetermined")
from __future__ import annotations

from typing import Final

from systograph.core.models.ai_system_map_v2 import CanonicalLayer

SLOT_LAYER_BY_ID: Final[dict[str, CanonicalLayer]] = {
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
