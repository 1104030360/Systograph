# Backend Architecture Diagrams

本文件用 Mermaid 描述目前後端架構、模組依賴、請求生命週期、資料流、使用者流程、認證現況與資料庫關係。

## 後端整體架構圖

```mermaid
flowchart TD
  User[Browser / User] --> Flask[Flask App<br/>Analysis.py]
  Launcher[run_analysis.py] --> Flask

  Flask --> Routes[API Blueprints<br/>api/*.py]
  Flask --> Pages[Templates<br/>templates/*.html]
  Flask --> Core[Core Infrastructure<br/>config / DI / logger / errors / db]

  Routes --> Upload[Upload Routes]
  Routes --> Chat[Chat Routes]
  Routes --> Cluster[Cluster Routes]
  Routes --> Config[Config Routes]
  Routes --> History[History Routes]

  Upload --> TicketService[TicketService]
  Chat --> RAGService[RAGService]
  Cluster --> ClusterService[ClusterService]
  Cluster --> KBService[KBService]
  Config --> ConfigService[ConfigService]
  History --> HistoryService[HistoryService]

  TicketService --> RiskService[RiskService]
  TicketService --> GPTUtils[gpt_utils.py]
  RAGService --> GPTChat[gptChat.py]
  GPTChat --> SQLAgent[SQLAgent]
  GPTChat --> SemanticAgent[SemanticAgent]
  GPTChat --> HybridAgent[HybridQueryAgent]
  ClusterService --> GPTUtils

  SQLAgent --> SQLite[(SQLite<br/>resultDB.db)]
  SemanticAgent --> FAISS[(FAISS Index<br/>kb_index.faiss)]
  SemanticAgent --> SQLite
  KBService --> BuildKB[build_kb.py]
  BuildKB --> SQLite
  BuildKB --> FAISS

  TicketService --> JSONData[(json_data)]
  TicketService --> ExcelUnclustered[(excel_result_Unclustered)]
  ClusterService --> ExcelClustered[(excel_result_Clustered)]
  RAGService --> ChatHistory[(chat_history)]
  ConfigService --> ConfigFiles[(config / gpt_data / data/sentences / StorageAddress)]

  GPTUtils --> PowerAutomate[Power Automate AI Builder]
  GPTUtils --> CloudOllama[Cloud Ollama]
  GPTUtils --> LocalOllama[Local Ollama]
```

說明：Flask route 是入口，service 層承載主要 workflow，repository / utils / agents 負責資料存取、AI 呼叫與 Excel/FAISS/SQLite 操作。此架構已往分層前進，但仍保留 `gptChat.py`、`gpt_utils.py`、`ClusterService` 等大型 orchestration 模組。

## 模組依賴圖

```mermaid
flowchart LR
  API[api] --> Core[core.dependencies]
  API --> Services[services]

  Services --> Core
  Services --> Repositories[repositories]
  Services --> Utils[utils]
  Services --> Agents[agents]
  Services --> LegacyAI[gptChat / gpt_utils / SmartScoring]

  Agents --> LegacyAI
  Agents --> Repositories
  Agents --> SQLite[(SQLite)]
  Agents --> ExternalAI[External AI Providers]

  Repositories --> CoreDB[core.database]
  Repositories --> Files[(JSON / FAISS / pickle files)]

  Utils --> ConfigFiles[(JSON configs)]
  Utils --> ExternalAI
```

說明：依賴方向大致是 API -> Services -> Repositories/Utils/Agents。主要例外是 `gptChat.py` 在 import 時建立 repository 與 agent singleton，且 agents 直接讀 `.env` 與呼叫外部 AI，這讓測試與併發隔離變困難。

## API Request Lifecycle

```mermaid
flowchart TD
  A[HTTP Request] --> B[Flask route in api/*.py]
  B --> C{Basic validation}
  C -->|invalid| E[make_error_response]
  C -->|valid| D[get_service from DI singleton]
  D --> F[Service workflow]
  F --> G{Needs data access?}
  G -->|SQLite / FAISS / JSON| H[Repository or direct file access]
  G -->|Excel / config / sync| I[utils]
  G -->|AI / RAG| J[gpt_utils / gptChat / agents]
  J --> K[Power Automate / Cloud Ollama / Local Ollama]
  H --> L[Domain result]
  I --> L
  K --> L
  L --> M{Response type}
  M -->|JSON| N[jsonify]
  M -->|File| O[send_file]
  M -->|SSE| P[Response text/event-stream]
  E --> Q[Unified error JSON]
```

說明：route 本身多數只做 request parsing。錯誤處理同時存在 route try/except 與 app error handler，短期可接受，但長期應統一，避免錯誤格式漂移。

## 上傳分析資料流

```mermaid
flowchart TD
  Upload[Upload xlsx] --> Validate[Validate extension / size / columns]
  Validate --> SaveOriginal[uploads/original_timestamp.xlsx]
  SaveOriginal --> ReadExcel[pandas read_excel]
  ReadExcel --> RowTasks[Async row analysis]
  RowTasks --> Risk[RiskService scoring]
  RowTasks --> AI[AI summary and solution extraction]
  AI --> Providers[AI Builder -> Cloud Ollama -> Local Ollama]
  Risk --> ResultData[Analysis result data]
  Providers --> ResultData
  ResultData --> SaveJSON[json_data/result_timestamp.json]
  ResultData --> SaveExcel[excel_result_Unclustered/result_timestamp_Unclustered.xlsx]
  SaveExcel --> SyncTarget[Optional sync target Excel]
  SaveJSON --> RebuildKB[Background build_kb.py]
  RebuildKB --> SQLite[(metadata table)]
  RebuildKB --> FAISS[(FAISS index + metadata + texts)]
```

說明：上傳流程會產生 JSON、Excel，再觸發背景 KB rebuild。這符合實用流程，但背景 subprocess 沒有佇列、去重或狀態追蹤，併發上傳時容易互相踩到 KB lock / output files。

## RAG 查詢資料流

```mermaid
flowchart TD
  Query[User query] --> ChatRoute[/api/v2/chat or /chat/stream]
  ChatRoute --> RAG[RAGService]
  RAG --> LoadHistory[Load chat_history/chat_id.json]
  LoadHistory --> GPTChat[gptChat orchestration]
  GPTChat --> Classifier[AutoGen classifier]
  Classifier --> SQL[SQLAgent]
  Classifier --> Semantic[SemanticAgent]
  Classifier --> Hybrid[HybridQueryAgent]
  SQL --> SQLite[(SQLite metadata)]
  Semantic --> FAISS[(FAISS vector search)]
  Semantic --> SQLite
  Hybrid --> SQL
  Hybrid --> Semantic
  SQL --> LLM[LLM summarization]
  Semantic --> LLM
  Hybrid --> LLM
  LLM --> Answer[Answer text]
  Answer --> SaveHistory[Append chat history]
  SaveHistory --> Response[JSON or SSE complete event]
```

說明：RAG 使用 agent 分派，能處理 SQL、語意與混合查詢。但 `gptChat.py` 使用 module-level singleton 與全域 callback，對多使用者、多執行緒 Flask 不安全。

## 分群資料流

```mermaid
flowchart TD
  Unclustered[excel_result_Unclustered/*.xlsx] --> ClusterService[ClusterService.cluster_excel]
  ClusterService --> PerRow[For each row]
  PerRow --> CategoryMemory[cluster_excels/*_categories.json]
  PerRow --> ClassifyAI[AI category classification]
  ClassifyAI --> UpdateDF[Write aiCategory]
  UpdateDF --> Dedup[deduplicate_by_id_and_time]
  Dedup --> Details[excel_result_Clustered/Details/Cluster_*.xlsx]
  Details --> SummaryAI[AI group summary]
  SummaryAI --> Summaries[excel_result_Clustered/Summaries/Summary_*.xlsx]
  Details --> MoveOriginal[Move *_Unclustered.xlsx to *_Clustered.xlsx]
  Summaries --> OptionalSync[Optional manual sync target]
```

說明：分群流程以檔案為主，逐列呼叫 AI。優點是操作直觀；缺點是部分 exception 被吞掉，出錯時可能仍顯示完成。

## 使用者流程圖

```mermaid
flowchart TD
  Start[Open web UI] --> Choose{User action}
  Choose --> Upload[Upload ticket Excel]
  Upload --> Progress[Poll /api/v2/progress]
  Progress --> Result[View result / history]
  Result --> Cluster[Generate cluster]
  Cluster --> Download[Download clustered or summary Excel]

  Choose --> Chat[Ask RAG question]
  Chat --> ChatHistory[Read / append chat session]
  ChatHistory --> ChatAnswer[Receive answer]

  Choose --> Settings[System settings]
  Settings --> Weight[Update risk weights]
  Settings --> Sentences[Manage risk sentences]
  Settings --> Prompts[Manage GPT prompts]
  Settings --> Storage[Set sync storage path]
```

說明：使用者主要工作流是上傳分析、看結果、分群、RAG 查詢、系統設定。設定 API 目前沒有權限保護，因此應優先補上管理員邊界。

## 認證 / 授權流程圖

```mermaid
flowchart TD
  Request[Incoming request] --> Flask[Flask route]
  Flask --> AuthCheck{Authentication middleware exists?}
  AuthCheck -->|No| Route[Route handler executes]
  Route --> Sensitive{Sensitive operation?}
  Sensitive -->|Upload / query| Service[Service executes]
  Sensitive -->|Delete / clear / open file / set path| AdminAction[Admin-like action executes without auth]
  Service --> Response[Response]
  AdminAction --> Response
```

說明：目前沒有認證與授權流程。這張圖刻意保留 `No` 分支，表示安全邊界不存在，而不是漏畫。若系統只在受控內網單機執行，風險較低；若對多人或網路開放，這是 Critical。

## Entity Relationship Diagram

```mermaid
erDiagram
  METADATA {
    INTEGER id PK
    TEXT text
    TEXT subcategory
    TEXT configurationItem
    TEXT roleComponent
    TEXT location
    TEXT opened
    TEXT analysisTime
    TEXT problemSummary
    TEXT solution
    REAL riskScore
    TEXT riskLevel
  }

  HIGH_RISK_SENTENCES {
    INTEGER id PK
    TEXT sentence
    TEXT category
    TIMESTAMP added_at
  }

  CHAT_SESSION {
    TEXT id PK
    TEXT title
    TEXT edit_title
    TEXT model
    TEXT timestamp
    JSON history
  }

  ANALYSIS_RESULT {
    TEXT uid PK
    TEXT file
    TEXT analysisTime
    JSON data
  }

  FAISS_METADATA {
    TEXT id PK
    TEXT text
    JSON metadata
  }

  METADATA ||--o{ FAISS_METADATA : "same ticket id / text"
  ANALYSIS_RESULT ||--o{ METADATA : "build_kb imports"
  CHAT_SESSION ||--o{ ANALYSIS_RESULT : "may reference context"
  HIGH_RISK_SENTENCES }o--|| METADATA : "used for risk scoring"
```

說明：只有 `metadata` 與 `high_risk_sentences` 是程式碼中明確建立的 SQLite 表。`CHAT_SESSION`、`ANALYSIS_RESULT`、`FAISS_METADATA` 是檔案型 entity，列入 ERD 是為了呈現實際資料關係。

