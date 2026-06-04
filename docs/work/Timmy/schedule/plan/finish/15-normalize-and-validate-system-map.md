# Task 15: Normalize and Validate System Map

## 目標
實作 `SystemMapNormalizeService`，並補強既有 `SystemMapValidationService`，將 Task 12 raw scan、Task 13 components、Task 14 endpoints / flows / risk hints 組成 canonical `RagSystemMap`，並在寫出前擋下 contract violation。

注意：Task 2 已先建立 `SystemMapValidationService` 起點，Task 15 不是從零重寫 validator，而是新增 canonical assembly layer，並補齊 validation 缺口。

## 為什麼要先做這個
Stage 7 是 canonical JSON 的最後閘門。所有後續 CLI、Markdown、viewer、trace 都應只讀 validated map，不能繞過 normalization/validation。

## 前置需求
- Task 2 已完成 schema/model。
- Task 12 已完成 raw scan facts / evidence / parse issues aggregation。
- Task 12a 已完成 provider-local rule catalog 外部化，Task 15 不需要知道 provider TOML rules。
- Task 13 已完成 component detection。
- Task 14 已完成 endpoint/risk/flow derivation。
- Task 14a 已完成 risk hint rule metadata TOML 外部化，Task 15 不觸發 risk rules、不查 risk catalog。
- Task 25 已完成 provider config mapping matrix；Task 15 應能組裝 config-driven detected components。

## 實作範圍
- 組裝 top-level `RagSystemMap`。
- Normalizer input 應明確接收：
  - `ProjectScanResult`：facts、evidence、issues、skipped files、scan counts。
  - `RagTemplate`：`rag-core-v1` slots 與 bare flow ids。
  - `ComponentDetectionResult`：`components_by_slot`、`extensions`、`unmapped_components`。
  - Task 14 outputs：`endpoints`、`flows`、`risk_hints`。
- Normalize 階段必須明確補齊 canonical top-level arrays：`evidence`、`endpoints`、`flows`、`extensions`、`unmapped_components`、`detail_scans`、`risk_hints`、`recommended_next_checks`、`query_trace_events`。若上游 service 沒有產出資料，應填入 `[]`，不可省略欄位或依賴 Pydantic default 偷補。
- 組裝 classification：`mode = user_selected_or_default`、`selected_template = rag-core-v1`。
- 組裝 project metadata，`project.root_path` 不得輸出真實本機路徑；使用 redacted / null / `<project_root>` 這類安全表示。
- 組裝 reference architecture：template slots 使用 canonical slot ids；template flow ids 保留 bare ids，例如 `indexing`、`query_answer`。
- 組裝 `scan_summary`：files scanned/skipped、detected/missing slot counts、unmapped count、risk hint count、secret masking status。
- deterministic ordering：evidence、components、endpoints、flows、risk hints、extensions、unmapped、recommended checks 輸出順序穩定。
- deterministic ids：優先沿用 Task 12-14 已產生的 readable deterministic ids，例如 `component:...`、`endpoint:...`、`risk:...`。不要使用 `uuid.uuid4()`、memory address、random string。只有未來需要 opaque id 時才考慮 `uuid.uuid5(namespace, stable_name)`。
- duplicate handling：Task 12 已處理 provider fact/evidence dedupe；Task 15 只做 canonical output 層的 duplicate id 檢查、穩定排序、必要時 fail fast，不重新定義 provider fact dedupe。
- 條件式產生 `recommended_next_checks`，初始支援：
  - `runtime_readiness`：有 endpoint、Docker service、runtime-critical missing slot 時，建議確認實際 runtime 可用性。
  - `privacy_exposure`：有 external provider、published port、secret-like config、local persistence 等 risk hint 時，建議確認資料外流、存取控制與敏感資料處理。
  - `rag_knowledge_trust`：缺 data source / retriever / citation / response composer，或 RAG pipeline evidence 不完整時，建議確認知識來源、retrieval quality 與 citation 可追溯性。
- `recommended_next_checks` 的 canonical output 必須由 deterministic Python triggers 搭配人工維護的 check catalog / metadata 產生，不由 LLM 即時生成或改寫。AI 可作為未來的 proposal / report explanation layer，但不能直接 mutation canonical map。
- 建議將 `recommended_next_checks` 的穩定 metadata 外部化到 package-bundled TOML catalog，例如 `recommended_next_check_rules.toml`；TOML 只放 `id`、`reason`、`action`、預設 `target_type` 等文案與分類，不放 trigger condition。
- 執行 JSON Schema validation。
- 補強 cross-reference invariants：evidence refs、endpoint component refs、flow edge refs、risk targets、extension/unmapped refs、detail scan refs、query trace refs、recommended next check targets、no confidence、no absolute paths、no unmasked secrets。

## 不包含範圍
- 不寫 artifacts。
- 不產生 Markdown。
- 不做 viewer graph projection。
- 不做 AI proposal；尤其不由 LLM 動態產生 canonical `recommended_next_checks`。
- 不重新跑 filesystem / config / compose / dependency / code pattern providers。
- 不重新做 component detection。
- 不重新推導 endpoint、risk hint 或 flow。
- 不讀 provider rule TOML catalog。
- 不讀 risk hint metadata TOML catalog。
- 不設計 `condition = "..."` 這類 TOML condition DSL；recommended next check 的觸發條件留在 Python code。
- 不處理 Task 19 manual mapping confirmation，只保留已由 Task 13 hook 套用後的 result。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/system_map_normalize_service.py`。
2. 定義 normalizer input dataclass 或明確 method signature，避免直接傳自由 dict。
3. 組裝 classification、project metadata、reference architecture。
4. 將所有可為空的 top-level collections normalize 成明確空陣列；例如尚未偵測到 endpoint 時輸出 `endpoints: []`，尚未跑 trace 時輸出 `query_trace_events: []`。
5. 組裝 `scan_summary`，用 upstream result count，不重新掃檔。
6. 新增 package-bundled `recommended_next_check_rules.toml` 與 loader validation，沿用既有 `RuleCatalogLoader` 風格或建立同等嚴格的 loader。
7. 條件式產生 `recommended_next_checks`，不要無腦固定輸出三條；trigger 判斷留在 Python，metadata 從 TOML catalog 讀取。
8. 對 canonical collections 做 deterministic sort。
9. 呼叫既有 `SystemMapValidationService.validate()` 作最後 gate。
10. 補強 `system_map_validation_service.py`：
   - duplicate top-level ids rejected。
   - `recommended_next_checks.target` 必須指向 valid slot / component / endpoint / risk / evidence / unmapped / extension / file target。
   - serialized JSON 不得包含 project root 真實路徑或 fixture fake full secret。
11. 將目前 phase14 integration test 中手刻 `system_map` dict 的 helper 改成使用 `SystemMapNormalizeService`。
12. 寫 contract / unit tests：invalid references、detected without evidence、confidence、absolute evidence path、缺少 canonical top-level array 時 validation 失敗、normalizer 輸出空陣列、deterministic ordering、recommended next checks 條件式產生、TOML metadata catalog duplicate / missing field validation。

## 預期輸出
- `src/kai_mind/core/services/system_map_normalize_service.py`
- `src/kai_mind/core/services/system_map_validation_service.py`
- `src/kai_mind/core/rules/recommended_next_check_rules.toml`
- 擴充 `tests/contracts/test_ai_system_map_schema.py`，必要時再新增 `tests/contracts/test_system_map_contract.py`
- `tests/unit/core/test_system_map_normalize_service.py`
- 擴充 `tests/unit/core/test_system_map_validation.py`
- 擴充 `tests/unit/core/test_rule_catalog_loader.py` 或新增同級 catalog loader tests，覆蓋 recommended next check metadata catalog。
- 更新 `tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py`，避免繼續手刻 canonical map dict。

## 驗收標準
- basic Qdrant/Ollama fixture 可透過 normalizer 產生 valid `RagSystemMap` object。
- OpenAI external provider fixture 可透過 normalizer 產生 valid `RagSystemMap` object，且 serialized JSON 不含完整 fake API key。
- custom router / reranker / unmapped fixture 可保留 `unmapped_components` 或 `extensions`，且 validation 通過。
- malformed config / compose / manifest fixture 可保留 partial scan evidence / risk hint，且 validation 通過；若 parse evidence path 不合法，validation fail。
- normalized map 即使沒有 endpoints、flows、risk hints、detail scans 或 trace events，也會輸出對應欄位且值為 `[]`。
- invalid map 不會被 validation 放行。
- normalized map deterministic ordering 穩定。
- full secret 不出現在 serialized JSON。
- `project.root_path` 不輸出真實本機路徑。
- `Evidence.file` 若是 absolute path、Windows separator、或 parent traversal，validation fail fast。
- `recommended_next_checks` 是條件式輸出，不是每份 map 固定三條。

## 可能風險與注意事項
- JSON Schema 無法檢查所有 dangling references，必須用 Python validator 補。
- 空陣列代表「目前沒有偵測到 / 尚未執行該階段」；缺少欄位代表產出端違反 canonical contract。不要在 validator 或 Pydantic model 裡替壞輸入補欄位，補齊責任屬於 normalize / map build 產出端。
- deterministic ids 要避免使用 absolute path、timestamp、random value。
- 不要為了 deterministic id 強制改成 `uuid.uuid5()`；本 repo 目前已使用 readable deterministic ids，Task 15 應優先沿用，避免破壞可讀性與既有測試。
- Pydantic v2 `@model_validator(mode='after')` 可作為 cross-field validation 參考，但本 repo 目前採 `SystemMapValidationService` 集中檢查 runtime invariants；Task 15 不必把所有 invariant 搬進 Pydantic model。
- 參考依據：JSON Schema 官方 validation 規格；GitDiagram/Understand-Anything 的 validation discipline 可作 path/graph validation 參考，但不要過度宣稱外部專案與本 repo 100% 相同。

## 既有 code 現況校正（2026-06-04）

Task 15 需要接住既有 codebase，而不是照舊版計劃從空白狀態開始。

- `RagSystemMap`、top-level arrays、`RecommendedNextCheck`、`ScanSummary` 已存在於 `src/kai_mind/core/models/system_map.py`。
- `SystemMapValidationService` 已存在於 `src/kai_mind/core/services/system_map_validation_service.py`，目前已檢查 confidence、evidence path、components、endpoints、flows、extensions、unmapped、risk hints、detail scans、query trace refs。
- `tests/unit/core/test_system_map_validation.py` 目前 pytest 收集 15 items 且通過；但這不是 15 個 test functions，而是 11 個 test functions 加上 parametrize 展開。
- 目前尚未建立 `SystemMapNormalizeService`。
- 目前尚未建立 `tests/unit/core/test_system_map_normalize_service.py`。
- 目前尚未建立 `tests/contracts/test_system_map_contract.py`；contract 測試主檔仍是 `tests/contracts/test_ai_system_map_schema.py`。
- 既有 `RuleCatalogLoader` 已用 `tomllib` 載入 package-bundled TOML catalogs，例如 dependency、Docker image、code pattern、risk hint rules；Task 15 若外部化 recommended next check metadata，應沿用此風格與 validation 嚴格度。

## Evidence path policy（2026-06-04）

結論：`Evidence.file` 在 Task 15 預設不轉路徑。錯就 fail。

正常 scanner pipeline 已由 provider 層保證 project-relative POSIX path：

| 層 | 路徑責任 | Task 15 結論 |
|---|---|---|
| `FilesystemProvider` | 將 file inventory path normalize 成 project-relative POSIX path，並 skip outside-root symlink | 這是 path normalization 的主要責任者 |
| `ConfigParseProvider` | 用 `project_root / record.path` 讀檔，輸出沿用 `record.path` | 正常 pipeline 下輸出 relative path |
| `DockerComposeProvider` | 用 `project_root / record.path` 讀檔，輸出沿用 `record.path` | 正常 pipeline 下輸出 relative path |
| `DependencyManifestProvider` | 用 `project_root / record.path` 讀檔，輸出沿用 `record.path` | 正常 pipeline 下輸出 relative path |
| `CodePatternProvider` | 驗證 `record.path` 不含 backslash、不是 absolute、沒有 `.` / `..`、不逃出 project root | 正常 pipeline 下輸出 relative path |
| `ProjectScanService` | 聚合 providers output，不重寫 evidence path | 不負責轉 path |
| `ComponentDetectionService` | `UnmappedComponent.source_file` 沿用 `ScanFact.file` | 不負責轉 path |
| `EndpointDetectionService` | 只引用 `evidence_id` | 不碰 file path |
| `RiskHintService` | parse issue risk 的 `target_type=file` 來自 parse evidence file | 不負責轉 path |
| `FlowDerivationService` | 只處理 slots/components edges | 不碰 file path |
| `SystemMapValidationService` | 驗證 `Evidence.file` 是 project-relative POSIX path | absolute / Windows separator / `..` 直接 fail |

重要邊界：
- 如果有人繞過 `FilesystemProvider`，手刻一個壞 `FileInventory` 餵給 `CodePatternProvider`，目前 `CodePatternProvider` 會輸出 `code_pattern_invalid_inventory_path` parse issue / parse evidence，且 `file` 會保留原本壞 path。這代表 Task 15 validator 仍必須 fail fast，不能假設所有 upstream input 永遠乾淨。
- `NormalizeService` 不應 silently 把 absolute `Evidence.file` 轉成 relative path，否則會掩蓋 upstream provider bug，甚至可能把 project root 外路徑洗白。
- 唯一可做 redaction / normalization 的是 project metadata，例如 `project.root_path`。Canonical map 不應輸出真實本機 root path。

建議寫成實作規則：

```text
Evidence.file:
  if project-relative POSIX path -> keep
  if absolute path / backslash / parent traversal -> validation fail

Project.root_path:
  output redacted / null / <project_root>
  never output local absolute path
```

## recommended_next_checks policy（2026-06-04）

`recommended_next_checks` 是掃描完成後給使用者的「下一步人工確認建議」，不是 risk hint，也不是 unmapped component 的 suggested action。

```text
risk_hints
  = 掃描已看到什麼可能風險
  例：Docker port 6333 被 publish

recommended_next_checks
  = 因為 static scan 無法確認 runtime / privacy / knowledge quality，
    建議使用者下一步查什麼
  例：確認 Qdrant published port 是否只允許 localhost / 內網存取
```

初始支援三類，但不要每份 map 固定輸出三條：

| Check id | 觸發條件 | 用途 |
|---|---|---|
| `runtime_readiness` | 有 endpoint、Docker service、runtime-critical missing slot、或 service 需要 runtime verification | 建議確認實際服務是否啟動、endpoint 是否能連、config 是否有效 |
| `privacy_exposure` | 有 external provider、published port、secret-like config、local vector persistence、Chroma/DB exposure risk | 建議確認資料外流、敏感資料、存取控制、retention、backup/cleanup |
| `rag_knowledge_trust` | 缺 data source / retriever / citation / response composer / guardrails，或 RAG pipeline evidence 不完整 | 建議確認資料來源可信度、retrieval quality、citation 可追溯性、回答可靠性 |

決策：Task 15 的 canonical `recommended_next_checks` 應由手寫 deterministic rules 產生，不應由 AI / LLM 動態生成。metadata 建議使用 TOML catalog；trigger condition 不放 TOML。

原因：
- `RagSystemMap` 是 canonical contract，必須 deterministic、可重跑、可測試、可 audit。相同輸入應產生相同 check ids / targets / wording。
- Semgrep 這類 SAST 工具的 rule model 是明確 pattern + metadata；SARIF 也把 rule metadata、result、artifact location 分開，方便工具與 CI 穩定消費。這比較接近 Task 15 需要的 output discipline。
- OWASP / AWS LLM 安全文件可協助定義 RAG 相關風險分類，例如資料外洩、供應鏈、過度代理、向量與知識庫信任問題；但這些應轉成固定 catalog 與 deterministic trigger，而不是掃描時讓 LLM 自由發揮。
- 若未來需要 AI，可放在非 canonical 的 proposal / explanation layer，例如針對已產生的 `risk_hints` 與 `recommended_next_checks` 補充人類可讀摘要。AI output 必須標記為 proposal，不應直接改 canonical ids、targets 或 validation result。
- repo 已經有 TOML rule catalog 慣例，且 Python `>=3.11` 可直接使用 `tomllib`，所以把 `reason` / `action` 這類穩定文案放進 TOML 成本低、也能和 `risk_hint_rules.toml` 對齊。
- 不要把 `condition = "has_endpoint OR has_docker_service"` 這類判斷式放進 TOML。那會引入自製 condition DSL，必須額外維護 parser、type checking、錯誤訊息與測試，超出 Task 15 MVP 範圍。

建議實作形狀：

```text
RecommendedNextCheckService
  input:
    validated-ish normalized facts / components / endpoints / risk_hints / missing slots

  deterministic trigger:
    if endpoints or docker runtime evidence -> runtime_readiness
    if privacy/security risk hints -> privacy_exposure
    if RAG trust-critical slots missing -> rag_knowledge_trust

  package-bundled TOML metadata:
    id, default_target_type, reason, action

  output:
    stable RecommendedNextCheck[]
```

建議 TOML 形狀：

```toml
[[recommended_next_checks]]
id = "runtime_readiness"
default_target_type = "system"
reason = "Static scan found runtime-dependent services or endpoints."
action = "Verify the services start successfully and configured endpoints are reachable in the intended environment."

[[recommended_next_checks]]
id = "privacy_exposure"
default_target_type = "system"
reason = "Static scan found potential data egress, published port, secret-like config, or persistence evidence."
action = "Review data flow, access control, retention, and whether sensitive data can leave the local environment."

[[recommended_next_checks]]
id = "rag_knowledge_trust"
default_target_type = "system"
reason = "Static scan found incomplete evidence for RAG knowledge source, retrieval, citation, or response composition."
action = "Review source trust, retrieval quality, citation traceability, and answer reliability before release."
```

Python 負責：

```text
if endpoints or docker_runtime_evidence or runtime_critical_missing_slots:
  emit("runtime_readiness")

if privacy_related_risk_hints:
  emit("privacy_exposure")

if rag_trust_critical_slots_missing:
  emit("rag_knowledge_trust")
```

## 外部研究校正（2026-06-04）

已查證後的可採用結論：

- JSON Schema 的 `required` 表示欄位必須存在；Task 15 normalizer 應明確輸出 required top-level arrays，validator 不應代補。
- Python `uuid.uuid5(namespace, name)` 可產生 namespace + stable name 的 hash UUID，`uuid.uuid4()` 是 random；但本 repo 不必強制改用 uuid5，因為 readable deterministic ids 已是既有慣例。
- Pydantic v2 支援 `@model_validator(mode='after')`，可作 cross-field validation 參考；但本 repo 現有設計把 runtime invariants 放在 `SystemMapValidationService`，不需要為了最佳實踐搬進 Pydantic model。
- GitDiagram README 描述其 pipeline 會用 repo file tree 與 README 產生 structured graph，驗證 bad paths / invalid connections，再編譯 Mermaid 並驗證 Mermaid。可借鏡「產出 graph 前後都有 validation」，但不要過度宣稱其完全 deterministic。
- Understand-Anything README 描述它會掃描 project、抽 file/function/class/dependency，輸出 `.understand-anything/knowledge-graph.json`，並使用 Tree-sitter deterministic structural extraction 與 importMap。可借鏡 staged pipeline 與 graph artifact discipline；若要引用特定 `merge-batch-graphs.py` 丟棄 dangling edges，需另行打開該原始碼確認，不可只靠 README 推論。
- Checkov 可借鏡 static scanner 報告輸出、path/source attribution、JSON/SARIF output discipline；但 KAI-Mind 不是 IaC scanner，不應照搬 Checkov output pipeline。
- OpenTelemetry Service Graph Connector 是 runtime trace -> service graph，不是 static scanner。可借鏡「edge 兩端必須能配對」與 dangling edge 風險，但不能當 Task 15 直接實作範本。
- Semgrep 的 rules 以明確 pattern / metadata / message / severity 定義 detection，不靠 LLM 即時判斷；Task 15 的 `recommended_next_checks` 應採相同精神：固定規則、穩定 metadata、可測試輸出。
- SARIF 將 tool rules、results、artifact locations 等資訊結構化，重點是 machine-readable、stable、可被 CI / viewer 消費；Task 15 canonical checks 不應混入非 deterministic AI 文案。
- AWS 對 OWASP Top 10 for LLM Applications 的整理可作 RAG/LLM 風險分類參考，但要先人工轉成本 repo 的 check catalog 與 trigger 條件。
- Checkov 同時支援 YAML custom policies 與 Python custom policies；可借鏡 metadata / policy definition 分離，但 Task 15 不需要為三條 checks 引入完整 YAML/TOML policy engine。
- Bandit 支援 TOML/YAML 作工具設定與 rule selection；可借鏡「外部設定/metadata」的維護方式，但不要把本 repo 的 runtime/check trigger 判斷全部搬成設定檔語言。

查證來源：
- JSON Schema object / required properties: https://json-schema.org/understanding-json-schema/reference/object
- Python `uuid` docs: https://docs.python.org/3/library/uuid.html
- Pydantic validators docs: https://docs.pydantic.dev/latest/concepts/validators/
- GitDiagram repo: https://github.com/ahmedkhaleel2004/gitdiagram
- Understand-Anything repo: https://github.com/Lum1104/Understand-Anything
- Checkov CLI docs: https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html
- OpenTelemetry service graph connector docs: https://pkg.go.dev/github.com/open-telemetry/opentelemetry-collector-contrib/connector/servicegraphconnector
- Semgrep rule syntax docs: https://semgrep.dev/docs/writing-rules/rule-syntax
- Semgrep detection docs: https://semgrep.dev/docs/for-developers/detection
- SARIF v2.1.0 specification: https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.pdf
- AWS Prescriptive Guidance for OWASP Top 10 for LLM Applications: https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-security/owasp-top-ten.html
- Checkov YAML custom policies: https://www.checkov.io/3.Custom%20Policies/YAML%20Custom%20Policies.html
- Checkov Python custom policies: https://www.checkov.io/3.Custom%20Policies/Python%20Custom%20Policies.html
- Bandit configuration docs: https://bandit.readthedocs.io/en/1.7.10/config.html

## 新手提示
Normalize 是整理資料，Validate 是守門。Normalize 不負責重新掃描或偷偷修掉 upstream bug；它只把已產生的 deterministic results 組成 canonical map。Validate 則負責擋掉 dangling refs、壞路徑、secret leak、contract drift。

## 視覺化說明
```text
┌────────────────┐ ┌──────────┐ ┌──────────────────────┐
│ Detected       │ │ Evidence │ │ Endpoints/Risks/Flows │
│ components     │ │          │ │                      │
└───────┬────────┘ └────┬─────┘ └──────────┬───────────┘
        └───────────────┼──────────────────┘
                        ↓
┌──────────────────────────────────────────┐
│ Normalize                                 │
│ assemble canonical fields, stable ids,    │
│ explicit [] arrays, redacted project path │
└────────────────────┬─────────────────────┘
                     ↓
┌──────────────────────────────────────────┐
│ RecommendedNextCheckService               │
│ Python deterministic triggers + TOML      │
│ check metadata catalog                    │
└────────────────────┬─────────────────────┘
                     ↓
┌──────────────────────────────────────────┐
│ Validate                                  │
│ schema + cross-reference invariants       │
│ no dangling refs, bad paths, raw secrets  │
└───────────────┬──────────────────┬───────┘
                │ pass             │ fail
                ↓                  ↓
┌────────────────────────┐ ┌────────────────┐
│ canonical RagSystemMap │ │ ValidationError │
│ source of truth        │ │                │
└───────────┬────────────┘ └────────────────┘
            ↓
┌──────────────────────────────────────────┐
│ Optional future AI proposal / explanation │
│ read-only consumer of validated map;      │
│ must not mutate canonical ids or checks   │
└──────────────────────────────────────────┘
```
