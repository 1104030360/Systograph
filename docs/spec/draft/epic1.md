# KAI-Mind — AI Agent CI/CD Release Readiness Gate

> Status: Planning  
> Current Focus: Epic 1 — System Map Builder  
> Date: 2026-05-18

---

## 1. Project Summary

KAI-Mind 是一個 **AI Agent / RAG 系統的 CI/CD Release Readiness Gate**。

它的目標不是幫使用者從零建立 AI 系統，也不是做另一個 AI chatbot，而是在使用者已經完成或準備交付一套 AI Agent / RAG 系統後，協助團隊把 AI 系統特有的風險放進開發、PR、release 與 deployment pipeline。

KAI-Mind 最終應該成為 AI Agent 系統的 CI/CD 工具：在 merge、demo、handoff、deployment 或 scheduled check 前，自動掃描系統、輸出 evidence-based report，並用明確的 gate result 告訴 pipeline 是否可以繼續。

它會檢查這套系統是否：

- 可以正常啟動
- Runtime 狀態是否 ready
- 資料是否可能離開預期環境
- 服務是否暴露到不該暴露的網路範圍
- Agent 工具權限是否過大
- RAG knowledge base 是否具備基本可信度
- 回答是否真的被 retrieved evidence 支持
- 是否適合 demo、交付、部署或進入 CI/CD

最終，KAI-Mind 會輸出一份 **Readiness Report**，並給出：

- `READY`
- `RISKY`
- `NOT_READY`

作為 AI 系統是否可以進入下一階段的 CI/CD gate 判斷依據。

---

## 2. One-line Description

### 中文版

KAI-Mind 是一個 AI Agent / RAG 系統的 CI/CD Release Readiness Gate，幫助團隊在 PR、demo、交付、部署或進入 CI/CD pipeline 前，檢查這套 AI 系統是否安全、可用、可信，並輸出 READY / RISKY / NOT_READY 的 gate result。

### English Version

KAI-Mind is a CI/CD release readiness gate for AI Agent and RAG systems, helping teams validate whether their AI systems are safe, reliable, trustworthy, and ready to pass PR, demo, handoff, deployment, or CI/CD gates.

---

## 3. Product Positioning

KAI-Mind 的定位是：

> AI Agent / RAG CI/CD Release Readiness Gate

它不是：

| 類型 | 是否為 KAI-Mind 目標 |
|---|---|
| AI chatbot | 否 |
| AI Agent builder | 否 |
| RAG builder | 否 |
| Open WebUI / AnythingLLM 替代品 | 否 |
| 完整 DevOps / MLOps 平台 | 否 |
| 完整資安防禦工具 | 否 |
| 單純 RAG evaluation wrapper | 否 |
| 單純 observability dashboard | 否 |

它應該是：

| 核心定位 | 說明 |
|---|---|
| AI 系統交付前健檢工具 | 在 demo、交付、部署前檢查風險 |
| AI System Map 建立工具 | 建立 AI 系統元件、資料流、風險位置的地圖 |
| Runtime readiness checker | 檢查 Ollama、Qdrant、Docker、App API 等是否正常 |
| Privacy & exposure checker | 檢查 port、API key、cloud endpoint、外部連線 |
| Agent tool risk checker | 檢查 Agent 工具權限與風險 |
| RAG / knowledge readiness checker | 檢查 collection、metadata、citation、groundedness |
| Release report generator | 產生可讀的交付前健檢報告 |
| CI/CD pass / fail gate | 提供 CLI exit code、JSON report 與 machine-readable verdict，支援 PR / release / deployment pipeline |

---

## 4. Core Workflow

KAI-Mind 的核心流程：

```text
Read → Map → Check → Risk → Recommend → Gate
```

中文流程：

```text
讀取系統
→ 建立 AI System Map
→ 執行健檢規則
→ 判斷風險
→ 產生優先修正建議
→ 作為 Release Gate
```

CI/CD 使用情境下，這個流程應該可以被自動化：

```text
PR / Release / Deployment Pipeline
        ↓
kai-mind gate --ci
        ↓
AI System Map + Readiness Checks
        ↓
JSON Report + Exit Code
        ↓
PASS / FAIL / Needs Review
```

---

## 5. Target Users

| 使用者類型 | 使用情境 | KAI-Mind 價值 |
|---|---|---|
| 學生 / Side Project 開發者 | Demo 前 | 確認作品不只是「能跑」，也能被解釋與展示 |
| AI / Backend 工程師 | 完成 Agent / RAG 功能後 | 找出 runtime、資料流、tool、RAG 風險 |
| 小型 AI PoC 團隊 | 內部展示或主管 demo 前 | 產生可讀的 Readiness Report |
| 企業內部 AI 團隊 | 導入知識庫、客服 Agent、文件問答前 | 檢查資料外流、工具權限、RAG 可追溯性 |
| SI / 顧問 / 接案團隊 | 交付客戶前 | 用報告作為交付附件 |
| Platform / DevOps 團隊 | PR / deployment 前 | 把 AI 系統風險放進 CI/CD Gate |

---

## 6. Core Pain Points

### 6.1 不知道 AI 系統整體架構長什麼樣子

AI Agent / RAG 系統通常由多個元件組成，例如：

- FastAPI / Open WebUI
- Ollama
- Qdrant
- Docker
- `.env` / config
- Agent tools
- RAG collection
- External APIs

使用者可能知道每個元件，但不一定知道整套系統的資料流、外部連線與風險位置。

---

### 6.2 不知道 runtime 是否真的 ready

使用者可能不確定：

- Ollama 是否正常
- 模型是否 loaded
- Docker container 是否 healthy
- Qdrant 是否 ready
- App / Agent API 是否有回應
- 模型是跑在 CPU、GPU 還是 hybrid
- 系統是否適合 demo / 交付 / 上線

---

### 6.3 不知道資料是否可能離開預期環境

常見風險包括：

- `.env` 裡有 OpenAI / Anthropic API key
- config 裡有 remote endpoint
- embedding 使用外部 provider
- cloud fallback 未關閉
- 系統其實不是 local-only，而是 hybrid

---

### 6.4 服務可能不小心暴露

例如：

- Qdrant 綁到 `0.0.0.0`
- Open WebUI 對區網開放
- Agent API 暴露到 LAN
- Docker port publish 到所有網卡
- Qdrant 沒有 API key

這些都可能讓 local AI 系統產生資料外洩或未授權存取風險。

---

### 6.5 Agent 工具權限可能過大

AI Agent 可能不只是回答問題，還能：

- 寄信
- 刪檔
- 寫資料庫
- 呼叫外部 API
- 執行 shell command
- 修改 ticket
- 觸發 workflow

如果沒有 approval、policy 或 tool call log，就不適合直接交付或上線。

---

### 6.6 RAG 回答不一定真的有根據

使用者可能不知道：

- retrieved chunks 是否相關
- citation 是否真的支持答案
- 回答是否有 unsupported claims
- metadata 是否足夠 trace source
- collection / chunk / source 設計是否足夠支援可信回答

所以 KAI-Mind 要檢查的不是「答案看起來像不像對」，而是：

> RAG 回答是否有被資料支持。

---

## 7. Overall Roadmap

目前先建立整體 Parent Issue / Epic roadmap。  
這不代表全部功能馬上開發，而是先讓團隊知道整個產品會分成哪些大模組。

| Epic | 模組名稱 | 核心目的 | 開發階段 |
|---|---|---|---|
| Epic 1 | System Map Builder | 讀取 repo / config / services，建立 AI 系統地圖，作為 CI/CD gate 的共同事實基礎 | 先做 |
| Epic 2 | Runtime Readiness Check | 檢查 Ollama、Docker、Qdrant、App API、模型狀態是否正常 | 後續 |
| Epic 3 | Privacy & Exposure Check | 檢查資料流、API key、cloud endpoint、port exposure | 後續 |
| Epic 4 | Agent Tool Risk Check | 檢查 Agent 工具權限是否過大 | 後續 |
| Epic 5 | RAG / Knowledge Readiness Check | 檢查 collection、metadata、chunk、citation、sample answer support | 後續 |
| Epic 6 | Release Report / CI Gate | 輸出 READY / RISKY / NOT_READY、JSON report 與 exit code，並作為 CI/CD pass / fail gate | 後續 |

---

## 8. Product Architecture Overview

```text
KAI-Mind
AI Agent / RAG Release Readiness Gate
│
├─ 1. System Map Builder
│   └─ 讀取 repo / config / services，建立 AI 系統地圖，作為 CI/CD gate 的共同事實基礎
│
├─ 2. Runtime Readiness Check
│   └─ 檢查 Ollama、Docker、Qdrant、App API、模型狀態是否正常
│
├─ 3. Privacy & Exposure Check
│   └─ 檢查資料流、API key、cloud endpoint、port exposure
│
├─ 4. Agent Tool Risk Check
│   └─ 檢查 agent 工具權限是否過大
│
├─ 5. RAG / Knowledge Readiness Check
│   └─ 檢查 collection、metadata、chunk、citation、sample answer support
│
└─ 6. Release Report / CI Gate
    └─ 輸出 READY / RISKY / NOT_READY、JSON report 與 exit code，並可作為 CI/CD pass / fail gate
```

---

## 9. Input / Process / Output

### 9.1 Input

KAI-Mind 的輸入是一套已完成或準備交付的 AI Agent / RAG 系統。

實際可能包含：

- repo / project folder
- config files
- `.env`
- `docker-compose.yml`
- running services
- Ollama endpoint
- Qdrant endpoint
- App / Agent API endpoint
- agent tools config
- RAG collection / metadata
- optional trace / logs
- optional sample Q&A

---

### 9.2 Process

```text
掃描系統
→ 建立 AI System Map
→ 執行健檢規則
→ 判斷風險
→ 排出最該先修的問題
→ 產生 Release Report / CI Gate
```

---

### 9.3 Output

KAI-Mind 最終輸出應同時服務人類 review 與 CI/CD pipeline：

- Readiness Report
- AI System Map
- Critical Findings
- Evidence
- Fix First Recommendation
- READY / RISKY / NOT_READY
- CI/CD PASS / FAIL
- CLI exit code
- machine-readable JSON artifact

---

## 10. Recommended Product Form

目前最推薦形式：

> CLI Core + JSON Report + CI/CD Gate + Local Web UI

### 10.1 CI/CD 模式

```bash
kai-mind gate --ci --project ./my-ai-agent --output readiness_report.json
```

輸出：

- JSON report
- machine-readable verdict
- exit code
- CI/CD pass / fail result
- artifacts for PR comments or release records

### 10.2 工程模式

```bash
kai-mind map --project ./my-ai-agent --output ai_system_map.json
kai-mind gate --ci
```

輸出：

- JSON report
- exit code
- CI/CD pass / fail result

### 10.3 使用者模式

```text
雙擊 EXE / 啟動 Local Web UI
→ 選擇 project folder
→ 執行 readiness check
→ 查看 AI System Map 與 Release Report
```

### 10.4 後續可擴展形式

成熟後再發展：

- GitHub Action
- Docker Desktop Extension
- VS Code Extension
- CI/CD Plugin

這樣做的好處：

- 不需要一開始做完整 desktop app
- CLI 可以先直接接 CI/CD
- JSON report 與 exit code 可以成為穩定 contract
- 使用者仍然可以透過 Local Web UI 理解報告與 System Map
- 核心邏輯可重用
- 未來能自然包成 plugin

---

# Epic 1 — System Map Builder

## 11. Epic Summary

Epic 1 的目標是建立 KAI-Mind 的第一個核心能力：

> 讀取一套 AI Agent / RAG 系統的 repo、設定檔與執行中服務，建立一份可供後續診斷使用的 AI System Map。

System Map Builder 不是單純畫圖工具。  
它的真正目的，是把一套看似分散的 AI 系統整理成結構化資料，讓後續的 readiness check 可以知道：

- 系統有哪些元件
- 元件之間如何連接
- 哪些服務正在執行
- 哪些服務可能暴露
- 哪些地方有外部 endpoint
- 哪些地方有 Agent tools
- 哪些地方與 RAG knowledge base 有關
- 後續哪些檢查模組需要接手

對 CI/CD 來說，System Map 是 gate 的事實層。  
如果 pipeline 要判斷一套 AI Agent 系統能不能 release，就必須先知道要檢查哪些 runtime、endpoint、tool、資料來源、外部 provider 與 exposure surface。

---

## 12. Why Start from System Map Builder?

第一個 Epic 應該先做 System Map Builder，原因很簡單：

> 如果 KAI-Mind 不知道系統裡有什麼，就不可能正確判斷系統是否 ready。

後續每個功能都依賴 System Map：

| 後續模組 | 為什麼需要 System Map |
|---|---|
| Runtime Readiness Check | 需要知道有哪些 runtime、container、endpoint 要檢查 |
| Privacy & Exposure Check | 需要知道服務綁在哪些 IP / port、是否有 external endpoint |
| Agent Tool Risk Check | 需要知道系統裡有哪些 tools、權限是什麼 |
| RAG / Knowledge Readiness Check | 需要知道 vector DB、collection、metadata、retrieval pipeline 在哪裡 |
| Release Report / CI Gate | 需要把所有檢查結果回填到同一張系統地圖上 |

如果沒有 System Map，KAI-Mind 會變成一堆零散 scanner。  
有了 System Map，KAI-Mind 才能變成真正可放進 CI/CD 的 AI 系統診斷與 release gate 工具。

---

## 13. Epic 1 Goal

Epic 1 完成後，使用者可以輸入一個既有的 AI Agent / RAG 專案資料夾，讓 KAI-Mind 自動掃描 repo、設定檔、Docker services、endpoint、Agent tools 與可能的外部連線，產生一份可追溯 evidence 的 AI System Map。使用者可以透過互動式 GUI 看到系統中的元件與資料流，點選節點或連線查看來源證據、confidence 與風險提示，並用這份 map 作為後續 Runtime Readiness、Privacy & Exposure、Agent Tool Risk、RAG Knowledge Trust 與 CI/CD Gate 的共同基礎。

Epic 1 要完成的不是完整 readiness check，而是：

> 建立 KAI-Mind 可以理解 AI Agent / RAG 系統的第一層結構，讓後續 CI/CD gate 可以基於同一份 map 做判斷。

也就是：

```text
Project Folder / Running Services
        ↓
System Scanner
        ↓
Detected Components
        ↓
AI System Map
        ↓
Structured JSON Output
        ↓
Interactive System Map GUI
```

---

## 14. Scope of Epic 1

### 14.1 In Scope

Epic 1 應該包含：

| 類別 | 內容 |
|---|---|
| Project folder scan | 掃描 repo / project folder |
| Config discovery | 找出 `.env`、config、Docker、agent、RAG 相關設定 |
| Runtime endpoint discovery | 偵測可能的 Ollama、Qdrant、App API endpoint |
| Docker compose parsing | 讀取 `docker-compose.yml` 中的 services、ports、volumes、env |
| AI component detection | 辨識 LLM runtime、vector DB、app API、agent tools、data source |
| External endpoint detection | 找出可能的外部 API endpoint |
| Network exposure hints | 記錄 localhost、0.0.0.0、LAN IP 等 exposure hints |
| System map output | 輸出結構化 JSON / Markdown summary |
| Interactive System Map GUI | 提供可操作的可視化介面，讓使用者可以探索 AI System Map |

---

### 14.2 Out of Scope

Epic 1 不應該做太多後續檢查，否則範圍會失控。

| 不納入 Epic 1 | 原因 |
|---|---|
| 完整 runtime health check | 留給 Epic 2 |
| 完整 port security 判斷 | 留給 Epic 3 |
| API key secret 掃描深度分析 | 留給 Epic 3 |
| Agent tool policy 判斷 | 留給 Epic 4 |
| RAG citation groundedness 評估 | 留給 Epic 5 |
| READY / RISKY / NOT_READY 最終判斷 | 留給 Epic 6 |
| 完整 readiness dashboard | Epic 1 只做 System Map viewer，不做完整 report dashboard |
| 複雜圖編輯器 | Epic 1 的 GUI 只需要探索與檢視，不需要手動建模或編輯 map |

---

## 15. AI System Map Data Model

Epic 1 的核心產物是一份 AI System Map。

最小版本可以長這樣：

```json
{
  "project": {
    "name": "example-ai-agent",
    "root_path": "/path/to/project"
  },
  "components": [
    {
      "id": "ollama_runtime",
      "type": "llm_runtime",
      "name": "Ollama",
      "source": "docker-compose.yml",
      "endpoint": "http://localhost:11434",
      "confidence": "high"
    },
    {
      "id": "qdrant_vector_db",
      "type": "vector_db",
      "name": "Qdrant",
      "source": "docker-compose.yml",
      "endpoint": "http://localhost:6333",
      "confidence": "high"
    },
    {
      "id": "app_api",
      "type": "app_api",
      "name": "FastAPI",
      "source": "project files",
      "endpoint": "http://localhost:8000",
      "confidence": "medium"
    }
  ],
  "connections": [
    {
      "from": "app_api",
      "to": "ollama_runtime",
      "reason": "LLM generation endpoint"
    },
    {
      "from": "app_api",
      "to": "qdrant_vector_db",
      "reason": "RAG retrieval endpoint"
    }
  ],
  "risk_hints": [
    {
      "type": "network_exposure",
      "target": "qdrant_vector_db",
      "evidence": "0.0.0.0:6333",
      "severity_hint": "high"
    }
  ]
}
```

---

## 16. Components to Detect

Epic 1 應優先偵測這些元件：

| Component Type | Examples | Priority |
|---|---|---|
| LLM Runtime | Ollama, llama.cpp server, vLLM | P0 |
| Vector DB | Qdrant, Chroma, Weaviate, FAISS folder | P0 |
| App / Agent API | FastAPI, Flask, Open WebUI, custom backend | P0 |
| Docker Services | docker-compose services, exposed ports | P0 |
| Config Files | `.env`, `.yaml`, `.json`, `.toml` | P0 |
| Agent Tools | shell, email, database, external API tools | P1 |
| Data Sources | PDF, Excel, Markdown, internal docs | P1 |
| External Endpoints | OpenAI, Anthropic, Azure OpenAI, custom remote APIs | P1 |
| RAG Pipeline Hints | retriever, embedding, reranker, collection name | P1 |

---

## 17. Files to Scan

Epic 1 可以從以下檔案開始掃描：

| File / Pattern | 用途 |
|---|---|
| `.env` | 找 endpoint、provider、API key name、runtime setting |
| `.env.example` | 推測系統需要哪些設定 |
| `docker-compose.yml` | 找 services、ports、volumes、env |
| `Dockerfile` | 判斷 app runtime 與啟動方式 |
| `requirements.txt` | 判斷 Python dependencies |
| `pyproject.toml` | 判斷 Python dependencies 與 project metadata |
| `package.json` | 判斷前端或 Node.js agent service |
| `config.yaml` / `config.yml` | 找模型、retriever、endpoint、tool config |
| `*.json` config | 找 agent / RAG 設定 |
| `README.md` | 補充辨識專案用途與啟動方式 |

---

## 18. Minimal Detection Rules

第一版不要追求完美。  
先做可解釋、可維護的 rule-based detection。

| 偵測目標 | 最小規則 |
|---|---|
| Ollama | 出現 `ollama`、`11434`、`OLLAMA_HOST` |
| Qdrant | 出現 `qdrant`、`6333`、`QDRANT_URL` |
| Open WebUI | 出現 `open-webui`、`3000`、`8080` |
| FastAPI | 出現 `fastapi`、`uvicorn` |
| Flask | 出現 `flask` |
| OpenAI API | 出現 `OPENAI_API_KEY`、`api.openai.com` |
| Anthropic API | 出現 `ANTHROPIC_API_KEY`、`anthropic.com` |
| Azure OpenAI | 出現 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_API_KEY` |
| LangChain | 出現 `langchain` |
| AutoGen | 出現 `autogen` |
| LlamaIndex | 出現 `llama-index` |
| RAG | 出現 `retriever`、`embedding`、`vectorstore`、`collection` |
| Agent Tool | 出現 `tools`、`tool_calls`、`function_calling`、`shell`、`send_email` |

---

## 19. Epic 1 Output

Epic 1 至少要輸出三種成果：machine-readable map、人類可讀 summary，以及真正可互動的 System Map GUI。

### 19.1 JSON Output

給後續 checker 使用：

```text
kai-mind-map.json
```

內容包含：

- project metadata
- detected components
- connections
- endpoints
- config evidence
- risk hints
- confidence score

---

### 19.2 Markdown Summary

給人閱讀：

```text
kai-mind-map.md
```

內容包含：

- 系統總覽
- 偵測到的元件
- 可能的資料流
- 可能的外部 endpoint
- 可能的 network exposure
- 後續建議檢查項目

---

### 19.3 Interactive System Map GUI

給使用者探索系統結構：

```text
Local System Map Viewer
```

最小功能包含：

- 載入 `kai-mind-map.json`
- 以 node / edge graph 顯示 AI 系統
- 使用不同視覺樣式區分 LLM runtime、vector DB、App API、config、external endpoint、network exposure、agent tool
- 點選 node 顯示 detail panel
- 點選 edge 顯示 connection reason
- 顯示 evidence、source、confidence
- 支援 filter：component type、external endpoint、network exposure、agent tool、risk hint
- 支援基本 zoom、pan、drag
- secret-like value 必須遮罩

Epic 1 的 GUI 不是完整 dashboard，也不是圖編輯器。  
它的目標是讓使用者真的可以互動探索 AI System Map，而不是只看到靜態文字或截圖。

---

## 20. Example Human-readable Output

```markdown
# AI System Map

## Detected Components

| Type | Name | Source | Endpoint | Confidence |
|---|---|---|---|---|
| LLM Runtime | Ollama | docker-compose.yml | http://localhost:11434 | High |
| Vector DB | Qdrant | docker-compose.yml | http://localhost:6333 | High |
| App API | FastAPI | requirements.txt | http://localhost:8000 | Medium |

## Possible Connections

| From | To | Reason |
|---|---|---|
| FastAPI | Ollama | LLM generation |
| FastAPI | Qdrant | RAG retrieval |

## Risk Hints

| Type | Target | Evidence | Severity Hint |
|---|---|---|---|
| Network Exposure | Qdrant | 0.0.0.0:6333 | High |
| External Endpoint | OpenAI | OPENAI_API_KEY exists | Medium |
```

---

## 21. Suggested Sub-issues for Epic 1

### Parent Issue

```text
Epic 1: System Map Builder
```

### Sub-issues

| Issue | Title | Priority | Purpose |
|---|---|---|---|
| 1.1 | Define AI System Map schema | P0 | 定義後續所有 checker 共用的資料格式 |
| 1.2 | Implement project folder scanner | P0 | 掃描 repo / project folder 內的設定檔 |
| 1.3 | Parse docker-compose services | P0 | 讀取 services、ports、volumes、env |
| 1.4 | Detect core AI components | P0 | 偵測 Ollama、Qdrant、FastAPI、Open WebUI |
| 1.5 | Detect config endpoints and providers | P0 | 找出 local / external endpoint |
| 1.6 | Generate system map JSON report | P0 | 輸出給後續 checker 使用的 JSON |
| 1.7 | Generate human-readable Markdown report | P1 | 輸出給使用者閱讀的 Markdown summary |
| 1.8 | Add confidence score and evidence field | P1 | 讓每個判斷都有可追溯證據 |
| 1.9 | Build interactive System Map GUI | P0 | 載入 map JSON，提供可互動的 node / edge 視覺化 |
| 1.10 | Add GUI evidence panel and filters | P0 | 支援點選 node / edge、查看 evidence、篩選風險訊號 |
| 1.11 | Add basic CLI command | P1 | 支援 `kai-mind map ./project` 與啟動 viewer |
| 1.12 | Prepare sample projects for testing | P1 | 建立測試用 local RAG / Agent 專案樣本 |

---

## 22. Parent Issue Draft

```markdown
# Epic 1: System Map Builder

## Objective

建立 KAI-Mind 的第一個核心模組：System Map Builder。

此模組負責讀取一套 AI Agent / RAG 系統的 repo、設定檔與執行中服務資訊，產生一份結構化的 AI System Map，讓後續 Runtime Readiness、Privacy & Exposure、Agent Tool Risk、RAG Readiness 與 Release Gate 模組可以基於同一份系統地圖進行檢查。

Epic 1 完成後，使用者不應該只拿到 JSON 或 Markdown。  
使用者應該可以打開一個互動式 GUI，實際看到 AI 系統的 node / edge map，並能點選元件、查看 evidence、篩選 endpoint / exposure / tool 等訊號。

## Why

KAI-Mind 的後續檢查都需要先知道系統中有哪些元件、服務、endpoint、資料來源與可能的風險位置。

如果沒有 System Map，後續 checker 會變成零散掃描，無法形成完整診斷。

## Scope

### In Scope

- 掃描 project folder
- 讀取 `.env`、config、Docker 相關檔案
- 解析 `docker-compose.yml`
- 偵測 Ollama、Qdrant、FastAPI、Open WebUI 等核心元件
- 偵測 local endpoint 與 external endpoint
- 建立 AI System Map JSON
- 建立 human-readable Markdown summary
- 建立互動式 System Map GUI
- GUI 可以載入 map JSON 並顯示 node / edge graph
- GUI 可以查看 selected node / edge 的 evidence 與 confidence
- GUI 可以依 component type、external endpoint、network exposure、agent tool、risk hint 篩選
- 為每個偵測結果保留 evidence 與 confidence score

### Out of Scope

- 不做完整 runtime health check
- 不做完整 security scan
- 不做 Agent tool policy 判斷
- 不做 RAG answer groundedness 評估
- 不做 READY / RISKY / NOT_READY 最終判斷
- 不做完整 readiness dashboard
- 不做手動 graph 編輯器

## Deliverables

- `kai-mind-map.json`
- `kai-mind-map.md`
- interactive System Map GUI
- `kai-mind map <project_path>` CLI prototype
- `kai-mind viewer <map_json>` viewer prototype
- 最小可測試 sample project
- System Map schema 文件

## Acceptance Criteria

- 可以輸入一個 project folder
- 可以找出至少以下元件：
  - Ollama
  - Qdrant
  - FastAPI / Flask / Open WebUI
  - `.env`
  - `docker-compose.yml`
- 可以輸出 JSON 格式的 AI System Map
- 可以輸出 Markdown 格式的人類可讀 summary
- 可以開啟互動式 GUI 查看 AI System Map
- GUI 可以點選 node / edge 並顯示 evidence
- GUI 可以用 filter 隱藏或顯示 external endpoints、network exposure、agent tools、risk hints
- 每個 detected component 都必須包含：
  - type
  - name
  - source
  - evidence
  - confidence
- 不得直接顯示完整 API key 或 secret value
- 若無法判斷，必須標示 `unknown`，不能假裝知道

## Expected Command

```bash
kai-mind map ./example-project
kai-mind viewer outputs/kai-mind-map.json
```

## Expected Output

```text
outputs/
├─ kai-mind-map.json
├─ kai-mind-map.md
└─ interactive System Map GUI
```
```

---

## 23. Epic 1 Success Criteria

Epic 1 完成時，應該可以回答這些問題：

| 問題 | 是否應可回答 |
|---|---|
| 這個專案有沒有使用 Ollama？ | 是 |
| 這個專案有沒有使用 Qdrant？ | 是 |
| App API 可能在哪裡啟動？ | 是 |
| 哪些設定檔包含 endpoint？ | 是 |
| 哪些服務可能是 Docker 啟動？ | 是 |
| 哪些服務可能暴露 port？ | 初步提示即可 |
| 是否存在外部 AI provider 設定？ | 初步提示即可 |
| RAG collection 是否 ready？ | 否，留給 Epic 5 |
| Qdrant 是否安全？ | 否，留給 Epic 3 |
| Runtime 是否真的健康？ | 否，留給 Epic 2 |
| 系統是否可以 release？ | 否，留給 Epic 6 |
| 使用者是否可以用 GUI 互動探索系統地圖？ | 是 |
| 使用者是否可以點選節點或連線查看 evidence？ | 是 |
| 使用者是否可以篩選 external endpoint、network exposure、agent tool？ | 是 |

---

## 24. Recommended Development Order for Epic 1

| Order | Task | Reason |
|---|---|---|
| 1 | Define System Map schema | 先定義資料格式，避免後面 scanner 各寫各的 |
| 2 | Build folder scanner | 先能讀 project folder |
| 3 | Parse config files | `.env`、yaml、json 是 endpoint 與 provider 的主要來源 |
| 4 | Parse docker-compose | 很多 local AI stack 會靠 Docker 啟動 |
| 5 | Detect core components | 先支援 Ollama、Qdrant、FastAPI、Open WebUI |
| 6 | Add evidence / confidence | 避免工具輸出不可驗證的結論 |
| 7 | Generate JSON report | 給後續 checker 使用 |
| 8 | Generate Markdown report | 給使用者閱讀 |
| 9 | Build interactive map viewer | 讓 Epic 1 完成後真的有可視化 GUI |
| 10 | Add evidence panel and filters | 讓 GUI 不只是圖，而是可追溯診斷工具 |
| 11 | Add CLI command | 讓工程流程可以開始串起來 |
| 12 | Prepare sample projects | 確保每次修改後都能測試 |

---

## 25. Strict Notes

Epic 1 最容易犯的錯是範圍失控。

不要一開始就做：

- 完整 dashboard
- 完整資安掃描
- 完整 RAG evaluator
- 完整 CI/CD gate
- 完整 Agent policy engine
- 手動 graph 編輯器

第一階段只要做到：

> 能把 AI Agent / RAG 專案整理成可信、可追溯、可被後續模組使用，並且可被使用者用 GUI 互動探索的 AI System Map。

這就已經足夠成為 KAI-Mind 的基礎。

---

## 26. Final MVP Definition for Epic 1

Epic 1 的 MVP 定義如下：

> 使用者輸入一個 AI Agent / RAG 專案資料夾後，KAI-Mind 可以掃描 repo、config 與 Docker 設定，偵測出核心 AI 元件、endpoint、資料流與風險提示，輸出一份 JSON 版與 Markdown 版 AI System Map，並提供一個真的可互動的 GUI 介面讓使用者探索這張 map。

最小可接受結果：

```text
Input:
  ./user-ai-project

Command:
  kai-mind map ./user-ai-project

Output:
  outputs/kai-mind-map.json
  outputs/kai-mind-map.md
  interactive System Map GUI
```

核心價值：

> 先讓 KAI-Mind 看懂一套 AI 系統，並讓使用者可以透過互動式 GUI 看懂這套系統；後面才有資格判斷它是否 ready。
