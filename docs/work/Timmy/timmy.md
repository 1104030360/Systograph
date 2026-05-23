# Timmy 工作事項 - Epic 1 Core Scanner / Schema / CLI

> 對應角色：工程師 A  
> 主要範圍：Core scanner、schema、CLI、evidence、JSON / Markdown artifact  
> 參考設計：`docs/design/epic1.md`

## 1. 工作目標

Timmy 負責建立 Epic 1 的「事實層」。也就是讓 KAI-Mind 能 read-only 掃描一個既有 RAG project folder，依照 `rag-core-v1` reference architecture 產生可信、可測試、可追溯 evidence 的 `ai_system_map.json` 與 `ai_system_map.md`。

這一側的重點不是把畫面做漂亮，而是確保：

- scanner 不會修改被掃描專案。
- 每個 detected component 都有 evidence。
- 沒有 evidence 的 slot 不得假裝 detected。
- JSON contract 穩定且可被 Bo-Han 的 viewer 使用。
- full secret 不會出現在 JSON、Markdown、logs、test snapshots。

## 2. 責任邊界

### Timmy 負責

- `rag-core-v1` reference architecture template。
- `ai-system-map/v1` schema 與 domain model。
- Provider-Service core scanner 架構。
- filesystem / config / Docker compose / dependency / code pattern 掃描。
- RAG component slot detection。
- endpoint detection。
- risk hint 產生。
- secret masking。
- output artifact policy。
- `kai-mind map <project_path>` CLI。
- `ai_system_map.json` 與 `ai_system_map.md`。
- scanner / CLI / schema / contract tests。

### Timmy 不負責

- 不負責 viewer 的視覺設計。
- 不負責 graph interaction、zoom、pan、drag。
- 不負責 query trace replay UI。
- 不在 viewer 層重新定義資料模型。
- 不把 LLM-generated summary 當作 scanner source of truth。

## 3. 必須交付的檔案或模組

實際路徑可依最終技術棧調整，但責任邊界應維持一致。

| 類別 | 建議路徑 | 說明 |
|---|---|---|
| Core models | `src/kai_mind/core/models/` | `RagSystemMap`、`ComponentSlot`、`Evidence`、`Endpoint`、`RiskHint`、`QueryTraceEvent` 等 DTO |
| Providers | `src/kai_mind/core/providers/` | filesystem、config、Docker compose、dependency、code pattern providers |
| Services | `src/kai_mind/core/services/` | map build、scan orchestration、component detection、normalization、validation、Markdown generation |
| Templates | `src/kai_mind/core/templates/` | `rag-core-v1` component slots 與 flows |
| CLI | `src/kai_mind/cli/` | `kai-mind map <project_path>` |
| Schema | `schemas/ai-system-map.v1.schema.json` | JSON schema contract |
| Fixtures | `tests/fixtures/rag_projects/` | sample RAG projects |
| Tests | `tests/contracts/`, `tests/core/`, `tests/cli/` | schema、scanner、CLI、secret masking tests |

## 4. 主要工作項目

### A1. 定義 `rag-core-v1` reference architecture

- [ ] 定義 component slots：
  - `data_sources`
  - `document_loader`
  - `chunking`
  - `embedding_model`
  - `vector_store`
  - `app_api_or_orchestrator`
  - `query_processing`
  - `retriever`
  - `prompt_builder`
  - `llm`
  - `citation_or_response_composer`
  - `guardrails`
  - `observability`
- [ ] 定義 `indexing` flow。
- [ ] 定義 `query_answer` flow。
- [ ] 定義每個 slot 的基本說明、常見 evidence signals、是否通常為 RAG 必要元件。
- [ ] 注意：`required_for_rag` 不是固定常數，必須由 scanner 根據 project evidence 判定。

驗收條件：

- `rag-core-v1` 可被 scanner 載入。
- Bo-Han 可以用 template 產生 graph node / edge 初始 view model。
- template 不含任何 project-specific 假設。

### A2. 定義 `ai-system-map/v1` schema 與 domain model

- [ ] 建立 `RagSystemMap` top-level contract。
- [ ] 支援必要欄位：
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
  - `query_trace_events`
- [ ] 定義 enum：
  - slot status: `detected`、`missing`、`not_configured`、`not_applicable`
  - endpoint type: `local`、`external`
  - risk target type: `component_instance`、`endpoint`、`component_slot`
- [ ] 禁止 `confidence` 欄位。
- [ ] 建立 JSON schema validation。

驗收條件：

- invalid status 會被 schema / validation 擋下。
- detected slot 沒有 evidence 時會 validation fail。
- schema 能支援 Bo-Han 的 viewer detail panel 與 query trace replay。

### A3. 建立 sample RAG fixtures

- [ ] `basic_qdrant_ollama_rag`：包含 Qdrant、Ollama、Python RAG code。
- [ ] `openai_external_provider_rag`：包含 OpenAI embeddings / API key name / external endpoint signal。
- [ ] `malformed_config_rag`：包含 invalid YAML 或 docker-compose。
- [ ] `missing_slots_rag`：只有 README 或 data folder，測試 missing slot。
- [ ] `viewer_invalid_map`：給 Bo-Han 測 viewer invalid map error state。

驗收條件：

- 每個 fixture 都能說明它要測什麼。
- fixture 不包含真實 secret。
- Bo-Han 可以直接使用 fixture map 開發 viewer。

### A4. 實作 read-only project scanner providers

- [ ] `FilesystemProvider`：建立 file inventory、過濾 noisy files、支援 POSIX relative path。
- [ ] `ConfigParseProvider`：解析 `.env`、`.env.example`、YAML、JSON、TOML-like config。
- [ ] `DockerComposeProvider`：解析 services、ports、volumes、env、image。
- [ ] `DependencyManifestProvider`：解析 `requirements.txt`、`pyproject.toml`、`package.json`。
- [ ] `CodePatternProvider`：掃描 bounded source files 中的 RAG signals。
- [ ] provider failures 產生 structured issue，不直接中止整個 scan，除非 project root 不可讀。

驗收條件：

- project root 不存在或不可讀時，輸出 `map-error.md`，不輸出正常 map。
- 單一 config 解析失敗時，仍產生 partial map。
- evidence file path 一律是 project-relative POSIX path。

### A5. 實作 component detection、endpoint detection、risk hints

- [ ] 根據 scan facts 映射 RAG component slots。
- [ ] 偵測 data source、chunking、embedding model、vector store、retriever、LLM、app API / orchestrator。
- [ ] 偵測 local / external endpoint。
- [ ] 針對 Docker published port 產生 network exposure risk hint。
- [ ] 針對 external provider signal 產生 external endpoint / provider risk hint。
- [ ] 針對 parse error 產生 parse_error evidence / risk hint。
- [ ] 每個 risk hint 必須包含：
  - `target`
  - `target_type`
  - `evidence_id`
  - `rule_id`
  - `rationale`
  - `uncertainty`
  - `severity_hint`

驗收條件：

- Qdrant compose fixture 能產生 `vector_store` detected component。
- OpenAI fixture 能產生 external provider / endpoint hint。
- malformed compose fixture 能產生 partial map 與 parse_error risk hint。

### A6. 實作 secret masking

- [ ] 建立唯一的 `SecretMaskingService`。
- [ ] secret-like value 只能顯示前後少量字元，中間遮罩。
- [ ] JSON、Markdown、logs、test snapshots 都必須使用同一個 masking policy。
- [ ] 掃描 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`AZURE_OPENAI_ENDPOINT` 等 key name 時，不輸出完整 value。

驗收條件：

- 測試 fixture 中的 secret-like value 不會完整出現在輸出。
- snapshot test 會檢查 full secret leakage。

### A7. 實作 `kai-mind map <project_path>`

- [ ] 驗證 project path。
- [ ] 建立 output directory。
- [ ] 若 `outputs/` 已有既有 artifact，建立 timestamped output directory。
- [ ] 執行 scanner。
- [ ] validate normalized map。
- [ ] 輸出 `ai_system_map.json`。
- [ ] 輸出 `ai_system_map.md`。
- [ ] project folder 不存在或不可讀時輸出 `map-error.md`。

驗收條件：

- `kai-mind map ./fixtures/basic-rag` 產出 JSON 與 Markdown。
- output directory 既有檔案不會被覆寫。
- missing project 不會產生正常 map。

### A8. 交付給 Bo-Han 的 viewer contract

- [ ] 提供至少 3 份可用的 sample `ai_system_map.json`：
  - 正常 RAG map。
  - missing slots map。
  - 含 risk hints / external endpoint map。
- [ ] 明確定義 graph view model 需要使用的欄位：
  - node id
  - slot
  - status
  - instance name
  - evidence refs
  - risk hint refs
  - edge relationship
- [ ] 與 Bo-Han 對齊 `QueryTraceEvent` 欄位。

驗收條件：

- Bo-Han 不需要重新掃描 repo，也能完成 viewer。
- Bo-Han 不需要猜測 component 是否存在。

## 5. 測試責任

Timmy 主要負責：

- unit tests：models、masking、provider parsing、component detection。
- integration tests：`kai-mind map` full flow。
- contract tests：JSON schema、golden snapshots、no full secret。
- CLI tests：missing project、existing outputs、partial parse failure。

最低測試清單：

- [ ] path normalization across Windows/macOS samples。
- [ ] secret masker prefix/suffix/middle mask。
- [ ] detected component 必須有 evidence。
- [ ] `confidence` 欄位不得出現在 JSON。
- [ ] malformed compose 仍輸出 partial map。
- [ ] output directory 已存在時建立 timestamped directory。

## 6. 與 Bo-Han 的協作節點

| 時點 | Timmy 交付 | Bo-Han 依賴 |
|---|---|---|
| 第 1 次同步 | `rag-core-v1` slots / flows 草案 | 開始 graph layout 與 node type 設計 |
| 第 2 次同步 | `ai-system-map/v1` schema 草案 | 建立 graph view model |
| 第 3 次同步 | 3 份 sample `ai_system_map.json` | 開始 viewer load / detail panel |
| 第 4 次同步 | endpoint detection contract | 開始 query trace replay |
| 第 5 次同步 | final schema validation rules | 補齊 viewer error state 與 tests |

## 7. Code Review 重點

Timmy 需要特別檢查 Bo-Han 的 PR：

- viewer 是否重新掃描檔案。
- viewer 是否自行推論 JSON 中沒有的 component。
- viewer 是否顯示未遮罩 secret。
- query trace UI 是否在 endpoint missing 時仍送出 query。
- graph detail panel 是否能追溯回 evidence。

Bo-Han 需要特別檢查 Timmy 的 PR：

- JSON 是否有足夠 label / relationship / evidence 支援使用者理解。
- missing / not_configured / not_applicable 是否能在 UI 上清楚呈現。
- risk hint 的 `rationale` 與 `uncertainty` 是否足夠可讀。

## 8. 完成定義

Timmy 的 Epic 1 工作完成標準：

- [ ] `kai-mind map <project_path>` 可產出 valid `ai_system_map.json`。
- [ ] `ai_system_map.json` 通過 `ai-system-map/v1` schema validation。
- [ ] `ai_system_map.md` 包含設計文件要求的 summary sections。
- [ ] scanner 對 malformed config 能產生 partial map。
- [ ] 所有 detected components 都有 evidence。
- [ ] no full secret 出現在 JSON、Markdown、logs、snapshots。
- [ ] Bo-Han 可直接用 Timmy 的 sample maps 完成 viewer，不需要自行掃描 repo。
