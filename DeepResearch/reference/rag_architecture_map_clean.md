# RAG 系統設計地圖 — 多層架構解析與 2026 最新進展

> 來源：由上傳的 HTML 檔案抽取並整理成乾淨 Markdown。已移除 CSS、JavaScript 與互動式 UI，只保留可閱讀的研究內容、分類、表格與參考連結。

## 目錄

- [1. 核心結論](#1)
- [2. RAG 四層模型總覽](#2-rag)
- [3. 端到端共同流程圖](#3)
- [3.1 十個 capability planes](#31-十個-capability-planes)
- [4. 分類地圖與技術卡片](#4)
- [5. 2026 年 RAG 四大進化方向](#5-2026--rag)
- [6. 共同架構：Naive RAG、Modular RAG 與 2026 新架構的關係](#6-naive-ragmodular-rag--2026)
- [7. 技術矩陣總覽表](#7)
- [8. 參考來源](#8)

---

## 1. 核心結論

RAG 不適合只畫成單一樹狀圖，因為不同 RAG 名稱代表的層級並不相同。有些是完整架構，有些只是檢索策略，有些是 chunk 前處理技巧，有些則是研究工具鏈。

較精準的整理方式是把 RAG 視為一組可組裝的多層設計地圖：

```text
RAG 系統
├── 0. Core Primitive：RAG 最小單元
├── 1. Architecture Maturity：架構成熟度
├── 2. Cross-cutting Components：橫向可疊加元件
├── 3. Query Understanding：查詢理解與分解
├── 4. Control & Reasoning Layer：控制與推理層
├── 5. Knowledge Structure：知識結構層
├── 6. Evidence Reliability：證據品質與衝突處理
├── 7. Multimodal / Semi-structured：多模態與半結構化資料
├── 8. Memory-augmented RAG：長期記憶型 RAG
└── 9. Collaborative / Federated RAG：協作式 / 聯邦式 RAG
```

最重要的判斷：

- **Naive RAG** 是最小可執行單元，不是現代 RAG 的完整共同架構。
- **Modular RAG** 比較適合作為現代 RAG 系統的共同骨架。
- **Agentic / Graph / Memory RAG** 可以理解成在 Modular RAG 之上加上控制層、結構層或長期記憶層。
- **Hybrid Retrieval、Contextual Retrieval、Reranking、Query Rewriting** 更適合視為橫向可疊加元件，而不是獨立主架構。

---

## 2. RAG 四層模型總覽

HTML 原始內容將現代 RAG 重構為「四層模型」：

```text
Layer 1：Core Primitive
  - Naive / 2-Step RAG

Layer 2：Common Framework
  - Advanced RAG
  - Modular RAG

Layer 3：Cross-cutting Components
  - Hybrid Retrieval
  - Contextual Retrieval
  - Reranking
  - Query Rewriting
  - Multi-query Retrieval
  - RAGLAB

Layer 4：Higher-level Variants
  - Query Understanding
  - Control & Reasoning
  - Knowledge Structure
  - Evidence Reliability
  - Multimodal / Semi-structured
  - Memory-augmented RAG
  - Collaborative / Federated RAG
```

---

## 3. 端到端共同流程圖

```text
User Query
   ↓
Query Understanding
   ├── Typed-RAG
   ├── MRAG
   └── Query Rewriting / Multi-query Retrieval
   ↓
Control Layer
   ├── Fixed Pipeline
   ├── Corrective Control
   └── Agentic / Reasoning Control
   ↓
Retrieval Layer
   ├── Dense Retrieval
   ├── Hybrid Retrieval
   ├── Graph Retrieval
   ├── Multimodal Retrieval
   └── Memory Retrieval
   ↓
Evidence Layer
   ├── Reranking
   ├── Conflict Resolution
   └── Evidence Validation
   ↓
Context Construction & Generation
   ↓
Memory Update / Feedback Loop
```

### 3.1 十個 capability planes

為了讓 repo mapping 能明確區分離線資料處理、線上檢索、持久狀態與營運治理，Viewer 採用以下十個 plane：

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

`Ingestion & Indexing` 負責載入、切分、embedding、metadata 與索引更新；`Retrieval` 只負責查詢時取回候選。`Memory & State` 負責 session、checkpoint 與長短期記憶；`Governance & Observability` 負責 policy、approval、trace、eval、成本與 latency 證據。這些 plane 是 capability mapping schema，不代表所有系統都必須照相同順序執行。

---

## 4. 分類地圖與技術卡片

### 0. RAG 最小單元（Core Primitive）

RAG 的歷史起點與最底層的執行單元，一切複雜架構的基礎。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| Naive / 2-Step RAG | 底層單元 | 全流程 (單次) | 基礎 | 最單純的兩步式流程：先向量檢索，再把結果丟給 LLM 生成答案，中間沒有查詢改寫、重排序或驗證。 | index → retrieve → generate |

### 1. 架構成熟度演進（Architecture Maturity）

代表 RAG 系統從固定管線走向可組裝樂高積木的主幹演進過程。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| Advanced RAG | 主架構 | 全流程 (加強版) | 可加載橫向元件 | 在 Naive 前後加入查詢改寫、混合檢索、重排序等優化，但依然維持相對固定的線性管線。 | Fixed Pipeline, Optimization |
| Modular RAG | 共同骨架 | 系統框架 | 高度可組合 | 把檢索、路由、生成等拆解成獨立可替換的模組，支援條件分支與迴圈，是現代複雜 RAG 的底層骨架。 | Reconfigurable, LEGO-like |

### 2. 橫向可疊加元件（Cross-cutting Components）

這些「不是」獨立的架構，而是可以隨插即用到各種 RAG 系統（包含 Agentic 或 Graph）裡的優化技巧。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| Hybrid Retrieval | 橫向技巧 | Retrieval | 是 (幾乎全部) | 結合關鍵字 (BM25) 與密集向量檢索，補足純語意搜尋對專有名詞不敏感的弱點。 | Sparse + Dense, RRF |
| Contextual Retrieval | 橫向技巧 | Indexing / Chunking | 是 (文件型) | 切塊前讓 LLM 幫每個 Chunk 加上全局上下文摘要，解決片段脫離原文脈絡的問題 (Anthropic 提出)。 | Context Enrichment |
| Reranking | 橫向技巧 | Evidence (Post-retrieval) | 是 | 檢索出候選名單後，使用另一個交叉編碼器模型重新精準排序，過濾無關雜訊。 | Cross-encoder |
| Query Rewriting | 橫向技巧 | Query Understanding | 是 | 檢索前把口語、指代不清的問題改寫成適合搜尋引擎的關鍵字組合。 | Query Transformation |
| Multi-query Retrieval | 橫向技巧 | Query Understanding | 是 | 一個問題產生多個不同角度的查詢字串，分別檢索後再去重合併。 | Query Expansion |
| RAGLAB | 工具鏈 | Evaluation / Research | 框架外 | 這不是 RAG 類型，而是一套評估與組合不同模組效能的實驗框架工具。 | Research Tool |

### 3. 查詢理解與分解（Query Understanding）

專注於處理使用者複雜提問的架構變體，先拆解再檢索。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| Typed-RAG | 架構變體 | Query Routing | 可與 Graph 疊加 | 先辨識問題類型（比較、列舉、原因），再套用不同的拆解與檢索策略模板。 | Intent Classification |
| Multi-Head RAG (MRAG) | 模型級技巧 | Embedding / Retrieval | 視模型支援 | 利用 Transformer 不同的注意力頭提取多面向語意，產生多組 Embedding。 | Multi-aspect Embedding |

### 4. 控制與推理層（Control & Reasoning Layer）

打破單次固定流程，由 Agent 負責動態決策、迴圈反思與工具調用。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| Self-RAG | 控制層 | Generation / Reflection | 可 | 在生成過程中產生特殊反思 Token，自我評估是否需要檢索、證據是否支持。 | Reflection Tokens |
| Corrective RAG (CRAG) | 控制層 | Evidence Evaluation | 可 | 評估檢索品質，若不佳則觸發網路搜尋或重寫查詢，具備糾錯迴圈。 | Fallback Search, Evaluation |
| ReaRAG | 控制層 | Reasoning + Retrieval | 可與 Graph 疊加 | 推理鏈與檢索交錯，每個推理節點決定「繼續推」或「補檢索資料」。 | Interleaved Process |
| MCTS-RAG | 控制層 | Search Strategy | 否 (高運算) | 把檢索路徑當成樹狀搜尋，透過蒙地卡羅模擬選出最佳回答路徑。 | Tree Search |
| InstructRAG | 模型訓練 | Generation | 可 | 訓練模型顯式解釋引用邏輯，藉此抗噪並提高可解釋性。 | Explicit Citation |
| Agentic RAG | 控制層架構 | 全流程決策 | 可疊加任何來源 | 泛指由 Agent 自主選擇檢索工具、判斷次數與策略的系統範式。 | ReAct, Tool Use |
| A-RAG | 控制層架構 | Retrieval Interface | 可 | 2026 最新提出，為 Agent 打造階層式檢索介面（關鍵字、語意、閱讀區塊），讓模型完全自主操作檢索。 | Autonomous Retrieval |

### 5. 知識結構層（Knowledge Structure）

放棄傳統扁平文字區塊，改用圖譜、樹狀等結構來組織知識，擅長整體摘要與多跳推理。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| GraphRAG | 主架構 | Index / Retrieval | 可與 Agentic 疊加 | 將文件轉化為實體與關係的知識圖譜，透過社群摘要與路徑推理回答複雜全域問題。 | Knowledge Graph, Global QA |
| Agentic GraphRAG | 主架構 | Control + Graph | 整合方案 | 2026 趨勢，讓 Analytical Agent 能根據意圖主動選擇圖查詢工具、執行反思迴圈與綜合答案。 | Graph + Agent |
| LightRAG | 主架構 | Index / Retrieval | 可 | 雙層圖檢索架構，平衡建圖成本，兼顧低層實體與高層主題摘要。 | Efficient Graph |
| Tree / Hierarchical RAG | 主架構 | Index / Retrieval | 可 | 遞迴聚類並摘要文件片段，形成樹狀索引，可依問題抽象層級檢索。 | Recursive Summary |
| HeteRAG | 主架構 | Index | 可 | 針對多源異質資料庫建立統一的異質圖索引，打通不同格式壁壘。 | Heterogeneous Data |

### 6. 證據品質與衝突處理（Evidence Reliability）

專門解決「檢索來的資料互相矛盾或可信度低」的問題。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| MADAM-RAG | 架構變體 | Evidence Resolution | 可 | 多 Agent 辯論機制，指派不同 Agent 代表不同資料源進行辯論與仲裁。 | Multi-agent Debate |
| Conflict-aware RAG | 架構變體 | Evidence Resolution | 可 | 主動偵測檢索片段間的矛盾，依時效或來源權重判斷，或直接呈現多方觀點。 | Fact Checking |

### 7. 多模態與半結構化資料（Multimodal / Semi-structured）

突破純文字限制，將視覺、圖表與公式納入檢索範圍。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| Multimodal RAG | 架構變體 | Embedding / Index | 可 | 使用多模態 Embedding 處理圖片與表格，實現跨模態相似度檢索。 | Vision Models |
| RAG-Anything | 主架構 | Knowledge Representation | 可與 Graph 疊加 | 2026 趨勢，用雙重圖結構同時捕捉跨模態關係與文本語意，實現無縫的混合多模態檢索。 | Cross-modal Graph |

### 8. 長期記憶型 RAG（Memory-augmented RAG）

2026 年新興領域，把 Agent 的「記憶」視為可迭代操作的專屬 RAG 系統。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| Long-term Memory RAG | 架構變體 | Memory | 與 Agentic 強綁定 | 賦予 Agent 寫入與讀取歷史互動的能力，突破對話 Context Window 限制。 | Persistent State |
| Infini Memory | 主架構 | Memory Architecture | 與 Agentic 強綁定 | 2026 趨勢，將記憶組織成結構化的「主題文件」，Agent 透過迭代呼叫工具來尋找與更新記憶，而非單次檢索。 | Topic Documents |

### 9. 協作式 RAG（Collaborative / Federated RAG）

解決跨組織資料隱私問題的架構。

| 技術名稱 | 定位 | 作用層級 | 是否可疊加 | 說明 | Tags |
|---|---|---|---|---|---|
| CoRAG | 架構變體 | Distributed Retrieval | 否 (獨立生態) | 多組織在不交換原始文件的前提下，透過交換檢索分數或特徵協作生成答案。 | Federated Learning, Privacy |

---

## 5. 2026 年 RAG 四大進化方向

### 5.1 趨勢 1：Agentic Retrieval 正式化 (A-RAG)

A-RAG 把檢索從固定 pipeline 變成 agent 可操作的工具介面。模型不再只是被動接收 top-k chunks，而是可以自主選擇 keyword search、semantic search 或 chunk read，並透過多輪工具調用逐步取得證據。

**來源 / 作用層級：** Du et al., 2026 · 作用層級: Control / Retrieval Decision

### 5.2 趨勢 2：GraphRAG + Agentic 合流

Agentic GraphRAG 代表 GraphRAG 從「靜態圖查詢」往「圖工具 + agent 控制」演進。重點不只是建構知識圖譜，而是讓 Analytical Agent 能根據任務意圖，動態選擇查圖、反思、補查與合成答案。

**來源 / 作用層級：** Capozzi & Helbing, 2026 · 作用層級: Control / Graph Access

### 5.3 趨勢 3：Long-term Memory RAG 崛起

如 Infini Memory 把 Agent Memory 組織成 topic-structured documents。在推論時，LLM 透過 iterative tool calls 迭代讀取記憶，而不是像以前一樣只做單次檢索，將「記憶」正式變成了另一種 RAG 問題。

**來源 / 作用層級：** Ji et al., 2026 · 作用層級: Persistent Memory Architecture

### 5.4 趨勢 4：Multimodal Knowledge RAG

如 RAG-Anything 把多模態內容重新看成 interconnected knowledge entities。它提出 dual-graph construction，同時捕捉 cross-modal 關係和文本語意，把圖片、表格、文字放進同一個圖譜邏輯裡檢索。

**來源 / 作用層級：** HKUDS, 2026 · 作用層級: Cross-modal Representation

---

## 6. 共同架構：Naive RAG、Modular RAG 與 2026 新架構的關係

### 6.1 共同架構不能直接等於 Naive RAG

Naive RAG 只能代表最底層的 primitive，也就是最小執行單元：

```text
retrieve → augment → generate
```

但它無法代表 2026 年新架構的控制邏輯。新架構的核心流程更接近：

```text
plan → choose tool → retrieve → inspect evidence → reflect → generate → update memory
```

### 6.2 更準確的層次關係

```text
Agentic / Graph / Memory RAG（2026 新架構）
└── 控制與結構層：由 Agent 決定何時檢索、讀取圖譜或操作長期記憶
    ↓
Modular RAG（共同骨架）
└── 可重新組裝、可分支、可循環的模組框架
    ↓
Naive RAG（最小單元）
└── 單次執行的 Index → Retrieve → Generate
```

### 6.3 最終判斷

更精確的說法是：**Modular RAG 是現代系統的共同骨架**；2026 年的 Agentic RAG、GraphRAG、Memory RAG，可以理解成在 Modular RAG 之上加上更強的控制層、結構層或記憶層。

---

## 7. 技術矩陣總覽表

| 技術名稱 | 分類歸屬 | 定位 | 作用層級 | 可疊加性 |
|---|---|---|---|---|
| Naive / 2-Step RAG | RAG 最小單元 | 底層單元 | 全流程 (單次) | 基礎 |
| Advanced RAG | 架構成熟度演進 | 主架構 | 全流程 (加強版) | 可加載橫向元件 |
| Modular RAG | 架構成熟度演進 | 共同骨架 | 系統框架 | 高度可組合 |
| Hybrid Retrieval | 橫向可疊加元件 | 橫向技巧 | Retrieval | 是 (幾乎全部) |
| Contextual Retrieval | 橫向可疊加元件 | 橫向技巧 | Indexing / Chunking | 是 (文件型) |
| Reranking | 橫向可疊加元件 | 橫向技巧 | Evidence (Post-retrieval) | 是 |
| Query Rewriting | 橫向可疊加元件 | 橫向技巧 | Query Understanding | 是 |
| Multi-query Retrieval | 橫向可疊加元件 | 橫向技巧 | Query Understanding | 是 |
| RAGLAB | 橫向可疊加元件 | 工具鏈 | Evaluation / Research | 框架外 |
| Typed-RAG | 查詢理解與分解 | 架構變體 | Query Routing | 可與 Graph 疊加 |
| Multi-Head RAG (MRAG) | 查詢理解與分解 | 模型級技巧 | Embedding / Retrieval | 視模型支援 |
| Self-RAG | 控制與推理層 | 控制層 | Generation / Reflection | 可 |
| Corrective RAG (CRAG) | 控制與推理層 | 控制層 | Evidence Evaluation | 可 |
| ReaRAG | 控制與推理層 | 控制層 | Reasoning + Retrieval | 可與 Graph 疊加 |
| MCTS-RAG | 控制與推理層 | 控制層 | Search Strategy | 否 (高運算) |
| InstructRAG | 控制與推理層 | 模型訓練 | Generation | 可 |
| Agentic RAG | 控制與推理層 | 控制層架構 | 全流程決策 | 可疊加任何來源 |
| A-RAG | 控制與推理層 | 控制層架構 | Retrieval Interface | 可 |
| GraphRAG | 知識結構層 | 主架構 | Index / Retrieval | 可與 Agentic 疊加 |
| Agentic GraphRAG | 知識結構層 | 主架構 | Control + Graph | 整合方案 |
| LightRAG | 知識結構層 | 主架構 | Index / Retrieval | 可 |
| Tree / Hierarchical RAG | 知識結構層 | 主架構 | Index / Retrieval | 可 |
| HeteRAG | 知識結構層 | 主架構 | Index | 可 |
| MADAM-RAG | 證據品質與衝突處理 | 架構變體 | Evidence Resolution | 可 |
| Conflict-aware RAG | 證據品質與衝突處理 | 架構變體 | Evidence Resolution | 可 |
| Multimodal RAG | 多模態與半結構化資料 | 架構變體 | Embedding / Index | 可 |
| RAG-Anything | 多模態與半結構化資料 | 主架構 | Knowledge Representation | 可與 Graph 疊加 |
| Long-term Memory RAG | 長期記憶型 RAG | 架構變體 | Memory | 與 Agentic 強綁定 |
| Infini Memory | 長期記憶型 RAG | 主架構 | Memory Architecture | 與 Agentic 強綁定 |
| CoRAG | 協作式 RAG | 架構變體 | Distributed Retrieval | 否 (獨立生態) |

---

## 8. 參考來源

- [[基礎演進] Retrieval-Augmented Generation for Large Language Models: A Survey (Gao et al.) — 確認 Naive/Advanced/Modular 演進主幹](https://arxiv.org/abs/2312.10997)
- [[共同骨架] Modular RAG: Transforming RAG Systems into LEGO-like Reconfigurable Frameworks (Gao et al.)](https://arxiv.org/abs/2407.21059)
- [[Agentic] A-RAG: Scaling Agentic Retrieval-Augmented Generation via Hierarchical Retrieval Interfaces (Du et al., 2026)](https://arxiv.org/abs/2602.03442)
- [[Graph] Agentic GraphRAG: Navigating Unstructured Financial Data with Collaborative AI (Capozzi & Helbing, 2026)](https://arxiv.org/abs/2605.18770)
- [[Memory] Infini Memory: Maintainable Topic Documents for Long-Term LLM Agent Memory (Ji et al., 2026)](https://arxiv.org/abs/2606.10677)
- [[Multimodal] RAG-Anything: Multimodal Knowledge Representation and Retrieval (HKUDS, 2026)](https://arxiv.org/abs/2603.00000)
- [[元件] Contextual Retrieval (Anthropic) — 改善 chunk 脈絡流失](https://www.anthropic.com/news/contextual-retrieval)

---

## 附註

- 本 Markdown 是從 HTML 中抽取內容後重新排版，未保留原本互動式導覽、卡片動畫、CSS 樣式與 JavaScript 渲染邏輯。
- 若要發佈成 GitHub README，建議保留本文的章節結構，並將「技術矩陣總覽表」放在前半部，方便快速查找。
