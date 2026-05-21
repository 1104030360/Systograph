# Epic 1 設計契約

> 狀態：設計契約
> 範圍：Epic 1 - RAG System Map Builder
> 實作依據：本文件

## 1. 目的

Epic 1 要建立 KAI-Mind 的第一個可用能力：掃描既有 RAG project folder，並產出穩定、可追溯 evidence 的 `ai_system_map.json`。

這份 map 是後續 Runtime Readiness、Privacy & Exposure、RAG Knowledge Trust、Release Report 與 CI Gate 的共同事實層。Epic 1 不判斷系統是否 ready，而是說清楚偵測到什麼、證據在哪裡，以及後續應該檢查哪些項目。

## 2. MVP 範圍

### 包含

- 以 read-only 方式掃描 project folder。
- 探索 config、Docker Compose、dependency manifests、部分 source files 與 README/documentation hints。
- 產生 deterministic raw scanner signals。
- 透過 normalization layer 轉換成 RAG-oriented System Map。
- 定義 `ai-system-map/v1` JSON contract。
- 產出人類可讀的 Markdown summary。
- JSON、Markdown、logs、fixtures、snapshots 都必須 secret-safe。
- 使用本地 synthetic fixtures 測試，不依賴 live external repositories。

### 不包含

- Runtime health checks。
- 深入 port security 判斷。
- 深入 secret scanning。
- Agent tool policy evaluation。
- RAG answer groundedness evaluation。
- `READY` / `RISKY` / `NOT_READY` verdict。
- 預設 query trace / replay。
- 完整 interactive dashboard。

Query trace 可以作為後續 explicit opt-in workflow，例如 `kai-mind trace --endpoint ...`。它不應該是第一版 map builder 的必要條件，因為它會呼叫使用者正在執行的服務，可能觸發 side effects、外部 LLM、API quota 使用或資料揭露。

## 3. 架構

```text
Project folder
  -> File discovery
  -> Format-specific parsers
  -> Raw scan signals
  -> Normalization service
  -> AI System Map validator
  -> JSON + Markdown artifacts
```

核心規則：parser 不直接輸出最終產品判斷。Parser 只產生 raw signals 與 evidence，normalization layer 再把 signals 轉成穩定 domain concepts。

建議未來模組邊界：

```text
src/kai_mind/
  core/
    models/
    providers/
    services/
    templates/
  cli/
tests/
  fixtures/rag_projects/
  contracts/
  core/
  cli/
schemas/
```

## 4. Provider 職責

Provider 負責和檔案、parser 或底層來源互動。對被掃描的 project 必須維持 read-only。

| Provider | 職責 | 輸出 |
|---|---|---|
| `FilesystemProvider` | 建立有限制的 file inventory，讀取 candidate files | file metadata、candidate contents |
| `ConfigParseProvider` | 解析 `.env`、YAML、JSON、TOML-like config | key/value signals、parse issues |
| `DockerComposeProvider` | 解析 services、images、ports、env、volumes | service and endpoint signals |
| `DependencyManifestProvider` | 解析 `requirements.txt`、`pyproject.toml`、`package.json` | dependency signals |
| `CodePatternProvider` | 有界限地掃描明確 RAG patterns | code pattern signals |
| `OutputArtifactProvider` | 建立 output directory 並寫出 artifacts | artifact paths |

Provider failure 必須結構化。Malformed config 不應中止整個 scan；它應該產生 parse-error evidence，並允許 partial map。Project root 不存在或不可讀才是 fatal error。

## 5. Service 職責

| Service | 職責 |
|---|---|
| `MapBuildService` | `kai-mind map` 的 top-level orchestration |
| `ProjectScanService` | 協調 providers 並收集 raw signals |
| `RagTemplateService` | 載入 `rag-core-v1` slot 與 flow template |
| `ComponentDetectionService` | 將 raw signals 映射到 component slots 與 instances |
| `EndpointDetectionService` | 正規化 local / external endpoint signals |
| `RiskHintService` | 產生 evidence-backed hints，不產生最終安全結論 |
| `SystemMapNormalizeService` | merge、dedupe 並組裝 map |
| `SystemMapValidationService` | 驗證 schema invariants |
| `MarkdownSummaryService` | 從已驗證 map 產生人類可讀 summary |
| `SecretMaskingService` | 套用唯一 masking policy |

Service 規則：

- Detected components 必須有 evidence。
- Map 不得包含 `confidence` 欄位。
- 缺少 evidence 時，slot 應是 `missing`、`not_configured` 或 `not_applicable`，不能猜測。
- Epic 1 無法證明真實 exposure severity 時，risk hint 必須標示 uncertainty。
- Report generation 只能讀 normalized map，不得重新掃描檔案。

## 6. `ai-system-map/v1` 契約

必要 top-level fields：

- `schema_version`
- `system_type`
- `classification`
- `project`
- `reference_architecture`
- `components_by_slot`
- `endpoints`
- `flows`
- `risk_hints`
- `recommended_next_checks`

重要 invariants：

- `schema_version` 是 `ai-system-map/v1`。
- Epic 1 的 `system_type` 是 `rag`。
- `classification.selected_template` 是 `rag-core-v1`。
- Component slot status 必須是 `detected`、`missing`、`not_configured`、`not_applicable` 之一。
- `required_for_rag` 由掃描結果與 template rules 推導，不是 universal constant。
- Endpoint type 是 `local` 或 `external`。
- Risk hint target type 是 `component_instance`、`endpoint` 或 `component_slot`。
- Evidence file path 使用 project-relative POSIX path。
- Secret-like values 在 serialization 前必須已遮罩。

實作時應新增 `schemas/ai-system-map.v1.schema.json` 與 contract tests，再把 schema 視為穩定 contract。

## 7. Evidence 模型

每個有意義的輸出都應該能追溯 evidence。

Evidence 建議包含：

- `id`
- `kind`
- `file`
- `path`
- `value`
- `line_start` / `line_end`
- `masked`
- `parser`

不要保存完整 secret value。預設也不要保存 raw retrieved chunks。RAG chunks 可能包含內部文件或 PII，不一定會被 secret masking 規則擋到。若未來 trace work 需要 chunk details，應使用 source IDs、hashes、counts、metadata summaries，或 explicit opt-in 的 redacted excerpts。

## 8. CLI 契約

第一版 command：

```bash
kai-mind map <project_path> [--output outputs] [--system-type rag]
```

預期行為：

- 驗證 `project_path` 存在且可讀。
- 若 invalid，寫出 `map-error.md` 並以 non-zero exit code 結束。
- 建立 output directory，不覆寫既有 artifacts。
- 解析錯誤時繼續產生 partial map，並包含 parse-error evidence。
- 寫出 success artifacts 前先 validate JSON。
- 寫出 `ai_system_map.json`。
- 寫出 `ai_system_map.md`。

`kai-mind viewer <map_json>` 可以作為後續規劃。Viewer 只能載入 map JSON，不得重新掃描 project folder 或創造 component。

## 9. Fixture 策略

公開 repositories 只作為研究輸入，不應 vendoring 第三方 repo 到本 repo。

建立 synthetic fixtures，混合多個參考來源的 patterns：

- `basic_qdrant_ollama_rag`：Docker Compose app、Ollama、Qdrant。
- `openai_external_provider_rag`：external provider 與 API key name signals。
- `malformed_config_rag`：invalid YAML 或 Docker Compose，用來測 partial scan。
- `missing_slots_rag`：minimal project，用來測 missing slot status。

Fixtures 不得包含真實 secrets。

## 10. 測試策略

實作被視為健康前，至少需要：

- Generated map schema validation。
- 至少一個 basic RAG fixture 的 golden output。
- JSON、Markdown、logs、snapshots 的 secret masking test。
- Windows/macOS path normalization test。
- Malformed config partial-map test。
- Missing project error artifact test。
- No `confidence` field test。
- Detected component requires evidence test。

## 11. Viewer 後續範圍

Viewer 很有用，但不應該反過來定義 core contract。Viewer 是 `ai_system_map.json` 的 projection。

未來實作 viewer 時的規則：

- 載入 validated `ai_system_map.json`。
- 不掃描 project folder。
- 不創造 map 中不存在的 components。
- 顯示 map 裡的 evidence 與 risk hints。
- Filters 保留完整 graph，只高亮 matched items。
- Invalid map input 顯示 error state，不顯示空白 graph。

## 12. Delivery Order

| 里程碑 | 交付物 | 說明 |
|---|---|---|
| M1 | Schema and domain models | UI work 前先鎖定 `ai-system-map/v1` |
| M2 | Synthetic fixtures | 不依賴 external repo |
| M3 | File/config/compose/dependency providers | Read-only and bounded |
| M4 | Normalization and risk hints | Evidence-backed，無 `confidence` |
| M5 | CLI and artifacts | JSON + Markdown |
| M6 | Contract and fixture tests | 下一個 epic 前必須完成 |
| M7 | Viewer prototype | 契約穩定後再做 |

## 13. Work Split

Timmy 負責 fact layer：

- schema
- scanner providers
- normalization
- evidence
- risk hints
- CLI map command
- fixture and contract tests

Bo-Han 在 schema 穩定後負責 presentation layer：

- viewer loading
- graph view model
- detail panel
- highlight-only filters
- invalid map state
- UI tests

共同 interface：

- `ai-system-map/v1`
- sample `ai_system_map.json` files
- evidence and risk hint shape

## 14. 待釐清問題

- 第一版實作語言要用 Python 還是 TypeScript？
- File scanner 的 ignore rules 應該包含哪些？
- `required_for_rag` 要寫在 template rules，還是完全從 detected flows 推導？
- 第一版 JSON schema path 與 migration policy 要怎麼定？
- 未來重新討論 query trace 時，需要哪些 opt-in UX 與 privacy boundaries？
