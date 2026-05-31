# Task 13: Implement Component Detection and Unmapped Components

## 目標
實作 `ComponentDetectionService`，將 raw facts 映射到 `rag-core-v1` component slots、component instances、extensions、unmapped components。此任務要守住 detected 必須有 evidence、不確定時不要硬塞 slot 的規則。

## 為什麼要先做這個
Stage 5 是從 facts 走向 system map 的核心。沒有 component detection，就無法建立 `components_by_slot`、flows、viewer graph，也無法處理 custom RAG architecture。

## 前置需求
- Task 3 已完成 `rag-core-v1` template。
- Task 12 已完成 raw facts aggregation。
- Task 2 已完成 component/evidence models。

## 實作範圍
- 建立 component detection rules。
- 初始支援 Qdrant、Chroma、Ollama、OpenAI、LangChain/LlamaIndex signals。
- 建立 all slots status：detected/missing/not_configured/not_applicable。
- 對 ambiguous router/reranker facts 輸出 `unmapped_components` 或 extension candidate。
- 套用 manual mapping 的 extension hook 先留 interface，Task 19 再實作。

## 不包含範圍
- 不使用 AI mapping proposal。
- 不寫 user mapping store。
- 不做 risk hints。
- 不做 query trace mapping。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/component_detection_service.py`。
2. 定義 rule input：template + facts + evidence。
3. 實作 direct evidence mapping：Docker Qdrant -> vector_store、Ollama -> llm、OpenAI SDK/config -> llm/embedding candidate。
4. 實作 missing slot fill：沒有 evidence 時 status 不得 detected。
5. 實作 unmapped output：有 evidence 但無安全 slot 時 status `needs_confirmation`。
6. 寫測試：Qdrant detected、citation missing、custom router unmapped。
7. 寫測試：無 evidence 不可 detected。

## 預期輸出
- `src/kai_mind/core/services/component_detection_service.py`
- `tests/unit/core/test_component_detection_service.py`

## 驗收標準
- Qdrant fixture 產生 detected vector_store instance。
- missing citation slot instances count = 0。
- custom router 不被硬塞進 retriever。
- JSON 不含 `confidence`。
- 每個 detected instance 都有 evidence_ids。

## 可能風險與注意事項
- Dependency evidence 通常只能當 supporting signal，不應單獨 detected。
- 不要把 AI wording 或猜測寫進 facts。
- LangChain/LlamaIndex concepts 可參考官方 RAG/retrieval docs，但 mapping rule 要保守。

## 新手提示
這一步像把收集到的線索貼到 RAG 架構圖上。貼不上去的線索不能丟掉，要放到 unmapped 等使用者確認。

## 視覺化說明
```text
┌──────────────┐
│ Scan facts   │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ clear slot match?     │
└──────┬───────┬───────┘
       │       │
 yes   │       │ clear custom
       ↓       ↓
┌──────────────┐ ┌──────────────┐
│ components   │ │ extensions   │
│ detected     │ │              │
└──────┬───────┘ └──────┬───────┘
       │                │
 uncertain path         │
       ↓                │
┌──────────────┐        │
│ unmapped     │        │
│ components   │        │
└──────┬───────┘        │
       └────────┬───────┘
                ↓
┌──────────────────────┐
│ Validation later      │
└──────────────────────┘
```
