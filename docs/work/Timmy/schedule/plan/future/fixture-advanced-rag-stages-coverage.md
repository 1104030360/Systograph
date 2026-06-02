# Future: Fixture Advanced RAG Stages Coverage

## 來源
Task 4 (Build Test Fixtures and Contract Baseline) 明確列出「第一版可以先延後的階段」：

> 第一版可以先延後的階段：
> - document_loader
> - chunking
> - reranker
> - citation
> - guardrails
> - observability
> - graph retrieval
> - multimodal ingestion

> 白話決策：
> 先測 scanner 會不會認錯核心 RAG 組件。
> 再測 RAG 流程是不是完整。
> 最後才測 reranker、citation、guardrails、observability、graph、multimodal 這些進階功能。

## 目的
擴充 test fixtures 覆蓋 RAG pipeline 中的進階階段，確保 scanner 不只辨識核心組件（embedding、vector store、LLM、retriever），也能辨識進階組件。

## 目前狀態（2026-06-02）
這份應視為「部分完成、主體仍 future」。Task 4 後來已補上一些進階 fixture signals，因此不要把整份文件理解成完全未開始。

已完成基礎 fixture coverage：
- `reranker_extension_rag/`：已有 reranker dependency / config / code signal，integration test 檢查 `cross-encoder`。
- `graph_rag_extension_rag/`：已有 GraphRAG / Neo4j / knowledge graph / graph retriever signals，integration test 檢查 `graphrag`、`neo4j`、`knowledge_graph`、`entity_extraction`。
- `healthcare_rag_minimal/`：已有 synthetic medical docs、citation、guardrails、PHI policy signals，integration test 檢查 `cite_sources_required`、`no_diagnosis`、`emergency_escalation`、`source_id`。
- `missing_slots_rag/`：已有刻意缺少 citation / guardrails / observability 的 fixture，可支援後續 missing slot detection。

仍屬 future：
- document loader fixture signals 尚未完整覆蓋。
- chunking fixture signals 尚未完整覆蓋。
- observability fixture signals 尚未完整覆蓋。
- multimodal ingestion 另有 `multimodal-rag-fixture-and-scanner-support.md`，目前仍未實作。
- Task 11-15 尚未完成，因此「scanner 能辨識這些進階 signals 並映射到 components / unmapped components」仍屬未來工作。

## 觸發條件
- 核心 RAG 階段的 scanner coverage 已穩定（Task 11–15 完成）。
- 使用者回報 scanner 漏判 reranker、citation、guardrails 等組件。
- 需要驗證 extension / unmapped component 處理邏輯。

## 建議覆蓋階段

### document_loader
- 測試不同 loader 類型：PDF loader、web scraper、API ingestion。
- Fixture signals：`PyPDFLoader`、`WebBaseLoader`、`UnstructuredLoader` import patterns。

### chunking
- 測試不同 chunking 策略：recursive splitter、token splitter、semantic chunking。
- Fixture signals：`RecursiveCharacterTextSplitter`、chunk size config。

### reranker
- 測試 cross-encoder、Cohere-style reranker。
- Fixture signals：`sentence-transformers` reranker dependency、reranker config。
- 狀態：已有 `reranker_extension_rag/` 基礎 fixture；future work 是讓 Task 11/13 scanner 與 component detection 正確輸出 extension / unmapped component。

### citation
- 測試 citation / source attribution。
- Fixture signals：source metadata in response、citation formatting。
- 狀態：已有 `healthcare_rag_minimal/src/citation.py` 基礎 signal；future work 是擴充 detection rules 與更多 citation pattern。

### guardrails
- 測試 input/output guardrails。
- Fixture signals：guardrails dependency、content filter config。
- 狀態：已有 `healthcare_rag_minimal/src/guardrails.py` 與 config 基礎 signal；future work 是擴充 detection rules 與 guardrail taxonomy。

### observability
- 測試 tracing / metrics / logging integration。
- Fixture signals：LangSmith / Weights & Biases / OpenTelemetry config。

### graph retrieval
- 測試 graph-based retrieval（已有 `graph_rag_extension_rag/` fixture 基礎）。
- 深化 knowledge graph / Neo4j / hybrid graph+vector retrieval signals。
- 狀態：已有 `graph_rag_extension_rag/` 基礎 fixture；future work 是深化 hybrid graph+vector retrieval 與 component/unmapped mapping。

## 與既有任務關係
- Task 4：已建立 fixture 框架，`basic_qdrant_ollama_rag/` 等核心 fixtures 已完成；reranker、graph retrieval、citation、guardrails 也已有基礎 fixture signals。
- Task 11：code pattern provider 需要對應 rules。
- Task 13：component detection 需要支援進階 component types。
- Task 12a：rule catalog 需要涵蓋進階 patterns。

## 不做事項
- 不一次建立所有 fixtures，應按需求逐步擴充。
- 不建立能真正執行的 RAG pipeline。
- 不放真實資料或 secret。
