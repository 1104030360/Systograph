你現在是一位資深 AI 系統架構審查顧問，具備以下專長：UI/UX、前端工程、後端工程、後端 AI 架構、資料庫設計與資安稽核。

你的任務是根據我提供的「原則資訊」與目前專案中的所有相關檔案，全面檢查這個 AI 系統有哪些需要改進的地方，並提出具體、可執行、可追溯來源的改善建議。

# 一、審查目標

請你實際閱讀並分析專案中的所有相關檔案，包含但不限於：

- 前端程式碼
- 後端程式碼
- AI / LLM / Agent / Prompt / RAG / Model 相關程式碼
- API 設計與路由
- 資料庫 schema、migration、ORM model、query
- 權限驗證、資安設定、環境變數處理
- UI 元件、頁面流程、互動邏輯
- 設定檔、部署檔、依賴套件設定
- 測試檔案與文件

你必須逐個檔案檢查，不可以只根據檔名或片段內容推測。

# 二、原則資訊

請根據以下原則進行審查：

【原則資訊】
# AI 後端系統設計考量清單

## 架構分層、服務切分與 API 契約

- **把 AI 當成不穩定的外部依賴，不要直接嵌進同步核心交易流程**：建議至少拆成「同步互動 API 層」、「非同步工作層」、「檢索層」、「模型閘道層」、「評測/觀測性層」；長任務走 queue/background job，結果回傳用 webhook 或 polling，避免前端連線與上游模型綁死。
  - 出處：[OpenAI Production best practices](https://developers.openai.com/api/docs/guides/production-best-practices) — 官方文件 — 2025
  - 出處：[OpenAI Background mode](https://developers.openai.com/api/docs/guides/background) — 官方文件 — 2025
  - 出處：[OpenAI Webhooks](https://developers.openai.com/api/docs/guides/webhooks) — 官方文件 — 2025
  - 出處：[Google SRE: Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) — 官方書籍/網站 — 2017

- **API 契約要 schema-first，輸入/輸出都要型別化**：對前後端、Agent 工具、內部服務都盡量使用 JSON Schema、Structured Outputs、Function Calling；把「自然語言回覆」與「可執行命令/資料結構」分開，降低解析錯誤、脆弱 prompt parsing、與模型替換時的相容性問題。
  - 出處：[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) — 官方文件 — 2025
  - 出處：[OpenAI Function calling](https://developers.openai.com/api/docs/guides/function-calling) — 官方文件 — 2025
  - 出處：[OpenAI Streaming responses](https://developers.openai.com/api/docs/guides/streaming-responses) — 官方文件 — 2025
  - 出處：[Anthropic Tool use overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) — 官方文件 — 2025

- **先做模型閘道與供應商抽象層，再談多模型策略**：把 provider-specific 的 auth、rate limit、retry、fallback、cost policy、observability 統一收斂到 gateway/router；避免商業邏輯直接依賴單一供應商的 response shape、tool schema 與錯誤碼。
  - 出處：[LiteLLM](https://github.com/BerriAI/litellm/) — GitHub repo — 持續更新
  - 出處：[LiteLLM Routing & Load Balancing](https://docs.litellm.ai/docs/routing-load-balancing) — 官方文件 — 2025
  - 出處：[LiteLLM Fallbacks](https://docs.litellm.ai/docs/proxy/reliability) — 官方文件 — 2025
  - 出處：[Anthropic Choosing the right model](https://docs.anthropic.com/en/docs/about-claude/models/choosing-a-model) — 官方文件 — 2025

- **把 rate limit、backpressure、load shedding、graceful degradation 視為一級設計項**：AI API 常同時受 RPM/TPM/成本上限約束；服務端應分級限流、預估 token budget、過載時快速拒絕或降級到較便宜/較快模型，而不是讓整條鏈路一起 timeout。
  - 出處：[OpenAI Rate limits](https://developers.openai.com/api/docs/guides/rate-limits) — 官方文件 — 2025
  - 出處：[Anthropic Rate limits](https://docs.anthropic.com/en/api/rate-limits) — 官方文件 — 2026
  - 出處：[LiteLLM Health Check Driven Routing](https://docs.litellm.ai/docs/proxy/health_check_routing) — 官方文件 — 2025
  - 出處：[Google SRE: Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) — 官方書籍/網站 — 2017

- **SLO 不只看 latency，也要看 quality、safety、cost**：至少把 TTFT、TPOT、成功率、tool success rate、hallucination/groundedness proxy、每請求 token/cost、fallback 率納入營運指標；否則延遲看起來健康，產品品質仍可能失控。
  - 出處：[Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) — 官方書籍/網站 — 2017
  - 出處：[LangSmith Observability](https://www.langchain.com/langsmith/observability) — 官方文件 — 2025
  - 出處：[OpenTelemetry GenAI metrics](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/) — 官方規範 — 2026

## 模型選型、推論服務與部署策略

- **模型選型要用「能力 × 速度 × 成本 × 風險」矩陣，不要只看排行榜**：複雜規劃/高風險決策可用 reasoning model，格式化抽取、分類、重寫、檢索後生成可用較快/便宜模型；常見實務是「規劃模型 + 執行模型」分工，而不是所有步驟都用最貴模型。
  - 出處：[OpenAI Reasoning best practices](https://developers.openai.com/api/docs/guides/reasoning-best-practices) — 官方文件 — 2025
  - 出處：[Anthropic Choosing the right model](https://docs.anthropic.com/en/docs/about-claude/models/choosing-a-model) — 官方文件 — 2025
  - 出處：[Anthropic Models overview](https://docs.anthropic.com/en/docs/about-claude/models) — 官方文件 — 2026
  - 出處：[Anthropic Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents) — 技術文章/官方研究 — 2024

- **自建推論與外部 API 要分場景選，不要先入為主**：若需求是資料主權、固定高流量、可控延遲、模型可替換，自建 vLLM / SGLang / KServe / Ray Serve 更合適；若需求是快速上市、全球可用、低維運，外部 API 常更划算。
  - 出處：[vLLM](https://github.com/vllm-project/vllm) — GitHub repo — 持續更新
  - 出處：[SGLang Documentation](https://docs.sglang.io/) — 官方文件 — 2026 查證
  - 出處：[KServe](https://kserve.github.io/website/) — 官方文件 — 2026
  - 出處：[Ray Serve](https://docs.ray.io/en/latest/serve/index.html) — 官方文件 — 2026

- **Serving 引擎的內部排程會直接決定你的毛利**：continuous batching、PagedAttention、chunked prefill、PD disaggregation 都是在改善吞吐/延遲/記憶體效率；如果產品是高併發長輸入，這些能力通常比 benchmark 分數更影響成本。
  - 出處：[vLLM Documentation](https://docs.vllm.ai/) — 官方文件 — 2026
  - 出處：[PagedAttention paper](https://arxiv.org/abs/2309.06180) — 論文 — 2023
  - 出處：[Sarathi-Serve](https://arxiv.org/abs/2403.02310) — 論文 — 2024
  - 出處：[DistServe](https://arxiv.org/abs/2401.09670) — 論文 — 2024
  - 出處：[SGLang PD Disaggregation](https://docs.sglang.io/docs/advanced_features/pd_disaggregation) — 官方文件 — 2026 查證

- **部署策略要支援 canary、shadow、A/B、快速 rollback**：模型升級常同時改變拒答率、工具選擇、格式穩定性與安全行為；promotion 前至少要做流量隔離、回歸評測、老新模型並跑與一鍵回退。
  - 出處：[KServe](https://kserve.github.io/website/) — 官方文件 — 2026
  - 出處：[Ray Serve LLM on Kubernetes](https://docs.ray.io/en/latest/cluster/kubernetes/examples/rayserve-llm-example.html) — 官方文件 — 2026
  - 出處：[Kubeflow Architecture](https://www.kubeflow.org/docs/started/architecture/) — 官方文件 — 2026

- **先做成本控制機制，再放大流量**：優先用 prompt caching、batch/flex、prefix cache、預測輸出、分級模型路由；批次/低優先任務不要占用即時流量池。
  - 出處：[OpenAI Prompt Caching](https://developers.openai.com/api/docs/guides/prompt-caching) — 官方文件 — 2024
  - 出處：[Anthropic Prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — 官方文件 — 2025
  - 出處：[OpenAI Batch API](https://developers.openai.com/api/docs/guides/batch) — 官方文件 — 2025
  - 出處：[OpenAI Flex processing](https://developers.openai.com/api/docs/guides/flex-processing) — 官方文件 — 2025
  - 出處：[OpenAI Predicted Outputs](https://developers.openai.com/api/docs/guides/predicted-outputs) — 官方文件 — 2025

## RAG、知識庫與檢索設計

- **不要預設 RAG 一定比長上下文好，或長上下文一定能取代 RAG**：長上下文在部分 QA benchmark 很強，但 RAG 在 freshness、可追溯、權限過濾、成本與互動式查詢上仍有優勢；真正的選擇應用離線評測與真實查詢分佈決定。
  - 出處：[Long Context RAG Performance of Large Language Models](https://arxiv.org/abs/2411.03538) — 論文 — 2024
  - 出處：[Retrieval Augmented Generation or Long-Context LLMs? A Comprehensive Study](https://arxiv.org/abs/2407.16833) — 論文 — 2024
  - 出處：[RAFT: Adapting Language Model to Domain Specific RAG](https://arxiv.org/abs/2403.10131) — 論文 — 2024
  - 出處：[OpenAI Optimizing LLM Accuracy](https://developers.openai.com/api/docs/guides/optimizing-llm-accuracy) — 官方文件 — 2025

- **檢索鏈路至少要做 chunking、metadata filter、hybrid search、rerank、citation/provenance**：只做 dense vector top-k 通常不夠；實務上 hybrid search + reranker + 權限/租戶過濾，會比單一向量召回穩很多。
  - 出處：[Weaviate Hybrid search](https://docs.weaviate.io/weaviate/search/hybrid) — 官方文件 — 2026
  - 出處：[Milvus Hybrid Search and Reranking in RAG](https://milvus.io/docs/full_text_search_with_milvus.md) — 官方文件 — 2025
  - 出處：[Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval) — 技術文章/官方研究 — 2024
  - 出處：[Pinecone Hybrid Search](https://docs.pinecone.io/guides/search/hybrid-search) — 官方文件 — 2025

- **向量資料庫選型要看既有資料面，不要只看 ANN benchmark**：若團隊已經重度用 Postgres，且規模與查詢型態可控，pgvector 能大幅簡化維運；若需要大型 hybrid search、rerank、生態整合、分散式能力，再考慮 Milvus / Weaviate。
  - 出處：[pgvector](https://github.com/pgvector/pgvector) — GitHub repo — 持續更新
  - 出處：[Weaviate Documentation](https://docs.weaviate.io/weaviate) — 官方文件 — 2026
  - 出處：[Milvus Hybrid Search](https://milvus.io/docs/llamaindex_milvus_hybrid_search.md) — 官方文件 — 2025

- **知識庫要可版本化、可回溯、可重建索引**：文件版本、embedding model 版本、chunking 規則、index alias、TTL、權限標籤都要可追蹤；否則你無法回答「這個回答是基於哪一版知識」或快速回滾壞 index。
  - 出處：[Weaviate in 2025: lifecycle management via aliases and TTL](https://weaviate.io/blog/weaviate-in-2025) — 技術文章/官方 — 2026
  - 出處：[OpenLineage](https://openlineage.io/) — 官方文件 — 2026
  - 出處：[DataHub Features](https://docs.datahub.com/docs/features) — 官方文件 — 2026
  - 出處：[DataHub Metadata Standards](https://docs.datahub.com/docs/metadata-standards) — 官方文件 — 2026

- **對複雜問題才用 Agentic RAG，不要把所有問答都升級成 Agent**：多輪檢索、檢索後反思、重查詢、工具補證據，在複雜任務上有價值；但若問題主要是 FAQ/文件問答，簡單 RAG workflow 通常更可控、更便宜。
  - 出處：[Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval) — 技術文章/官方研究 — 2024
  - 出處：[What Is Agentic RAG?](https://weaviate.io/blog/what-is-agentic-rag) — 技術文章/官方 — 2024
  - 出處：[Self-RAG](https://arxiv.org/abs/2310.11511) — 論文 — 2023
  - 出處：[Agentic Retrieval-Augmented Generation Survey](https://arxiv.org/html/2501.09136v4) — 綜述 — 2026

## Agent、工具調用與 Prompt 管理

- **先做 deterministic workflow，再做 open-ended agent**：大多數企業流程先用「明確狀態機/圖式工作流 + 少量模型決策點」就能滿足；只有在任務需要動態規劃、工具探索、長期記憶時，才值得引入完整 agent。
  - 出處：[Anthropic Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents) — 技術文章/官方研究 — 2024
  - 出處：[LangGraph](https://github.com/langchain-ai/langgraph) — GitHub repo — 持續更新
  - 出處：[LangGraph Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) — 官方文件 — 2026

- **工具要最小權限、型別化、可審計、可補償**：tool schema 要嚴格、作用域要最小、每次工具執行都要帶 audit log；對寫入型工具要支援 dry-run、confirm、timeout、budget、idempotency、compensation/saga。
  - 出處：[Anthropic Tool use overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) — 官方文件 — 2025
  - 出處：[MCP Tools spec](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) — 規範 — 2025
  - 出處：[MCP Client Best Practices](https://modelcontextprotocol.io/docs/develop/clients/client-best-practices) — 官方文件 — 2026
  - 出處：[Anthropic MCP](https://docs.anthropic.com/en/docs/agents-and-tools/mcp) — 官方文件 — 2025

- **高風險動作一定要有人審核節點**：發信、下單、刪改資料、執行 SQL、控制基礎設施、存取機敏文件，都不應完全無人監督；durable checkpoint + interrupt 比單純「再問模型一次」可靠。
  - 出處：[LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) — 官方文件 — 2026
  - 出處：[LangChain Human-in-the-Loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) — 官方文件 — 2026
  - 出處：[LangChain Frontend HITL](https://docs.langchain.com/oss/python/langchain/frontend/human-in-the-loop) — 官方文件 — 2026
  - 出處：[LangGraph Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) — 官方文件 — 2026

- **Prompt 要像程式碼一樣管理，不要散落在 source code 與 Notion**：至少做版本號、變數模板、owner、變更紀錄、對應 eval dataset、對應 trace；prompt 升版不能只靠肉眼驗證。
  - 出處：[MLflow Prompt Registry](https://mlflow.org/docs/latest/genai/prompt-registry/) — 官方文件 — 2026
  - 出處：[MLflow Evaluating Prompts](https://mlflow.org/docs/latest/genai/prompt-registry/evaluate-prompts/) — 官方文件 — 2026
  - 出處：[MLflow Tracing](https://mlflow.org/docs/latest/genai/tracing/) — 官方文件 — 2026

- **Prompt Injection 防護要做在系統外層，不要只靠 system prompt**：把外部文件/網頁/工具輸出一律當不可信來源；做來源標記、權限分離、allowlist tool、輸出淨化、檢索內容隔離、敏感工具前的人審/策略引擎；高風險場景可評估 spotlighting 或資訊流控制類設計。
  - 出處：[OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — 官方文件 — 2025
  - 出處：[Defending Against Indirect Prompt Injection Attacks With Spotlighting](https://arxiv.org/abs/2403.14720) — 論文 — 2024
  - 出處：[System-Level Defense against Indirect Prompt Injection](https://arxiv.org/abs/2409.19091) — 論文 — 2024
  - 出處：[Azure Prompt Shields](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/content-filter-prompt-shields) — 官方文件 — 2026
  - 出處：[OWASP LLM07:2025 System Prompt Leakage](https://genai.owasp.org/llmrisk/llm07-insecure-plugin-design/) — 官方文件 — 2025

- **MCP/遠端工具整合會把安全邊界放大**：要落實 OAuth/OIDC、最小 scope、操作確認、tool input/output 驗證、trace context 與稽核日誌；若工具可碰到檔案系統、資料庫或外部 API，就要視同擴張執行面。
  - 出處：[MCP Security Best Practices](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices) — 官方文件 — 2026
  - 出處：[MCP Authorization](https://modelcontextprotocol.io/docs/tutorials/security/authorization) — 官方文件 — 2026
  - 出處：[OpenTelemetry MCP Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/) — 官方規範 — 2026
  - 出處：[MCP Intro](https://modelcontextprotocol.io/docs/getting-started/intro) — 官方文件 — 2025

## 資料治理、評測與測試

- **資料治理要覆蓋 training data、eval data、RAG corpus、tool outputs，不只看 warehouse**：對每個資料集定義 schema、語義、品質規則、權責人與使用條款；對 AI 製程則要補 lineage、版本與用途標記。
  - 出處：[Data Contract Specification](https://github.com/datacontract/datacontract-specification) — GitHub repo/規範 — 持續更新
  - 出處：[OpenLineage](https://openlineage.io/) — 官方文件 — 2026
  - 出處：[DataHub Features](https://docs.datahub.com/docs/features) — 官方文件 — 2026
  - 出處：[DataHub Metadata Standards](https://docs.datahub.com/docs/metadata-standards) — 官方文件 — 2026

- **文件 ingestion 與資料管線要有「資料單元測試」**：OCR/切 chunk/清洗/embedding/metadata 萃取/權限標籤，每一步都可能造成 RAG 壞掉；先在 pipeline 擋錯，遠比在 LLM 端補救便宜。
  - 出處：[Great Expectations](https://github.com/great-expectations/great_expectations) — GitHub repo — 持續更新
  - 出處：[Data Contract CLI](https://github.com/datacontract/datacontract-cli) — GitHub repo — 持續更新
  - 出處：[OpenLineage GitHub](https://github.com/OpenLineage/OpenLineage) — GitHub repo — 持續更新

- **若系統同時含傳統 ML 與 LLM 決策，特徵一致性要平台化**：像推薦、風控、排序、詐欺偵測這類混合系統，要處理 offline/online feature skew，必要時用 feature store 把傳統特徵 serving 與 LLM 流程整合。
  - 出處：[Feast](https://github.com/feast-dev/feast) — GitHub repo — 持續更新
  - 出處：[Feast RAG example](https://github.com/feast-dev/feast/blob/master/examples/rag/milvus-quickstart.ipynb) — GitHub repo/examples — 持續更新

- **評測要做成金字塔：離線評測、預上線回歸、線上監控、人評校準**：離線用固定資料集比較版本；上線前做 regression/canary；線上追蹤品質與成本；爭議高或高風險案例保留人工審查與標註回流。
  - 出處：[OpenAI Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices) — 官方文件 — 2025
  - 出處：[MLflow End-to-End RAG Evaluation](https://mlflow.org/cookbook/rag-evaluation/) — 官方文件 — 2026
  - 出處：[LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation) — 官方文件 — 2026
  - 出處：[MLflow Agent & LLM datasets](https://mlflow.org/docs/latest/genai/datasets/) — 官方文件 — 2026

- **LLM-as-judge 可以用，但不能無條件相信**：judge 會有偏見、穩定性與校準問題；實務上要做 rubric 固化、跨模型 judge、抽樣人工複核，並把重要任務維持人工黃金集。
  - 出處：[A Survey on LLM-as-a-Judge](https://arxiv.org/abs/2411.15594) — 綜述 — 2024
  - 出處：[Can You Trust LLM Judgments?](https://arxiv.org/abs/2412.12509) — 論文 — 2024
  - 出處：[JudgeBench](https://arxiv.org/abs/2410.12784) — 論文 — 2024

- **測試策略要補上 AI 行為測試與紅隊測試**：除了 unit/integration/E2E，還要測 prompt regression、tool misuse、indirect prompt injection、越權存取、資料外洩、unsafe tool chain；Agent 系統建議持續對照 AgentDojo / Agent-SafetyBench 類 benchmark 思維。
  - 出處：[Agent-SafetyBench](https://arxiv.org/abs/2412.14470) — 論文 — 2024
  - 出處：[AgentDojo](https://arxiv.org/abs/2406.13352) — 論文 — 2024
  - 出處：[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) — GitHub repo — 持續更新
  - 出處：[Promptfoo Assertions and Metrics](https://www.promptfoo.dev/docs/configuration/expected-outputs/) — 官方文件 — 2026 查證

- **把 model、prompt、embedding、index 都當 release artifact 管理**：promotion 應綁定版本、評測報告、owner、rollback 路徑與 alias，而不是靠環境變數或手工改設定檔。
  - 出處：[MLflow Model Registry](https://mlflow.org/docs/latest/ml/model-registry/) — 官方文件 — 2026
  - 出處：[MLflow Prompt Registry](https://mlflow.org/docs/latest/genai/prompt-registry/) — 官方文件 — 2026
  - 出處：[KServe](https://kserve.github.io/website/) — 官方文件 — 2026

## 可觀測性、效能、可靠性與成本

- **觀測性要從 app traces 升級成 LLM traces / agent traces**：至少追 prompt、檢索結果、tool calls、model 版本、token、latency、cost、user/session、grounding 證據；若仍只看應用層 access log，幾乎無法除錯。
  - 出處：[OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — 官方規範 — 2026
  - 出處：[OpenTelemetry GenAI spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/) — 官方規範 — 2026
  - 出處：[OpenInference](https://github.com/Arize-ai/openinference) — GitHub repo — 持續更新
  - 出處：[MLflow Tracing](https://mlflow.org/docs/latest/genai/tracing/) — 官方文件 — 2026

- **品質監控要拆成 retrieval、generation、tooling 三層**：檢索層看 hit rate、rerank 分數、empty retrieval、權限過濾；生成層看 groundedness / refusal / hallucination proxy；工具層看 tool selection、success rate、重試、timeout、side effect。
  - 出處：[OpenTelemetry GenAI metrics](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/) — 官方規範 — 2026
  - 出處：[Phoenix](https://github.com/arize-ai/phoenix) — GitHub repo — 持續更新
  - 出處：[LangSmith Evaluation](https://docs.langchain.com/langsmith/evaluation) — 官方文件 — 2026

- **成本追蹤要做到 request 級與 tenant 級，不要只看月底帳單**：建議記錄每次請求的 provider、model、prompt/completion token、cache hit、embedding cost、retrieval cost、tool cost、人工審核成本，並對 team/project/tenant 做 budget。
  - 出處：[LiteLLM](https://github.com/BerriAI/litellm/) — GitHub repo — 持續更新
  - 出處：[LangSmith Observability](https://www.langchain.com/langsmith/observability) — 官方文件 — 2025
  - 出處：[OpenAI Prompt Caching](https://developers.openai.com/api/docs/guides/prompt-caching) — 官方文件 — 2024
  - 出處：[OpenAI Pricing](https://developers.openai.com/api/docs/pricing) — 官方文件 — 2026

- **效能最佳化要先分清 TTFT、TPOT、throughput、context reuse 的瓶頸**：對聊天/RAG 常見瓶頸不是單純模型慢，而是長 prompt、無快取、錯誤 batch 策略、向量檢索慢、tool call 太多；優先做 prefix/prompt cache、請求分類、併發隔離、adaptive autoscaling。
  - 出處：[vLLM Documentation](https://docs.vllm.ai/) — 官方文件 — 2026
  - 出處：[LiteLLM Health Check Driven Routing](https://docs.litellm.ai/docs/proxy/health_check_routing) — 官方文件 — 2025
  - 出處：[KServe v0.15: LLM Autoscaler with KEDA](https://kserve.github.io/website/blog/kserve-0.15-release) — 官方文章 — 2025
  - 出處：[OpenAI Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization) — 官方文件 — 2025

- **快取要分層做，但要避免把錯答案快取放大**：可分成 prompt/prefix cache、retrieval cache、embedding cache、工具結果 cache、片段 response cache；對受權限、時效、個資、外部狀態影響的內容，要加 tenant scope、TTL、cache invalidation 與 provenance。
  - 出處：[OpenAI Prompt Caching](https://developers.openai.com/api/docs/guides/prompt-caching) — 官方文件 — 2024
  - 出處：[Anthropic Prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — 官方文件 — 2025
  - 出處：[Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval) — 技術文章/官方研究 — 2024

- **可靠性策略要明確定義 fallback 順序，不要任由 SDK 自由發揮**：先同模型不同 deployment，再同能力不同模型，最後才降到低能力模型或純檢索/純模板模式；同時加上健康檢查與流量摘除。
  - 出處：[LiteLLM Router](https://docs.litellm.ai/docs/routing) — 官方文件 — 2025
  - 出處：[LiteLLM Proxy Load Balancing](https://docs.litellm.ai/docs/proxy/load_balancing) — 官方文件 — 2025
  - 出處：[LiteLLM Health Check Driven Routing](https://docs.litellm.ai/docs/proxy/health_check_routing) — 官方文件 — 2025
  - 出處：[Google SRE: Addressing Cascading Failures](https://sre.google/sre-book/addressing-cascading-failures/) — 官方書籍/網站 — 2017

## 安全、隱私、合規與開源技術棧

- **認證與祕密管理要用短期憑證，不要把長期 API key 散在環境變數或 CI**：優先採 workload identity federation / OIDC / managed identity / SPIFFE，搭配 secret manager、scope 分離與 key rotation。
  - 出處：[OpenAI Workload identity federation](https://developers.openai.com/api/docs/guides/workload-identity-federation) — 官方文件 — 2026
  - 出處：[OpenAI WIF for Kubernetes](https://developers.openai.com/api/docs/guides/workload-identity-federation/kubernetes) — 官方文件 — 2026
  - 出處：[OpenAI WIF for SPIFFE](https://developers.openai.com/api/docs/guides/workload-identity-federation/spiffe) — 官方文件 — 2026
  - 出處：[Google Secret Manager best practices](https://docs.cloud.google.com/secret-manager/docs/best-practices) — 官方文件 — 2026

- **資料隱私要在供應商選型前就定義邊界**：要釐清哪些資料可送外部模型、保留多久、是否訓練回流、是否支援 ZDR、是否需 region pinning、是否需 tenant isolation/HIPAA/BAA；不要等法務問才補。
  - 出處：[OpenAI Data controls](https://developers.openai.com/api/docs/guides/your-data) — 官方文件 — 2026
  - 出處：[Anthropic Zero Data Retention](https://docs.anthropic.com/en/docs/build-with-claude/zero-data-retention) — 官方文件 — 2026
  - 出處：[Anthropic Messages API patterns](https://docs.anthropic.com/en/api/prompt-validation) — 官方文件 — 2026

- **Safety/filtering/guardrails 應是獨立控制層，不要只靠 system prompt**：輸入前做 moderation / jailbreak detection / prompt shield，輸出後做政策驗證、格式驗證、敏感資料檢查；需要時再接人工審核。
  - 出處：[OpenAI Safety best practices](https://developers.openai.com/api/docs/guides/safety-best-practices) — 官方文件 — 2025
  - 出處：[Azure AI Content Safety](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/overview) — 官方文件 — 2026
  - 出處：[OpenAI Guardrails Python](https://github.com/openai/openai-guardrails-python) — GitHub repo — 2025
  - 出處：[OWASP LLM07:2025 System Prompt Leakage](https://genai.owasp.org/llmrisk/llm07-insecure-plugin-design/) — 官方文件 — 2025

- **治理機制要先定義責任人，再談上線**：至少明確區分 product owner、後端 owner、模型 owner、資料 owner、資安、法遵、SRE；高風險場景要有 pre-deployment testing、incident disclosure、人工覆核與 audit trail。
  - 出處：[NIST AI RMF 1.0](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf?source=download) — 官方框架 — 2023
  - 出處：[NIST AI 600-1 Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) — 官方框架 — 2024
  - 出處：[EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng) — 法規原文 — 2024
  - 出處：[EU GPAI Code of Practice](https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai) — 官方文件 — 2025

- **模型供應鏈與序列化風險不能忽略**：自建模型時要掃描模型檔、鏡像、套件與反序列化格式；RAG 與 agent 也要把 data poisoning / adversarial inputs 納入 threat model。
  - 出處：[ModelScan](https://github.com/protectai/modelscan) — GitHub repo — 持續更新
  - 出處：[NIST Adversarial ML Taxonomy](https://csrc.nist.gov/pubs/ai/100/2/e2025/final) — 官方文件 — 2025
  - 出處：[AWS Security considerations for data in generative AI](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-data-considerations-gen-ai/security.html) — 官方文件 — 2025

- **小到中型團隊的 OSS 技術棧建議**：`FastAPI/Go API + Postgres/pgvector + Redis + LiteLLM + LangGraph + vLLM + MLflow + Phoenix/OpenInference + Great Expectations + Promptfoo/Inspect AI`；重點是減少元件數、先把 version/eval/trace 打通。
  - 出處：[pgvector](https://github.com/pgvector/pgvector) — GitHub repo — 持續更新
  - 出處：[LiteLLM](https://github.com/BerriAI/litellm/) — GitHub repo — 持續更新
  - 出處：[LangGraph](https://github.com/langchain-ai/langgraph) — GitHub repo — 持續更新
  - 出處：[vLLM](https://github.com/vllm-project/vllm) — GitHub repo — 持續更新
  - 出處：[MLflow](https://mlflow.org/) — 官方文件/開源平台 — 2026
  - 出處：[Phoenix](https://github.com/arize-ai/phoenix) — GitHub repo — 持續更新
  - 出處：[Great Expectations](https://github.com/great-expectations/great_expectations) — GitHub repo — 持續更新
  - 出處：[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) — GitHub repo — 持續更新
  - 出處：[Promptfoo](https://github.com/promptfoo/promptfoo) — GitHub repo — 持續更新

- **平台型/多團隊/高合規場景的 OSS 技術棧建議**：`Kubernetes + KServe 或 Ray Serve + vLLM/SGLang + LiteLLM gateway + OpenTelemetry/OpenInference + MLflow + OpenLineage + DataHub + Great Expectations + Feast + LangGraph + Inspect AI`；重點是多租戶隔離、標準化 rollout、可稽核與可追溯。
  - 出處：[KServe](https://kserve.github.io/website/) — 官方文件 — 2026
  - 出處：[Ray Serve](https://docs.ray.io/en/latest/serve/index.html) — 官方文件 — 2026
  - 出處：[SGLang](https://docs.sglang.io/) — 官方文件 — 2026 查證
  - 出處：[OpenTelemetry GenAI](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — 官方規範 — 2026
  - 出處：[OpenLineage](https://openlineage.io/) — 官方文件 — 2026
  - 出處：[DataHub](https://docs.datahub.com/docs/introduction) — 官方文件 — 2026
  - 出處：[Great Expectations](https://github.com/great-expectations/great_expectations) — GitHub repo — 持續更新
  - 出處：[Feast](https://github.com/feast-dev/feast) — GitHub repo — 持續更新
  - 出處：[LangGraph](https://github.com/langchain-ai/langgraph) — GitHub repo — 持續更新
  - 出處：[Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) — GitHub repo — 持續更新

## 最新開源專案與對應清單考量點

- **工具協議優先評估 MCP，但不要把 MCP 當成安全邊界本身**（對應 Agent、工具調用）：2024 年 11 月 Anthropic 推出並開源 Model Context Protocol；官方定位是讓 AI application 透過 MCP client 連到 MCP server，標準化存取外部資料、工具與 workflow。MCP Tools 規範支援 `tools/list` 自動列舉與 `tools/call` 調用，適合取代每個工具各自定義一套 ad hoc API；但敏感 tool 仍必須做權限、確認提示、輸入驗證、輸出淨化、timeout 與 audit log。
  - 出處：[Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol) — 官方公告 — 2024
  - 出處：[MCP Intro](https://modelcontextprotocol.io/docs/getting-started/intro) — 官方文件 — 2026 查證
  - 出處：[MCP Tools spec](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) — 規範 — 2025

- **多 Agent / 跨系統協作才評估 A2A，不要把單一後端內部流程過早拆成 agent 網路**（對應 Agent、服務切分）：A2A 是 Agent2Agent protocol，官方定位是讓不同框架、不同供應商、甚至不同伺服器上的 agent 可以 discover capability、協作長任務，且不必暴露內部 memory、tools 或 proprietary logic。它和 MCP 是互補關係：MCP 處理 agent-to-tool/data，A2A 處理 agent-to-agent；若目前只是單一後端服務內的 deterministic workflow，先用 LangGraph / queue / service boundary 即可，等真的需要跨團隊、跨產品、跨 vendor agent 協作時再導入 A2A。
  - 出處：[A2A Protocol](https://a2a-protocol.org/latest/) — 官方文件 — 2026 查證
  - 出處：[A2A GitHub](https://github.com/a2aproject/A2A) — GitHub repo — 持續更新
  - 出處：[Google Developers Blog: Agent2Agent Protocol](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) — 官方公告 — 2025

- **Agent/RAG 高重複 Prompt 場景可評估 SGLang，但要用自己的流量壓測，不宜保證一定優於 vLLM**（對應推論服務與部署）：SGLang 官方文件將其定位為高效能 LLM / multimodal serving framework，支援 RadixAttention、prefix caching 與多 GPU 推論；原始 LMSYS 技術文與論文指出 RadixAttention 會用 radix tree 自動重用 KV cache，對多輪對話、few-shot、agent、RAG 等有共享 prefix 的 workload 特別有利。DeepSeek-V3/R1 文件也列出 vLLM 與 SGLang 作為可用部署方式；因此比較合理的寫法是「在高 prefix reuse 場景優先納入 benchmark」，而不是做通用優劣結論。
  - 出處：[SGLang Documentation](https://docs.sglang.io/) — 官方文件 — 2026 查證
  - 出處：[Fast and Expressive LLM Inference with RadixAttention and SGLang](https://www.lmsys.org/blog/2024-01-17-sglang/) — 官方技術文 — 2024
  - 出處：[DeepSeek-V3](https://github.com/deepseek-ai/DeepSeek-V3) — GitHub repo — 持續更新
  - 出處：[SGLang](https://github.com/sgl-project/sglang) — GitHub repo — 持續更新

- **用 LangGraph 狀態圖突破線性 RAG 限制**（對應 RAG、知識庫與檢索設計）：將流程建成 state graph，讓檢索、生成、評估、重新檢索與人工審核成為明確節點與條件邊；這適合 Agentic RAG、Corrective RAG、Evaluator-Optimizer 這類需要回圈與條件轉移的任務，但簡單 FAQ / 文件問答仍不一定需要升級成 agent。
  - 出處：[LangGraph](https://github.com/langchain-ai/langgraph) — GitHub repo — 持續更新
  - 出處：[LangGraph Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) — 官方文件 — 2026 查證
  - 出處：[What Is Agentic RAG?](https://weaviate.io/blog/what-is-agentic-rag) — 技術文章/官方 — 2024

- **把文件解析 / ingestion 當成一級元件，可評估 Docling 這類結構化轉換工具**（對應 RAG、知識庫與檢索設計）：RAG 品質常敗在 PDF、表格、簡報、掃描圖、標題階層與 reading order 解析錯誤，而不是敗在模型本身。Docling 可把 PDF、DOCX、PPTX、HTML、圖片等轉成 Markdown / JSON / DoclingDocument，並保留文字、表格、版面與 OCR 結果，適合放在 ingestion pipeline 的前段；採用時要同步保存原檔 hash、parser 版本、chunking 規則與轉換後 artifact，方便重建 index 與追查錯誤回答來源。
  - 出處：[Docling Documentation](https://docling-project.github.io/docling/) — 官方文件 — 2026 查證
  - 出處：[Docling GitHub](https://github.com/docling-project/docling) — GitHub repo — 持續更新
  - 出處：[Docling Technical Report](https://arxiv.org/abs/2408.09869) — 論文/技術報告 — 2024

- **用 Phoenix/OpenInference 落實 OTel 相容的 GenAI 觀測，但要標註 OTel GenAI conventions 仍在 Development 狀態**（對應評測、可觀測性）：Phoenix 是開源 AI observability / evaluation 平台，使用 OpenTelemetry-based instrumentation；OpenInference 提供補足 LLM、retrieval、tool/API 使用脈絡的 tracing conventions 與多框架 instrumentation。OpenTelemetry 官方 GenAI semantic conventions 可作為 no-vendor-lock-in 的目標，但目前頁面明確標示 Status: Development，所以實作時要接受欄位命名與相容性可能變動。
  - 出處：[Phoenix](https://github.com/arize-ai/phoenix) — GitHub repo — 持續更新
  - 出處：[OpenInference](https://github.com/Arize-ai/openinference) — GitHub repo — 持續更新
  - 出處：[OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — 官方規範 — 2026 查證

- **RAG / Agent 評測要補 Ragas 或 DeepEval，不要只看 demo 主觀覺得準**（對應評測、測試與 CI）：Ragas 提供 context precision/recall、faithfulness、response relevancy、tool call accuracy、agent goal accuracy 等評測方向，也支援 testset generation 與 workflow/agent evaluation；DeepEval 則偏向把 LLM eval 寫成測試，支援 end-to-end eval、component-level eval、CI/CD、RAG、agentic、multi-turn 與 safety 指標。採用時要把 evaluation dataset、judge prompt、judge model、threshold、抽樣人工複核規則一起版本化；LLM-as-judge 只能當品質訊號，不應當唯一上線閘門。
  - 出處：[Ragas Documentation](https://docs.ragas.io/en/stable/) — 官方文件 — 2026 查證
  - 出處：[Ragas GitHub](https://github.com/vibrantlabsai/ragas) — GitHub repo — 持續更新
  - 出處：[DeepEval Documentation](https://deepeval.com/docs/getting-started) — 官方文件 — 2026 查證
  - 出處：[DeepEval GitHub](https://github.com/confident-ai/deepeval) — GitHub repo — 持續更新

- **用 NeMo Guardrails 建立可測試的安全控制層，不要只靠 System Prompt**（對應安全性與防護）：NVIDIA NeMo Guardrails 是開源 programmable guardrails 工具，可放在 application code 與 LLM 之間，支援 input、dialog、retrieval、execution、output rails；官方也提供 Llama Guard input/output moderation 整合。它可以降低 prompt injection、jailbreak、敏感資料輸出與不安全工具調用風險，但 OWASP 明確指出 prompt injection 沒有 fool-proof 防法，所以需要搭配 least privilege、人審、權限隔離、紅隊測試與觀測紀錄。
  - 出處：[NeMo Guardrails](https://github.com/NVIDIA-NeMo/Guardrails) — GitHub repo — 持續更新
  - 出處：[NeMo Guardrails Llama Guard integration](https://docs.nvidia.com/nemo/guardrails/latest/configure-guardrails/guardrail-catalog/third-party/llama-guard) — 官方文件 — 2026 查證
  - 出處：[OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — 官方文件 — 2025

- **觀測、報告與 prompt 測試前先做 PII / secret 去識別化，可評估 Presidio 類工具**（對應安全性、隱私與觀測性）：AI trace、retrieval context、tool arguments、eval dataset、錯誤報告很容易把病歷、token、API key、連線字串、個資一起保存到 Phoenix/Langfuse/CI artifact。Microsoft Presidio 可做文字、圖片、半結構化資料的 PII detection、masking、anonymization；但官方也提醒自動偵測不能保證找出所有敏感資訊，所以它應該是 defense-in-depth 的一層，搭配 secret scanner、allowlist/denylist、欄位級 redaction、取樣人工複核與資料保存期限。
  - 出處：[Microsoft Presidio](https://microsoft.github.io/presidio/) — 官方文件 — 2026 查證
  - 出處：[Presidio GitHub](https://github.com/microsoft/presidio) — GitHub repo — 持續更新

## 能夠吸引使用者的 UX/DX 設計要點

### 終端使用者體驗（UX）亮點

- **「進度軌跡」透明化，用 SSE / streaming 推播 Agent 狀態而非轉圈等待**：當 Agent 執行耗時檢索或分析時，透過 Server-Sent Events 或等效 streaming channel 即時推播狀態轉移（例如：檢索知識庫中 → 正在分析 docker-compose.yml → 發現資料庫節點）。OpenAI latency 文件也建議在多步驟或 tool 使用時讓使用者看到真實進度；這裡應顯示「可揭露的工作狀態」，不要暴露完整 chain-of-thought 或敏感 prompt。
  - 出處：[CopilotKit](https://github.com/CopilotKit/CopilotKit) — GitHub repo — 持續更新
  - 出處：[MDN Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) — 官方文件 — 2026 查證
  - 出處：[OpenAI Streaming responses](https://developers.openai.com/api/docs/guides/streaming-responses) — 官方文件 — 2026 查證
  - 出處：[OpenAI Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization) — 官方文件 — 2026 查證

- **Agent 前端互動可評估 AG-UI，不要只把 SSE 當成文字 token stream**：AG-UI 是 Agent-User Interaction protocol，定位是把 agentic backend 和 user-facing frontend 之間的事件流標準化；它涵蓋 run lifecycle、message streaming、tool call、tool result、state snapshot/delta、error event、interrupt、人審、generative UI、frontend tool call 與 backend tool rendering。對 Systograph 這類 readiness / scan report 產品，這代表前端可以即時渲染「正在掃描哪個檔案、哪個檢查點通過、哪個 evidence 需要使用者確認」，而不是等最後一次性吐出長報告。
  - 出處：[AG-UI Documentation](https://docs.ag-ui.com/introduction) — 官方文件 — 2026 查證
  - 出處：[AG-UI GitHub](https://github.com/ag-ui-protocol/ag-ui) — GitHub repo — 持續更新

- **互動式與漸進式 UI（Generative UI），跳脫純文字對話**：後端不回傳渲染好的 HTML，而是回傳 Tool Call JSON（例如 `{"name": "render_db_node", "data": {...}}`），前端攔截後動態渲染 React/Vue 元件（資料庫圖示、互動式圖表等），提供超越傳統 Chatbot 的豐富互動體驗。
  - 出處：[Vercel AI SDK Generative UI](https://ai-sdk.dev/docs/ai-sdk-ui/generative-user-interfaces) — 官方文件 — 2026 查證
  - 出處：[CopilotKit](https://github.com/CopilotKit/CopilotKit) — GitHub repo — 持續更新

- **高風險工具要有可中斷、可批准、可修改、可重試的操作 UI**：只在後端寫 `confirm=true` 不夠；使用者需要看懂 agent 想做什麼、會影響哪些資源、使用哪些 evidence、批准後是否可 rollback。對刪改資料、發信、部署、執行 SQL、讀取敏感檔案、外部網路請求等操作，UI 應提供 diff/preview、scope、理由、風險標籤、approve/reject/edit/retry/escalate，並把決策寫進 audit trail。
  - 出處：[AG-UI Interrupts](https://docs.ag-ui.com/concepts/interrupts) — 官方文件 — 2026 查證
  - 出處：[LangGraph Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) — 官方文件 — 2026 查證

- **優化 TTFT，但不要承諾長上下文一定幾百毫秒出首字**：後端推論引擎可評估 RadixAttention / prefix cache、chunked prefill、prompt caching、streaming 與請求分類；這些方法能降低使用者感知等待或在高 prefix reuse workload 改善 first-token latency，但實際 TTFT 仍取決於模型大小、硬體、context 長度、併發、batching 與 cache hit，因此報告中不應寫成固定 SLA。
  - 出處：[SGLang Documentation](https://docs.sglang.io/) — 官方文件 — 2026 查證
  - 出處：[Fast and Expressive LLM Inference with RadixAttention and SGLang](https://www.lmsys.org/blog/2024-01-17-sglang/) — 官方技術文 — 2024
  - 出處：[OpenAI Latency optimization](https://developers.openai.com/api/docs/guides/latency-optimization) — 官方文件 — 2025

### 開發者體驗（DX）亮點

- **觀測標準要 No-Vendor-Lock-in，優先對齊 OpenTelemetry / OpenInference，但保留版本隔離層**：將 model call、retriever、tool execution 包成 trace/span/event，監控資料可送到 Phoenix、Grafana、Datadog 或其他 OTel-compatible backend；但因 OTel GenAI conventions 仍是 Development，實作上要在內部 schema 與外部 exporter 之間保留 mapping layer，避免規範變動直接打破報表。
  - 出處：[OpenTelemetry GenAI spans](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/) — 官方規範 — 2026 查證
  - 出處：[OpenInference](https://github.com/Arize-ai/openinference) — GitHub repo — 持續更新
  - 出處：[Langfuse](https://github.com/langfuse/langfuse) — GitHub repo — 持續更新
  - 出處：[Phoenix](https://github.com/arize-ai/phoenix) — GitHub repo — 持續更新

- **Prompt 測試要程式碼化，修改後自動驗證無 regression**：將提示詞測試納入 CI；修改 System Prompt 後，自動化測試確保邏輯不倒退，讓 Prompt 工程從「玄學」變成真正的軟體工程，以 Assertion 驗證模型輸出。
  - 出處：[Promptfoo](https://github.com/promptfoo/promptfoo) — GitHub repo — 持續更新
  - 出處：[Promptfoo Assertions and Metrics](https://www.promptfoo.dev/docs/configuration/expected-outputs/) — 官方文件 — 2026 查證

- **本地開發要支援無痛沙盒與 Mock，兼顧成本與隱私**：本地開發時能無縫切換到本地模型或 Mock 回應；加速開發流程、節省 API 成本，並在開發初期保護敏感專案資料（符合 Local-first Privacy）。
  - 出處：[LiteLLM](https://github.com/BerriAI/litellm/) — GitHub repo — 持續更新
  - 出處：[LiteLLM Mock Completion Responses](https://docs.litellm.ai/docs/completion/mock_requests) — 官方文件 — 2026 查證
  - 出處：[LiteLLM Ollama Provider](https://docs.litellm.ai/docs/providers/ollama) — 官方文件 — 2026 查證
  - 出處：[Ollama](https://github.com/ollama/ollama) — GitHub repo — 持續更新



# 三、審查分類

請將所有問題與建議依照以下分類整理：

1. UI/UX
   - 使用者流程是否清楚
   - 介面是否直覺
   - 錯誤狀態、載入狀態、空狀態是否完整
   - 資訊架構是否合理
   - 是否符合使用者任務與產品目標

2. 前端工程
   - 元件結構是否清楚
   - 狀態管理是否合理
   - API 呼叫是否安全且可維護
   - 表單驗證與錯誤處理是否完整
   - 效能、可讀性、可測試性是否足夠
   - 是否有重複邏輯或不必要的複雜度

3. 後端工程
   - API 設計是否一致
   - 錯誤處理是否完整
   - 權限、驗證、日誌、例外處理是否合理
   - 業務邏輯是否清楚分層
   - 是否有可維護性、可擴充性或效能問題

4. 後端 AI
   - Prompt 設計是否清楚且安全
   - AI 回覆是否有足夠約束
   - RAG / 向量搜尋 / 工具調用流程是否合理
   - 是否有 hallucination、prompt injection、資料外洩風險
   - 是否有評估、監控、fallback、guardrails
   - AI 輸出是否可追蹤、可驗證、可控

5. 資料庫
   - schema 設計是否合理
   - 關聯設計是否清楚
   - indexing 是否足夠
   - migration 是否安全
   - query 是否有效率
   - 是否有資料一致性、資料完整性或擴充性問題

6. 資安
   - 身分驗證與授權是否正確
   - 是否有敏感資料外洩風險
   - 是否有 SQL injection、XSS、CSRF、SSRF、RCE 等風險
   - 環境變數與 secrets 是否妥善管理
   - API 是否有 rate limit、輸入驗證與權限檢查
   - AI 相關資安風險是否被處理，例如 prompt injection、資料外洩、越權查詢

# 四、來源引用要求

你必須為每一項問題提供明確來源引用。

來源引用請依照類型分類，並包含：

- 檔案路徑
- 函式、元件、class、API route 或資料表名稱
- 相關行號或程式碼片段
- 為什麼該來源支持你的判斷

引用格式如下：

【來源分類】：UI/UX / 前端工程 / 後端工程 / 後端 AI / 資料庫 / 資安
【檔案】：path/to/file
【位置】：第 X-Y 行，或函式 / 元件 / class 名稱
【證據】：引用或摘要相關程式碼
【判斷原因】：說明為什麼這裡構成問題或改進點

如果無法取得行號，請改用「檔案路徑 + 函式 / 元件 / class / route 名稱 + 具體程式碼片段」作為引用依據。

禁止沒有來源的泛泛而談。
禁止在沒有實際讀過檔案的情況下假設問題存在。
如果某個分類沒有發現明確問題，也請寫出「未發現明確問題」並說明你檢查了哪些檔案。

# 五、審查輸出格式

請依照以下格式輸出：

## 1. 總覽摘要

請用 5-10 點整理這個 AI 系統目前最重要的問題與改善方向。

每一點都要標示影響程度：

- Critical：會造成資安、資料外洩、系統不可用或重大業務風險
- High：會嚴重影響穩定性、正確性、可維護性或使用者體驗
- Medium：有明顯改進空間，但不是立即阻斷
- Low：可優化但不急迫

## 2. 檔案檢查清單

請列出你實際檢查過的檔案，格式如下：

| 檔案路徑 | 類型 | 是否發現問題 | 主要觀察 |
|---|---|---|---|

## 3. 分類問題與改善建議

請依照以下分類輸出：

### A. UI/UX

每個問題請使用以下格式：

#### 問題 A-1：問題標題
- 嚴重程度：Critical / High / Medium / Low
- 來源引用：
  - 檔案：
  - 位置：
  - 證據：
- 問題說明：
- 為什麼需要改進：
- 具體改善建議：
- 預期改善效果：
- 相關影響範圍：

### B. 前端工程

使用同樣格式逐項列出。

### C. 後端工程

使用同樣格式逐項列出。

### D. 後端 AI

使用同樣格式逐項列出。

### E. 資料庫

使用同樣格式逐項列出。

### F. 資安

使用同樣格式逐項列出。

## 4. 跨分類問題

請整理那些同時影響多個分類的問題，例如：

- 前端與後端 API 契約不一致
- AI 輸出格式沒有被後端驗證，導致前端顯示錯誤
- 資料庫 schema 不支援 AI 系統需要的追蹤紀錄
- 權限設計同時影響後端、資料庫與資安
- UI 沒有呈現 AI 回覆來源，導致信任度不足

格式如下：

| 問題 | 影響分類 | 來源引用 | 風險 | 建議 |
|---|---|---|---|---|

## 5. 優先修正路線圖

請按照以下時間順序提出改善計畫：

### 立即處理
適合修正 Critical / High 問題。

### 短期處理
適合修正 Medium 問題。

### 中期處理
適合改善架構、可維護性、可觀測性與測試覆蓋率。

每一項請包含：

- 任務名稱
- 對應問題
- 建議負責角色：UI/UX、前端、後端、AI、DBA、資安
- 預期效益
- 可能風險
- 驗收標準

## 6. 最終結論

請總結：

- 目前系統最大的 3 個風險
- 最應該優先修正的 5 件事
- 哪些地方已經做得不錯
- 若要讓系統達到可上線或可擴充狀態，還需要補齊什麼

# 六、重要規則

1. 你必須根據實際檔案內容分析，不可以憑空假設。
2. 每一項問題都必須有來源引用。
3. 來源引用必須分類為：UI/UX、前端工程、後端工程、後端 AI、資料庫、資安。
4. 請逐個檔案檢查，並列出檔案檢查清單。
5. 對每個問題都要說明「為什麼這是問題」以及「為什麼需要改進」。
6. 改善建議必須具體到可以交給工程師執行。
7. 若資訊不足，請明確標示「資訊不足」，並說明還需要哪些檔案或背景資料。
8. 不要只給概念性建議，請提供可落地的修正方向。
9. 請避免過度簡化，必須全面、詳細、逐項分析。
10. 請使用繁體中文，並採用台灣常用工程術語。