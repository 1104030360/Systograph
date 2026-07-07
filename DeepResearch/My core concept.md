你的核心想法，用白話講就是這樣：

你看到很多 AI agent 或 RAG 專案，表面長得不一樣——有的叫 PrivateGPT，有的有 Graph，有的會叫工具，有的只是單純問答——但你想知道的是：它們底層到底在做什麼事？ 是不是真的有檢索？是不是真的有 agent 在決策？有沒有記憶、有沒有治理、有沒有風險控制？這些問題如果每個 repo 各看各的，就沒辦法比、也沒辦法驗。

所以你選 Modular RAG 當共同地圖，不是說「所有系統都長得像 Modular RAG」，而是把它當一張固定的 10-plane 能力地圖：

```text
AI Agent / RAG System (Normalized)
├── 1. Input & Intent Plane
│   ├── User Input
│   ├── Session Context
│   └── Query Classifier
│
├── 2. Control Plane
│   ├── Planner
│   ├── Router
│   ├── Agent Loop
│   ├── Orchestrator
│   ├── Stop Policy
│   └── Human Approval Gate
│
├── 3. Ingestion & Indexing Plane
│   ├── Document Loader
│   ├── Parser
│   ├── Chunker
│   ├── Metadata Extractor
│   ├── Embedder
│   └── Index Builder
│
├── 4. Retrieval Plane
│   ├── Dense Retriever
│   ├── Sparse Retriever
│   ├── Hybrid Retriever
│   ├── Graph Retriever
│   ├── Memory Retriever
│   └── Web Retriever
│
├── 5. Extension Subsystems Plane
│   ├── GraphRAG Subsystem
│   ├── RAG-Anything / Multimodal Subsystem
│   ├── Infini Memory / Long-term Memory Subsystem
│   └── CoRAG / Federated Subsystem
│
├── 6. Evidence Plane
│   ├── Reranker
│   ├── Conflict Checker
│   ├── Citation Mapper
│   └── Evidence Pack
│
├── 7. Generation Plane
│   ├── Context Composer
│   ├── Prompt Builder
│   ├── LLM Answerer
│   ├── Tool-Using Generator
│   └── Output Guardrail
│
├── 8. Memory & State Plane
│   ├── Session State
│   ├── Working Memory
│   ├── Long-term Memory
│   ├── Memory Reader
│   └── Memory Writer
│
├── 9. Governance & Observability Plane
│   ├── Input Guardrail
│   ├── Permission Policy
│   ├── Human Approval
│   ├── Trace Store
│   ├── Eval Harness
│   ├── Cost Monitor
│   └── Latency Monitor
│
└── 10. Deployment Topology Plane
    ├── Client App
    ├── API Server
    ├── Agent Runtime
    ├── Worker / Queue
    ├── Tool Network
    └── Federated Clients
```

這個拆法會把離線的資料載入、切分與建索引，和線上的候選檢索分開；也會把記憶與狀態管理，和治理、trace、eval、成本及 latency 觀測分開。不管輸入哪個 repo，都試著把它的元件對位到這張地圖上——這個專案的 retriever 落在哪、planner 落在哪、Graph 或 Memory 這種特殊能力又落在哪。對得上的就標準化呈現；對不上、看不準的，就老實標成「未知」，不硬湊。

同一張地圖還可以換角度看：有人關心資料怎麼流，有人關心 agent 怎麼控制，有人關心風險。底圖不變，只是 highlight 不同部分。

最後你要的不是替某個 repo 寫文件，而是建立一種通用方式：把任意 AI agent system 都放到同一套理解框架裡，讓人一眼看出它「真的有什麼、可能沒有什麼、哪裡還不確定」，方便比較、檢查、驗證。
