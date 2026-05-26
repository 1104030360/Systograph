# Epic 1 Scan Pipeline Research

> Status: Research + Backend Design Note  
> Scope: Stages 1-7 from `Precondition check` to `Normalize and validate`  
> Source Backend Design: `docs/work/Timmy/design/epic1-backend-design.md`  
> Output: `docs/work/Timmy/design/epic1-scan-pipeline-research.md`

## 1. 這份文件回答什麼

這份文件專門討論 Epic 1 後端最重要的掃描管線：

```text
1. Precondition check
2. File inventory
3. Deterministic providers
4. Raw scan facts
5. RAG slot mapping
6. Endpoint / Risk / Flow derivation
7. Normalize and validate
```

每一段都回答三件事：

- 目前有哪些現有工具或開源做法可以 deterministic 使用。
- 哪些判斷需要 AI 輔助。
- 外部專案可以借鑑什麼，以及對 KAI-Mind 的設計關聯。

核心結論：

```text
AI 不應該參與 1、2、4、7 的 canonical decision。
AI 可以輔助 5、6 的「不確定 mapping / 使用者說明 / rationale wording」。
第 3 段大多應用 parser、static analysis、manifest scanner；AI 只可幫助產生 rule proposal。
```

## 2. 總覽判斷表

| Stage | 主要目的 | 現有工具可直接做嗎 | AI 是否需要 | Canonical truth |
|---|---|---:|---:|---|
| 1. Precondition check | 確認 project path、output policy、scan limits | 是 | 不需要 | filesystem / CLI args |
| 2. File inventory | 找出要掃哪些檔案、排除噪音 | 是 | 不需要 | git/filesystem inventory |
| 3. Deterministic providers | parse config、Docker、dependencies、code patterns | 大多可以 | 少量輔助 rule proposal | parsers / rule matches |
| 4. Raw scan facts | 統一 facts、evidence、parse issues | 是 | 不需要 | structured facts |
| 5. RAG slot mapping | facts 對到 `rag-core-v1` slots | 部分可以 | 需要輔助 unknown/custom | rules + user confirmation |
| 6. Endpoint / Risk / Flow derivation | endpoint、risk hints、flows | 部分可以 | 可輔助 rationale / extension flow | rules + evidence |
| 7. Normalize and validate | 組 JSON、驗證 schema/invariants | 是 | 不需要 | schema validator |

設計原則：

```text
Deterministic first.
AI proposal second.
User confirmation when uncertain.
JSON validation always.
```

## 3. Stage 1: Precondition Check

### 這段要做什麼

```text
1. Precondition check
   檢查 project folder 是否存在、可讀，決定 output policy
```

這段是啟動掃描前的安全門。

必做：

- `project_path` 是否存在。
- `project_path` 是否是 directory。
- 是否可讀。
- output directory 是否可建立。
- output artifacts 是否已存在。
- 若已存在，是否建立 timestamped output directory。
- scan limits 是否載入。
- ignore rules 是否載入。

### 可用現有工具

這段不需要外部 AI，也不需要大型 scanner。

可直接使用：

- Python: `pathlib`, `os`, `stat`, `datetime`, `tempfile`。
- Node/TypeScript: `fs`, `path`, `fs.promises`。
- Git: `git rev-parse --show-toplevel` 可用於判斷是否在 git repo 內。

### AI 輔助判斷

不建議。

原因：

- path 是否存在、是否可讀是 deterministic fact。
- output policy 必須可測、可重現。
- AI 參與只會增加不確定性。

### 設計建議

輸出統一用：

```text
PreconditionResult {
  ok
  project_root
  output_run_dir
  warnings
}
```

fatal error 統一轉成：

```text
PreconditionError {
  project_path
  failure_reason
  scan_stage = "precondition"
}
```

這樣 `kai-mind map ./missing-project` 可以穩定輸出 `outputs/map-error.md`。

## 4. Stage 2: File Inventory

### 這段要做什麼

```text
2. File inventory
   掃描候選檔案，排除 dependency/build/binary/generated files
```

這段的目標不是理解程式，而是建立「哪些檔案會被掃」的 deterministic inventory。

必做：

- 優先使用 git tracked files。
- fallback recursive listing。
- 排除 dependency/build/binary/generated files。
- 保留 config、docs、Docker、dependency manifests、source files。
- 記錄 skipped files 與 reason。
- evidence path 轉成 project-relative POSIX path。

### 可用現有工具與開源參考

#### Git / filesystem

可直接使用：

```bash
git ls-files
```

優點：

- 比 recursive listing 更穩定。
- 不容易掃到 build output、local cache、臨時檔。
- 適合 CI/CD 與 release-readiness 場景。

#### Gitingest

來源：https://github.com/coderamp-labs/gitingest

簡短摘要：

- Gitingest 把 Git repository 轉成 prompt-friendly text digest。
- 它的核心價值是整理 repo file tree、內容與 token-friendly context。

可借鑑什麼：

- file selection discipline。
- include / exclude pattern。
- max file size。
- token / size budget 思維。
- 把 repository inventory 和後續 AI context 分開。

和 KAI-Mind 的關聯：

- KAI-Mind 不應把整個 repo dump 給 AI。
- 但可以借鑑 Gitingest 的「先控制掃描範圍」與「prompt-friendly subset」概念。
- Stage 2 應輸出 `FileInventory`，而不是直接輸出 AI prompt。

#### Understand-Anything

來源：https://github.com/Lum1104/Understand-Anything

簡短摘要：

- Understand-Anything 會掃描 codebase，產生 `.understand-anything/knowledge-graph.json`。
- 它用 deterministic Tree-sitter 結構分析加上 LLM semantic layer。
- 它也支援 incremental update，只重新分析變更檔案。

可借鑑什麼：

- 先產生 scan inventory。
- structural facts 與 LLM semantic output 分層。
- intermediate files。
- incremental update。
- 不讓 file analyzer 重新發明 import map。

和 KAI-Mind 的關聯：

- KAI-Mind 的 Stage 2 應是 deterministic source of truth。
- 後續 provider 不應重新決定掃描範圍。
- 未來可以加入 fingerprint / changed files incremental scan。

### AI 輔助判斷

不建議在 Stage 2 使用 AI 來決定 canonical file inventory。

可以允許的 AI 輔助：

- 根據 inventory summary 提醒「可能需要 include 某個目錄」。
- 幫使用者產生 ignore rule proposal。

但這些只能是 proposal，不可直接改 canonical inventory。

## 5. Stage 3: Deterministic Providers

### 這段要做什麼

```text
3. Deterministic providers
   config / Docker / dependency / code pattern parsers
```

這段是掃描的核心。每個 provider 都應該只做一件事：從某類檔案產生可追溯 facts。

```text
ConfigParseProvider
DockerComposeProvider
DependencyManifestProvider
CodePatternProvider
```

### 3.1 ConfigParseProvider

可用工具：

- JSON: Python `json` / Node `JSON.parse`。
- TOML: Python `tomllib`。
- YAML: `PyYAML` / `ruamel.yaml`。
- `.env`: `python-dotenv` 或自寫簡單 parser。

AI 角色：

- 不應用於 parse。
- 可用於解釋 malformed config 對使用者的影響，但不能修正成 facts。

設計要求：

- parse error 變成 `ParseIssue` + `Evidence`。
- secret-like value 必須先 mask。
- `.env` 可以記錄 key exists，不輸出完整 value。

### 3.2 DockerComposeProvider

來源：https://docs.docker.com/compose/compose-file/

簡短摘要：

- Docker Compose file 定義 services、networks、volumes、configs、secrets 等。
- services 裡包含 image、ports、environment、volumes、depends_on 等高價值訊號。

可借鑑什麼：

- Compose file 是偵測 service topology 和 port exposure 的高信號來源。
- `services.*.image` 可推導 Qdrant、Ollama、Redis、Postgres 等 runtime components。
- `services.*.ports` 可推導 local endpoint 與初步 network exposure hint。

和 KAI-Mind 的關聯：

- Docker Compose parsing 應是 deterministic。
- `qdrant/qdrant`、`ollama/ollama`、`ports: ["6333:6333"]` 是直接 evidence。
- malformed compose 不應讓整體 scan 失敗，應產生 partial map。

AI 角色：

- 不應用於 parse Compose。
- 可輔助把複雜 service name 說明成 user-facing explanation。

### 3.3 DependencyManifestProvider

可用工具：

- `requirements.txt` parser。
- `pyproject.toml` parser。
- `package.json` parser。
- `go.mod`, `Cargo.toml`, `pom.xml` 可作未來 extension。
- Syft 可作更完整 dependency inventory 的參考。

#### Syft

來源：https://oss.anchore.com/docs/guides/sbom/getting-started/

簡短摘要：

- Syft 可以從 container images、filesystems、directories 產生 SBOM。
- SBOM 是軟體組件清單，常用於 supply chain 與 dependency inventory。

可借鑑什麼：

- dependency inventory 應該是獨立階段。
- dependency discovery 不應混在 RAG component detection 裡。
- 可以考慮未來用 SBOM 格式作為 dependency facts 的來源。

和 KAI-Mind 的關聯：

- Epic 1 不一定要直接整合 Syft。
- 但 DependencyManifestProvider 的輸出可以設計得像 lightweight SBOM facts。
- 後續 Epic 3/6 若要做安全與 gate，可以接 Syft/Trivy 這類工具。

AI 角色：

- 不應用於 dependency parse。
- 可輔助辨識 uncommon package 是否可能是 RAG-related，但只能產生 rule proposal。

### 3.4 CodePatternProvider

可用工具：

#### Semgrep

來源：https://semgrep.dev/docs/running-rules/

簡短摘要：

- Semgrep 支援 local rules、ephemeral rules、YAML-defined rules。
- 它可以用 pattern matching 掃描程式碼，回報符合規則的 findings。

可借鑑什麼：

- RAG patterns 可以先做成 rules。
- 例如偵測 `OpenAIEmbeddings(...)`、`QdrantClient(...)`、`as_retriever()`、`PromptTemplate(...)`。
- rules 可以 versioned、可測、可 review。

和 KAI-Mind 的關聯：

- CodePatternProvider 可以自寫 pattern engine，也可以未來整合 Semgrep。
- 關鍵是每個 match 都要輸出 `rule_id`、file、path、value。
- 不要讓 AI 自由讀 source 然後直接產生 detected component。

#### Tree-sitter

來源：https://tree-sitter.github.io/tree-sitter/cli/parse.html

簡短摘要：

- Tree-sitter 可以 parse source files 產生 syntax tree。
- 它適合做 language-aware code structure extraction。

可借鑑什麼：

- L2/L3 detail scan 可用 Tree-sitter 做 bounded AST extraction。
- 可用來找 function/class/route/call-like pattern。
- 比純 regex 更可靠，但成本比 manifest parsing 高。

和 KAI-Mind 的關聯：

- Epic 1 L1 不需要完整 AST。
- L2 component detail scan 或 L3 code path scan 可以引入 Tree-sitter。
- 不要把 Tree-sitter output 直接變成 whole-repo call graph。

#### Understand-Anything 的 Tree-sitter + LLM split

來源：https://github.com/Lum1104/Understand-Anything

簡短摘要：

- Understand-Anything 明確把 Tree-sitter 當 deterministic structural analysis。
- LLM 只負責 summary、tags、architectural layers、guided tours。

可借鑑什麼：

- structural facts 與 semantic explanations 分層。
- import/call/class/function 等 facts 可由 parser 先提取。
- LLM 不應重新解決 deterministic facts。

和 KAI-Mind 的關聯：

- KAI-Mind 的 CodePatternProvider 可採同樣原則。
- RAG facts 由 deterministic rules 產生。
- AI 只協助 unknown/custom mapping proposal。

## 6. Stage 4: Raw Scan Facts

### 這段要做什麼

```text
4. Raw scan facts
   ScanFact[] + Evidence[] + ParseIssue[]
```

這段把各 provider 的結果統一成一致格式。

核心資料：

```text
ScanFact
  scanner 掃到的事實

Evidence
  事實的來源：file/path/value/rule_id

ParseIssue
  provider 解析失敗或部分失敗
```

### 可用現有工具

這段主要靠自己定義 domain model。可以借鑑：

- Trivy 的 finding model：scanner 把 secret/misconfig findings 結構化。
- Semgrep 的 finding model：rule id + file location + matched pattern。
- JSON Schema：後續 validation。

#### Trivy

來源：https://trivy.dev/v0.38/docs/secret/scanning/

簡短摘要：

- Trivy 可掃 container image、filesystem、git repository 中的 secrets。
- 它有 built-in rules，也支援 configuration。
- 它建議用 skip dirs/files 來提升掃描速度與控制範圍。

可借鑑什麼：

- Secret-like values 要當成高風險資料處理。
- 掃描結果應該是 rule-based findings。
- skip dirs/files 是必要性能策略。

和 KAI-Mind 的關聯：

- Epic 1 不做完整 secret scanner，但必須 secret-safe。
- `SecretMaskingService` 應在 Stage 4 前或 Stage 4 內統一處理。
- Raw facts 不可保存完整 secret。

### AI 輔助判斷

不建議。

原因：

- Raw facts 是 canonical truth 的最低層。
- AI 介入會破壞可重現性。

AI 可以做：

- 讀 masked facts 後產生人類可讀 summary。
- 但 summary 不可回寫為 raw facts。

## 7. Stage 5: RAG Slot Mapping

### 這段要做什麼

```text
5. RAG slot mapping
   facts -> rag-core-v1 component slots
```

這段把 Stage 4 的 facts 對到 RAG reference architecture。

例子：

```text
qdrant/qdrant image -> vector_store
OpenAIEmbeddings -> embedding_model
ChatOpenAI -> llm
RecursiveCharacterTextSplitter -> chunking
retriever.invoke -> retriever
FastAPI POST /query -> app_api_or_orchestrator
```

### 可用現有工具與框架參考

#### LangChain

來源：https://docs.langchain.com/oss/python/langchain/retrieval

簡短摘要：

- LangChain retrieval docs 把 RAG building blocks 拆成 document loaders、text splitters、embedding models、vector stores、retrievers。
- 它說明 retriever 是針對 query 回傳 documents 的 interface。

可借鑑什麼：

- `rag-core-v1` 的 slot 命名可以對齊主流 RAG building blocks。
- `document_loader`、`chunking`、`embedding_model`、`vector_store`、`retriever` 都是合理 baseline slots。

和 KAI-Mind 的關聯：

- Stage 5 的 mapping rules 可以從 LangChain 常見 API / package names 開始。
- 但 LangChain 不是唯一 RAG 形狀，所以無法對上的 facts 要進 `extensions` 或 `unmapped_components`。

#### LlamaIndex

來源：https://developers.llamaindex.ai/python/framework/module_guides/indexing/vector_store_index/

簡短摘要：

- LlamaIndex 指出 vector stores 是 RAG 常見核心元件。
- 它的 ingestion pipeline 包含 transformations，例如 splitter、metadata extractor、embedding。
- `VectorStoreIndex` 可以從 documents 建立 index，也可以作為 retriever/query engine 的基礎。

可借鑑什麼：

- Stage 5 mapping 不應只支援 LangChain。
- LlamaIndex 的 concepts 可對應到 ingestion、indexing、retriever、query engine。
- 需要 framework-specific mapping rules。

和 KAI-Mind 的關聯：

- `llama_index.core.ingestion.IngestionPipeline` 可對應 indexing pipeline。
- `VectorStoreIndex` 可對應 vector store / indexing component。
- `as_retriever()` / query engine 可對應 retriever / app orchestrator。

### 哪裡需要 AI

這段是第一個可能需要 AI 的地方，但 AI 只能當 assistant。

AI 適合做：

- 對 `unmapped_components` 產生 mapping proposal。
- 根據使用者文字說明，建議 existing slot 或 extension component。
- 對 custom architecture 提出 2-3 個候選 slot。
- 產生 rationale wording。

AI 不可以做：

- 沒有 evidence 就創造 component。
- 直接把 proposal 寫進 `components_by_slot`。
- 用 `confidence` 取代 evidence。

決策規則：

```text
clear rule match
  -> components_by_slot

clear non-standard component
  -> extensions

uncertain but evidence exists
  -> unmapped_components / needs_confirmation

AI suggestion
  -> MappingProposal only

user confirms + validation passes
  -> ManualMapping -> regenerated canonical JSON
```

## 8. Stage 6: Endpoint / Risk / Flow Derivation

### 這段要做什麼

```text
6. Endpoint / Risk / Flow derivation
   endpoints + risk_hints + indexing/query_answer flows
```

這段根據 facts 和 mapped components 推導：

- local endpoints。
- external endpoints。
- risk hints。
- indexing flow。
- query_answer flow。
- extension flow edges。

### 可用工具與參考

#### Docker Compose services / ports

來源：https://docs.docker.com/reference/compose-file/services/

簡短摘要：

- Docker Compose service 可以設定 images、ports、environment、env_file、depends_on 等。
- `ports` 和 `expose` 是推導服務暴露方式的重要欄位。

可借鑑什麼：

- `ports` 可以產生 endpoint hints。
- `environment` / `env_file` 可以產生 provider config evidence。
- `depends_on` 可產生 service relationship hints。

和 KAI-Mind 的關聯：

- `6333:6333` 可產生 Qdrant endpoint 與 network exposure hint。
- `11434:11434` 可產生 Ollama local LLM endpoint。
- `env_file: .env` 只可記錄 env file usage，不可輸出完整 secrets。

#### OpenInference

來源：https://arize-ai.github.io/openinference/spec/traces.html

簡短摘要：

- OpenInference trace span kinds 包含 Chain、Retriever、Reranker、LLM、Embedding、Agent、Tool、Guardrail 等。
- 它的 span kinds 很接近 RAG replay 的 step vocabulary。

可借鑑什麼：

- Query replay step 可以對齊 Retriever、Reranker、LLM、Embedding、Guardrail。
- extension component 例如 reranker 不必硬塞 retriever，可獨立作為 extension step。

和 KAI-Mind 的關聯：

- Stage 6 的 flow derivation 可輸出 `relationship` 與 `step_type`。
- QueryTraceEvent 可以映射到 slot 或 extension component。
- 未確認的 component 可以顯示 `unknown_step`，不讓 replay 失敗。

#### OpenTelemetry GenAI semantic conventions

來源：https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/

簡短摘要：

- OpenTelemetry GenAI semconv 定義 inference、embedding、retrieval、tool execution 等 spans。
- 文檔提醒 inputs/outputs 可能很敏感，預設不應 capture，需要 opt-in。

可借鑑什麼：

- Query trace 不應預設記錄 full prompt/input/output。
- Replay events 應該有 span-like categories。
- Sensitive content 要 opt-in 或 masked。

和 KAI-Mind 的關聯：

- `QueryTraceEvent.input/output/retrieved_chunks` 必須 masked。
- Stage 6 risk hints 可以保留 uncertainty，不做完整 security verdict。
- Replay 可以先用 MVP spans，不需要完整 observability platform。

### 哪裡需要 AI

AI 可以輔助：

- 對 extension/custom flow 提出 edge proposal。
- 把 risk hint rationale 寫得比較容易懂。
- 對 unknown endpoint 用人類語言解釋 uncertainty。

AI 不可以：

- 把沒有 evidence 的 endpoint 寫入 JSON。
- 把 risk hint 升級成 final verdict。
- 自行決定 network exposure severity。

## 9. Stage 7: Normalize and Validate

### 這段要做什麼

```text
7. Normalize and validate
   assemble RagSystemMap, validate ai-system-map/v1
```

這段是 canonical JSON 的最後閘門。

必做：

- deterministic IDs。
- merge duplicate facts。
- remove dangling references。
- validate schema。
- validate invariants。
- reject `confidence`。
- reject detected without evidence。
- reject unmasked secret。
- reject absolute evidence path。

### 可用工具與開源參考

#### JSON Schema

來源：https://json-schema.org/specification

簡短摘要：

- JSON Schema 規格分為 Core 和 Validation。
- Validation 定義 JSON instance 應如何用 schema 驗證。

可借鑑什麼：

- `ai-system-map/v1` 應有 checked-in JSON schema。
- schema validation 是 Stage 7 的必要 gate。
- field removal、enum changes、breaking contract 都應由 tests 擋住。

和 KAI-Mind 的關聯：

- `schema_version` 是後續 Epic 的契約。
- JSON Schema 可以擋 invalid enum、missing required fields、wrong shapes。
- 但「detected must have evidence」這類 cross-reference invariant 需要額外 validator。

#### GitDiagram

來源：https://github.com/ahmedkhaleel2004/gitdiagram

簡短摘要：

- GitDiagram 把 GitHub repo 轉成 interactive diagram。
- 它先抓 repo default branch、recursive file tree、README，過濾 noisy assets/dependency folders。
- 它用 model 產生 architecture explanation 和 graph，並驗證 graph paths/invalid connections，再輸出 Mermaid。

可借鑑什麼：

- path validation。
- graph references 必須對得上實際 file tree。
- graph generation 後必須 validate/retry。

和 KAI-Mind 的關聯：

- KAI-Mind 不應複製 GitDiagram 的 AI-first diagram 方式。
- 但 Stage 7 可以借鑑它的 validation discipline：bad path / dangling edge 不可進 final output。

#### Understand-Anything

來源：https://github.com/Lum1104/Understand-Anything

簡短摘要：

- Understand-Anything 會產生 knowledge graph JSON。
- 它使用 static analysis + LLM hybrid pipeline，並有 graph reviewer / schema validation / dashboard load validation。
- intermediate results 存在 `.understand-anything/intermediate/`，final graph 存到 `.understand-anything/knowledge-graph.json`。

可借鑑什麼：

- intermediate artifacts。
- merge / normalize / validate 分階段。
- dashboard 載入時再次 validate。
- incremental update。

和 KAI-Mind 的關聯：

- Stage 7 應是 explicit service：`SystemMapNormalizeService` + `SystemMapValidationService`。
- Viewer 也要再次 validate map JSON。
- 不要讓 LLM bypass validator。

### AI 輔助判斷

不建議。

AI 可以做：

- 根據 validation error 產生使用者可讀說明。
- 幫開發者產生修復建議。

AI 不可以：

- 修改 validator result。
- 自行放行 invalid JSON。
- 產生 final canonical map。

## 10. 逐段外部參考總表

| Reference | Source | Summary | KAI-Mind 可以借鑑什麼 |
|---|---|---|---|
| Gitingest | https://github.com/coderamp-labs/gitingest | 把 Git repo 轉成 prompt-friendly text digest。 | Stage 2 file selection、ignore、size/token budget。 |
| GitDiagram | https://github.com/ahmedkhaleel2004/gitdiagram | 把 GitHub repo 轉成 interactive architecture diagram，並驗證 paths / graph。 | Stage 7 graph/path validation discipline；不要照搬 AI-first truth。 |
| Understand-Anything | https://github.com/Lum1104/Understand-Anything | static analysis + LLM semantic layer，產生 codebase knowledge graph。 | Stage 2 inventory、Stage 3 parser/LLM 分工、Stage 7 merge/validate。 |
| Docker Compose Docs | https://docs.docker.com/compose/compose-file/ | Compose file 定義 services、networks、volumes 等。 | Stage 3 Docker parsing、Stage 6 endpoint/risk derivation。 |
| Docker Compose Services | https://docs.docker.com/reference/compose-file/services/ | services 可定義 image、ports、environment、env_file、depends_on。 | Qdrant/Ollama endpoint、published port risk hints。 |
| Semgrep | https://semgrep.dev/docs/running-rules/ | rule-based static analysis，可用 YAML rules 或 ephemeral rules。 | CodePatternProvider 可用 rule-based findings。 |
| Tree-sitter | https://tree-sitter.github.io/tree-sitter/cli/parse.html | source parsing tool，可 parse files/globs 產生 syntax trees。 | L2/L3 bounded AST extraction，不做 whole-repo graph。 |
| Syft | https://oss.anchore.com/docs/guides/sbom/getting-started/ | 從 container images/filesystems 產生 SBOM。 | Dependency inventory 設計參考，未來可整合。 |
| Trivy | https://trivy.dev/v0.38/docs/secret/scanning/ | 掃 filesystem/git repo/container image secret，支援 built-in rules。 | Secret-safe、skip dirs/files、rule-based findings。 |
| LangChain Retrieval | https://docs.langchain.com/oss/python/langchain/retrieval | RAG building blocks: loaders、splitters、embeddings、vector stores、retrievers。 | `rag-core-v1` baseline slots 與 mapping rules。 |
| LlamaIndex VectorStoreIndex | https://developers.llamaindex.ai/python/framework/module_guides/indexing/vector_store_index/ | Vector stores 是 RAG 常用元件；ingestion pipeline 會做 transformations。 | LlamaIndex-specific slot mapping。 |
| OpenInference | https://arize-ai.github.io/openinference/spec/traces.html | trace span kinds 包含 Chain、Retriever、Reranker、LLM、Embedding、Tool、Guardrail。 | Query replay vocabulary、extension steps。 |
| OpenTelemetry GenAI | https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/ | 定義 GenAI spans，提醒 inputs/outputs 敏感且不應預設 capture。 | QueryTraceEvent privacy、span-like categories。 |
| JSON Schema | https://json-schema.org/specification | JSON Schema Core + Validation 規格。 | `ai-system-map/v1` schema gate。 |

## 11. 推薦的最終分工

### Deterministic only

這些階段不應該讓 AI 參與 canonical decision：

```text
1. Precondition check
2. File inventory
4. Raw scan facts
7. Normalize and validate
```

### Deterministic first, AI proposal only

這些階段可以使用 AI，但不能直接改 canonical JSON：

```text
3. CodePatternProvider rule proposal
5. RAG slot mapping for unknown/custom component
6. Extension flow / rationale wording
```

### AI 使用邊界

AI 可以：

- 產生 mapping proposal。
- 解釋 why uncertain。
- 幫使用者把自然語言轉成 structured proposal。
- 產生 human-readable rationale。

AI 不可以：

- 創造沒有 evidence 的 component。
- 直接寫入 `components_by_slot`。
- 直接寫入 `risk_hints` 當 final verdict。
- 放行 invalid JSON。
- 顯示或保存 full secrets。

## 12. 對後端文件的建議更新

建議把 `docs/work/Timmy/design/epic1-backend-design.md` 中的主要資料流補成：

```text
1. Precondition check        deterministic only
2. File inventory            deterministic only
3. Deterministic providers   parsers/rules first, AI only for rule proposal
4. Raw scan facts            deterministic only
5. RAG slot mapping          rules first, AI proposal for unmapped/custom
6. Endpoint/Risk/Flow        rules first, AI wording/proposal only
7. Normalize/validate        deterministic only
```

這樣可以避免兩個風險：

- 太依賴 AI，導致 release-readiness report 不可驗證。
- 太死板 deterministic，導致 custom RAG architecture 被丟掉。

最終建議：

```text
Use deterministic tools for facts.
Use AI only for proposals and explanations.
Require user confirmation for uncertain mappings.
Validate everything before writing canonical JSON.
```
