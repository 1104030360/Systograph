const layers = [
  {
    id: "input",
    title: "1. Input & Intent Plane",
    description: "理解使用者、任務與上下文。",
  },
  {
    id: "control",
    title: "2. Control Plane",
    description: "決定怎麼解題、是否查詢、何時停止。",
  },
  {
    id: "ingestion",
    title: "3. Ingestion & Indexing Plane",
    description: "載入、切分並建立可供檢索使用的索引資料。",
  },
  {
    id: "retrieval",
    title: "4. Retrieval Plane",
    description: "從文字、圖、記憶與多模態索引取回候選。",
  },
  {
    id: "extensions",
    title: "5. Extension Subsystems Plane",
    description: "Graph、Memory、多模態與協作式 RAG 的可展開子系統。",
  },
  {
    id: "evidence",
    title: "6. Evidence Plane",
    description: "排序、驗證、整理可引用證據。",
  },
  {
    id: "generation",
    title: "7. Generation Plane",
    description: "組 context、呼叫模型、工具與輸出 guardrail。",
  },
  {
    id: "memory",
    title: "8. Memory & State Plane",
    description: "管理 session state、短期記憶、長期記憶與持久化更新。",
  },
  {
    id: "governance",
    title: "9. Governance & Observability Plane",
    description: "彙整治理證據、trace、eval、成本與 latency 觀測。",
  },
  {
    id: "topology",
    title: "10. Deployment Topology Plane",
    description: "單機、client-server、多 agent、tool network 與 federated 邊界。",
  },
];

const source = (...items) => items;

const nodes = [
  {
    id: "user_input",
    layer: "input",
    label: "User Input",
    kind: "primitive",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "使用者需求、檔案、對話或外部事件的入口。",
    inputs: ["message", "file", "event"],
    outputs: ["raw_request"],
    contracts: ["InputEnvelope"],
    risks: ["ambiguous intent", "prompt injection"],
    metrics: ["parse success", "unsafe input rate"],
    sources: source("code: app/routes/chat", "trace: request.input", "doc: UX import boundary"),
    tags: ["overview", "known", "dataflow", "risk", "source"],
  },
  {
    id: "session_context",
    layer: "input",
    label: "Session Context",
    kind: "context",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "把當前 session、user profile、權限與歷史任務變成可用上下文。",
    inputs: ["raw_request", "session_id"],
    outputs: ["context"],
    contracts: ["SessionContext"],
    risks: ["cross-user leakage"],
    metrics: ["context size", "ACL hit rate"],
    sources: source("config: auth.session", "trace: session.load", "doc: privacy boundary"),
    tags: ["overview", "known", "dataflow", "memory", "governance", "risk", "source"],
  },
  {
    id: "query_classifier",
    layer: "input",
    label: "Query Classifier",
    kind: "router",
    nodeType: "known",
    mode: "predefined",
    topology: "single-process",
    summary: "判斷任務類型、需要的資料來源與是否進入 agentic loop。",
    inputs: ["raw_request", "context"],
    outputs: ["intent", "route_hint"],
    contracts: ["IntentProfile"],
    risks: ["wrong route"],
    metrics: ["route accuracy", "fallback rate"],
    sources: source("code: classifier.intent()", "config: routes.intent_map", "trace: intent.classified"),
    tags: ["overview", "known", "dataflow", "control", "retrieval", "mode", "source"],
  },
  {
    id: "planner",
    layer: "control",
    label: "Planner",
    kind: "agentic",
    nodeType: "known",
    mode: "agentic",
    topology: "agent-runtime",
    summary: "把目標拆成步驟，產生查詢、工具與驗證計畫。",
    inputs: ["intent", "route_hint"],
    outputs: ["plan"],
    contracts: ["PlanStep[]"],
    risks: ["over-planning", "unbounded task"],
    metrics: ["steps per task", "plan repair rate"],
    sources: source("code: agent/planner", "trace: plan.created", "doc: control plane"),
    tags: ["overview", "known", "control", "mode", "risk", "source"],
  },
  {
    id: "router",
    layer: "control",
    label: "Router",
    kind: "router",
    nodeType: "known",
    mode: "hybrid",
    topology: "agent-runtime",
    summary: "把每個 step 指派給 retriever、tool、LLM 或 approval gate。",
    inputs: ["plan", "context"],
    outputs: ["route"],
    contracts: ["RouteDecision"],
    risks: ["wrong tool", "cost spike"],
    metrics: ["route latency", "tool success rate"],
    sources: source("code: router.dispatch()", "config: tool_registry", "trace: route.selected"),
    tags: ["overview", "known", "control", "runtime", "mode", "risk", "source"],
  },
  {
    id: "agent_loop",
    layer: "control",
    label: "Agent Loop",
    kind: "agentic",
    nodeType: "known",
    mode: "agentic",
    topology: "agent-runtime",
    summary: "根據工具結果與證據不足狀態，決定 retry、補查或收斂。",
    inputs: ["route", "tool_result", "evidence_gap"],
    outputs: ["next_action", "done"],
    contracts: ["AgentState"],
    risks: ["loop runaway", "tool misuse"],
    metrics: ["iterations", "timeout rate"],
    sources: source("code: agent/loop", "trace: loop.iteration", "config: max_steps"),
    tags: ["overview", "known", "control", "runtime", "mode", "risk", "source"],
  },
  {
    id: "unmapped_orchestrator",
    layer: "control",
    label: "Orchestrator",
    kind: "unmapped",
    nodeType: "unmapped",
    mode: "unknown",
    topology: "unknown",
    summary: "掃描到 workflow 或 agent-like 呼叫鏈，但目前沒有 adapter 能可靠判斷其控制語意。",
    inputs: ["detected_calls"],
    outputs: ["extension_candidate"],
    contracts: ["UnmappedComponent"],
    risks: ["misclassification", "hidden side effects"],
    metrics: ["evidence count", "confidence gap"],
    sources: source("code: custom/workflow.py", "trace: missing span", "doc: no known adapter"),
    tags: ["overview", "unmapped", "control", "mode", "risk", "source"],
  },
  {
    id: "stop_policy",
    layer: "control",
    label: "Stop Policy",
    kind: "policy",
    nodeType: "known",
    mode: "predefined",
    topology: "agent-runtime",
    summary: "限制迴圈、成本、工具次數與 unsupported answer。",
    inputs: ["AgentState", "budget"],
    outputs: ["continue_or_stop"],
    contracts: ["StopDecision"],
    risks: ["premature stop", "budget overrun"],
    metrics: ["stop reason", "cost per answer"],
    sources: source("config: limits.max_steps", "trace: stop.reason", "doc: SLA policy"),
    tags: ["overview", "known", "control", "governance", "runtime", "mode", "risk", "source"],
  },
  {
    id: "approval_gate",
    layer: "control",
    label: "Human Approval Gate",
    kind: "governance",
    nodeType: "known",
    mode: "human_gated",
    topology: "client-server",
    summary: "高風險工具、外部寫入或敏感資料輸出前的人類審核點。",
    inputs: ["action_request", "risk_level"],
    outputs: ["approved_action", "denial"],
    contracts: ["ApprovalRequest"],
    risks: ["missing approval"],
    metrics: ["approval latency", "denial rate"],
    sources: source("code: approvals/request", "config: high_risk_tools", "trace: approval.decision"),
    tags: ["overview", "known", "control", "governance", "mode", "risk", "source"],
  },
  {
    id: "document_loader",
    layer: "ingestion",
    label: "Document Loader",
    kind: "data",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "載入文件、網頁、檔案或 connector 資料。",
    inputs: ["source_ref"],
    outputs: ["documents"],
    contracts: ["Document[]"],
    risks: ["stale data", "permission mismatch"],
    metrics: ["load errors", "freshness"],
    sources: source("code: ingestion/loaders", "config: connectors", "trace: document.loaded"),
    tags: ["overview", "known", "dataflow", "ingestion", "retrieval", "governance", "risk", "source"],
  },
  {
    id: "parser",
    layer: "ingestion",
    label: "Parser",
    kind: "data",
    nodeType: "known",
    mode: "deterministic",
    topology: "single-process",
    summary: "解析文件格式並保留文字、結構與來源位置。",
    inputs: ["documents"],
    outputs: ["parsed_documents"],
    contracts: ["ParsedDocument[]"],
    risks: ["format loss", "unsafe parser"],
    metrics: ["parse success", "unsupported format rate"],
    sources: source("code: ingestion/parsers", "config: parser.registry", "trace: document.parsed"),
    tags: ["overview", "known", "dataflow", "ingestion", "risk", "source"],
  },
  {
    id: "chunker",
    layer: "ingestion",
    label: "Chunker",
    kind: "data",
    nodeType: "known",
    mode: "deterministic",
    topology: "single-process",
    summary: "把文件切成可檢索單位，附 metadata 與 source span。",
    inputs: ["parsed_documents"],
    outputs: ["chunks"],
    contracts: ["Chunk"],
    risks: ["lost context"],
    metrics: ["chunk count", "avg chunk tokens"],
    sources: source("code: indexing/chunker", "config: chunk_size", "trace: chunks.created"),
    tags: ["overview", "known", "dataflow", "ingestion", "retrieval", "source"],
  },
  {
    id: "metadata_extractor",
    layer: "ingestion",
    label: "Metadata Extractor",
    kind: "data",
    nodeType: "known",
    mode: "deterministic",
    topology: "single-process",
    summary: "萃取來源、時間、權限、類型與可追溯位置等 metadata。",
    inputs: ["chunks"],
    outputs: ["enriched_chunks"],
    contracts: ["ChunkMetadata"],
    risks: ["missing ACL", "incorrect provenance"],
    metrics: ["metadata coverage", "ACL coverage"],
    sources: source("code: indexing/metadata", "config: metadata.fields", "trace: metadata.extracted"),
    tags: ["overview", "known", "dataflow", "ingestion", "governance", "risk", "source"],
  },
  {
    id: "embedder",
    layer: "ingestion",
    label: "Embedder",
    kind: "data",
    nodeType: "known",
    mode: "predefined",
    topology: "client-server",
    summary: "將可索引內容轉成向量表示，並記錄 embedding model 版本。",
    inputs: ["enriched_chunks"],
    outputs: ["embedded_chunks"],
    contracts: ["EmbeddingRecord[]"],
    risks: ["model drift", "dimension mismatch"],
    metrics: ["embed latency", "embedding failures"],
    sources: source("code: indexing/embed", "config: embedding.model", "trace: embedding.created"),
    tags: ["overview", "known", "dataflow", "ingestion", "runtime", "risk", "source"],
  },
  {
    id: "index_builder",
    layer: "ingestion",
    label: "Index Builder",
    kind: "data",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "將 chunks、embeddings、metadata 與 ACL 寫入可查詢的索引。",
    inputs: ["embedded_chunks"],
    outputs: ["index_ref"],
    contracts: ["IndexManifest"],
    risks: ["stale index", "ACL mismatch"],
    metrics: ["index freshness", "indexing failures"],
    sources: source("code: indexing/build", "config: index.strategy", "trace: index.updated"),
    tags: ["overview", "known", "dataflow", "ingestion", "retrieval", "governance", "risk", "source"],
  },
  {
    id: "dense_retriever",
    layer: "retrieval",
    label: "Dense Retriever",
    kind: "retriever",
    nodeType: "known",
    mode: "predefined",
    topology: "client-server",
    summary: "以 embedding similarity 從向量索引取回語意相關候選。",
    inputs: ["query", "filters"],
    outputs: ["dense_candidates"],
    contracts: ["Candidate[]"],
    risks: ["semantic near miss", "ACL leak"],
    metrics: ["recall@k", "latency p95"],
    sources: source("code: retrieval/dense", "config: vector_store", "trace: dense.results"),
    tags: ["overview", "known", "dataflow", "retrieval", "runtime", "risk", "source"],
  },
  {
    id: "sparse_retriever",
    layer: "retrieval",
    label: "Sparse Retriever",
    kind: "retriever",
    nodeType: "known",
    mode: "predefined",
    topology: "client-server",
    summary: "以 BM25 或關鍵字索引取回字詞精確匹配候選。",
    inputs: ["query", "filters"],
    outputs: ["sparse_candidates"],
    contracts: ["Candidate[]"],
    risks: ["vocabulary mismatch", "ACL leak"],
    metrics: ["recall@k", "latency p95"],
    sources: source("code: retrieval/sparse", "config: sparse_index", "trace: sparse.results"),
    tags: ["overview", "known", "dataflow", "retrieval", "runtime", "risk", "source"],
  },
  {
    id: "hybrid_retriever",
    layer: "retrieval",
    label: "Hybrid Retriever",
    kind: "retriever",
    nodeType: "known",
    mode: "predefined",
    topology: "client-server",
    summary: "合併 dense 與 sparse 候選，透過 fusion 或 RRF 產生混合檢索結果。",
    inputs: ["query", "filters"],
    outputs: ["candidates[]"],
    contracts: ["Candidate"],
    risks: ["stale index", "ACL leak", "retrieval drift"],
    metrics: ["recall@k", "latency p95", "precision@k"],
    sources: source("code: retrieval/*", "config: retriever.strategy", "trace: retrieval.results"),
    tags: ["overview", "known", "dataflow", "retrieval", "runtime", "mode", "risk", "source"],
  },
  {
    id: "graph_retriever",
    layer: "retrieval",
    label: "Graph Retriever",
    kind: "retriever",
    nodeType: "known",
    mode: "predefined",
    topology: "client-server",
    summary: "用 entity、relationship 與 path 支援多跳或關係查詢。",
    inputs: ["entities", "query"],
    outputs: ["graph_candidates"],
    contracts: ["GraphEvidence"],
    risks: ["entity mismatch", "schema drift"],
    metrics: ["path confidence", "coverage"],
    sources: source("code: graph/query", "config: graph_store", "trace: graph.paths"),
    tags: ["overview", "known", "retrieval", "variant", "dataflow", "mode", "risk", "source"],
  },
  {
    id: "memory_retriever",
    layer: "retrieval",
    label: "Memory Retriever",
    kind: "memory",
    nodeType: "known",
    mode: "agentic",
    topology: "client-server",
    summary: "讀取長期記憶、user preference 或 project memory。",
    inputs: ["context", "query"],
    outputs: ["memory_candidates"],
    contracts: ["MemorySnippet"],
    risks: ["stale memory", "privacy leak"],
    metrics: ["memory hit rate", "age"],
    sources: source("code: memory/retrieve", "config: retention", "trace: memory.search"),
    tags: ["overview", "known", "memory", "retrieval", "governance", "mode", "risk", "variant", "source"],
  },
  {
    id: "web_retriever",
    layer: "retrieval",
    label: "Web Retriever",
    kind: "retriever",
    nodeType: "known",
    mode: "agentic",
    topology: "tool-network",
    summary: "透過受控 web search 或 fetch 工具取回外部即時資訊。",
    inputs: ["query", "domain_policy"],
    outputs: ["web_candidates"],
    contracts: ["WebCandidate[]"],
    risks: ["untrusted content", "network exposure"],
    metrics: ["source success", "fetch latency"],
    sources: source("code: retrieval/web", "config: web.allowlist", "trace: web.results"),
    tags: ["overview", "known", "retrieval", "control", "governance", "runtime", "risk", "source"],
  },
  {
    id: "graph_rag_system",
    layer: "extensions",
    label: "GraphRAG Subsystem",
    kind: "extension",
    nodeType: "extension",
    mode: "predefined",
    topology: "client-server",
    summary: "完整 graph-based RAG 子系統，可展開成 entity extraction、KG build、community/path query 與 graph evidence。",
    inputs: ["documents", "query"],
    outputs: ["graph_evidence_pack"],
    contracts: ["GraphRAGBundle"],
    risks: ["graph schema drift", "expensive indexing"],
    metrics: ["entity coverage", "path recall"],
    sources: source("adapter: graphrag", "config: graph_index", "trace: graph_query"),
    subgraph: ["Entity extraction", "Graph index build", "Community/path retrieval", "Graph evidence scoring"],
    tags: ["overview", "extension", "variant", "retrieval", "topology", "mode", "risk", "source"],
  },
  {
    id: "rag_anything_system",
    layer: "extensions",
    label: "RAG-Anything / Multimodal Subsystem",
    kind: "extension",
    nodeType: "extension",
    mode: "hybrid",
    topology: "client-server",
    summary: "多模態文件管線，可展開為 multimodal parsing、dual graph、cross-modal retrieval 與 evidence fusion。",
    inputs: ["pdf", "image", "table", "formula", "query"],
    outputs: ["cross_modal_evidence"],
    contracts: ["MultimodalEvidence"],
    risks: ["modality loss", "benchmark mismatch"],
    metrics: ["modal coverage", "cross-modal recall"],
    sources: source("adapter: rag-anything", "config: multimodal_parser", "trace: modal.parse"),
    subgraph: ["Multimodal parser", "Table/image/formula extraction", "Dual graph construction", "Cross-modal hybrid retrieval", "Evidence fusion"],
    tags: ["overview", "extension", "variant", "retrieval", "dataflow", "topology", "mode", "risk", "source"],
  },
  {
    id: "infini_memory_system",
    layer: "extensions",
    label: "Infini Memory / Long-term Memory Subsystem",
    kind: "extension",
    nodeType: "extension",
    mode: "agentic",
    topology: "agent-runtime",
    summary: "長期記憶子系統，可展開成 buffer、topic documents、consolidation 與 agentic retrieval tools。",
    inputs: ["observations", "events", "query"],
    outputs: ["topic_memory_evidence"],
    contracts: ["TopicMemoryDocument"],
    risks: ["wrong consolidation", "retention leak"],
    metrics: ["memory freshness", "revision count"],
    sources: source("adapter: infini-memory", "config: memory_topics", "trace: memory.consolidate"),
    subgraph: ["Short-term buffer", "Topic document maintenance", "Revision/source metadata", "Agentic memory tools", "Evidence expansion"],
    tags: ["overview", "extension", "memory", "variant", "topology", "mode", "governance", "risk", "source"],
  },
  {
    id: "corag_federated_system",
    layer: "extensions",
    label: "CoRAG / Federated Subsystem",
    kind: "extension",
    nodeType: "extension",
    mode: "predefined",
    topology: "federated",
    summary: "協作式 / 聯邦式 RAG 子系統，重點在多 client passage store 與分散式訓練或聚合。",
    inputs: ["client_passages", "local_retriever_updates"],
    outputs: ["collaborative_store", "aggregated_model"],
    contracts: ["FederatedRAGState"],
    risks: ["client data leak", "shared store poisoning"],
    metrics: ["client coverage", "aggregation drift"],
    sources: source("adapter: federated_rag", "config: clients", "trace: federation.round"),
    subgraph: ["Client passage stores", "Hard negative exchange", "Federated aggregation", "Collaborative reader/retriever update"],
    tags: ["overview", "extension", "variant", "topology", "governance", "risk", "source"],
  },
  {
    id: "reranker",
    layer: "evidence",
    label: "Reranker",
    kind: "evidence",
    nodeType: "known",
    mode: "predefined",
    topology: "single-process",
    summary: "重排候選片段，讓最支持答案的證據優先。",
    inputs: ["candidates[]"],
    outputs: ["ranked_candidates"],
    contracts: ["RankedCandidate"],
    risks: ["rank bias"],
    metrics: ["MRR", "nDCG"],
    sources: source("code: evidence/rerank", "config: reranker.model", "trace: rerank.scores"),
    tags: ["overview", "known", "retrieval", "dataflow", "source"],
  },
  {
    id: "conflict_checker",
    layer: "evidence",
    label: "Conflict Checker",
    kind: "evidence",
    nodeType: "known",
    mode: "predefined",
    topology: "single-process",
    summary: "檢查多來源證據是否互相衝突或過期。",
    inputs: ["ranked_candidates"],
    outputs: ["conflict_report"],
    contracts: ["ConflictReport"],
    risks: ["silent contradiction"],
    metrics: ["conflict rate", "resolution rate"],
    sources: source("code: evidence/conflict", "trace: conflict.detected", "doc: evidence policy"),
    tags: ["overview", "known", "retrieval", "governance", "mode", "risk", "source"],
  },
  {
    id: "citation_mapper",
    layer: "evidence",
    label: "Citation Mapper",
    kind: "evidence",
    nodeType: "known",
    mode: "deterministic",
    topology: "single-process",
    summary: "把 claim 對回 source span，產生可追溯 citation map。",
    inputs: ["ranked_candidates", "claims"],
    outputs: ["citation_map"],
    contracts: ["CitationMap"],
    risks: ["unsupported claim"],
    metrics: ["citation coverage", "unsupported rate"],
    sources: source("code: evidence/citations", "trace: claim.source_span", "doc: citation contract"),
    tags: ["overview", "known", "retrieval", "dataflow", "governance", "risk", "source"],
  },
  {
    id: "evidence_pack",
    layer: "evidence",
    label: "Evidence Pack",
    kind: "evidence",
    nodeType: "known",
    mode: "deterministic",
    topology: "single-process",
    summary: "把候選證據、衝突、引用與信心整理成 generator 的輸入。",
    inputs: ["ranked_candidates", "conflict_report", "citation_map"],
    outputs: ["evidence_pack"],
    contracts: ["EvidencePack"],
    risks: ["overstuffed context"],
    metrics: ["token footprint", "support score"],
    sources: source("code: evidence/pack", "trace: evidence.pack", "doc: answer contract"),
    tags: ["overview", "known", "retrieval", "dataflow", "source"],
  },
  {
    id: "context_composer",
    layer: "generation",
    label: "Context Composer",
    kind: "generation",
    nodeType: "known",
    mode: "deterministic",
    topology: "single-process",
    summary: "把 evidence pack、system policy 與任務格式組成 prompt context。",
    inputs: ["evidence_pack", "policy"],
    outputs: ["model_context"],
    contracts: ["PromptContext"],
    risks: ["context injection"],
    metrics: ["context tokens", "template version"],
    sources: source("code: generation/context", "config: prompt_template", "trace: prompt.rendered"),
    tags: ["overview", "known", "dataflow", "generation", "risk", "source"],
  },
  {
    id: "prompt_builder",
    layer: "generation",
    label: "Prompt Builder",
    kind: "generation",
    nodeType: "known",
    mode: "deterministic",
    topology: "single-process",
    summary: "套用 prompt template、訊息角色、工具 schema 與輸出格式。",
    inputs: ["model_context", "prompt_template", "tool_schema"],
    outputs: ["prompt_messages"],
    contracts: ["PromptEnvelope"],
    risks: ["template drift", "prompt injection"],
    metrics: ["prompt version", "prompt tokens"],
    sources: source("code: generation/prompt", "config: prompt_template", "trace: prompt.built"),
    tags: ["overview", "known", "dataflow", "generation", "governance", "risk", "source"],
  },
  {
    id: "llm_answerer",
    layer: "generation",
    label: "LLM Answerer",
    kind: "generation",
    nodeType: "known",
    mode: "hybrid",
    topology: "client-server",
    summary: "根據 evidence-first context 生成回答或中止。",
    inputs: ["prompt_messages"],
    outputs: ["draft_answer", "claims"],
    contracts: ["AnswerDraft"],
    risks: ["hallucination"],
    metrics: ["faithfulness", "answer latency"],
    sources: source("code: generation/answer", "config: model.provider", "trace: llm.response"),
    tags: ["overview", "known", "dataflow", "generation", "runtime", "mode", "risk", "source"],
  },
  {
    id: "tool_agent",
    layer: "generation",
    label: "Tool-Using Generator",
    kind: "agentic",
    nodeType: "known",
    mode: "agentic",
    topology: "tool-network",
    summary: "在生成過程中，依明確 allowlist 呼叫搜尋、計算或外部工具。",
    inputs: ["tool_request", "approval"],
    outputs: ["tool_result"],
    contracts: ["ToolCall"],
    risks: ["unsafe action", "side effect"],
    metrics: ["tool latency", "error rate"],
    sources: source("code: tools/execute", "config: tool_allowlist", "trace: tool.call"),
    tags: ["overview", "known", "control", "generation", "governance", "runtime", "mode", "topology", "risk", "source"],
  },
  {
    id: "output_guardrail",
    layer: "generation",
    label: "Output Guardrail",
    kind: "governance",
    nodeType: "known",
    mode: "predefined",
    topology: "single-process",
    summary: "檢查 PII、policy、citation coverage、unsafe output 與格式。",
    inputs: ["draft_answer", "citation_map"],
    outputs: ["final_answer", "blocked_output"],
    contracts: ["GuardrailReport"],
    risks: ["unsafe output"],
    metrics: ["block rate", "policy warning rate"],
    sources: source("code: guardrails/output", "config: output_policy", "trace: guardrail.report"),
    tags: ["overview", "known", "generation", "governance", "mode", "risk", "source"],
  },
  {
    id: "session_state",
    layer: "memory",
    label: "Session State",
    kind: "memory",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "保存目前 session 的識別、權限、checkpoint 與執行狀態。",
    inputs: ["session_context", "agent_state"],
    outputs: ["session_snapshot"],
    contracts: ["SessionState"],
    risks: ["cross-session leakage", "stale checkpoint"],
    metrics: ["checkpoint age", "state load success"],
    sources: source("code: state/session", "config: session.ttl", "trace: state.session"),
    tags: ["overview", "known", "memory", "governance", "runtime", "risk", "source"],
  },
  {
    id: "working_memory",
    layer: "memory",
    label: "Working Memory",
    kind: "memory",
    nodeType: "known",
    mode: "agentic",
    topology: "agent-runtime",
    summary: "保存目前任務的中間步驟、工具結果與短期推理上下文。",
    inputs: ["agent_state", "tool_result"],
    outputs: ["working_context"],
    contracts: ["WorkingMemory"],
    risks: ["context drift", "sensitive transient data"],
    metrics: ["working set size", "eviction rate"],
    sources: source("code: memory/working", "config: working_memory.limit", "trace: memory.working"),
    tags: ["overview", "known", "memory", "control", "runtime", "risk", "source"],
  },
  {
    id: "long_term_memory",
    layer: "memory",
    label: "Long-term Memory",
    kind: "memory",
    nodeType: "known",
    mode: "predefined",
    topology: "client-server",
    summary: "持久保存經核准的偏好、事實、事件與可追溯來源。",
    inputs: ["memory_record"],
    outputs: ["persisted_memory"],
    contracts: ["LongTermMemoryRecord"],
    risks: ["retention leak", "stale memory"],
    metrics: ["record age", "retention compliance"],
    sources: source("code: memory/store", "config: retention_policy", "trace: memory.persisted"),
    tags: ["overview", "known", "memory", "governance", "risk", "source"],
  },
  {
    id: "memory_reader",
    layer: "memory",
    label: "Memory Reader",
    kind: "memory",
    nodeType: "known",
    mode: "agentic",
    topology: "client-server",
    summary: "依目前任務讀取 session、working 與 long-term memory。",
    inputs: ["query", "session_snapshot", "working_context", "persisted_memory"],
    outputs: ["memory_context"],
    contracts: ["MemoryContext"],
    risks: ["privacy leak", "irrelevant memory"],
    metrics: ["read latency", "memory relevance"],
    sources: source("code: memory/read", "config: memory.scope", "trace: memory.read"),
    tags: ["overview", "known", "memory", "retrieval", "governance", "mode", "risk", "source"],
  },
  {
    id: "memory_writer",
    layer: "memory",
    label: "Memory Writer",
    kind: "memory",
    nodeType: "known",
    mode: "human_gated",
    topology: "client-server",
    summary: "把使用者偏好、確認事實與重要結果寫回記憶層。",
    inputs: ["final_answer", "approved_memory"],
    outputs: ["memory_record"],
    contracts: ["MemoryRecord"],
    risks: ["wrong persistence", "sensitive retention"],
    metrics: ["write count", "redaction rate"],
    sources: source("code: memory/write", "config: retention_policy", "trace: memory.write"),
    tags: ["overview", "known", "memory", "governance", "mode", "risk", "source"],
  },
  {
    id: "input_guardrail",
    layer: "governance",
    label: "Input Guardrail",
    kind: "governance",
    nodeType: "known",
    mode: "predefined",
    topology: "single-process",
    summary: "在進入 agent 或 retrieval 前檢查 prompt injection、PII 與不安全輸入。",
    inputs: ["raw_request"],
    outputs: ["screened_request", "blocked_input"],
    contracts: ["InputGuardrailReport"],
    risks: ["false negative", "over-blocking"],
    metrics: ["block rate", "warning rate"],
    sources: source("code: guardrails/input", "config: input_policy", "trace: input.guardrail"),
    tags: ["overview", "known", "governance", "control", "risk", "source"],
  },
  {
    id: "permission_policy",
    layer: "governance",
    label: "Permission Policy",
    kind: "governance",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "限制資料、工具、tenant 與外部資源的存取範圍。",
    inputs: ["identity", "requested_resource", "action"],
    outputs: ["allow", "deny", "scoped_permissions"],
    contracts: ["AuthorizationDecision"],
    risks: ["excessive privilege", "ACL bypass"],
    metrics: ["deny rate", "policy evaluation latency"],
    sources: source("code: policy/permissions", "config: access_policy", "trace: permission.decision"),
    tags: ["overview", "known", "governance", "control", "topology", "risk", "source"],
  },
  {
    id: "human_approval",
    layer: "governance",
    label: "Human Approval",
    kind: "governance",
    nodeType: "known",
    mode: "human_gated",
    topology: "client-server",
    summary: "記錄高風險操作的人類核准、拒絕、理由與稽核證據。",
    inputs: ["approval_request"],
    outputs: ["approval_decision"],
    contracts: ["ApprovalDecision"],
    risks: ["approval bypass", "missing audit trail"],
    metrics: ["approval latency", "denial rate"],
    sources: source("code: approvals/decision", "config: approval_policy", "trace: approval.audit"),
    tags: ["overview", "known", "governance", "control", "mode", "risk", "source"],
  },
  {
    id: "trace_store",
    layer: "governance",
    label: "Trace Store",
    kind: "runtime",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "記錄 request、route、retrieval、tool call、model 與 output trace。",
    inputs: ["trace_events"],
    outputs: ["trace_id"],
    contracts: ["TraceEvent"],
    risks: ["secret in logs"],
    metrics: ["trace completeness", "sampling rate"],
    sources: source("code: observability/traces", "config: sampling", "trace: trace.persisted"),
    tags: ["overview", "known", "runtime", "governance", "topology", "risk", "source"],
  },
  {
    id: "eval_harness",
    layer: "governance",
    label: "Eval Harness",
    kind: "runtime",
    nodeType: "known",
    mode: "deterministic",
    topology: "single-process",
    summary: "用測資與 regression 指標驗證 retrieval、faithfulness 與 task success。",
    inputs: ["trace_id", "golden_set"],
    outputs: ["eval_report"],
    contracts: ["EvalReport"],
    risks: ["weak benchmark"],
    metrics: ["pass rate", "regression delta"],
    sources: source("code: eval/harness", "config: golden_sets", "trace: eval.run"),
    tags: ["overview", "known", "runtime", "retrieval", "governance", "source"],
  },
  {
    id: "cost_monitor",
    layer: "governance",
    label: "Cost Monitor",
    kind: "runtime",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "追蹤 token、模型、retrieval、工具與每次任務成本。",
    inputs: ["trace_events", "usage"],
    outputs: ["cost_report"],
    contracts: ["CostMetric"],
    risks: ["budget overrun"],
    metrics: ["cost/query", "budget utilization"],
    sources: source("code: observability/cost", "config: budgets", "trace: usage.metered"),
    tags: ["overview", "known", "runtime", "topology", "governance", "risk", "source"],
  },
  {
    id: "latency_monitor",
    layer: "governance",
    label: "Latency Monitor",
    kind: "runtime",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "追蹤 ingestion、retrieval、tool、model 與端到端 latency。",
    inputs: ["trace_events", "timings"],
    outputs: ["latency_report"],
    contracts: ["LatencyMetric"],
    risks: ["missing spans", "SLO breach"],
    metrics: ["p50 latency", "p95 latency", "p99 latency"],
    sources: source("code: observability/latency", "config: latency.slo", "trace: latency.measured"),
    tags: ["overview", "known", "runtime", "topology", "governance", "risk", "source"],
  },
  {
    id: "client_app",
    layer: "topology",
    label: "Client App",
    kind: "topology",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "使用者互動介面或 API client，是 request 與 approval 的實際發起端。",
    inputs: ["user_event"],
    outputs: ["request", "approval"],
    contracts: ["ClientBoundary"],
    risks: ["over-broad client permissions"],
    metrics: ["active sessions", "approval completion"],
    sources: source("deploy: web-client", "config: auth scopes", "trace: client.request"),
    tags: ["overview", "known", "topology", "governance", "source"],
  },
  {
    id: "api_server",
    layer: "topology",
    label: "API Server",
    kind: "topology",
    nodeType: "known",
    mode: "deterministic",
    topology: "client-server",
    summary: "提供 request validation、authentication、streaming 與 system boundary。",
    inputs: ["client_request"],
    outputs: ["agent_request", "api_response"],
    contracts: ["APIEnvelope"],
    risks: ["unauthorized access", "unsafe exposure"],
    metrics: ["request rate", "error rate"],
    sources: source("code: api/server", "config: server.bind", "trace: api.request"),
    tags: ["overview", "known", "topology", "governance", "runtime", "risk", "source"],
  },
  {
    id: "agent_runtime",
    layer: "topology",
    label: "Agent Runtime",
    kind: "topology",
    nodeType: "known",
    mode: "hybrid",
    topology: "agent-runtime",
    summary: "承載 planner、router、agent loop 與 tool execution 的 runtime 邊界。",
    inputs: ["request", "state", "tools"],
    outputs: ["actions", "trace_events"],
    contracts: ["RuntimeBoundary"],
    risks: ["state corruption", "timeout cascade"],
    metrics: ["runtime p95", "active loops"],
    sources: source("deploy: agent-service", "config: runtime limits", "trace: runtime.span"),
    tags: ["overview", "known", "topology", "control", "runtime", "mode", "risk", "source"],
  },
  {
    id: "worker_queue",
    layer: "topology",
    label: "Worker / Queue",
    kind: "topology",
    nodeType: "known",
    mode: "deterministic",
    topology: "distributed",
    summary: "承接背景 ingestion、indexing、eval 或長任務的排程與執行。",
    inputs: ["job"],
    outputs: ["job_result", "job_status"],
    contracts: ["JobEnvelope"],
    risks: ["duplicate execution", "poisoned job"],
    metrics: ["queue depth", "job latency", "failure rate"],
    sources: source("code: workers", "config: queue", "trace: job.executed"),
    tags: ["overview", "known", "topology", "runtime", "governance", "risk", "source"],
  },
  {
    id: "tool_network",
    layer: "topology",
    label: "Tool Network",
    kind: "topology",
    nodeType: "known",
    mode: "agentic",
    topology: "tool-network",
    summary: "外部工具、MCP、API、database 或 workflow actions 的連線邊界。",
    inputs: ["tool_call"],
    outputs: ["tool_result"],
    contracts: ["ToolNetworkBoundary"],
    risks: ["least privilege failure", "network side effect"],
    metrics: ["tool error rate", "denied calls"],
    sources: source("config: tool registry", "deploy: network policy", "trace: tool.egress"),
    tags: ["overview", "known", "topology", "control", "governance", "runtime", "risk", "source"],
  },
  {
    id: "federated_clients",
    layer: "topology",
    label: "Federated Clients",
    kind: "topology",
    nodeType: "extension",
    mode: "predefined",
    topology: "federated",
    summary: "多 client 或多組織協作的資料與模型更新邊界，支援 CoRAG 類拓樸。",
    inputs: ["local_passages", "local_updates"],
    outputs: ["aggregated_state"],
    contracts: ["FederatedBoundary"],
    risks: ["data isolation breach", "poisoned updates"],
    metrics: ["client participation", "aggregation quality"],
    sources: source("adapter: federated clients", "config: tenant boundary", "trace: aggregation.round"),
    tags: ["overview", "extension", "topology", "governance", "risk", "source"],
  },
];

const edges = [
  ["user_input", "input_guardrail", "data"],
  ["input_guardrail", "session_context", "data"],
  ["session_context", "permission_policy", "approval"],
  ["permission_policy", "query_classifier", "control"],
  ["query_classifier", "planner", "control"],
  ["planner", "router", "control"],
  ["router", "agent_loop", "control"],
  ["unmapped_orchestrator", "router", "control"],
  ["agent_loop", "stop_policy", "control"],
  ["stop_policy", "approval_gate", "approval"],
  ["approval_gate", "human_approval", "approval"],
  ["router", "dense_retriever", "control"],
  ["router", "sparse_retriever", "control"],
  ["router", "hybrid_retriever", "control"],
  ["router", "graph_retriever", "control"],
  ["router", "memory_retriever", "control"],
  ["router", "web_retriever", "control"],
  ["router", "graph_rag_system", "control"],
  ["router", "rag_anything_system", "control"],
  ["router", "infini_memory_system", "control"],
  ["document_loader", "parser", "data"],
  ["parser", "chunker", "data"],
  ["chunker", "metadata_extractor", "data"],
  ["metadata_extractor", "embedder", "data"],
  ["embedder", "index_builder", "data"],
  ["index_builder", "dense_retriever", "data"],
  ["index_builder", "sparse_retriever", "data"],
  ["index_builder", "hybrid_retriever", "data"],
  ["dense_retriever", "hybrid_retriever", "data"],
  ["sparse_retriever", "hybrid_retriever", "data"],
  ["dense_retriever", "reranker", "evidence"],
  ["sparse_retriever", "reranker", "evidence"],
  ["hybrid_retriever", "reranker", "evidence"],
  ["graph_retriever", "reranker", "evidence"],
  ["memory_retriever", "reranker", "evidence"],
  ["web_retriever", "reranker", "evidence"],
  ["graph_rag_system", "graph_retriever", "data"],
  ["rag_anything_system", "evidence_pack", "evidence"],
  ["infini_memory_system", "long_term_memory", "memory_write"],
  ["corag_federated_system", "hybrid_retriever", "data"],
  ["reranker", "conflict_checker", "evidence"],
  ["conflict_checker", "citation_mapper", "evidence"],
  ["citation_mapper", "evidence_pack", "evidence"],
  ["evidence_pack", "context_composer", "data"],
  ["memory_reader", "context_composer", "memory_read"],
  ["context_composer", "prompt_builder", "data"],
  ["prompt_builder", "llm_answerer", "data"],
  ["llm_answerer", "tool_agent", "tool_call"],
  ["llm_answerer", "output_guardrail", "data"],
  ["tool_agent", "output_guardrail", "tool_call"],
  ["output_guardrail", "memory_writer", "memory_write"],
  ["session_context", "session_state", "memory_write"],
  ["agent_loop", "working_memory", "memory_write"],
  ["session_state", "memory_reader", "memory_read"],
  ["working_memory", "memory_reader", "memory_read"],
  ["long_term_memory", "memory_reader", "memory_read"],
  ["long_term_memory", "memory_retriever", "memory_read"],
  ["memory_writer", "session_state", "memory_write"],
  ["memory_writer", "working_memory", "memory_write"],
  ["memory_writer", "long_term_memory", "memory_write"],
  ["memory_writer", "infini_memory_system", "memory_write"],
  ["llm_answerer", "trace_store", "telemetry"],
  ["tool_agent", "trace_store", "telemetry"],
  ["trace_store", "eval_harness", "telemetry"],
  ["eval_harness", "cost_monitor", "telemetry"],
  ["cost_monitor", "latency_monitor", "telemetry"],
  ["latency_monitor", "stop_policy", "control"],
  ["client_app", "api_server", "deployment"],
  ["api_server", "agent_runtime", "deployment"],
  ["agent_runtime", "worker_queue", "deployment"],
  ["agent_runtime", "tool_network", "deployment"],
  ["agent_runtime", "trace_store", "telemetry"],
  ["worker_queue", "index_builder", "deployment"],
  ["worker_queue", "eval_harness", "deployment"],
  ["tool_network", "tool_agent", "deployment"],
  ["federated_clients", "corag_federated_system", "deployment"],
];

const views = {
  overview: {
    label: "Overview",
    summary: "顯示完整圖：每個節點代表一個可替換能力，連線代表資料、控制、證據、狀態或部署邊界。",
    tags: ["overview"],
    edgeTypes: ["data", "control", "evidence", "tool_call", "memory_write", "memory_read", "approval", "telemetry", "deployment"],
  },
  dataflow: {
    label: "Data Flow",
    summary: "突出資料從輸入、檢索、證據包、context composer 到回答輸出的路徑。",
    tags: ["dataflow", "generation"],
    edgeTypes: ["data", "evidence"],
  },
  ingestion: {
    label: "Ingestion & Indexing",
    summary: "聚焦文件載入、chunking、metadata、ACL 與索引更新，避免把離線資料處理混入查詢階段。",
    tags: ["ingestion"],
    edgeTypes: ["data", "telemetry"],
  },
  control: {
    label: "Agent Control",
    summary: "突出 agentic RAG 的控制層：planner、router、agent loop、orchestrator、stop policy 與 approval gate。",
    tags: ["control"],
    edgeTypes: ["control", "tool_call", "approval"],
  },
  retrieval: {
    label: "Retrieval & Evidence",
    summary: "聚焦 retrieval plane 與 evidence plane，檢查線上候選取回、重排、衝突檢查與 citation coverage。",
    tags: ["retrieval"],
    edgeTypes: ["data", "evidence", "memory_read"],
  },
  memory: {
    label: "Memory & State",
    summary: "檢查 session state、working memory、long-term memory、memory reader/writer 與持久化風險。",
    tags: ["memory"],
    edgeTypes: ["memory_write", "memory_read", "data"],
  },
  governance: {
    label: "Governance & Observability",
    summary: "突出 input guardrail、permission policy、human approval、trace、eval、cost 與 latency 等治理證據。",
    tags: ["governance"],
    edgeTypes: ["approval", "control", "tool_call", "memory_write", "telemetry", "deployment"],
  },
  runtime: {
    label: "Runtime",
    summary: "從 trace、eval、latency、cost 與 stop reason 檢查 production readiness。",
    tags: ["runtime"],
    edgeTypes: ["telemetry", "control", "tool_call", "deployment"],
  },
  variant: {
    label: "Variants",
    summary: "突出 GraphRAG、Memory RAG、多模態與協作式 RAG 如何接到 Modular RAG backbone。",
    tags: ["variant", "memory", "control"],
    edgeTypes: ["control", "data", "evidence", "memory_write", "memory_read", "deployment"],
  },
  known: {
    label: "Known Nodes",
    summary: "只突出高信心標準能力節點，例如 retriever、router、planner、memory、guardrail、trace store。",
    tags: ["known"],
    edgeTypes: ["data", "control", "evidence", "tool_call", "memory_write", "approval", "telemetry", "deployment"],
  },
  extension: {
    label: "Extension Systems",
    summary: "突出 GraphRAG、RAG-Anything、Infini Memory、CoRAG 這種可展開的專門子系統。",
    tags: ["extension"],
    edgeTypes: ["control", "data", "evidence", "memory_read", "memory_write", "deployment"],
  },
  unmapped: {
    label: "Unmapped",
    summary: "保守顯示掃描到但無法分類的元件，不把未知架構硬塞進標準節點。",
    tags: ["unmapped"],
    edgeTypes: ["control", "tool_call", "telemetry"],
  },
  mode: {
    label: "Reasoning Mode",
    summary: "用 deterministic、predefined、agentic、hybrid 標記決策權在固定流程、預設推理或模型自主控制。",
    tags: ["mode"],
    edgeTypes: ["control", "tool_call", "approval", "memory_read", "memory_write"],
  },
  topology: {
    label: "Topology",
    summary: "顯示單機、client-server、agent runtime、tool network、federated clients 等實際部署與協作邊界。",
    tags: ["topology"],
    edgeTypes: ["deployment", "tool_call", "telemetry", "control", "data"],
  },
  source: {
    label: "Source Map",
    summary: "突出每個 node 如何回到 code path、config key、trace span 或文件段落，避免 UI 成為無證據猜測。",
    tags: ["source"],
    edgeTypes: ["data", "control", "evidence", "tool_call", "memory_write", "approval", "telemetry", "deployment"],
  },
  risk: {
    label: "Risk Lens",
    summary: "集中看 prompt injection、ACL leak、unsafe tool、secret in logs、stale memory、unmapped component 等風險點。",
    tags: ["risk", "governance", "unmapped"],
    edgeTypes: ["approval", "control", "tool_call", "telemetry", "memory_write", "deployment"],
  },
};

const importExamples = [
  {
    id: "direct-private-gpt",
    group: "direct",
    label: "zylon-ai/private-gpt",
    short: "PrivateGPT",
    mode: "full repo or backend package",
    gate: "Tier B bounded app gate",
    result: "Direct app target",
    resultTone: "pass",
    directRate: "Counts toward direct import if fixed SHA scan passes",
    scanRoot: "repo root 或 backend package",
    summary: "適合作為 local document QA / private RAG app。預期會產生 grounded RAG evidence，並檢查 local/private patterns 與 modular composition。",
    graphShape: ["Import project", "Read-only scan", "RAG grounding", "Profile overlay", "Viewer payload"],
    profileRows: [
      ["rag-grounding", "detected candidate"],
      ["modular-composition", "detected or undetermined"],
      ["source-traceability", "readiness finding"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "readiness_report.json", "ai_system_map.md", "system_map.mmd"],
    warnings: ["需固定 commit SHA。", "不得安裝或啟動 target app dependencies。"],
  },
  {
    id: "direct-quivr",
    group: "direct",
    label: "QuivrHQ/quivr",
    short: "Quivr",
    mode: "bounded app/backend scan",
    gate: "Tier B bounded app gate",
    result: "Direct app target with caution",
    resultTone: "warn",
    directRate: "Counts only if bounded app scan is schema-valid",
    scanRoot: "明確 app/backend subdir",
    summary: "偏 full-stack RAG platform。適合驗證 file ingestion、parser、vectorstore、reranking 與 modular evidence，但不能作為唯一 acceptance gate。",
    graphShape: ["Bounded import", "Parser/vectorstore evidence", "Reranking profile", "Unmapped platform parts", "Viewer payload"],
    profileRows: [
      ["rag-grounding", "detected candidate"],
      ["reranking", "detected candidate"],
      ["modular-composition", "detected or undetermined"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "readiness_report.json", "scan limitation note"],
    warnings: ["先 review license file。", "平台型目錄超出 bounded path 時要落入 unmapped 或 limitation，不可 silent pass。"],
  },
  {
    id: "direct-langchain-chatchat",
    group: "direct",
    label: "chatchat-space/Langchain-Chatchat",
    short: "Langchain-Chatchat",
    mode: "bounded backend scan",
    gate: "Tier B bounded app gate",
    result: "Direct app target with repo-drift risk",
    resultTone: "warn",
    directRate: "Counts if fixed SHA + backend scan passes",
    scanRoot: "backend/server subdir",
    summary: "預期可看到 File RAG、BM25+KNN、Agent 與 image chat 類訊號；UI 應呈現多 profile stack，而不是只顯示單一 RAG 類型。",
    graphShape: ["Backend import", "Hybrid retrieval", "Agent control", "Multimodal evidence", "Profile matrix"],
    profileRows: [
      ["reranking", "detected candidate"],
      ["hybrid-retrieval", "detected candidate"],
      ["agentic-control", "detected candidate"],
      ["multimodal-grounding", "boundary-limited"],
    ],
    artifacts: ["profile_signals.json", "readiness_report.json", "system_map.mmd", "drift note"],
    warnings: ["default branch / repo structure 會 drift，必須 pin SHA。", "image chat evidence 要標清楚邊界，不能擴張成完整 multimodal RAG。"],
  },
  {
    id: "direct-khoj",
    group: "direct",
    label: "khoj-ai/khoj",
    short: "Khoj",
    mode: "full repo or backend package",
    gate: "Tier B bounded app gate",
    result: "Direct app target",
    resultTone: "pass",
    directRate: "Counts if read-only scan passes",
    scanRoot: "repo root 或 backend package",
    summary: "personal AI app，預期呈現 hybrid search、agentic behavior 與 modular composition；license 只需在結果中記錄，不修改上游。",
    graphShape: ["Import project", "Hybrid search", "Agent routes", "Memory candidate", "Profile overlay"],
    profileRows: [
      ["hybrid-retrieval", "detected candidate"],
      ["agentic-control", "detected candidate"],
      ["tool-calling", "detected candidate"],
      ["memory", "requires state-use evidence"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "readiness_report.json", "license note"],
    warnings: ["AGPL license 要記錄。", "memory 不能只憑 dependency/name detected，需 persistence/use evidence。"],
  },
  {
    id: "direct-kotaemon",
    group: "direct",
    label: "Cinnamon/kotaemon",
    short: "Kotaemon",
    mode: "full repo or app package",
    gate: "Tier B direct/bounded import",
    result: "Direct app target",
    resultTone: "pass",
    directRate: "Counts if app package scan passes",
    scanRoot: "repo root 或 app package",
    summary: "document chat RAG UI 與 customizable pipeline，預期可驗證 UI-backed RAG app 的 profile projection。",
    graphShape: ["App import", "Document chat RAG", "Rerank/pipeline evidence", "Multimodal boundary", "Viewer graph"],
    profileRows: [
      ["rag-grounding", "detected candidate"],
      ["reranking", "detected candidate"],
      ["modular-composition", "detected candidate"],
      ["multimodal-grounding", "boundary-limited"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "ai_system_map.md", "system_map.mmd"],
    warnings: ["多模態只在明確 code/config evidence 出現時才標 detected。"],
  },
  {
    id: "direct-neo4j-builder",
    group: "direct",
    label: "neo4j-labs/llm-graph-builder",
    short: "Neo4j Graph Builder",
    mode: "full repo or backend subdir",
    gate: "Tier B graph app target",
    result: "Direct GraphRAG app target",
    resultTone: "pass",
    directRate: "Counts if graph-store evidence is valid",
    scanRoot: "repo root / backend subdir",
    summary: "unstructured data 到 knowledge graph 的 app target。預期 source map 會回到 entity extraction、relationship、Neo4j graph store 相關 code/config。",
    graphShape: ["Import project", "Entity extraction", "Graph store", "Graph retrieval", "Evidence map"],
    profileRows: [
      ["graph-retrieval", "detected candidate"],
      ["source-traceability", "required"],
      ["modular-composition", "possible"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "graph evidence refs", "system_map.mmd"],
    warnings: ["GraphRAG app evidence 必須可追到 code/config，不可只看 README。"],
  },
  {
    id: "direct-onyx",
    group: "direct",
    label: "onyx-dot-app/onyx",
    short: "Onyx",
    mode: "bounded scan only",
    gate: "Tier C scale calibration",
    result: "Calibration only",
    resultTone: "gap",
    directRate: "Does not block acceptance and must not be sole pass target",
    scanRoot: "small bounded subdir only",
    summary: "大型 platform-like repo。預期 UI 要顯示 calibration / scale boundary，而不是把它當成一般 direct success。",
    graphShape: ["Bounded import", "Scale boundary", "Hybrid/agent signals", "Unmapped platform surface", "Calibration report"],
    profileRows: [
      ["hybrid-retrieval", "calibration candidate"],
      ["agentic-control", "calibration candidate"],
      ["scan-boundary", "required"],
    ],
    artifacts: ["calibration report", "scan limitation note", "readiness_report.json"],
    warnings: ["非 blocking gate。", "需記錄耗時、記憶體、false positives 與 bounded scan root。"],
  },
  {
    id: "direct-backblaze",
    group: "direct",
    label: "backblaze-b2-samples/agentic-rag-vector-starter-kit",
    short: "Backblaze starter kit",
    mode: "full repo",
    gate: "Tier A deterministic direct gate",
    result: "Small direct gate",
    resultTone: "pass",
    directRate: "Must pass for Tier A",
    scanRoot: "repo root",
    summary: "小型 grounded agent sample，適合作為 CI/release checklist 的可讀性 regression case。",
    graphShape: ["Import project", "Vector RAG", "Agent control", "Tool binding", "Tier A pass/fail"],
    profileRows: [
      ["agentic-control", "detected candidate"],
      ["rag-grounding", "detected candidate"],
      ["tool-calling", "detected candidate"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "readiness_report.json", "read-only status"],
    warnings: ["Tier A 應全部通過；失敗要變成可重現 follow-up。"],
  },
  {
    id: "fixture-lightrag",
    group: "fixture",
    label: "HKUDS/LightRAG",
    short: "LightRAG",
    mode: "fixture / reference only",
    gate: "Coverage fallback",
    result: "Fixture-only coverage gap",
    resultTone: "gap",
    directRate: "Does not count toward direct import success",
    scanRoot: "minimal fixture/snippet",
    summary: "framework/library，不是 application repo。應抽 minimal server 或 graph retrieval sample 校準 expected profile signals。",
    graphShape: ["Reference source", "Minimal fixture", "Graph retrieval rule", "Coverage gap label"],
    profileRows: [
      ["graph-retrieval", "fixture coverage"],
      ["hierarchical-retrieval", "fixture coverage"],
    ],
    artifacts: ["fixture source URL", "commit SHA", "expected profile rows", "coverage gap note"],
    warnings: ["不可作 direct import primary target。", "只能驗證 rule coverage。"],
  },
  {
    id: "fixture-graphrag",
    group: "fixture",
    label: "microsoft/graphrag",
    short: "Microsoft GraphRAG",
    mode: "fixture / reference only",
    gate: "Coverage fallback",
    result: "Fixture-only coverage gap",
    resultTone: "gap",
    directRate: "Does not count toward direct import success",
    scanRoot: "minimal hierarchical graph fixture",
    summary: "data pipeline / transformation suite，不是 app。應用於 hierarchical graph RAG wording 與 rule expected-signal 校準。",
    graphShape: ["Reference source", "Hierarchical graph fixture", "Profile row", "Coverage gap"],
    profileRows: [
      ["graph-retrieval", "fixture coverage"],
      ["hierarchical-retrieval", "fixture coverage"],
    ],
    artifacts: ["fixture snippet", "source commit", "expected evidence rule IDs"],
    warnings: ["不得把 framework/reference 成功算入 direct import success rate。"],
  },
  {
    id: "fixture-rag-anything",
    group: "fixture",
    label: "HKUDS/RAG-Anything",
    short: "RAG-Anything",
    mode: "fixture / reference only",
    gate: "Coverage fallback",
    result: "Fixture-only multimodal coverage",
    resultTone: "gap",
    directRate: "Does not count toward direct import success",
    scanRoot: "minimal multimodal parsing fixture",
    summary: "multimodal RAG framework。UI 應把它顯示成 extension subsystem fixture，而不是 direct imported app。",
    graphShape: ["Reference source", "Multimodal parser", "Dual graph fixture", "Extension subsystem", "Coverage gap"],
    profileRows: [
      ["multimodal-grounding", "fixture coverage"],
      ["extension_nodes", "subgraph preview"],
    ],
    artifacts: ["fixture snippet", "source URL/SHA", "expected profile rows"],
    warnings: ["只抽 parsing / dual-graph 最小 fixture，不引入整個外部專案。"],
  },
  {
    id: "fixture-self-rag",
    group: "fixture",
    label: "AkariAsai/self-rag",
    short: "Self-RAG",
    mode: "fixture / reference only",
    gate: "Coverage fallback",
    result: "Research fixture coverage gap",
    resultTone: "gap",
    directRate: "Does not count toward direct import success",
    scanRoot: "reflection-token fixture",
    summary: "original research implementation，不是 app。預期只抽 reflection/adaptive retrieval 相關最小 fixture。",
    graphShape: ["Research reference", "Reflection-token fixture", "Self-reflection profile", "Coverage gap"],
    profileRows: [
      ["self-reflection", "fixture coverage"],
      ["agentic-control", "not assumed"],
    ],
    artifacts: ["fixture snippet", "paper/repo reference", "expected rule IDs"],
    warnings: ["研究 repo 不作 direct import acceptance gate。"],
  },
  {
    id: "fixture-rag-techniques",
    group: "fixture",
    label: "NirDiamant/RAG_Techniques",
    short: "RAG Techniques",
    mode: "notebook cells to minimal .py fixtures",
    gate: "Coverage fallback",
    result: "Notebook fixture coverage",
    resultTone: "gap",
    directRate: "Does not count toward direct import success",
    scanRoot: "selected notebook-derived .py fixtures",
    summary: "advanced RAG technique cookbook。應只抽最小 cells 轉 `.py` fixture，驗證 corrective/contextual/multi-query retrieval rules。",
    graphShape: ["Notebook source", "Minimal .py fixture", "Retrieval technique rule", "Coverage gap"],
    profileRows: [
      ["corrective-retrieval", "fixture coverage"],
      ["contextual-retrieval", "fixture coverage"],
      ["multi-query-retrieval", "fixture coverage"],
    ],
    artifacts: ["notebook path", "commit SHA", "converted fixture", "expected profile rows"],
    warnings: ["notebook cookbook 不適合 full repo scan。"],
  },
  {
    id: "fixture-rag-fusion",
    group: "fixture",
    label: "Raudaschl/rag-fusion",
    short: "RAG-Fusion",
    mode: "fixture / snippet only",
    gate: "Coverage fallback",
    result: "PoC fixture coverage gap",
    resultTone: "gap",
    directRate: "Does not count toward direct import success",
    scanRoot: "multi-query + RRF fixture",
    summary: "PoC / evaluation harness，不是 app。預期只驗證 multi-query 與 reciprocal rank fusion 類 rule coverage。",
    graphShape: ["PoC reference", "Multi-query fixture", "RRF evidence", "Coverage gap"],
    profileRows: [["multi-query-retrieval", "fixture coverage"]],
    artifacts: ["fixture snippet", "source SHA", "expected rule IDs"],
    warnings: ["不可作 direct import success。"],
  },
  {
    id: "excluded-enterprise-agentic-rag",
    group: "excluded",
    label: "ara-5/Enterprise-Agentic-RAG-Platform",
    short: "Enterprise Agentic RAG",
    mode: "excluded research candidate",
    gate: "Not in Plan 14 validation set",
    result: "Excluded for low maturity",
    resultTone: "gap",
    directRate: "Does not count toward any gate",
    scanRoot: "none",
    summary: "名稱與描述相關，但目前只作 research snapshot。UI 應顯示 excluded，不建立 direct import 或 fixture validation 狀態。",
    graphShape: ["Research snapshot", "Maturity check", "Excluded", "No import artifact", "No gate credit"],
    profileRows: [
      ["agentic-control", "not evaluated"],
      ["rag-grounding", "not evaluated"],
    ],
    artifacts: ["research note only"],
    warnings: ["成熟度不足，暫不納入。", "不要用它補 direct app coverage。"],
  },
  {
    id: "excluded-contextual-rag",
    group: "excluded",
    label: "Abiorh001/Contextual_rag",
    short: "Contextual_rag",
    mode: "excluded research candidate",
    gate: "Not in Plan 14 validation set",
    result: "Excluded for low maturity",
    resultTone: "gap",
    directRate: "Does not count toward any gate",
    scanRoot: "none",
    summary: "描述相關，但目前只作 research snapshot。預期狀態是 no import / no fixture，不計入 coverage fallback。",
    graphShape: ["Research snapshot", "Maturity check", "Excluded", "No import artifact", "No gate credit"],
    profileRows: [["contextual-retrieval", "not evaluated"]],
    artifacts: ["research note only"],
    warnings: ["成熟度不足，暫不納入。", "不應被 UI 誤標為 coverage fallback。"],
  },
  {
    id: "excluded-precision-rag",
    group: "excluded",
    label: "garvitsingh006/PrecisionRAG",
    short: "PrecisionRAG",
    mode: "excluded research candidate",
    gate: "Not in Plan 14 validation set",
    result: "Excluded for insufficient metadata",
    resultTone: "gap",
    directRate: "Does not count toward any gate",
    scanRoot: "none",
    summary: "描述相關但成熟度與 metadata 不適合作 canonical validation target。UI 應呈現為 excluded 候選，不進入 scanner simulation。",
    graphShape: ["Research snapshot", "Maturity check", "Excluded", "No import artifact", "No gate credit"],
    profileRows: [["rag-grounding", "not evaluated"]],
    artifacts: ["research note only"],
    warnings: ["成熟度不足，暫不納入。", "沒有 profile coverage 意義。"],
  },
  {
    id: "det-non-grounded",
    group: "deterministic",
    label: "non_grounded_llm_app",
    short: "Non-grounded LLM",
    mode: "deterministic fixture",
    gate: "Required AI-system fixture",
    result: "Valid non-RAG app",
    resultTone: "pass",
    directRate: "Counts as fixture validation, not direct import",
    scanRoot: "tests/fixtures/ai_systems/non_grounded_llm_app",
    summary: "沒有 grounding、沒有 agent control。UI 應顯示 generic LLM app，且 Naive RAG core applicable=false。",
    graphShape: ["Input", "Prompt composer", "LLM generation", "Output guardrail"],
    profileRows: [
      ["rag-grounding", "not_detected"],
      ["agentic-control", "not_detected"],
      ["naive-rag-core", "applicable=false"],
    ],
    artifacts: ["ai_system_map.json", "readiness_report.json", "system_map.mmd"],
    warnings: ["不能因為有 LLM dependency 就宣告 RAG。"],
  },
  {
    id: "det-tool-agent",
    group: "deterministic",
    label: "tool_using_agent",
    short: "Tool agent",
    mode: "deterministic fixture",
    gate: "Required AI-system fixture",
    result: "Agent without RAG",
    resultTone: "pass",
    directRate: "Counts as fixture validation, not direct import",
    scanRoot: "tests/fixtures/ai_systems/tool_using_agent",
    summary: "沒有 grounding，但有 tool/agent components。UI 應顯示 agent control 與 tool binding，不可宣告 RAG。",
    graphShape: ["Input", "Planner/router", "Tool binding", "Tool result", "LLM output"],
    profileRows: [
      ["tool-calling", "detected"],
      ["agentic-control", "detected"],
      ["rag-grounding", "not_detected"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "execution_paths.json"],
    warnings: ["tool definition 與 actual binding/dispatch evidence 要分開記錄。"],
  },
  {
    id: "det-grounded-rag",
    group: "deterministic",
    label: "grounded_rag_service",
    short: "Grounded RAG",
    mode: "deterministic fixture",
    gate: "Required AI-system fixture",
    result: "RAG without agentic control",
    resultTone: "pass",
    directRate: "Counts as fixture validation, not direct import",
    scanRoot: "tests/fixtures/ai_systems/grounded_rag_service",
    summary: "有 grounding、沒有 agent loop。UI 應呈現 Naive RAG core readiness，但 agentic-control 不應被 detected。",
    graphShape: ["Document loader", "Chunk/index", "Retriever", "Prompt augmentation", "LLM answer"],
    profileRows: [
      ["rag-grounding", "detected"],
      ["naive-rag-core", "evaluated"],
      ["agentic-control", "not_detected"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "readiness_report.json", "system_map.mmd"],
    warnings: ["沒有 citation/source mapping 不代表不是 RAG，只會形成 source_traceability finding。"],
  },
  {
    id: "det-grounded-agent",
    group: "deterministic",
    label: "grounded_agent_system",
    short: "Grounded agent",
    mode: "deterministic fixture",
    gate: "Required AI-system fixture",
    result: "Grounding + agent control",
    resultTone: "pass",
    directRate: "Counts as fixture validation, not direct import",
    scanRoot: "tests/fixtures/ai_systems/grounded_agent_system",
    summary: "同時有 grounding 與 agentic-control。UI 應把 retrieval/evidence 與 planner/router/action decision 分開標記。",
    graphShape: ["Planner", "Retriever", "Evidence pack", "Tool/action decision", "Answer"],
    profileRows: [
      ["rag-grounding", "detected"],
      ["agentic-control", "detected"],
      ["tool-calling", "detected or undetermined"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "execution_paths.json", "readiness_report.json"],
    warnings: ["兩種能力要各自有 evidence，不能互相推論。"],
  },
  {
    id: "det-workflow-json",
    group: "deterministic",
    label: "workflow_orchestrated_ai_system",
    short: "Workflow JSON",
    mode: "workflow JSON fixture",
    gate: "Required AI-system fixture",
    result: "Generic workflow graph",
    resultTone: "pass",
    directRate: "Counts as fixture validation, not direct import",
    scanRoot: "tests/fixtures/ai_systems/workflow_orchestrated_ai_system",
    summary: "以 Langflow/Dify/Flowise-like JSON 驗證 generic nodes/edges/config facts。UI 應顯示 JSON pointer evidence，但不宣稱平台 runtime semantics。",
    graphShape: ["Workflow JSON", "JSON pointer evidence", "Nodes/edges", "Generic graph projection", "Schema validation"],
    profileRows: [
      ["workflow-orchestration", "detected from JSON pointers"],
      ["rag-grounding", "optional"],
      ["agentic-control", "optional"],
    ],
    artifacts: ["ai_system_map.json", "profile_signals.json", "system_map.mmd", "json pointer evidence"],
    warnings: ["只驗證 generic workflow facts；不承諾平台專用 importer、runtime execution 或 round-trip。"],
  },
];

const sourceBackedExampleRefinements = {
  "direct-private-gpt": {
    summary: "PrivateGPT 比較像 API-first AI application layer，不是單一路徑 RAG app。source 顯示 ingest/artifacts API、VectorStore + NodeStore、semantic search workflow/tool 與 chat/tools/skills/files；但 primitives router 裡 keyword/hybrid search 尚未實作，所以主圖應標 semantic retrieval，而不是硬說 hybrid retrieval。",
    graphShape: ["FastAPI routers", "Artifact ingest", "VectorStore + NodeStore", "Semantic search workflow/tool", "Chat/tools/skills layer"],
    profileRows: [
      ["rag-grounding", "detected: semantic retriever workflow"],
      ["modular-composition", "detected: componentized ingest/vector/workflow"],
      ["tool-calling", "detected candidate: chat/tools/skills layer"],
      ["hybrid-retrieval", "not detected: keyword/hybrid primitives are unimplemented"],
    ],
    sourceFiles: [
      ["retrieval workflow", "https://github.com/zylon-ai/private-gpt/blob/main/private_gpt/components/workflows/retrieval/retrieval.py"],
      ["semantic search workflow", "https://github.com/zylon-ai/private-gpt/blob/main/private_gpt/components/workflows/retrieval/semantic_search.py"],
      ["semantic search tool", "https://github.com/zylon-ai/private-gpt/blob/main/private_gpt/components/tools/builders/semantic_search_builder.py"],
      ["primitives API", "https://github.com/zylon-ai/private-gpt/blob/main/private_gpt/server/primitives/primitives_router.py"],
      ["ingest API", "https://github.com/zylon-ai/private-gpt/blob/main/private_gpt/server/ingest/ingest_router.py"],
    ],
  },
  "direct-quivr": {
    summary: "Quivr 的核心是 Brain orchestration：storage upload 經 file processor 變 LangChain Documents，再進 embeddings/vector store；QuivrQARAGLangGraph 做 task split/tool routing，檢索層用 ContextualCompressionRetriever + reranker，dynamic_retrieve 會放大 top_n/k 重試。",
    graphShape: ["Brain/storage upload", "File processor", "Embeddings/vector store", "LangGraph task split", "Contextual rerank + answer"],
    profileRows: [
      ["rag-grounding", "detected: vector retriever chain"],
      ["reranking", "detected: ContextualCompressionRetriever"],
      ["agentic-control", "detected candidate: LangGraph task/tool routing"],
      ["tool-calling", "secondary: available tools, not the whole OS"],
    ],
    sourceFiles: [
      ["brain orchestration", "https://github.com/QuivrHQ/quivr/blob/main/core/quivr_core/brain/brain.py"],
      ["LangGraph RAG", "https://github.com/QuivrHQ/quivr/blob/main/core/quivr_core/rag/quivr_rag_langgraph.py"],
      ["classic RAG chain", "https://github.com/QuivrHQ/quivr/blob/main/core/quivr_core/rag/quivr_rag.py"],
      ["tool factory", "https://github.com/QuivrHQ/quivr/blob/main/core/quivr_core/llm_tools/llm_tools.py"],
    ],
  },
  "direct-langchain-chatchat": {
    summary: "Langchain-Chatchat 的主線不能被誤判成純 agent-first。kb_chat 路徑是 classic KB chat：search_docs -> KBService.search_docs -> context prompt -> LLM；FAISS KB service / file_rag ensemble 可合併 BM25 + vector similarity。另有 search-engine chat、file RAG 與 agent/tool 模式；kb_chat 這條路上的 reranker code 仍是註解狀態。",
    graphShape: ["KB chat/API", "KBService.search_docs", "FAISS/vector index", "BM25 + vector ensemble", "Prompt + LLM / optional tools"],
    profileRows: [
      ["hybrid-retrieval", "detected: BM25 + vector ensemble"],
      ["tool-calling", "detected: tools_factory + PlatformToolsAgentExecutor"],
      ["agentic-control", "detected: separate agent/tool mode"],
      ["reranking", "boundary: not active on kb_chat path"],
    ],
    sourceFiles: [
      ["KB chat route", "https://github.com/chatchat-space/Langchain-Chatchat/blob/master/libs/chatchat-server/chatchat/server/chat/kb_chat.py"],
      ["KB document API", "https://github.com/chatchat-space/Langchain-Chatchat/blob/master/libs/chatchat-server/chatchat/server/knowledge_base/kb_doc_api.py"],
      ["FAISS KB service", "https://github.com/chatchat-space/Langchain-Chatchat/blob/master/libs/chatchat-server/chatchat/server/knowledge_base/kb_service/faiss_kb_service.py"],
      ["local KB tool", "https://github.com/chatchat-space/Langchain-Chatchat/blob/master/libs/chatchat-server/chatchat/server/agent/tools_factory/search_local_knowledgebase.py"],
      ["ensemble retriever", "https://github.com/chatchat-space/Langchain-Chatchat/blob/master/libs/chatchat-server/chatchat/server/file_rag/retrievers/ensemble.py"],
    ],
  },
  "direct-khoj": {
    summary: "Khoj 是 personal AI / second-brain platform，不是單純 RAG。api_chat/event_generator 統籌 chat、research、online/code/operator/MCP tools；search_documents 會先用 LLM extract_questions 產生查詢，再做 knowledge search 去重；agenerate_chat_response 把 references、online、code、operator、research context 組進 conversation context 後分派 provider。",
    graphShape: ["Chat event generator", "Query rewrite / extract_questions", "Knowledge search + dedupe", "Tool/research/operator context", "Provider response"],
    profileRows: [
      ["agentic-control", "detected: agents with configured input tools"],
      ["tool-calling", "detected: online search/run_code/MCP/GUI actions"],
      ["memory", "detected candidate: user memory adapters"],
      ["rag-grounding", "conditional: Notes or agent knowledge must be active"],
    ],
    sourceFiles: [
      ["chat router", "https://github.com/khoj-ai/khoj/blob/master/src/khoj/routers/api_chat.py"],
      ["router helpers", "https://github.com/khoj-ai/khoj/blob/master/src/khoj/routers/helpers.py"],
      ["research router", "https://github.com/khoj-ai/khoj/blob/master/src/khoj/routers/research.py"],
      ["content API", "https://github.com/khoj-ai/khoj/blob/master/src/khoj/routers/api_content.py"],
      ["agents API", "https://github.com/khoj-ai/khoj/blob/master/src/khoj/routers/api_agents.py"],
    ],
  },
  "direct-kotaemon": {
    summary: "Kotaemon 預設是 RAG UI/framework，不是純 GraphRAG repo。flowsettings 把 docstore/vectorstore/LLM/embeddings/rerankings 都抽成可換元件；FullQAPipeline 是預設 QA 流；ReactAgentPipeline/RewooAgentPipeline 是工具型 reasoning；NanoGraphRAG/LightRAG 是 optional graph indexing/retrieval extension。",
    graphShape: ["Config/UI", "DocStore + VectorStore", "Full QA retrieval", "Evidence prep/citations", "Optional agent + KG extensions"],
    profileRows: [
      ["rag-grounding", "detected: vector index/retrieval"],
      ["reranking", "detected candidate: reranking components"],
      ["graph-retrieval", "optional extension: NanoGraphRAG/LightRAG"],
      ["agentic-control", "optional extension: React/ReWOO pipelines"],
    ],
    sourceFiles: [
      ["flow settings", "https://github.com/Cinnamon/kotaemon/blob/main/flowsettings.py"],
      ["default QA pipeline", "https://github.com/Cinnamon/kotaemon/blob/main/libs/ktem/ktem/reasoning/simple.py"],
      ["React agent pipeline", "https://github.com/Cinnamon/kotaemon/blob/main/libs/ktem/ktem/reasoning/react.py"],
      ["NanoGraphRAG pipeline", "https://github.com/Cinnamon/kotaemon/blob/main/libs/ktem/ktem/index/file/graph/nano_pipelines.py"],
      ["vector index", "https://github.com/Cinnamon/kotaemon/blob/main/libs/kotaemon/kotaemon/indices/vectorindex.py"],
    ],
  },
  "direct-neo4j-builder": {
    summary: "Neo4j LLM Graph Builder 的主軸是 knowledge graph construction，而不是 generic RAG。流程是 source scan + chunk + LLM graph extraction + Neo4j indexing，再進 graph/vector/fulltext QA；Q&A 是建立在已抽出的 graph documents、chunks 與 vector/fulltext index 之上。",
    graphShape: ["Source scan/extract API", "Create chunks", "LLM graph extraction", "Neo4j graph/vector/fulltext index", "Graph/vector QA"],
    profileRows: [
      ["graph-retrieval", "detected: Neo4j graph + vector QA"],
      ["rag-grounding", "detected: chunks/sources/QA references"],
      ["source-traceability", "strong: source nodes and chunk ids"],
    ],
    sourceFiles: [
      ["scan/extract API", "https://github.com/neo4j-labs/llm-graph-builder/blob/main/backend/score.py"],
      ["chunk creation", "https://github.com/neo4j-labs/llm-graph-builder/blob/main/backend/src/create_chunks.py"],
      ["LLM graph extraction", "https://github.com/neo4j-labs/llm-graph-builder/blob/main/backend/src/llm.py"],
      ["post processing", "https://github.com/neo4j-labs/llm-graph-builder/blob/main/backend/src/post_processing.py"],
      ["QA integration", "https://github.com/neo4j-labs/llm-graph-builder/blob/main/backend/src/QA_integration.py"],
    ],
  },
  "direct-onyx": {
    summary: "Onyx 是多 worker、多 connector、多租戶的 enterprise search/chat platform，不能壓成單機 document RAG。source 顯示 connector docfetching worker -> indexing pipeline -> search pipeline/search tool -> LLM loop/deep research；SearchTool 會包 persona/project/ACL filters，也能混 federated search。它是 scale calibration，不是一般 direct success target。",
    graphShape: ["Connectors/docfetching workers", "Chunk/embed/index pipeline", "Search pipeline/tool with ACL filters", "LLM loop / deep research", "Citations/UI calibration"],
    profileRows: [
      ["hybrid-retrieval", "detected candidate: search pipeline + document index"],
      ["agentic-control", "detected candidate: tool-backed chat/research flows"],
      ["deployment topology", "platform: workers/connectors/multi-tenant"],
      ["scan-boundary", "required: calibration only, Lite mode differs"],
    ],
    sourceFiles: [
      ["chat processing", "https://github.com/onyx-dot-app/onyx/blob/main/backend/onyx/chat/process_message.py"],
      ["LLM loop", "https://github.com/onyx-dot-app/onyx/blob/main/backend/onyx/chat/llm_loop.py"],
      ["search pipeline", "https://github.com/onyx-dot-app/onyx/blob/main/backend/onyx/context/search/pipeline.py"],
      ["docfetching worker", "https://github.com/onyx-dot-app/onyx/blob/main/backend/onyx/background/indexing/run_docfetching.py"],
      ["indexing pipeline", "https://github.com/onyx-dot-app/onyx/blob/main/backend/onyx/indexing/indexing_pipeline.py"],
      ["search tool", "https://github.com/onyx-dot-app/onyx/blob/main/backend/onyx/tools/tool_implementations/search/search_tool.py"],
    ],
  },
  "direct-backblaze": {
    summary: "Backblaze starter kit 是小型 reference app，分層和文件一致：B2 upload -> document pipeline chunk/classify/summarize/embed/store -> agentic retrieval intent route/query planning/vector search/RRF/rerank/evidence loop -> chat SSE with citations。它是 vector-centric RAG，不是 GraphRAG 或 connector-rich platform。",
    graphShape: ["B2 upload", "Chunk/classify/summarize", "Embed + LanceDB vector store", "Planner + fusion/rerank/evidence loop", "Chat SSE + citations"],
    profileRows: [
      ["rag-grounding", "detected: retrieval service"],
      ["agentic-control", "detected: intent routing/query planning/evidence loop"],
      ["reranking", "detected: reranker service"],
      ["deployment topology", "reference starter kit, not enterprise platform"],
    ],
    sourceFiles: [
      ["architecture doc", "https://github.com/backblaze-b2-samples/agentic-rag-vector-starter-kit/blob/main/ARCHITECTURE.md"],
      ["document pipeline doc", "https://github.com/backblaze-b2-samples/agentic-rag-vector-starter-kit/blob/main/docs/features/document-pipeline.md"],
      ["agentic retrieval doc", "https://github.com/backblaze-b2-samples/agentic-rag-vector-starter-kit/blob/main/docs/features/agentic-retrieval.md"],
      ["pipeline", "https://github.com/backblaze-b2-samples/agentic-rag-vector-starter-kit/blob/main/services/api/app/service/pipeline.py"],
      ["retrieval", "https://github.com/backblaze-b2-samples/agentic-rag-vector-starter-kit/blob/main/services/api/app/service/retrieval.py"],
    ],
  },
  "fixture-lightrag": {
    summary: "LightRAG 是 library/server，不是 app target。真實架構是 graph/entity relation pipeline + query API + graph API + optional rerank。UI 應把它映射成 extension subsystem fixture，而不是直接 app import。",
    graphShape: ["Document/query API", "Graph/entity pipeline", "Graph storage APIs", "Optional rerank", "Graph viewer"],
    profileRows: [
      ["graph-retrieval", "fixture coverage: dual-layer graph + vector"],
      ["extension_nodes", "subgraph: LightRAG framework/server"],
      ["direct-import", "not counted: framework/reference target"],
    ],
    warnings: [
      "可作 graph-RAG extension fixture，但不得計入 direct app success rate。",
      "目前未覆蓋完整 server/WebUI、parser routing、多 storage、multimodal 與 role-specific LLM。",
    ],
    sourceFiles: [
      ["pipeline", "https://github.com/HKUDS/LightRAG/blob/main/lightrag/pipeline.py"],
      ["query routes", "https://github.com/HKUDS/LightRAG/blob/main/lightrag/api/routers/query_routes.py"],
      ["graph routes", "https://github.com/HKUDS/LightRAG/blob/main/lightrag/api/routers/graph_routes.py"],
      ["rerank", "https://github.com/HKUDS/LightRAG/blob/main/lightrag/rerank.py"],
    ],
  },
  "fixture-graphrag": {
    summary: "Microsoft GraphRAG 是 indexing/query pipeline library：PipelineFactory 組 extract_graph、finalize_graph、create_communities、community reports、embeddings；query factory 建 local/global/drift/basic search engine。不是 app direct target。",
    graphShape: ["Load documents", "Extract entity graph", "Create communities", "Community reports/embeddings", "Local/global/drift search"],
    profileRows: [
      ["graph-retrieval", "fixture coverage: entity/community graph"],
      ["hierarchical-retrieval", "fixture coverage: communities/reports"],
      ["direct-import", "not counted: indexing/query framework"],
    ],
    warnings: [
      "只適合校準 GraphRAG pipeline signals，不應宣稱完整 app import。",
      "目前未覆蓋 claim extraction、community report generation、DRIFT/global/local query engine 與 prompt tuning。",
    ],
    sourceFiles: [
      ["pipeline factory", "https://github.com/microsoft/graphrag/blob/main/packages/graphrag/graphrag/index/workflows/factory.py"],
      ["extract graph workflow", "https://github.com/microsoft/graphrag/blob/main/packages/graphrag/graphrag/index/workflows/extract_graph.py"],
      ["communities workflow", "https://github.com/microsoft/graphrag/blob/main/packages/graphrag/graphrag/index/workflows/create_communities.py"],
      ["query factory", "https://github.com/microsoft/graphrag/blob/main/packages/graphrag/graphrag/query/factory.py"],
    ],
  },
  "fixture-rag-anything": {
    summary: "RAG-Anything 是 LightRAG-backed multimodal processing pipeline：RAGAnything class 包 QueryMixin/ProcessorMixin/BatchMixin，ProcessorMixin 管 doc_status 與 multimodal completion state，modalprocessors 對 image/table/equation/generic content 做 context extraction/captioning，再寫回 LightRAG。",
    graphShape: ["Parse documents", "Text insertion to LightRAG", "Image/table/equation processors", "Multimodal status/cache", "Text/VLM enhanced query"],
    profileRows: [
      ["multimodal-grounding", "fixture coverage: modal processors"],
      ["graph-retrieval", "via LightRAG backend"],
      ["extension_nodes", "subgraph: multimodal processor pipeline"],
    ],
    sourceFiles: [
      ["RAGAnything class", "https://github.com/HKUDS/RAG-Anything/blob/main/raganything/raganything.py"],
      ["query mixin", "https://github.com/HKUDS/RAG-Anything/blob/main/raganything/query.py"],
      ["processor mixin", "https://github.com/HKUDS/RAG-Anything/blob/main/raganything/processor.py"],
      ["modal processors", "https://github.com/HKUDS/RAG-Anything/blob/main/raganything/modalprocessors.py"],
    ],
  },
  "fixture-self-rag": {
    summary: "Self-RAG 是 research implementation，不是 app。source 分成 data_creation 的 critic/reward prompts 與 retrieval_lm 的 passage retrieval/index/baseline runs；應映射成 self-reflection/adaptive retrieval fixture。",
    graphShape: ["Need-retrieval critic", "Passage embeddings/index", "Retrieve passages", "Groundness/relevance/utility critics", "Generate/evaluate"],
    profileRows: [
      ["self-reflection", "fixture coverage: reflection/adaptive retrieval"],
      ["rag-grounding", "fixture coverage: passage retrieval path"],
      ["agentic-control", "not assumed: no tool runtime"],
    ],
    warnings: [
      "這是 research inference/training code，不是 app import target。",
      "目前 fixture 不覆蓋訓練資料生成、retriever setup、beam/path scoring 與完整 inference。",
    ],
    sourceFiles: [
      ["passage retrieval", "https://github.com/AkariAsai/self-rag/blob/main/retrieval_lm/passage_retrieval.py"],
      ["short-form run", "https://github.com/AkariAsai/self-rag/blob/main/retrieval_lm/run_short_form.py"],
      ["need retrieval critic", "https://github.com/AkariAsai/self-rag/blob/main/data_creation/critic/gpt4_reward/chatgpt_need_retrieval.py"],
    ],
  },
  "fixture-rag-techniques": {
    summary: "RAG_Techniques 是 runnable cookbook scripts，不是 app。實際 code 分別示範 fusion retrieval、CRAG、Self-RAG、GraphRAG 等技法；UI 應呈現多個 fixture snippets，而非一個統一產品架構。",
    graphShape: ["Notebook/script source", "Fusion BM25+vector", "CRAG evaluate/rewrite", "Self-RAG decisions", "GraphRAG script"],
    sourceFiles: [
      ["fusion retrieval", "https://github.com/NirDiamant/RAG_Techniques/blob/main/all_rag_techniques_runnable_scripts/fusion_retrieval.py"],
      ["CRAG script", "https://github.com/NirDiamant/RAG_Techniques/blob/main/all_rag_techniques_runnable_scripts/crag.py"],
      ["Self-RAG script", "https://github.com/NirDiamant/RAG_Techniques/blob/main/all_rag_techniques_runnable_scripts/self_rag.py"],
      ["GraphRAG script", "https://github.com/NirDiamant/RAG_Techniques/blob/main/all_rag_techniques_runnable_scripts/graph_rag.py"],
    ],
  },
  "fixture-rag-fusion": {
    summary: "RAG-Fusion 是 PoC/evaluation harness。eval/retrieval.py 有 vector search、BM25、hybrid RRF、LLM-generated query rewrites、多種 fusion variants；eval/rerank.py 用 cross-encoder rerank；query_cache.py 快取 LLM-generated rewrites。",
    graphShape: ["Generate query rewrites", "Vector search", "BM25/hybrid retrieval", "RRF fusion", "Cross-encoder rerank"],
    profileRows: [
      ["multi-query-retrieval", "fixture coverage: query rewrites + RRF"],
      ["hybrid-retrieval", "fixture coverage: BM25 + vector"],
      ["reranking", "fixture coverage: cross-encoder rerank"],
    ],
    sourceFiles: [
      ["retrieval variants", "https://github.com/Raudaschl/rag-fusion/blob/master/eval/retrieval.py"],
      ["reranker", "https://github.com/Raudaschl/rag-fusion/blob/master/eval/rerank.py"],
      ["query cache", "https://github.com/Raudaschl/rag-fusion/blob/master/eval/query_cache.py"],
    ],
  },
  "excluded-enterprise-agentic-rag": {
    mode: "excluded but source-read",
    result: "Code-present but excluded",
    directRate: "Does not count toward any Plan 14 gate",
    scanRoot: "repo source inspected; no import artifact",
    summary: "雖然 Plan 14 因成熟度/metadata 把它排除，但 code 確實是 LangGraph corrective agentic RAG：route_query 決定是否用 documents，retrieve 做 hybrid FAISS+BM25 + cross-encoder rerank，grade_documents/rewrite_query/web_search 形成 corrective loop。",
    graphShape: ["Route query", "Hybrid FAISS+BM25 retrieve", "Cross-encoder rerank", "Grade/rewrite loop", "Optional web search"],
    profileRows: [
      ["agentic-control", "code-present but excluded from gate"],
      ["hybrid-retrieval", "code-present but excluded from gate"],
      ["corrective-retrieval", "code-present but excluded from gate"],
    ],
    artifacts: ["research note only", "source links", "no ai_system_map.json"],
    warnings: [
      "架構上像 app，但因成熟度/validation policy 暫不作 canonical direct target。",
      "不得用它補 direct app coverage；若未來納入，應走 direct-app candidate 而不是 fixture。",
    ],
    sourceFiles: [
      ["LangGraph agent", "https://github.com/ara-5/Enterprise-Agentic-RAG-Platform/blob/main/app/agent.py"],
      ["RAG QA", "https://github.com/ara-5/Enterprise-Agentic-RAG-Platform/blob/main/app/rag_qa.py"],
      ["ingestion", "https://github.com/ara-5/Enterprise-Agentic-RAG-Platform/blob/main/ingestion/ingest.py"],
      ["hybrid store", "https://github.com/ara-5/Enterprise-Agentic-RAG-Platform/blob/main/vectorstore/store.py"],
    ],
  },
  "excluded-contextual-rag": {
    mode: "excluded but source-read",
    result: "Code-present but excluded",
    directRate: "Does not count toward any Plan 14 gate",
    scanRoot: "repo source inspected; no import artifact",
    summary: "Contextual_rag 雖被排除，但 code 是 contextual chunking + hybrid search：ContextualizedRAG 先用 LLM 產生 chunk context，OpenAI embeddings 存 ChromaDB，ElasticsearchBM25 做 sparse search，process_hybrid_search 合併，再 rerank。",
    graphShape: ["Document chunking", "Contextualize chunks", "Chroma embeddings", "Elasticsearch BM25", "Hybrid search/rerank"],
    profileRows: [
      ["contextual-retrieval", "code-present but excluded from gate"],
      ["hybrid-retrieval", "code-present but excluded from gate"],
      ["reranking", "code-present but excluded from gate"],
    ],
    artifacts: ["research note only", "source links", "no ai_system_map.json"],
    warnings: [
      "技術本質是 contextual/hybrid retrieval pipeline，不是 control-plane agent。",
      "仍因成熟度、service/API boundary 與測試不足留在 excluded，不計入 coverage fallback。",
    ],
    sourceFiles: [
      ["contextual RAG", "https://github.com/Abiorh001/Contextual_rag/blob/main/contextual_rag.py"],
      ["BM25 search", "https://github.com/Abiorh001/Contextual_rag/blob/main/elasticsearch_bm25.py"],
    ],
  },
  "excluded-precision-rag": {
    mode: "excluded but source-read",
    result: "Code-present but excluded",
    directRate: "Does not count toward any Plan 14 gate",
    scanRoot: "repo source inspected; no import artifact",
    summary: "PrecisionRAG 雖被排除，但 code 是 LangGraph + parent-doc retrieval + Tavily corrective path：precision_rag.py 建 FAISS retriever cache、RetrieveDecision parser、StateGraph；app.py 提供 config/upload/evaluation API；frontend PipelineVisualizer 顯示 Retrieve/Web Search 等步驟。",
    graphShape: ["Upload/config API", "Parent-doc FAISS retriever", "Retrieve decision", "LangGraph correction/web search", "Pipeline visualizer"],
    profileRows: [
      ["agentic-control", "code-present but excluded from gate"],
      ["rag-grounding", "code-present but excluded from gate"],
      ["corrective-retrieval", "code-present but excluded from gate"],
    ],
    artifacts: ["research note only", "source links", "no ai_system_map.json"],
    warnings: [
      "架構上是 full-stack RAG app，但不適合作 minimal/canonical fixture。",
      "若未來納入，應拆成 direct-app candidate：agent loop、parent-doc retrieval、web fallback、evaluation API。",
    ],
    sourceFiles: [
      ["PrecisionRAG graph", "https://github.com/garvitsingh006/PrecisionRAG/blob/main/backend/models/precision_rag.py"],
      ["FastAPI backend", "https://github.com/garvitsingh006/PrecisionRAG/blob/main/backend/app.py"],
      ["pipeline visualizer", "https://github.com/garvitsingh006/PrecisionRAG/blob/main/frontend/src/components/PipelineVisualizer.jsx"],
    ],
  },
};

importExamples.forEach((example) => {
  Object.assign(example, sourceBackedExampleRefinements[example.id] || {});
});

const defaultGraphFocus = {
  view: "overview",
  selectedNodeId: "hybrid_retriever",
  quality: "87%",
  note: "顯示完整 normalized graph。",
};

const exampleGraphFocus = {
  "direct-private-gpt": {
    view: "retrieval",
    selectedNodeId: "hybrid_retriever",
    quality: "86%",
    note: "PrivateGPT source：主 graph 聚焦 semantic retrieval / grounding path，不宣稱 hybrid search。",
  },
  "direct-quivr": {
    view: "retrieval",
    selectedNodeId: "reranker",
    quality: "74%",
    note: "Bounded RAG platform scan：主 graph 聚焦 retrieval enhancement，並保留 bounded-scan 風險。",
  },
  "direct-langchain-chatchat": {
    view: "mode",
    selectedNodeId: "tool_agent",
    quality: "76%",
    note: "多 profile app：主 graph 聚焦 agentic/tool mode 與多能力疊加。",
  },
  "direct-khoj": {
    view: "control",
    selectedNodeId: "tool_agent",
    quality: "82%",
    note: "Personal AI app：主 graph 聚焦 agent control 與 tool dispatch。",
  },
  "direct-kotaemon": {
    view: "retrieval",
    selectedNodeId: "reranker",
    quality: "84%",
    note: "UI-backed document RAG：主 graph 聚焦 retrieval/rerank pipeline。",
  },
  "direct-neo4j-builder": {
    view: "extension",
    selectedNodeId: "graph_rag_system",
    quality: "88%",
    note: "GraphRAG app：主 graph 聚焦可展開 graph retrieval subsystem。",
  },
  "direct-onyx": {
    view: "unmapped",
    selectedNodeId: "unmapped_orchestrator",
    quality: "61%",
    note: "大型 platform calibration：主 graph 聚焦 unmapped / bounded scan boundary。",
  },
  "direct-backblaze": {
    view: "control",
    selectedNodeId: "tool_agent",
    quality: "91%",
    note: "Tier A grounded agent sample：主 graph 聚焦 agent control + RAG path。",
  },
  "fixture-lightrag": {
    view: "extension",
    selectedNodeId: "graph_rag_system",
    quality: "68%",
    note: "Reference-only graph RAG fixture：主 graph 聚焦 extension subsystem，不計入 direct success。",
  },
  "fixture-graphrag": {
    view: "extension",
    selectedNodeId: "graph_rag_system",
    quality: "69%",
    note: "Reference-only hierarchical GraphRAG：主 graph 聚焦 graph extension 與 coverage gap。",
  },
  "fixture-rag-anything": {
    view: "extension",
    selectedNodeId: "rag_anything_system",
    quality: "67%",
    note: "Reference-only multimodal RAG：主 graph 聚焦 RAG-Anything subgraph。",
  },
  "fixture-self-rag": {
    view: "mode",
    selectedNodeId: "agent_loop",
    quality: "62%",
    note: "Research fixture：主 graph 聚焦 reasoning mode，而非 direct app import。",
  },
  "fixture-rag-techniques": {
    view: "retrieval",
    selectedNodeId: "hybrid_retriever",
    quality: "66%",
    note: "Notebook-derived retrieval fixtures：主 graph 聚焦 retrieval technique rules。",
  },
  "fixture-rag-fusion": {
    view: "retrieval",
    selectedNodeId: "hybrid_retriever",
    quality: "65%",
    note: "PoC fixture：主 graph 聚焦 multi-query retrieval path，標記 fixture-only gap。",
  },
  "det-non-grounded": {
    view: "dataflow",
    selectedNodeId: "llm_answerer",
    quality: "93%",
    note: "Non-grounded LLM fixture：主 graph 聚焦 generation path，retrieval/RAG 不亮起。",
  },
  "det-tool-agent": {
    view: "control",
    selectedNodeId: "tool_agent",
    quality: "92%",
    note: "Tool agent fixture：主 graph 聚焦 tool/agent control，不宣告 RAG。",
  },
  "det-grounded-rag": {
    view: "retrieval",
    selectedNodeId: "hybrid_retriever",
    quality: "94%",
    note: "Grounded RAG fixture：主 graph 聚焦 Naive RAG readiness path。",
  },
  "det-grounded-agent": {
    view: "control",
    selectedNodeId: "agent_loop",
    quality: "91%",
    note: "Grounded agent fixture：主 graph 聚焦 agent loop，同時保留 retrieval evidence。",
  },
  "det-workflow-json": {
    view: "source",
    selectedNodeId: "router",
    quality: "89%",
    note: "Workflow JSON fixture：主 graph 聚焦 source mapping / JSON pointer evidence。",
  },
  "excluded-enterprise-agentic-rag": {
    view: "unmapped",
    selectedNodeId: "unmapped_orchestrator",
    quality: "34%",
    note: "Excluded candidate：主 graph 顯示 unknown-safe unmapped 狀態，不建立 import result。",
  },
  "excluded-contextual-rag": {
    view: "unmapped",
    selectedNodeId: "unmapped_orchestrator",
    quality: "32%",
    note: "Excluded candidate：主 graph 顯示 metadata 不足時的保守未映射結果。",
  },
  "excluded-precision-rag": {
    view: "unmapped",
    selectedNodeId: "unmapped_orchestrator",
    quality: "30%",
    note: "Excluded candidate：主 graph 顯示不進 scanner simulation 的 excluded 狀態。",
  },
};

Object.assign(exampleGraphFocus, {
  "direct-quivr": {
    view: "control",
    selectedNodeId: "router",
    quality: "78%",
    note: "Quivr source：主 graph 聚焦 LangGraph task/tool routing，再接 retrieval+rerank chain。",
  },
  "direct-langchain-chatchat": {
    view: "topology",
    selectedNodeId: "tool_agent",
    quality: "79%",
    note: "Langchain-Chatchat source：主 graph 聚焦 hybrid retrieval + platform/MCP tool agent。",
  },
  "direct-khoj": {
    view: "topology",
    selectedNodeId: "tool_network",
    quality: "80%",
    note: "Khoj source：主 graph 聚焦 agent tools、MCP/online search、memory 與 chat API 邊界。",
  },
  "direct-kotaemon": {
    view: "extension",
    selectedNodeId: "graph_rag_system",
    quality: "84%",
    note: "Kotaemon source：主 graph 聚焦 vector RAG + GraphRAG/LightRAG extension + ReWOO planner。",
  },
  "direct-onyx": {
    view: "topology",
    selectedNodeId: "tool_network",
    quality: "62%",
    note: "Onyx source：主 graph 聚焦 enterprise search/chat platform、tool network 與 calibration boundary。",
  },
  "excluded-enterprise-agentic-rag": {
    view: "control",
    selectedNodeId: "agent_loop",
    quality: "44%",
    note: "Excluded but code-present：主 graph 顯示 LangGraph corrective agent loop；不計入 Plan 14 gate。",
  },
  "excluded-contextual-rag": {
    view: "retrieval",
    selectedNodeId: "hybrid_retriever",
    quality: "40%",
    note: "Excluded but code-present：主 graph 顯示 contextual + hybrid retrieval；不計入 Plan 14 gate。",
  },
  "excluded-precision-rag": {
    view: "control",
    selectedNodeId: "agent_loop",
    quality: "42%",
    note: "Excluded but code-present：主 graph 顯示 LangGraph corrective retrieval path；不計入 Plan 14 gate。",
  },
});

const state = {
  view: "overview",
  selectedNodeId: "hybrid_retriever",
  query: "",
  exampleGroup: "all",
  selectedExampleId: "direct-private-gpt",
  linkedExampleId: null,
};

const graphLayers = document.querySelector("#graphLayers");
const edgeLayer = document.querySelector("#edgeLayer");
const graphCanvas = document.querySelector("#graphCanvas");
const nodeDetail = document.querySelector("#nodeDetail");
const filterButtons = document.querySelectorAll("[data-view]");
const searchInput = document.querySelector("#nodeSearch");
const exampleList = document.querySelector("#exampleList");
const exampleDetail = document.querySelector("#exampleDetail");
const exampleTabs = document.querySelectorAll("[data-example-group]");

function nodeMatchesView(node, viewName) {
  const view = views[viewName];
  return viewName === "overview" || view.tags.some((tag) => node.tags.includes(tag));
}

function nodeMatchesSearch(node) {
  if (!state.query) return true;
  const haystack = [
    node.label,
    node.kind,
    node.layer,
    node.summary,
    node.nodeType,
    node.mode,
    node.topology,
    ...node.tags,
    ...node.sources,
  ]
    .join(" ")
    .toLowerCase();
  return haystack.includes(state.query);
}

function isFocused(node) {
  return nodeMatchesView(node, state.view) && nodeMatchesSearch(node);
}

function renderGraph() {
  graphLayers.innerHTML = layers
    .map((layer) => {
      const layerNodes = nodes.filter((node) => node.layer === layer.id);
      return `
        <section class="graph-layer ${layer.id}" aria-labelledby="${layer.id}-title">
          <div class="layer-label">
            <h3 id="${layer.id}-title">${layer.title}</h3>
            <p>${layer.description}</p>
          </div>
          <div class="layer-nodes">
            ${layerNodes.map(renderNode).join("")}
          </div>
        </section>
      `;
    })
    .join("");

  document.querySelectorAll("[data-node-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedNodeId = button.dataset.nodeId;
      applyView();
    });
  });
}

function renderNode(node) {
  const warning = node.risks.length > 1 || node.tags.includes("risk");
  return `
    <button
      class="node-card ${node.layer} ${node.kind} ${node.nodeType}${warning ? " has-warning" : ""}"
      type="button"
      data-node-id="${node.id}"
      aria-pressed="false"
    >
      <strong>${node.label}</strong>
      <small>${node.nodeType} · ${node.mode}</small>
    </button>
  `;
}

function drawEdges() {
  const canvasRect = graphCanvas.getBoundingClientRect();
  edgeLayer.setAttribute("viewBox", `0 0 ${canvasRect.width} ${canvasRect.height}`);
  edgeLayer.setAttribute("width", canvasRect.width);
  edgeLayer.setAttribute("height", canvasRect.height);

  const view = views[state.view];
  edgeLayer.innerHTML = edges
    .map(([from, to, type], index) => {
      const fromEl = document.querySelector(`[data-node-id="${from}"]`);
      const toEl = document.querySelector(`[data-node-id="${to}"]`);
      if (!fromEl || !toEl) return "";

      const a = fromEl.getBoundingClientRect();
      const b = toEl.getBoundingClientRect();
      const x1 = a.right - canvasRect.left;
      const y1 = a.top + a.height / 2 - canvasRect.top;
      const x2 = b.left - canvasRect.left;
      const y2 = b.top + b.height / 2 - canvasRect.top;
      const mid = Math.max(44, Math.abs(x2 - x1) * 0.45);
      const path = `M ${x1} ${y1} C ${x1 + mid} ${y1}, ${x2 - mid} ${y2}, ${x2} ${y2}`;
      const fromNode = nodes.find((node) => node.id === from);
      const toNode = nodes.find((node) => node.id === to);
      const focused = view.edgeTypes.includes(type) && (isFocused(fromNode) || isFocused(toNode));
      const dimmed = state.view !== "overview" && !focused;
      return `<path class="edge-path ${type}${focused ? " is-focused" : ""}${dimmed ? " is-dimmed" : ""}" d="${path}" data-edge-index="${index}" />`;
    })
    .join("");
}

function applyView() {
  const view = views[state.view];
  const focusedNodes = nodes.filter(isFocused);
  const selectedStillFocused = focusedNodes.some((node) => node.id === state.selectedNodeId);

  if (!selectedStillFocused && focusedNodes.length > 0) {
    state.selectedNodeId = focusedNodes[0].id;
  }

  filterButtons.forEach((button) => {
    const active = button.dataset.view === state.view;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  const linkedExample = importExamples.find((example) => example.id === state.linkedExampleId);
  const linkedFocus = linkedExample ? getExampleGraphFocus(linkedExample) : null;
  document.querySelector("#viewSummary").textContent = linkedExample
    ? `Linked example: ${linkedExample.short}. ${linkedFocus.note}`
    : view.summary;
  document.querySelector("#activeViewLabel").textContent = `View: ${view.label}`;

  document.querySelectorAll("[data-node-id]").forEach((button) => {
    const node = nodes.find((item) => item.id === button.dataset.nodeId);
    const focused = isFocused(node);
    const hiddenBySearch = !nodeMatchesSearch(node);
    const selected = node.id === state.selectedNodeId;
    button.classList.toggle("is-focused", focused);
    button.classList.toggle("is-dimmed", state.view !== "overview" && !focused);
    button.classList.toggle("is-hidden", hiddenBySearch);
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  });

  renderInspector();
  updateStatus(focusedNodes);
  requestAnimationFrame(drawEdges);
}

function renderInspector() {
  const node = nodes.find((item) => item.id === state.selectedNodeId) || nodes[0];
  const subgraph = node.subgraph
    ? `
      <section class="detail-section">
        <details open class="subgraph-details">
          <summary>Expand internal pipeline</summary>
          <ol>${node.subgraph.map((step) => `<li>${step}</li>`).join("")}</ol>
        </details>
      </section>
    `
    : "";

  nodeDetail.innerHTML = `
    <div class="detail-title">
      <span class="detail-icon ${node.layer}" aria-hidden="true"></span>
      <div>
        <h3>${node.label}</h3>
        <p>${node.summary}</p>
      </div>
    </div>
    <div class="tag-row">
      <span class="tag">${node.nodeType}</span>
      <span class="tag">${node.layer}</span>
      <span class="tag">${node.kind}</span>
      <span class="tag">${node.mode}</span>
      <span class="tag">${node.topology}</span>
      ${node.contracts.map((contract) => `<span class="tag">${contract}</span>`).join("")}
    </div>
    <section class="detail-section">
      <h4>Schema classification</h4>
      <div class="meta-grid">
        <div><strong>Node type</strong><span>${node.nodeType}</span></div>
        <div><strong>Reasoning mode</strong><span>${node.mode}</span></div>
        <div><strong>Topology</strong><span>${node.topology}</span></div>
      </div>
    </section>
    ${subgraph}
    <section class="detail-section">
      <h4>I/O contract</h4>
      <div class="io-grid">
        <div><strong>Inputs</strong><span>${node.inputs.join(", ")}</span></div>
        <div><strong>Outputs</strong><span>${node.outputs.join(", ")}</span></div>
      </div>
    </section>
    <section class="detail-section">
      <h4>Source mapping</h4>
      <ul>${node.sources.map((item) => `<li><code>${item}</code></li>`).join("")}</ul>
    </section>
    <section class="detail-section">
      <h4>Risks</h4>
      <ul>${node.risks.map((risk) => `<li>${risk}</li>`).join("")}</ul>
    </section>
    <section class="detail-section">
      <h4>Metrics</h4>
      <ul>${node.metrics.map((metric) => `<li>${metric}</li>`).join("")}</ul>
    </section>
  `;
}

function updateStatus(focusedNodes) {
  const view = views[state.view];
  const visibleEdges = edges.filter(([from, to, type]) => {
    const fromNode = nodes.find((node) => node.id === from);
    const toNode = nodes.find((node) => node.id === to);
    return view.edgeTypes.includes(type) && (isFocused(fromNode) || isFocused(toNode));
  });
  const warnings = focusedNodes.reduce((count, node) => count + (node.tags.includes("risk") ? 1 : 0), 0);

  document.querySelector("#focusedCount").textContent = focusedNodes.length;
  document.querySelector("#visibleEdgeCount").textContent = visibleEdges.length;
  document.querySelector("#warningCount").textContent = warnings;
  document.querySelector("#nodeMetric").textContent = nodes.length;
  document.querySelector("#edgeMetric").textContent = edges.length;
  const linkedExample = importExamples.find((example) => example.id === state.linkedExampleId);
  document.querySelector("#qualityMetric").textContent = linkedExample
    ? getExampleGraphFocus(linkedExample).quality
    : defaultGraphFocus.quality;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function groupLabel(group) {
  const labels = {
    direct: "Direct import target",
    fixture: "Fixture / reference-only",
    deterministic: "Deterministic fixture",
    excluded: "Excluded candidate",
  };
  return labels[group] || "Example";
}

function getExampleGraphFocus(example) {
  return exampleGraphFocus[example.id] || defaultGraphFocus;
}

function visibleExamples() {
  if (state.exampleGroup === "all") return importExamples;
  return importExamples.filter((example) => example.group === state.exampleGroup);
}

function renderExampleList() {
  const examples = visibleExamples();
  if (!examples.some((example) => example.id === state.selectedExampleId)) {
    state.selectedExampleId = examples[0]?.id || importExamples[0].id;
  }

  exampleTabs.forEach((tab) => {
    const active = tab.dataset.exampleGroup === state.exampleGroup;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-pressed", String(active));
  });

  exampleList.innerHTML = examples
    .map(
      (example) => `
        <button
          class="example-button ${example.resultTone}${example.id === state.selectedExampleId ? " is-active" : ""}"
          type="button"
          data-example-id="${escapeHtml(example.id)}"
          aria-pressed="${example.id === state.selectedExampleId}"
        >
          <span>${escapeHtml(example.short)}</span>
          <small>${escapeHtml(groupLabel(example.group))}</small>
        </button>
      `,
    )
    .join("");

  exampleList.querySelectorAll("[data-example-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedExampleId = button.dataset.exampleId;
      renderExampleSimulator({ syncGraph: true });
    });
  });
}

function renderExampleDetail() {
  const example = importExamples.find((item) => item.id === state.selectedExampleId) || importExamples[0];
  const focus = getExampleGraphFocus(example);
  const focusNode = nodes.find((node) => node.id === focus.selectedNodeId) || nodes[0];
  const focusView = views[focus.view] || views.overview;
  const profileRows = example.profileRows
    .map(
      ([profile, status]) => `
        <div>
          <strong>${escapeHtml(profile)}</strong>
          <span>${escapeHtml(status)}</span>
        </div>
      `,
    )
    .join("");
  const sourceFiles = (example.sourceFiles || [])
    .map(
      ([label, href]) => `
        <li>
          <a href="${escapeHtml(href)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>
        </li>
      `,
    )
    .join("");

  exampleDetail.innerHTML = `
    <div class="example-detail-head">
      <div>
        <p>${escapeHtml(groupLabel(example.group))}</p>
        <h3>${escapeHtml(example.label)}</h3>
      </div>
      <span class="example-status ${escapeHtml(example.resultTone)}">${escapeHtml(example.result)}</span>
    </div>

    <p class="example-summary">${escapeHtml(example.summary)}</p>

    <div class="example-meta-grid">
      <div><strong>Import mode</strong><span>${escapeHtml(example.mode)}</span></div>
      <div><strong>Gate</strong><span>${escapeHtml(example.gate)}</span></div>
      <div><strong>Scan root</strong><span>${escapeHtml(example.scanRoot)}</span></div>
      <div><strong>Success-rate rule</strong><span>${escapeHtml(example.directRate)}</span></div>
    </div>

    <section class="example-graph-link" aria-label="Linked main graph focus">
      <div>
        <h4>Linked main graph</h4>
        <p>${escapeHtml(focus.note)}</p>
      </div>
      <dl>
        <div><dt>View</dt><dd>${escapeHtml(focusView.label)}</dd></div>
        <div><dt>Selected node</dt><dd>${escapeHtml(focusNode.label)}</dd></div>
        <div><dt>Quality</dt><dd>${escapeHtml(focus.quality)}</dd></div>
      </dl>
    </section>

    ${
      sourceFiles
        ? `
          <section class="example-source-evidence">
            <h4>Source files checked</h4>
            <ul>${sourceFiles}</ul>
          </section>
        `
        : ""
    }

    <section class="example-flow" aria-label="Projected graph shape">
      <h4>Projected state shape</h4>
      <ol>
        ${example.graphShape.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
      </ol>
    </section>

    <div class="example-columns">
      <section>
        <h4>Profile rows</h4>
        <div class="profile-rows">${profileRows}</div>
      </section>
      <section>
        <h4>Artifacts expected</h4>
        <ul>${example.artifacts.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </section>
      <section>
        <h4>Warnings / gaps</h4>
        <ul>${example.warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </section>
    </div>
  `;
}

function applyExampleFocusToGraph() {
  const example = importExamples.find((item) => item.id === state.selectedExampleId);
  if (!example) return;
  const focus = getExampleGraphFocus(example);
  state.linkedExampleId = example.id;
  state.view = focus.view;
  state.query = "";
  searchInput.value = "";
  state.selectedNodeId = focus.selectedNodeId;
  applyView();
}

function renderExampleSimulator({ syncGraph = false } = {}) {
  renderExampleList();
  renderExampleDetail();
  if (syncGraph) applyExampleFocusToGraph();
}

filterButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.linkedExampleId = null;
    state.view = button.dataset.view;
    applyView();
  });
});

exampleTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    state.exampleGroup = tab.dataset.exampleGroup;
    renderExampleSimulator({ syncGraph: true });
  });
});

document.querySelector("[data-open-examples]").addEventListener("click", () => {
  document.querySelector("#plan14Examples").scrollIntoView({ behavior: "smooth", block: "start" });
});

searchInput.addEventListener("input", (event) => {
  state.query = event.target.value.trim().toLowerCase();
  applyView();
});

document.querySelector("[data-reset-view]").addEventListener("click", () => {
  state.view = "overview";
  state.query = "";
  searchInput.value = "";
  state.selectedNodeId = "hybrid_retriever";
  document.querySelector(".filter-stack").scrollTo({ top: 0, behavior: "smooth" });
  applyView();
});

document.querySelector("[data-fit-view]").addEventListener("click", () => {
  document.querySelector(".canvas-scroll").scrollTo({ left: 0, behavior: "smooth" });
});

document.querySelector("[data-export-view]").addEventListener("click", () => {
  const detail = views[state.view].label;
  window.alert(`Prototype export prepared for: ${detail}`);
});

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", () => {
    const action = button.dataset.action;
    const labels = {
      import: "Import System 需要後端接 code/config/workflow/trace/doc adapters。",
      map: "Auto-map 需要後端把 raw components 正規化成 known / extension / unmapped nodes。",
      validate: "Validate 需要後端檢查 schema、source evidence、policy 與 unmapped components。",
      trace: "Run Trace 需要後端提供 runtime spans，讓 UI 能播放真實路徑。",
    };
    window.alert(labels[action]);
  });
});

window.addEventListener("resize", () => requestAnimationFrame(drawEdges));

renderGraph();
renderExampleSimulator({ syncGraph: true });
applyView();
if (document.fonts) {
  document.fonts.ready.then(() => requestAnimationFrame(drawEdges));
}
