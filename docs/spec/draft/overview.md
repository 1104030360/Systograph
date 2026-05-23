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

## 11. Related Drafts

- [Epic 1 — RAG System Map Builder](epic1.md)
