# Epic 1 規格：RAG System Map Builder

> 狀態：規格概述
> 詳細實作契約：`docs/design/epic1.md`

## 目標

Epic 1 讓 KAI-Mind 可以掃描既有 RAG project folder，並產出穩定、evidence-based 的 `ai_system_map.json`。

這份 output 應該讓後續 epics 可以回答：

- 系統有哪些 components？
- 哪些檔案或設定證明它們存在？
- 偵測到哪些 endpoints？
- 哪些風險需要後續檢查？
- 哪些 RAG slots 缺失或尚未設定？

Epic 1 不判斷 release readiness。

## 使用者故事

作為準備 review local RAG project 的開發者，我可以執行：

```bash
kai-mind map ./my-rag-project
```

並得到：

```text
outputs/
  ai_system_map.json
  ai_system_map.md
```

JSON 給工具與後續 checks 使用，Markdown 給人閱讀。

## 包含範圍

- Project folder discovery。
- `.env`、config、Docker Compose、dependency manifest 與 bounded source scan。
- RAG-oriented component slots。
- Endpoint detection。
- Evidence-backed risk hints。
- Secret-safe output。
- Synthetic fixtures and contract tests。

## 不包含範圍

- Runtime health checks。
- 完整 security scanning。
- Agent tool policy。
- RAG answer groundedness。
- CI gate verdicts。
- 預設 query trace / replay。
- 完整 interactive dashboard。

## RAG Slots

初始 `rag-core-v1` slots：

- data source
- document loader
- chunking
- embedding model
- vector store
- app API or orchestrator
- query processing
- retriever
- prompt builder
- LLM
- citation or response composer
- guardrails
- observability

每個 slot 可以是：

- `detected`
- `missing`
- `not_configured`
- `not_applicable`

Detected slots 必須有 evidence。

## 必要 Map Concepts

`ai-system-map/v1` 應包含：

- project metadata
- selected reference architecture
- components by slot
- component instances
- endpoints
- flows and edges
- evidence
- risk hints
- recommended next checks

Map 不使用 `confidence`。如果 evidence 弱或不存在，應直接用 status 表達。

## Privacy Rules

- Scanner read-only。
- Secret-like values 在 output 前遮罩。
- Full secret values 不得出現在 JSON、Markdown、logs、snapshots 或 UI。
- Raw retrieved chunks 不屬於 default map contract。
- External endpoints 只是後續檢查 hints，不是資料外洩證明。

## Fixture 策略

使用 synthetic fixtures，不 vendoring public repositories。

初始 fixtures：

- basic Qdrant + Ollama RAG stack
- external OpenAI provider signal
- malformed config for partial map behavior
- minimal project with missing RAG slots

Public repos 可以協助設計 fixture patterns，但 tests 只能跑本地 fixtures。

## 驗收標準

- `kai-mind map <project_path>` 會建立 valid `ai_system_map.json`。
- JSON 通過 `ai-system-map/v1` validation。
- Markdown summary 由同一份 map 產生。
- Malformed config 產生 partial map 與 parse-error evidence。
- Missing project 產生 `map-error.md` 並以 non-zero exit code 結束。
- Detected components 包含 evidence。
- 輸出使用 project-relative POSIX paths。
- 輸出不包含完整 secret。
- Tests 覆蓋 schema、fixtures、masking、path normalization 與 partial failure。

## 後續工作

- Schema 穩定後做 viewer prototype。
- Query trace 在 privacy 與 side-effect boundaries 明確後，作為 explicit opt-in 功能。
- Epic 2 做 runtime readiness checks。
- Epic 3 做 privacy and exposure guard。
