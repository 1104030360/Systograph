# GitHub RAG Repo Research Report

## 1. 任務摘要

本報告依據本機規則檔：

- `docs/work/Timmy/schedule/explain/rag-repo-reference-criteria.md`
- `.cursor/rules/explain_visualize.mdc`

搜尋並整理 GitHub 上可作為 **Systograph / Systograph Task 4 fixtures 參考來源** 的 RAG repositories。

本報告的重點不是找「最大」或「star 最高」的 repo，而是找：

```text
RAG 訊號清楚
↓
授權與安全風險可控
↓
適合抽出 deterministic scanner signals
↓
可轉寫成本專案 tests/fixtures/rag_projects/ 的最小 fixture
```

資料查詢時間：2026-05-31；**private-gpt 同型補充**：2026-08-15  
主要資料來源：GitHub repository metadata、GitHub 搜尋結果、repo 官方連結。  
2026-08-15 補充重點：多找「經典文件 Q&A 應用」（loader → chunk → embed → vector store → retriever → LLM + SDK），對齊 Systograph 掃描甜蜜點（private-gpt 類），並在 §9 依掃描器能力分類。

---

## 2. 篩選條件整理

根據本機規則檔，實際使用的篩選條件如下。

### 2.1 核心條件

| 條件 | 說明 |
|---|---|
| RAG 流程清楚 | 最好可看出 loader、chunking、embedding、vector store、retriever、prompt、LLM |
| 結構不要太大 | 優先小型 sample 或架構清楚的 reference implementation |
| dependency 明確 | 有 `requirements.txt`、`pyproject.toml`、`package.json` 或明確框架 topics |
| config / docker / env 訊號明確 | 適合後續 filesystem、config、docker provider 測試 |
| 不含真 secret | 不適合使用有真 API key、token、password 的 repo |
| 不需要真的跑起來 | Task 4 需要 scanner fixture，不是 E2E demo |
| 授權清楚 | 優先 MIT、Apache-2.0、BSD；未確認 license 需標示 |
| 可轉寫成 minimal fixture | 不整包複製 repo，只參考 pattern 與結構 |

### 2.2 可視化說明規則

`.cursor/rules/explain_visualize.mdc` 要求：

- 使用 WHAT / WHY / HOW 的思路。
- 視覺化優先，不以程式碼解釋為主。
- 使用 ASCII 架構圖、流程圖、表格。
- 每個圖表前後都要有文字說明。
- 從高階概念到具體資料流。

本報告每個 repo 都包含至少一個 ASCII 架構或流程圖。

---

## 3. 搜尋方法

### 3.1 搜尋方向

使用 GitHub 搜尋下列方向：

- `RAG language:Python stars:>100`
- `GraphRAG RAG stars:>50`
- `local RAG offline LLM stars:>50`
- `healthcare RAG language:Python`
- `medical retrieval augmented generation language:Python`
- `production ready RAG template`
- `multimodal RAG framework`
- 2026-08-15 補充：`localGPT`、`kotaemon`、`Langchain-Chatchat`、`khoj RAG`、`docker genai-stack`、`azure-search-openai-demo`（經典文件 Q&A / SDK 應用，排除框架本體與 GraphRAG）

### 3.2 判斷標準

初篩時不只看 star 數，還看：

- 是否與 RAG 直接相關。
- 是否能代表某類 RAG 架構。
- 是否有官方 repo 或清楚 owner。
- 是否活躍更新。
- 是否可抽出 scanner fixture signal。
- 是否有授權資訊。
- 是否適合本專案 Task 4 / 後續 Task 7-16 參考。

---

## 4. Repo 分類總覽表

| 分類 | Repo | GitHub 連結 | 主要用途 | 適合度 | 備註 |
|---|---|---|---|---|---|
| RAG Framework / 基礎框架 | langchain-ai/langchain | https://github.com/langchain-ai/langchain | LLM / agent / RAG app framework | 中 | 太大，不適合整包 fixture，但 patterns 重要 |
| RAG Framework / 基礎框架 | run-llama/llama_index | https://github.com/run-llama/llama_index | document agent / data framework | 中 | 很適合參考 loader / index / retriever 概念 |
| RAG Framework / 基礎框架 | deepset-ai/haystack | https://github.com/deepset-ai/haystack | production RAG pipeline / orchestration | 中 | pipeline 概念清楚，但 repo 偏大 |
| Agentic RAG / 代理式 RAG | infiniflow/ragflow | https://github.com/infiniflow/ragflow | RAG engine + agent capabilities | 中 | 代表性強，適合參考架構，不適合最小 fixture |
| Agentic RAG / 代理式 RAG | ragapp/ragapp | https://github.com/ragapp/ragapp | enterprise Agentic RAG app | 高 | Docker / app 結構可能適合轉成 fixture |
| Graph RAG / 知識圖譜 RAG | microsoft/graphrag | https://github.com/microsoft/graphrag | modular GraphRAG system | 高 | GraphRAG 代表性最高 |
| Graph RAG / 知識圖譜 RAG | HKUDS/LightRAG | https://github.com/HKUDS/LightRAG | simple and fast Graph/RAG | 高 | 架構明確，適合參考 graph + vector hybrid |
| Graph RAG / 知識圖譜 RAG | neo4j/neo4j-graphrag-python | https://github.com/neo4j/neo4j-graphrag-python | Neo4j GraphRAG Python library | 中 | 適合 graph DB integration fixture |
| Multimodal RAG / 多模態 RAG | HKUDS/RAG-Anything | https://github.com/HKUDS/RAG-Anything | all-in-one multimodal RAG | 中 | 多模態代表性強，但 fixture 需簡化 |
| Multimodal / Production GraphRAG | apecloud/ApeRAG | https://github.com/apecloud/ApeRAG | production GraphRAG + multimodal indexing | 中 | 架構完整但偏大型 |
| Local RAG / 本地端 RAG | zylon-ai/private-gpt | https://github.com/zylon-ai/private-gpt | private local document Q&A | 高 | 本地 / 隱私 RAG 代表性強；掃描甜蜜點基準 |
| Local RAG / 本地端 RAG | AllAboutAI-YT/easy-local-rag | https://github.com/AllAboutAI-YT/easy-local-rag | simple local RAG with Ollama | 高 | 很適合抽成小型 fixture |
| Local RAG / 本地端 RAG | PromtEngineer/localGPT | https://github.com/PromtEngineer/localGPT | local document Q&A，資料不離機 | 高 | private-gpt 最接近的雙胞胎；Ollama / HF embedding |
| Local RAG / 本地端 RAG | Cinnamon/kotaemon | https://github.com/Cinnamon/kotaemon | RAG document chat UI | 高 | 經典文件問答 app；LlamaIndex 生態 |
| Local RAG / 本地端 RAG | chatchat-space/Langchain-Chatchat | https://github.com/chatchat-space/Langchain-Chatchat | 本地知識庫 RAG + Agent | 高 | LangChain + FAISS/Milvus + Ollama |
| Local RAG / 本地端 RAG | khoj-ai/khoj | https://github.com/khoj-ai/khoj | self-host 第二大腦 / 文件 RAG | 中 | 形狀像；AGPL-3.0；產品偏大 |
| Local RAG / 本地端 RAG | docker/genai-stack | https://github.com/docker/genai-stack | LangChain + Ollama + Neo4j 範例棧 | 高 | 小型可掃；Ollama 在規則內，Neo4j 可能規則缺口 |
| Local RAG / 本地端 RAG | Mintplex-Labs/anything-llm | https://github.com/Mintplex-Labs/anything-llm | local / self-hosted AI productivity and RAG app | 高 | 完整 local/private RAG app，適合參考 app 邊界 |
| Cloud classic RAG | Azure-Samples/azure-search-openai-demo | https://github.com/Azure-Samples/azure-search-openai-demo | Azure AI Search + Azure OpenAI RAG | 中 | 管線經典；Azure SDK 多半不在現有規則 |
| Medical / Healthcare RAG | dmis-lab/RAG2 | https://github.com/dmis-lab/RAG2 | medical QA RAG research | 中 | 醫療 RAG 研究代表，license 未確認 |
| Medical / Healthcare RAG | souvikmajumder26/Multi-Agent-Medical-Assistant | https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant | medical multi-agent assistant with RAG | 中 | 醫療 + agentic + RAG，適合延伸參考 |
| Vector Database RAG Examples | qdrant/examples | https://github.com/qdrant/examples | Qdrant examples and tutorials | 高 | 適合參考 vector DB signal |
| Vector Database RAG Examples | weaviate/Verba | https://github.com/weaviate/Verba | Weaviate-powered RAG chatbot | 高 | RAG app + vector DB 明確 |
| RAG Evaluation / Benchmark | vibrantlabsai/ragas | https://github.com/vibrantlabsai/ragas | LLM / RAG evaluation | 中 | 不適合 fixture，但適合後續 evaluation design |
| Production-ready RAG Templates | NVIDIA-AI-Blueprints/rag | https://github.com/NVIDIA-AI-Blueprints/rag | foundational RAG reference pipeline | 高 | production blueprint，適合參考交付結構 |

---

## 5. 分類詳細說明

### 5.1 RAG Framework / 基礎框架

#### 5.1.1 langchain-ai/langchain

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `langchain-ai/langchain` |
| GitHub | https://github.com/langchain-ai/langchain |
| 主要用途 | LLM / agent / RAG application framework |
| 主要語言 | Python |
| 技術或框架 | LangChain、agents、RAG、LLM app orchestration |
| 與 RAG 直接相關 | 是，repo topics 包含 `rag` |
| 更新時間 | 2026-05-30 |
| Stars | 138,051 |
| License | MIT |

**簡短說明**

LangChain 是通用 LLM application framework，可用來組合 loader、retriever、tool、agent 與 LLM。它不是單一 RAG app，但很多 RAG 專案會用它當核心拼裝層。

**架構可視化**

```text
┌──────────────┐
│ Data Sources │
└──────┬───────┘
       ↓
┌──────────────┐
│ Loaders      │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Retrievers   │ ──→ │ LLM / Agent  │
└──────┬───────┘     └──────┬───────┘
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│ Vector Store │     │ Answer/Tools │
└──────────────┘     └──────────────┘
```

**選入原因**

- 代表性極高，許多 RAG fixture 都可參考其常見 pattern。
- 不適合整包複製，但適合參考 `loader -> retriever -> LLM` 組合概念。
- 對本專案後續 code pattern provider 有參考價值。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | repo 太大，但 RAG 訊號與框架代表性強 |
| 與 RAG 直接相關 | 是 | GitHub topics 包含 `rag` |
| GitHub repo 可存取 | 是 | 官方 GitHub repo 可存取 |
| 文件足夠理解架構 | 是 | 社群與文件成熟 |
| 適合本專案參考 | 部分符合 | 適合參考 pattern，不適合直接 fixture |

#### 5.1.2 run-llama/llama_index

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `run-llama/llama_index` |
| GitHub | https://github.com/run-llama/llama_index |
| 主要用途 | document agent / OCR / data framework |
| 主要語言 | Python |
| 技術或框架 | LlamaIndex、RAG、vector database、agents |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 49,780 |
| License | MIT |

**簡短說明**

LlamaIndex 專注在把文件、資料來源、索引、retriever 與 LLM 串起來。對 Task 4 來說，它很適合參考「文件如何被 ingestion、index、query」的 fixture 訊號。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Index Build  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Retriever    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Query Engine │
└──────┬───────┘
       ↓
┌──────────────┐
│ LLM Answer   │
└──────────────┘
```

**選入原因**

- RAG 資料流非常清楚。
- 適合參考 fixture 中 `ingest.py`、`retriever.py`、`query_engine` 類型 pattern。
- 不建議整包使用，建議抽概念。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | repo 大，但 RAG 資料流明確 |
| 與 RAG 直接相關 | 是 | topics 包含 `rag`、`vector-database` |
| GitHub repo 可存取 | 是 | 官方 GitHub repo 可存取 |
| 文件足夠理解架構 | 是 | 文件與社群成熟 |
| 適合本專案參考 | 是 | 適合抽 ingestion / index / retriever patterns |

#### 5.1.3 deepset-ai/haystack

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `deepset-ai/haystack` |
| GitHub | https://github.com/deepset-ai/haystack |
| 主要用途 | production-ready LLM / RAG pipeline orchestration |
| 主要語言 | MDX metadata，實際框架以 Python 生態為主 |
| 技術或框架 | Haystack、pipelines、retrieval、routing、generation |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 25,415 |
| License | Apache-2.0 |

**簡短說明**

Haystack 強調 pipeline-based RAG。它適合參考 component 邊界：retriever、ranker、generator、router 彼此如何組合。

**架構可視化**

```text
┌──────────────┐
│ Input Query  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Router       │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Retriever    │ ──→ │ Ranker       │
└──────┬───────┘     └──────┬───────┘
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│ Document DB  │     │ Generator    │
└──────────────┘     └──────────────┘
```

**選入原因**

- pipeline 架構清楚，對後續 flow derivation 有參考價值。
- Apache-2.0 授權清楚。
- repo 偏大，適合架構參考，不適合直接 fixture。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | 架構清楚但 repo 大 |
| 與 RAG 直接相關 | 是 | description 明確提到 RAG |
| GitHub repo 可存取 | 是 | 官方 GitHub repo 可存取 |
| 文件足夠理解架構 | 是 | pipeline abstraction 明確 |
| 適合本專案參考 | 部分符合 | 適合參考 pipeline，不適合整包 fixture |

### 5.2 Agentic RAG / 代理式 RAG

#### 5.2.1 infiniflow/ragflow

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `infiniflow/ragflow` |
| GitHub | https://github.com/infiniflow/ragflow |
| 主要用途 | RAG engine + agent capabilities |
| 主要語言 | Python |
| 技術或框架 | RAGFlow、agentic retrieval、context engine |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 81,562 |
| License | Apache-2.0 |

**簡短說明**

RAGFlow 是完整 RAG engine，包含 retrieval、context layer 與 agent 能力。它比較像完整產品，不是小 fixture，但很適合看 production RAG 應該有哪些模組。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ RAG Engine   │
├──────────────┤
│ Parse/Index  │
│ Retrieve     │
│ Context      │
│ Agent        │
└──────┬───────┘
       ↓
┌──────────────┐
│ LLM Response │
└──────────────┘
```

**選入原因**

- RAG + agentic retrieval 代表性高。
- 適合本專案理解「完整 RAG system map」的元件類型。
- repo 大，不適合直接拿來當 Task 4 fixture。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | 活躍且 RAG 明確，但偏大型 |
| 與 RAG 直接相關 | 是 | description 直接說 RAG engine |
| GitHub repo 可存取 | 是 | 官方 repo 可存取 |
| 文件足夠理解架構 | 是 | metadata 與 repo 說明足夠初步理解 |
| 適合本專案參考 | 部分符合 | 適合架構參考，不適合直接 fixture |

#### 5.2.2 ragapp/ragapp

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `ragapp/ragapp` |
| GitHub | https://github.com/ragapp/ragapp |
| 主要用途 | enterprise Agentic RAG app |
| 主要語言 | TypeScript |
| 技術或框架 | LlamaIndex、Docker、agents、RAG |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-29 |
| Stars | 4,438 |
| License | Apache-2.0 |

**簡短說明**

RagApp 目標是讓企業更容易使用 Agentic RAG。它包含 app 層與 RAG backend 概念，對本專案可參考 local API / app integration 的邊界。

**架構可視化**

```text
┌──────────────┐
│ User / UI    │
└──────┬───────┘
       ↓
┌──────────────┐
│ RagApp       │
├──────────────┤
│ Agent Layer  │
│ RAG Layer    │
│ Data Layer   │
└──────┬───────┘
       ↓
┌──────────────┐
│ LLM / Index  │
└──────────────┘
```

**選入原因**

- Agentic RAG 類別明確。
- Apache-2.0 授權清楚。
- 可能適合參考 Docker、app route、RAG app structure。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | RAG app、Docker topic、架構方向清楚 |
| 與 RAG 直接相關 | 是 | description 與 topics 都指向 RAG |
| GitHub repo 可存取 | 是 | 官方 repo 可存取 |
| 文件足夠理解架構 | 部分符合 | 需進一步檢查細部目錄 |
| 適合本專案參考 | 是 | 適合參考 app + RAG integration |

### 5.3 Graph RAG / 知識圖譜 RAG

#### 5.3.1 microsoft/graphrag

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `microsoft/graphrag` |
| GitHub | https://github.com/microsoft/graphrag |
| 主要用途 | modular graph-based RAG system |
| 主要語言 | Python |
| 技術或框架 | GraphRAG、LLM、knowledge graph |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 33,330 |
| License | MIT |

**簡短說明**

Microsoft GraphRAG 是 Graph RAG 代表專案，用 graph-based indexing 與 retrieval 來改善一般向量檢索不足的全域推理與關係查詢。

**架構可視化**

```text
┌──────────────┐
│ Source Docs  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Entity/Graph │
│ Extraction   │
└──────┬───────┘
       ↓
┌──────────────┐
│ Graph Index  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Graph Query  │
└──────┬───────┘
       ↓
┌──────────────┐
│ LLM Answer   │
└──────────────┘
```

**選入原因**

- Graph RAG 類別最具代表性的 repo 之一。
- MIT 授權清楚。
- 適合本專案後續思考 `extensions` / `unmapped_components` 中 graph 元件。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | RAG/GraphRAG 明確，活躍維護 |
| 與 RAG 直接相關 | 是 | description 直接說 Retrieval-Augmented Generation |
| GitHub repo 可存取 | 是 | 官方 Microsoft repo |
| 文件足夠理解架構 | 是 | modular GraphRAG system |
| 適合本專案參考 | 是 | 適合 GraphRAG fixture / architecture 參考 |

#### 5.3.2 HKUDS/LightRAG

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `HKUDS/LightRAG` |
| GitHub | https://github.com/HKUDS/LightRAG |
| 主要用途 | simple and fast Retrieval-Augmented Generation |
| 主要語言 | Python |
| 技術或框架 | LightRAG、knowledge graph、GraphRAG |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 35,979 |
| License | MIT |

**簡短說明**

LightRAG 主打簡單、快速，並和 knowledge graph / GraphRAG 概念相關。對本專案來說，它比大型 GraphRAG 更可能適合抽出簡化 fixture。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Lightweight  │
│ Indexing     │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Vector Signal│ ←→  │ Graph Signal │
└──────┬───────┘     └──────┬───────┘
       └──────────┬─────────┘
                  ↓
          ┌──────────────┐
          │ RAG Answer   │
          └──────────────┘
```

**選入原因**

- Graph + vector hybrid signals 適合 scanner detection。
- MIT 授權清楚。
- 活躍、社群大。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | RAG 流程與 graph/vector signal 清楚 |
| 與 RAG 直接相關 | 是 | repo name、description、topics 皆相關 |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 部分符合 | 需再看細部 README 才能抽 fixture |
| 適合本專案參考 | 是 | 適合 graph/vector hybrid 參考 |

#### 5.3.3 neo4j/neo4j-graphrag-python

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `neo4j/neo4j-graphrag-python` |
| GitHub | https://github.com/neo4j/neo4j-graphrag-python |
| 主要用途 | Neo4j GraphRAG Python library |
| 主要語言 | Python |
| 技術或框架 | Neo4j、Cypher、GraphRAG、graph database |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 1,175 |
| License | Other，需進一步確認細節 |

**簡短說明**

這是 Neo4j 官方 GraphRAG Python library，適合參考 graph database 作為 RAG retrieval layer 時，scanner 可能看到哪些依賴與程式碼訊號。

**架構可視化**

```text
┌──────────────┐
│ User Query   │
└──────┬───────┘
       ↓
┌──────────────┐
│ GraphRAG API │
└──────┬───────┘
       ↓
┌──────────────┐
│ Neo4j Graph  │
│ Cypher Query │
└──────┬───────┘
       ↓
┌──────────────┐
│ Context      │
└──────┬───────┘
       ↓
┌──────────────┐
│ LLM Answer   │
└──────────────┘
```

**選入原因**

- 代表 graph database RAG integration。
- 適合 Task 4 extension fixture：graph retriever / graph store。
- License metadata 顯示 `Other`，需進一步人工確認。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | 技術訊號清楚，但 license 需確認 |
| 與 RAG 直接相關 | 是 | repo topics 包含 `rag`、`graphrag` |
| GitHub repo 可存取 | 是 | Neo4j repo 可存取 |
| 文件足夠理解架構 | 部分符合 | 初步可理解，細節需看 docs |
| 適合本專案參考 | 部分符合 | 適合 graph extension，不宜直接複製 |

### 5.4 Multimodal RAG / 多模態 RAG

#### 5.4.1 HKUDS/RAG-Anything

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `HKUDS/RAG-Anything` |
| GitHub | https://github.com/HKUDS/RAG-Anything |
| 主要用途 | all-in-one multimodal RAG framework |
| 主要語言 | Python |
| 技術或框架 | multi-modal RAG、retrieval-augmented generation |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 20,781 |
| License | MIT |

**簡短說明**

RAG-Anything 是多模態 RAG 代表專案，涵蓋文字以外的資料型態。對本專案來說，它適合思考未來 scanner 如何處理 PDF、image、table、diagram 等訊號。

**架構可視化**

```text
┌──────────────┐
│ Text / Image │
│ Table / PDF  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Multimodal   │
│ Parsing      │
└──────┬───────┘
       ↓
┌──────────────┐
│ Unified Index│
└──────┬───────┘
       ↓
┌──────────────┐
│ Retrieval    │
└──────┬───────┘
       ↓
┌──────────────┐
│ LLM / VLM    │
└──────────────┘
```

**選入原因**

- 多模態 RAG 類別代表性高。
- MIT 授權清楚。
- 不適合 Task 4 初版最小 fixture，但適合未來 multimodal extension。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | RAG 明確但可能偏大 |
| 與 RAG 直接相關 | 是 | repo description 明確 |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 部分符合 | 需進一步看 docs 才能抽 fixture |
| 適合本專案參考 | 部分符合 | 適合未來多模態 scanner，不是 Task 4 首選 |

#### 5.4.2 apecloud/ApeRAG

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `apecloud/ApeRAG` |
| GitHub | https://github.com/apecloud/ApeRAG |
| 主要用途 | production-ready GraphRAG with multimodal indexing |
| 主要語言 | Python |
| 技術或框架 | GraphRAG、multimodal indexing、AI agents、MCP、K8s |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 1,180 |
| License | Apache-2.0 |

**簡短說明**

ApeRAG 是偏 production 的 GraphRAG / multimodal indexing 系統，包含 agent、MCP 與 K8s deployment。它適合參考 production map 的 component 類型。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
│ Multimodal   │
└──────┬───────┘
       ↓
┌──────────────┐
│ Indexing     │
│ Graph + Multi│
└──────┬───────┘
       ↓
┌──────────────┐
│ Agent / MCP  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Deployment   │
│ K8s / Service│
└──────────────┘
```

**選入原因**

- production + GraphRAG + multimodal 的組合很有參考價值。
- Apache-2.0 授權清楚。
- 對 Task 4 初版而言太大，較適合延伸參考。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | 訊號豐富但系統偏大 |
| 與 RAG 直接相關 | 是 | description 直接提到 GraphRAG |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 部分符合 | 初步 metadata 可理解，細節需看 docs |
| 適合本專案參考 | 部分符合 | 適合 production architecture，不適合最小 fixture |

### 5.5 Local RAG / 本地端 RAG

#### 5.5.1 zylon-ai/private-gpt

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `zylon-ai/private-gpt` |
| GitHub | https://github.com/zylon-ai/private-gpt |
| 主要用途 | private local document Q&A |
| 主要語言 | Python |
| 技術或框架 | local/private RAG、document Q&A |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 57,219 |
| License | Apache-2.0 |

**簡短說明**

PrivateGPT 強調 100% private document interaction。它非常貼近本專案「local AI 系統掃描」與「不外洩資料」的價值觀。

**架構可視化**

```text
┌──────────────┐
│ Local Docs   │
└──────┬───────┘
       ↓
┌──────────────┐
│ Local Index  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Local Query  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Private LLM  │
└──────────────┘
```

**選入原因**

- local / private RAG 代表性高。
- Apache-2.0 授權清楚。
- 適合本專案思考 local-only、secret masking、no network exposure 的 fixture。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | local/private document RAG 明確 |
| 與 RAG 直接相關 | 是 | document interaction + retrieval-based QA |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 是 | 目標與架構方向明確 |
| 適合本專案參考 | 是 | 高度貼近 Systograph |

#### 5.5.2 AllAboutAI-YT/easy-local-rag

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `AllAboutAI-YT/easy-local-rag` |
| GitHub | https://github.com/AllAboutAI-YT/easy-local-rag |
| 主要用途 | simple local RAG with Ollama + email RAG |
| 主要語言 | Python |
| 技術或框架 | Ollama、local RAG |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-29 |
| Stars | 1,222 |
| License | MIT |

**簡短說明**

easy-local-rag 是簡單 local RAG 範例，使用 Ollama 方向很適合本專案 Task 4 的 `basic_qdrant_ollama_rag` 或 local fixture 參考。

**架構可視化**

```text
┌──────────────┐
│ Local Files  │
│ Email Data   │
└──────┬───────┘
       ↓
┌──────────────┐
│ Local Index  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Retrieval    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Ollama LLM   │
└──────────────┘
```

**選入原因**

- 小型 local RAG 方向符合 Task 4。
- MIT 授權清楚。
- 適合抽出 Ollama、local LLM、document retrieval fixture signal。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | local RAG、Ollama signal 明確 |
| 與 RAG 直接相關 | 是 | repo description 直接說 local RAG |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 部分符合 | 初步足夠，細節需看 README |
| 適合本專案參考 | 是 | 高度適合 Task 4 local fixture |

#### 5.5.3 Mintplex-Labs/anything-llm

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `Mintplex-Labs/anything-llm` |
| GitHub | https://github.com/Mintplex-Labs/anything-llm |
| 主要用途 | local / self-hosted AI productivity and RAG app |
| 主要語言 | JavaScript |
| 技術或框架 | local LLM、Ollama、vector database、RAG、AI agents、MCP、multimodal |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-31 |
| Stars | 60,820 |
| License | MIT |

**簡短說明**

AnythingLLM 是完整 local / self-hosted RAG app，強調 on-device、privacy first，並整合 local LLM、Ollama、vector database、agents 與 MCP。它不是小型 fixture，但非常適合參考「完整 local RAG app 會有哪些掃描訊號」。

**架構可視化**

```text
┌──────────────┐
│ Workspace    │
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Ingestion    │
│ Chunk/Embed  │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Vector DB    │ ←→  │ Local LLM    │
└──────┬───────┘     │ Ollama/etc.  │
       ↓             └──────┬───────┘
┌──────────────┐            ↓
│ Chat / Agent │ ─────────→ │ Answer │
└──────────────┘            └────────┘
```

**選入原因**

- 補足原本 research 中缺少的 AnythingLLM 類型：完整 local / self-hosted RAG app。
- MIT 授權清楚，GitHub metadata 顯示 topics 包含 `rag`、`localai`、`vector-database`、`ollama`、`local-llm`、`ai-agents`、`mcp`。
- 適合本專案參考 local/private app 邊界、workspace/document ingestion、vector DB / local LLM integration。
- 不適合整包作為 fixture；應抽出最小 deterministic scanner signals。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | RAG/local/privacy 訊號清楚，但 repo 是完整產品，偏大 |
| 與 RAG 直接相關 | 是 | GitHub topics 包含 `rag`、`vector-database`、`ollama` |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 部分符合 | metadata 足夠初篩，細節需再看 README / docs |
| 適合本專案參考 | 是 | 適合參考 local/private RAG app 邊界，不適合整包複製 |

### 5.6 Medical or Healthcare RAG / 醫療健康相關 RAG

#### 5.6.1 dmis-lab/RAG2

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `dmis-lab/RAG2` |
| GitHub | https://github.com/dmis-lab/RAG2 |
| 主要用途 | rationale-guided RAG for medical QA |
| 主要語言 | Python |
| 技術或框架 | Medical QA、RAG、research implementation |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-20 |
| Stars | 36 |
| License | 未確認 |

**簡短說明**

RAG2 是 medical question answering 的 RAG 研究實作。它不是 production app，但適合了解醫療 QA 中 retrieval 與 rationale 如何搭配。

**架構可視化**

```text
┌──────────────┐
│ Medical Q    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Retrieval    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Rationale    │
│ Guidance     │
└──────┬───────┘
       ↓
┌──────────────┐
│ Medical A    │
└──────────────┘
```

**選入原因**

- 醫療 RAG 研究代表，補足 healthcare 類別。
- 適合作為醫療 QA fixture 概念參考。
- license 未確認，不適合複製程式碼。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | RAG 明確，但 license 未確認、stars 少 |
| 與 RAG 直接相關 | 是 | description 直接說 medical QA RAG |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 部分符合 | 初步可理解，需看論文/README |
| 適合本專案參考 | 部分符合 | 適合概念，不適合直接 fixture |

#### 5.6.2 souvikmajumder26/Multi-Agent-Medical-Assistant

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `souvikmajumder26/Multi-Agent-Medical-Assistant` |
| GitHub | https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant |
| 主要用途 | medical diagnostics / healthcare research assistant |
| 主要語言 | Python |
| 技術或框架 | LangChain、LangGraph、agents、RAG、vector database |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 894 |
| License | Apache-2.0 |

**簡短說明**

這個 repo 結合 medical assistant、multi-agent 與 RAG。它適合參考醫療場景下 agent / retrieval / guardrails 的組合，但需要小心不要引入醫療建議風險。

**架構可視化**

```text
┌──────────────┐
│ User / Case  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Agent Router │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Medical RAG  │ ──→ │ Vector DB    │
└──────┬───────┘     └──────────────┘
       ↓
┌──────────────┐
│ Guarded LLM  │
└──────────────┘
```

**選入原因**

- 醫療 + agentic + RAG 訊號明確。
- Apache-2.0 授權清楚。
- 適合本專案醫療健康 RAG 分類參考，但應轉寫成假資料 fixture。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | 架構有價值，但醫療風險需簡化 |
| 與 RAG 直接相關 | 是 | topics 包含 `rag`、`retrieval-augmented-generation` |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 部分符合 | 初步足夠，細節需看 README |
| 適合本專案參考 | 部分符合 | 適合 healthcare extension，不適合直接複製 |

### 5.7 Vector Database RAG Examples / 向量資料庫整合範例

#### 5.7.1 qdrant/examples

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `qdrant/examples` |
| GitHub | https://github.com/qdrant/examples |
| 主要用途 | Qdrant vector search examples and tutorials |
| 主要語言 | Jupyter Notebook |
| 技術或框架 | Qdrant、vector search、examples |
| 與 RAG 直接相關 | 部分符合 |
| 更新時間 | 2026-05-27 |
| Stars | 215 |
| License | Apache-2.0 |

**簡短說明**

這不是單一 RAG app，而是 Qdrant examples 集合。它很適合參考 vector store signal，例如 `qdrant-client`、collection、embedding、similarity search。

**架構可視化**

```text
┌──────────────┐
│ Text Chunks  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Embeddings   │
└──────┬───────┘
       ↓
┌──────────────┐
│ Qdrant       │
│ Collection   │
└──────┬───────┘
       ↓
┌──────────────┐
│ Similarity   │
│ Search       │
└──────────────┘
```

**選入原因**

- 本專案 Task 4 明確提到 basic Qdrant/Ollama fixture。
- Apache-2.0 授權清楚。
- 可抽出 deterministic vector store signal。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | vector DB signal 明確 |
| 與 RAG 直接相關 | 部分符合 | 是 vector search examples，不一定每個都是 RAG |
| GitHub repo 可存取 | 是 | Qdrant 官方 examples |
| 文件足夠理解架構 | 部分符合 | examples 型態需挑子目錄 |
| 適合本專案參考 | 是 | 適合 Qdrant fixture |

#### 5.7.2 weaviate/Verba

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `weaviate/Verba` |
| GitHub | https://github.com/weaviate/Verba |
| 主要用途 | Weaviate-powered RAG chatbot |
| 主要語言 | Python |
| 技術或框架 | Weaviate、RAG chatbot、vector database |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-29 |
| Stars | 7,713 |
| License | BSD-3-Clause |

**簡短說明**

Verba 是 Weaviate 的 RAG chatbot，對本專案來說很適合參考「vector DB + app + ingestion」的完整關係。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Embedding    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Weaviate     │
└──────┬───────┘
       ↓
┌──────────────┐
│ Chatbot RAG  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Answer       │
└──────────────┘
```

**選入原因**

- vector database RAG app 代表性強。
- BSD-3-Clause 授權清楚。
- 適合參考 vector DB provider detection。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | RAG chatbot + vector DB 明確 |
| 與 RAG 直接相關 | 是 | description 直接說 RAG chatbot |
| GitHub repo 可存取 | 是 | Weaviate repo 可存取 |
| 文件足夠理解架構 | 是 | 用途明確 |
| 適合本專案參考 | 是 | 適合 vector DB RAG fixture 參考 |

### 5.8 RAG Evaluation / 評測與 Benchmark

#### 5.8.1 vibrantlabsai/ragas

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `vibrantlabsai/ragas` |
| GitHub | https://github.com/vibrantlabsai/ragas |
| 主要用途 | LLM / RAG application evaluation |
| 主要語言 | Python |
| 技術或框架 | RAG evaluation、LLMOps、metrics |
| 與 RAG 直接相關 | 部分符合 |
| 更新時間 | 2026-05-30 |
| Stars | 14,141 |
| License | Apache-2.0 |

**簡短說明**

Ragas 不是 RAG app，而是 RAG / LLM app 評測工具。它適合後續設計 readiness report 的 evidence-based metrics，但不是 Task 4 fixture 首選。

**架構可視化**

```text
┌──────────────┐
│ RAG Outputs  │
└──────┬───────┘
       ↓
┌──────────────┐
│ Evaluation   │
│ Metrics      │
└──────┬───────┘
       ↓
┌──────────────┐
│ Score /      │
│ Diagnostics  │
└──────────────┘
```

**選入原因**

- 評測與 benchmark 類別代表性強。
- Apache-2.0 授權清楚。
- 可作為未來 evidence-based report 設計參考。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | 不適合 fixture，但適合 evaluation design |
| 與 RAG 直接相關 | 部分符合 | evaluation tool，不是 RAG pipeline |
| GitHub repo 可存取 | 是 | repo 可存取 |
| 文件足夠理解架構 | 是 | evaluation 目的清楚 |
| 適合本專案參考 | 部分符合 | 適合後續 readiness metrics，不是 Task 4 首選 |

### 5.9 Production-ready RAG Templates / 可落地部署模板

#### 5.9.1 NVIDIA-AI-Blueprints/rag

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `NVIDIA-AI-Blueprints/rag` |
| GitHub | https://github.com/NVIDIA-AI-Blueprints/rag |
| 主要用途 | foundational RAG reference pipeline |
| 主要語言 | Python |
| 技術或框架 | NVIDIA RAG blueprint、NIM、RAG |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-05-30 |
| Stars | 649 |
| License | Apache-2.0 |

**簡短說明**

這是 NVIDIA 的 RAG blueprint，定位是 reference solution。它很適合參考 production-ready RAG 應該有哪些部署與 pipeline 邊界。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ RAG Pipeline │
├──────────────┤
│ Ingest       │
│ Embed        │
│ Retrieve     │
│ Generate     │
└──────┬───────┘
       ↓
┌──────────────┐
│ Deployment   │
│ Blueprint    │
└──────────────┘
```

**選入原因**

- 明確是 RAG reference pipeline。
- Apache-2.0 授權清楚。
- 適合本專案 Task 4 / Task 16 思考 production artifact 邊界。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | reference pipeline 清楚 |
| 與 RAG 直接相關 | 是 | repo description 直接說 RAG pipeline |
| GitHub repo 可存取 | 是 | NVIDIA repo 可存取 |
| 文件足夠理解架構 | 部分符合 | blueprint 概念清楚，細節需看 docs |
| 適合本專案參考 | 是 | 適合 production-ready reference |

### 5.10 Classic document Q&A（private-gpt 同型補充，2026-08-15）

本節只收 **應用**，不收框架本體。判斷「同型」：文件問答、經典向量 RAG 站、以 SDK/套件名接模型或向量庫（不是 Graph 管線、不是評估套件）。

Stars / license / language 取自 2026-08-15 GitHub API。

#### 5.10.1 PromtEngineer/localGPT

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `PromtEngineer/localGPT` |
| GitHub | https://github.com/PromtEngineer/localGPT |
| 主要用途 | 本機文件問答，資料不離機 |
| 主要語言 | Python |
| 技術或框架 | Ollama、HuggingFace embeddings、local RAG、API |
| 與 RAG 直接相關 | 是 |
| 更新時間 | 2026-07-18 |
| Stars | 22,208 |
| License | MIT |

**簡短說明**

localGPT 與 private-gpt 幾乎同一產品形狀：本機文件 → 索引 → 檢索 → 本機 LLM。現況支援 Ollama 推論與 HF embedding/rerank，並有 API。是補充清單裡最接近的「第二個 private-gpt」。

**架構可視化**

```text
┌──────────────┐
│ Local Docs   │
└──────┬───────┘
       ↓
┌──────────────┐
│ Chunk/Embed  │
│ (HF / local) │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Local Index  │ ──→ │ Ollama LLM   │
└──────┬───────┘     └──────┬───────┘
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│ Retriever    │ ──→ │ Cited Answer │
└──────────────┘     └──────────────┘
```

**選入原因**

- 與 private-gpt 同為 local/private document Q&A。
- MIT、Python、Ollama 訊號在現有規則涵蓋內。
- 適合當第二個甜蜜點掃描對照，或抽小型 fixture。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | local RAG、授權清楚、可抽 signal |
| 與 RAG 直接相關 | 是 | description 直接說 chat with documents |
| GitHub repo 可存取 | 是 | 官方 repo |
| 文件足夠理解架構 | 是 | README 寫明 Ollama / embedding / API |
| 適合本專案參考 | 是 | 高度適合甜蜜點對照 |

#### 5.10.2 Cinnamon/kotaemon

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `Cinnamon/kotaemon` |
| GitHub | https://github.com/Cinnamon/kotaemon |
| 主要用途 | 開源 RAG 文件聊天工具 |
| 主要語言 | Python |
| 技術或框架 | RAG chatbot、LLMs、LlamaIndex 生態 |
| 與 RAG 直接相關 | 是（topics 含 `rag`） |
| 更新時間 | 2026-07-14 |
| Stars | 25,700 |
| License | Apache-2.0 |

**簡短說明**

kotaemon 是「跟文件聊天」的完整 app，不是框架。管線仍是 ingestion / index / retrieve / generate，和 private-gpt、ragapp 同一家族。UI 較完整，整包偏大，應抽 LlamaIndex loader/index/query 訊號，不要整倉當 fixture。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Ingest/Index │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Retriever    │ ──→ │ Chat UI      │
└──────┬───────┘     └──────┬───────┘
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│ Vector Index │     │ LLM Answer   │
└──────────────┘     └──────────────┘
```

**選入原因**

- 經典文件 RAG app，Apache-2.0。
- 與 private-gpt / ragapp 同型，可驗證 LlamaIndex 規則是否只對 private-gpt 有效。
- 不適合整包 fixture。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | RAG 清楚但產品偏大 |
| 與 RAG 直接相關 | 是 | topics 含 `rag` |
| GitHub repo 可存取 | 是 | 官方 repo |
| 文件足夠理解架構 | 是 | README 定位明確 |
| 適合本專案參考 | 是 | 適合同型掃描，不適合整包複製 |

#### 5.10.3 chatchat-space/Langchain-Chatchat

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `chatchat-space/Langchain-Chatchat` |
| GitHub | https://github.com/chatchat-space/Langchain-Chatchat |
| 主要用途 | 本地知識庫 RAG + Agent（ChatGLM / Qwen / Llama） |
| 主要語言 | Python |
| 技術或框架 | LangChain、FAISS、Milvus、Ollama、FastChat、Xinference |
| 與 RAG 直接相關 | 是（topics 含 `rag`、`langchain`、`ollama`、`faiss`、`milvus`） |
| 更新時間 | 2025-11-10 |
| Stars | 38,546 |
| License | Apache-2.0 |

**簡短說明**

原 Langchain-ChatGLM，是中文社群最常見的「本地知識庫問答」應用。形狀與 private-gpt 相同，框架換成 LangChain。Ollama / LangChain 在規則內；Milvus 屬 P1 規則廣度缺口（格子是 `index_builder`，規則可能沒有）。

**架構可視化**

```text
┌──────────────┐
│ Knowledge    │
│ Files        │
└──────┬───────┘
       ↓
┌──────────────┐
│ LangChain    │
│ Load/Split   │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ FAISS/Milvus │ ──→ │ Local LLM    │
└──────┬───────┘     │ Ollama/Qwen  │
       ↓             └──────┬───────┘
┌──────────────┐            ↓
│ Retriever    │ ─────────→ │ Answer │
└──────────────┘            └────────┘
```

**選入原因**

- 本地知識庫 RAG app，不是框架本體。
- LangChain + Ollama 可對現有規則；Milvus 可當「同型但規則不夠」對照。
- Apache-2.0。更新較慢（2025-11），仍具代表性。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | 本地 RAG、dependency topics 清楚 |
| 與 RAG 直接相關 | 是 | topics 含 rag / langchain / ollama |
| GitHub repo 可存取 | 是 | 官方 repo |
| 文件足夠理解架構 | 是 | README 與 topics 足夠 |
| 適合本專案參考 | 是 | 同型掃描；Milvus 當規則缺口樣本 |

#### 5.10.4 khoj-ai/khoj

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `khoj-ai/khoj` |
| GitHub | https://github.com/khoj-ai/khoj |
| 主要用途 | self-host 第二大腦：文件 / 筆記 RAG + agent |
| 主要語言 | Python |
| 技術或框架 | RAG、semantic search、local/offline LLM、agents |
| 與 RAG 直接相關 | 是（topics 含 `rag`、`self-hosted`、`semantic-search`） |
| 更新時間 | 2026-08-02 |
| Stars | 36,499 |
| License | **AGPL-3.0**（可讀、不適合複製進本 repo fixture） |

**簡短說明**

Khoj 是完整 self-host 產品：索引本機文件與筆記，再用線上或離線 LLM 問答。管線仍是經典 RAG，但產品面比 private-gpt 寬（agent、排程、多前端）。授權是 AGPL，只可掃描參考，不可整段搬進 Systograph fixture。

**架構可視化**

```text
┌──────────────┐
│ Notes/Docs   │
│ (md/pdf/org) │
└──────┬───────┘
       ↓
┌──────────────┐
│ Index /      │
│ Semantic     │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Retriever    │ ──→ │ Local/Cloud  │
└──────┬───────┘     │ LLM          │
       ↓             └──────┬───────┘
┌──────────────┐            ↓
│ Chat/Agent   │ ─────────→ │ Answer │
└──────────────┘            └────────┘
```

**選入原因**

- 與 private-gpt 同為 self-host 文件 RAG。
- 活躍、RAG topics 清楚。
- AGPL 限制複製；掃描對照可以，fixture 轉寫需自己重寫。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | RAG 清楚，但 AGPL + 產品大 |
| 與 RAG 直接相關 | 是 | topics 含 `rag` |
| GitHub repo 可存取 | 是 | 官方 repo |
| 文件足夠理解架構 | 是 | README 足夠 |
| 適合本專案參考 | 部分符合 | 可掃；不要複製原始碼 |

#### 5.10.5 docker/genai-stack

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `docker/genai-stack` |
| GitHub | https://github.com/docker/genai-stack |
| 主要用途 | LangChain + Docker + Neo4j + Ollama 範例棧 |
| 主要語言 | Python |
| 技術或框架 | LangChain、Ollama、Neo4j、Docker Compose |
| 與 RAG 直接相關 | 是（官方描述即此組合） |
| 更新時間 | 2026-08-10 |
| Stars | 5,386 |
| License | CC0-1.0 |

**簡短說明**

官方 Docker 教學棧，體積小、compose 清楚，適合當「可掃的小型經典 RAG」。Ollama / LangChain 應能亮；Neo4j 若當向量或圖庫，現有規則可能對不到（規則缺口，不是目錄缺口）。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ LangChain    │
│ Ingest       │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Neo4j        │ ──→ │ Ollama       │
└──────┬───────┘     └──────┬───────┘
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│ Retriever    │ ──→ │ Answer       │
└──────────────┘     └──────────────┘
```

**選入原因**

- 小、Docker/Ollama 訊號明確，接近 Task 4 fixture 需求。
- CC0，轉寫無授權負擔。
- 可同時測「Ollama 甜蜜點」與「Neo4j 規則缺口」。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 是 | 小型、dependency/docker 清楚 |
| 與 RAG 直接相關 | 是 | LangChain + Ollama 問答棧 |
| GitHub repo 可存取 | 是 | Docker 官方 repo |
| 文件足夠理解架構 | 是 | compose / README 清楚 |
| 適合本專案參考 | 是 | 高度適合掃描與 fixture |

#### 5.10.6 Azure-Samples/azure-search-openai-demo

**基本資訊**

| 項目 | 內容 |
|---|---|
| Repo | `Azure-Samples/azure-search-openai-demo` |
| GitHub | https://github.com/Azure-Samples/azure-search-openai-demo |
| 主要用途 | Azure AI Search + Azure OpenAI 的經典 RAG 範例 |
| 主要語言 | Python |
| 技術或框架 | Azure OpenAI、Azure AI Search、ChatGPT-style Q&A |
| 與 RAG 直接相關 | 是（topics 含 `openai`、`azurecognitivesearch`） |
| 更新時間 | 2026-08-13 |
| Stars | 7,731 |
| License | MIT |

**簡短說明**

微軟官方經典 RAG 參考實作：ingest → Azure Search → Azure OpenAI → 引用式回答。**管線與 private-gpt 同型**，但供應商是 Azure SDK。現有規則認 `openai` / Qdrant / Ollama，多半認不到 Azure Search → 預期像 Verba：形狀對、規則不夠。

**架構可視化**

```text
┌──────────────┐
│ Documents    │
└──────┬───────┘
       ↓
┌──────────────┐
│ Ingest /     │
│ Embed        │
└──────┬───────┘
       ↓
┌──────────────┐     ┌──────────────┐
│ Azure AI     │ ──→ │ Azure OpenAI │
│ Search       │     └──────┬───────┘
       ↓                    ↓
┌──────────────┐     ┌──────────────┐
│ Retriever    │ ──→ │ Cited Answer │
└──────────────┘     └──────────────┘
```

**選入原因**

- 業界最常見的雲端經典 RAG 樣本，MIT。
- 用來對照「同型但規則不夠」，不要期待掃得像 private-gpt。
- 不要把 Azure 金鑰或真實 endpoint 寫進 fixture。

**符合條件檢查表**

| 檢查項目 | 是否符合 | 證據或理由 |
|---|---:|---|
| 符合主要規則 | 部分符合 | RAG 清楚；雲端 SDK 非現有規則甜蜜點 |
| 與 RAG 直接相關 | 是 | description 直接說 RAG pattern |
| GitHub repo 可存取 | 是 | Azure Samples |
| 文件足夠理解架構 | 是 | 官方 demo 文件完整 |
| 適合本專案參考 | 部分符合 | 適合規則缺口對照，不適合當甜蜜點證明 |

---

## 6. 最終複查

| Repo | 是否符合條件 | 是否已分類 | 是否有架構視覺化 | 是否有選入理由 | 是否有檢查表 |
|---|---:|---:|---:|---:|---:|
| langchain-ai/langchain | 部分符合 | 是 | 是 | 是 | 是 |
| run-llama/llama_index | 是 | 是 | 是 | 是 | 是 |
| deepset-ai/haystack | 部分符合 | 是 | 是 | 是 | 是 |
| infiniflow/ragflow | 部分符合 | 是 | 是 | 是 | 是 |
| ragapp/ragapp | 是 | 是 | 是 | 是 | 是 |
| microsoft/graphrag | 是 | 是 | 是 | 是 | 是 |
| HKUDS/LightRAG | 是 | 是 | 是 | 是 | 是 |
| neo4j/neo4j-graphrag-python | 部分符合 | 是 | 是 | 是 | 是 |
| HKUDS/RAG-Anything | 部分符合 | 是 | 是 | 是 | 是 |
| apecloud/ApeRAG | 部分符合 | 是 | 是 | 是 | 是 |
| zylon-ai/private-gpt | 是 | 是 | 是 | 是 | 是 |
| AllAboutAI-YT/easy-local-rag | 是 | 是 | 是 | 是 | 是 |
| Mintplex-Labs/anything-llm | 部分符合 | 是 | 是 | 是 | 是 |
| dmis-lab/RAG2 | 部分符合 | 是 | 是 | 是 | 是 |
| souvikmajumder26/Multi-Agent-Medical-Assistant | 部分符合 | 是 | 是 | 是 | 是 |
| qdrant/examples | 是 | 是 | 是 | 是 | 是 |
| weaviate/Verba | 是 | 是 | 是 | 是 | 是 |
| vibrantlabsai/ragas | 部分符合 | 是 | 是 | 是 | 是 |
| NVIDIA-AI-Blueprints/rag | 是 | 是 | 是 | 是 | 是 |
| PromtEngineer/localGPT | 是 | 是 | 是 | 是 | 是 |
| Cinnamon/kotaemon | 部分符合 | 是 | 是 | 是 | 是 |
| chatchat-space/Langchain-Chatchat | 是 | 是 | 是 | 是 | 是 |
| khoj-ai/khoj | 部分符合 | 是 | 是 | 是 | 是 |
| docker/genai-stack | 是 | 是 | 是 | 是 | 是 |
| Azure-Samples/azure-search-openai-demo | 部分符合 | 是 | 是 | 是 | 是 |

---

## 7. 推薦優先順序

### 7.1 高優先參考

| Repo | 原因 |
|---|---|
| [AllAboutAI-YT/easy-local-rag](https://github.com/AllAboutAI-YT/easy-local-rag) | 小型 local RAG + Ollama，最接近 Task 4 fixture 需求 |
| [Mintplex-Labs/anything-llm](https://github.com/Mintplex-Labs/anything-llm) | 完整 local/private RAG app，適合參考 workspace、document ingestion、vector DB、Ollama/local LLM、agent/MCP integration 邊界 |
| [qdrant/examples](https://github.com/qdrant/examples) | Task 4 明確需要 basic Qdrant/Ollama fixture，可抽 vector store signal |
| [weaviate/Verba](https://github.com/weaviate/Verba) | 完整 vector DB RAG chatbot，適合 ingestion + vector store + query pattern |
| [NVIDIA-AI-Blueprints/rag](https://github.com/NVIDIA-AI-Blueprints/rag) | production RAG reference pipeline，適合 map build / artifact 邊界 |
| [microsoft/graphrag](https://github.com/microsoft/graphrag) | GraphRAG 代表性高，可作 graph extension fixture 參考 |
| [zylon-ai/private-gpt](https://github.com/zylon-ai/private-gpt) | local/private RAG 代表性強，貼近本專案 local scanner 定位 |
| [PromtEngineer/localGPT](https://github.com/PromtEngineer/localGPT) | private-gpt 同型雙胞胎；MIT、Ollama，適合第二個甜蜜點掃描 |
| [docker/genai-stack](https://github.com/docker/genai-stack) | 小型 LangChain+Ollama+compose，接近 fixture 體積 |

### 7.2 中優先參考

| Repo | 原因 |
|---|---|
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | ingestion / index / retriever pattern 清楚 |
| [ragapp/ragapp](https://github.com/ragapp/ragapp) | Agentic RAG + app integration 值得參考 |
| [Cinnamon/kotaemon](https://github.com/Cinnamon/kotaemon) | 經典文件 RAG app（LlamaIndex），可驗證規則是否只對 private-gpt 有效 |
| [chatchat-space/Langchain-Chatchat](https://github.com/chatchat-space/Langchain-Chatchat) | LangChain 本地知識庫；Ollama 甜蜜點 + Milvus 規則缺口 |
| [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | graph/vector hybrid RAG 值得參考 |
| [deepset-ai/haystack](https://github.com/deepset-ai/haystack) | pipeline abstraction 值得參考 |
| [neo4j/neo4j-graphrag-python](https://github.com/neo4j/neo4j-graphrag-python) | graph DB integration 值得參考，但 license 需確認 |
| [souvikmajumder26/Multi-Agent-Medical-Assistant](https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant) | 醫療 + agentic RAG 可參考，但需簡化與避免醫療風險 |

### 7.3 低優先參考

| Repo | 原因 |
|---|---|
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 基礎框架太大，適合理解 pattern，不適合直接 fixture |
| [infiniflow/ragflow](https://github.com/infiniflow/ragflow) | 完整 RAG engine 很有代表性，但太大 |
| [HKUDS/RAG-Anything](https://github.com/HKUDS/RAG-Anything) | 多模態重要，但 Task 4 初版可先不做 |
| [apecloud/ApeRAG](https://github.com/apecloud/ApeRAG) | production GraphRAG 訊號多，但系統複雜 |
| [dmis-lab/RAG2](https://github.com/dmis-lab/RAG2) | medical RAG 有價值，但 license 未確認、偏研究 |
| [khoj-ai/khoj](https://github.com/khoj-ai/khoj) | self-host 文件 RAG，但 AGPL、產品大，只掃不複製 |
| [Azure-Samples/azure-search-openai-demo](https://github.com/Azure-Samples/azure-search-openai-demo) | 經典雲端 RAG；Azure SDK 多半掃不亮，當規則缺口樣本 |

### 7.4 僅作延伸閱讀

| Repo | 原因 |
|---|---|
| [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas) | evaluation 設計有用，但不是 scanner fixture 來源 |

---

## 8. 建議 Task 4 使用方式

不要整包複製上述 repo。建議流程：

```text
挑 2-3 個高優先 repo
↓
觀察它們的檔案命名、dependency、docker/config、RAG pipeline pattern
↓
轉寫成小型 fixture
↓
放到 tests/fixtures/rag_projects/
↓
用 tests/helpers/fixtures.py 提供穩定 path helper
```

最建議先做：

```text
basic_qdrant_ollama_rag
├── 參考 qdrant/examples
├── 參考 AllAboutAI-YT/easy-local-rag
├── 參考 Mintplex-Labs/anything-llm 的 local/private app 邊界
└── 只保留 docker-compose、requirements、app/retriever/ingest pattern

openai_external_provider_rag
├── 參考 LlamaIndex / LangChain 常見 pattern
└── 只放 fake OPENAI_API_KEY，不放真 secret

graph_rag_extension_rag
├── 參考 microsoft/graphrag / LightRAG
└── 用最小 graph retriever signal 測 extension/unmapped behavior

localgpt_ollama_rag（可選第二個甜蜜點 fixture）
├── 參考 PromtEngineer/localGPT
├── 參考 docker/genai-stack 的 compose / Ollama
└── 只保留 ingest / embed / retrieve / ollama，不要複製 AGPL 或 Azure 金鑰
```

---

## 9. Systograph 掃描器分類（2026-08-15）

「像 private-gpt」= **經典向量 RAG 應用** + **SDK/套件名**（llama_index / langchain / qdrant / chroma / openai / ollama）。  
不是報告裡的「適合度高」（那是適不適合抽 fixture）。

### 9.1 甜蜜點（同型，現有規則較可能掃得動）

| Repo | 依據 |
|---|---|
| zylon-ai/private-gpt | 已實測：14 元件 / 15 格 |
| PromtEngineer/localGPT | 本機文件 Q&A + Ollama；private-gpt 雙胞胎 |
| AllAboutAI-YT/easy-local-rag | 小型 local RAG + Ollama |
| ragapp/ragapp | LlamaIndex RAG app（後端同家族；主語言 TS） |
| Cinnamon/kotaemon | 文件聊天 app，LlamaIndex 生態 |
| chatchat-space/Langchain-Chatchat | LangChain + Ollama；FAISS 可能亮、Milvus 可能不亮 |
| docker/genai-stack | 小棧；Ollama/LangChain 應亮 |
| souvikmajumder26/Multi-Agent-Medical-Assistant | LangChain + vector DB + RAG（醫療內容勿當 demo 資料） |
| qdrant/examples | 不是完整 app，但 `qdrant-client` 與 private-gpt 同層 |
| NVIDIA-AI-Blueprints/rag | 管線經典；若走 NIM SDK 會亮，若多半 URL 則掉到 9.2 |

**面試再掃一個的首選：** `PromtEngineer/localGPT` 或 `docker/genai-stack`。

### 9.2 同型但規則不夠（格子在，廠商/接法不在規則裡）

| Repo | 預期缺口 |
|---|---|
| weaviate/Verba | 已實測：Weaviate + 裸 HTTP |
| Mintplex-Labs/anything-llm | JS、多供應商、設定/HTTP 為主 |
| Azure-Samples/azure-search-openai-demo | Azure Search / Azure OpenAI SDK |
| docker/genai-stack 的 Neo4j 部分 | Ollama 可能亮，Neo4j 可能不亮 |
| Langchain-Chatchat 的 Milvus 路徑 | 與 P1 向量庫廣度同一題 |

### 9.3 不同型（不要當第二個 private-gpt）

| 類型 | Repo |
|---|---|
| Graph / 圖譜管線（目錄缺口） | microsoft/graphrag、HKUDS/LightRAG、neo4j/neo4j-graphrag-python、apecloud/ApeRAG |
| 多模態管線（目錄粗） | HKUDS/RAG-Anything |
| 框架本體，不是 app | langchain-ai/langchain、run-llama/llama_index、deepset-ai/haystack |
| 完整自研引擎 / 太大 | infiniflow/ragflow |
| 評估，不是 ingestion 管線 | vibrantlabsai/ragas |
| 研究向 / license 不清 | dmis-lab/RAG2 |
| 形狀像但 AGPL、只掃不複製 | khoj-ai/khoj |

### 9.4 本次沒收入的候選（查過、刻意不寫進 §5）

| Repo | 原因 |
|---|---|
| QuivrHQ/quivr | GitHub license = Other / NOASSERTION |
| embedchain/embedchain | 已轉成 mem0ai/mem0（記憶層，不是文件 Q&A app） |
| langchain-ai/chat-langchain | 現況主語言 TypeScript，較不像 private-gpt 掃描路徑 |
| llmware-ai/llmware | 偏框架，不是單一 RAG app |
| intel/fastRAG | 2026-08-15 GitHub API 404 |

```text
 報告全部 repo
    │
    ├─ 9.1 甜蜜點     private-gpt、localGPT、easy-local-rag、
    │                 kotaemon、Langchain-Chatchat、ragapp、
    │                 genai-stack、medical multi-agent、
    │                 qdrant/examples、NVIDIA blueprint（視 SDK）
    ├─ 9.2 規則缺口   Verba、anything-llm、Azure demo、Milvus/Neo4j
    └─ 9.3 不同型     Graph*、多模態、框架本體、ragas、ragflow
```
