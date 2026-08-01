# Task 12: Aggregate Raw Scan Facts

## 目標
建立 `ProjectScanService`，統一 orchestration providers，將各 provider 結果整理成 `ScanFact[]`、`Evidence[]`、`ParseIssue[]`、skipped files summary。這一層只收集 facts，不做 slot final judgment。

## 為什麼要先做這個
設計文件將 Stage 4 Raw Scan Facts 定義為 canonical truth 的最低層。若 providers 各自輸出不同形狀，後續 mapping、risk、validation 會難以穩定。

## 前置需求
- Task 7-11 providers 已有初始實作。
- Task 5 secret masking 已可共用。
- Task 2 已有 models/schema 基礎。
- **Task 12a (Extract Provider Rule Catalogs) 應在 Task 12 之前完成。**

## 與 Task 12a 的關係

Task 12a 將 Task 9 / 10 / 11 provider 中硬編碼的 detection rules 搬到 package-bundled TOML rule catalogs（詳見 [12a-extract-provider-rule-catalogs.md](./12a-extract-provider-rule-catalogs.md)）。

執行順序：

```text
Task 9  DockerComposeProvider（硬編碼 image rules）
Task 10 DependencyManifestProvider（硬編碼 package rules）
Task 11 CodePatternProvider（硬編碼 regex rules）
        ↓
Task 12a Extract Provider Rule Catalogs
  ├── dependency_manifest_rules.toml
  ├── docker_image_rules.toml
  ├── code_pattern_rules.toml
  └── RuleCatalogLoader
        ↓
Task 12 Aggregate Raw Scan Facts（本任務）
  └── ProjectScanService 收集所有 provider 結果
```

### 為什麼 12a 要在 12 之前

- Task 12 的 `ProjectScanService` 會統一呼叫所有 providers。如果 providers 的 rule 來源還在重構中（從 Python 搬到 TOML），同時做 aggregation 會增加 regression 風險。
- 先讓 12a 把規則來源穩定下來，12 只需要收集穩定的 `ProviderScanResult`，不用擔心 rule loading 方式的變化。

### Task 12a 對 Task 12 的影響

| 影響面 | 說明 |
|---|---|
| Provider API | 不變。每個 provider 仍回傳 `ProviderScanResult` |
| Facts / Evidence | 不變。rule_id、fact_kind、evidence 格式都不改 |
| Provider 建構方式 | 可能改變。Provider `__init__` 可能需要接收 rule catalog path 或 loader |
| 測試 | 12a 完成後，原有 provider tests 應全部通過，12 可放心整合 |

## 實作範圍
- 建立 `ScanFact`、`Evidence`、`ParseIssue` 統一 models。
- 建立 `ProjectScanService`。
- 串接 Filesystem、Config、Docker、Dependency、CodePattern providers。
- 產生 provider stage warnings。
- 保留 partial failures，不讓單一 provider 失敗中止整體 scan。

## 不包含範圍
- 不做 component detection。
- 不做 endpoint/risk/flow derivation。
- 不寫 artifacts。
- 不產生 Markdown。

## 建議實作步驟
1. **確認 Task 12a 已完成**：providers 已從 TOML rule catalogs 載入 rules，原有 provider tests 全部通過。
2. 補齊 `src/systograph/core/models/scan.py`。
3. 建立 provider result interface。
4. 建立 `src/systograph/core/services/project_scan_service.py`。
5. 將 provider outputs normalize 成統一 facts/evidence/issues。
6. 加入 deterministic ordering，讓 snapshot 穩定。
7. 寫 integration test：basic fixture 產生 Docker/config/dependency/code facts。
8. 寫 partial failure test：malformed compose 仍有 facts output。
9. 寫 rule catalog 載入失敗 test：TOML catalog 損壞時 `ProjectScanService` 應明確報錯，不靜默跳過。

## 預期輸出
- `src/systograph/core/models/scan.py`
- `src/systograph/core/services/project_scan_service.py`
- `tests/unit/core/test_project_scan_service.py`

### 前置產出（由 Task 12a 提供）
- `src/systograph/core/rules/dependency_manifest_rules.toml`
- `src/systograph/core/rules/docker_image_rules.toml`
- `src/systograph/core/rules/code_pattern_rules.toml`
- `src/systograph/core/services/rule_catalog_loader.py`
- `tests/unit/core/test_rule_catalog_loader.py`

## 驗收標準
- 所有 facts 都有 rule_id 或 provider source。
- 所有 evidence 都有 project-relative file path 或合理 non-file source。
- parse issues 帶 scan_stage、file、reason。
- provider partial failure 不讓 ProjectScanService crash。

## 可能風險與注意事項
- 這層不可偷偷決定 slot detected。
- evidence id 先可用穩定 hash input，但最終 deterministic id 在 normalize task 收斂。
- 不要保存 full raw config value。

## 外部研究查證與補充

本節為 2026-06-03 針對 Task 12 aggregation layer 重新上網查證後的補充。結論：原研究方向大致正確，但需要把 Checkov / OSV-Scanner / Trivy 定位成「聚合與可追溯輸出設計參考」，不要誤解成 Task 12 要做完整 IaC / SCA / vulnerability scanner。

### 已確認可採用的借鑑

- **Understand-Anything `merge-batch-graphs.py`：normalize + dedupe + recover 的思路可借鑑。**
  - 查證來源：`merge-batch-graphs.py` 會 normalize node id、重寫 edge references、dedupe nodes / edges、drop dangling edges，並從 `scan-result.json#importMap` recover 遺漏的 `imports` edges。
  - 對 Task 12 的啟發：`ProjectScanService` 應明確定義 facts/evidence/issues 的 canonical key，遇到跨 provider 重複訊號時合併 evidence，而不是覆蓋或產生兩份互相矛盾的 fact。
  - 但要注意：Systograph 目前掃描的是 RAG release-readiness facts，不是 code knowledge graph；所以只採「穩定 ID、deterministic merge、來源補證據」原則，不搬 Understand-Anything 的 node / edge schema。

- **GitDiagram：schema / path validation 的防呆思路可借鑑。**
  - 查證來源：GitDiagram README 說明它會抓 GitHub file tree / README，產生 structured graph 後，對照實際 file tree 驗證 path，發現 bad paths 或 invalid connections 會 retry，之後 Mermaid 還會再 validate。
  - 對 Task 12 的啟發：即使 Task 12 不依賴 LLM，也應以 Pydantic model 和 provider contract 阻擋壞資料進入 aggregation 結果；不符合 `ProviderScanResult` / `ScanFact` / `Evidence` / `ParseIssue` 的資料應轉成 issue 或丟棄並記錄，不要污染後續 Task 13-15。

- **Checkov `RunnerRegistry`：provider orchestration + report merge 的架構相近。**
  - 查證來源：Checkov 的 `RunnerRegistry` 接收多個 runner，根據 framework/file filter 篩選 runner，平行執行後用 `_merge_reports()` / `merge_reports()` 將同類 report 合併，也支援 SARIF / JSON / CycloneDX 等多種輸出。
  - 對 Task 12 的啟發：providers 應只負責掃描並回傳 `ProviderScanResult`；`ProjectScanService` 負責 orchestration、錯誤隔離、結果合併、排序與 stage warnings。這符合本專案 Provider-Service 邊界。

- **OSV-Scanner：source attribution 和 grouping 可作為 evidence traceability 參考。**
  - 查證來源：OSV-Scanner source scan 會掃 lockfiles / SBOMs / git directories；JSON output 的 `results[].source.path` / `source.type` 會保留 package 來源，SARIF output 會把 vulnerability group 映射到 rule 與 physical location。
  - 對 Task 12 的啟發：每個 `ScanFact` 不只要有 kind/value，也要能追到 evidence source，例如 project-relative file path、config path、line 或 non-file source。這比只輸出不可追溯的「有 Redis」更適合 release-readiness report。
  - 修正原說法：OSV-Scanner 主要是 dependency / vulnerability scanner；它不是 ProjectScanService 這種多 provider RAG fact aggregator。可借鑑的是 source path、grouping、machine-readable output，不是完整掃描 domain。

- **Trivy：標準化 output 與 secret-safe reporting 可作為輸出契約參考。**
  - 查證來源：Trivy README 說明它可掃 container image、filesystem、git repository、Kubernetes 等 targets，scanner 類型包含 vulnerabilities、misconfigurations、secrets、licenses；官方 reporting docs 支援 JSON 與 SARIF 2.1.0，secret scanner 也會在報表中顯示 path / line / masked match。
  - 對 Task 12 的啟發：Task 12 的 aggregation output 應穩定、machine-readable、可做 snapshot test，且 secret-like value 必須延續 Task 5 masking，不可把完整 `.env` value 放進 facts/evidence。
  - 修正原說法：Trivy 的 SARIF 支援是 output/reporting 層參考，不代表 Systograph Task 12 要採 SARIF schema；`ai-system-map/v1` 仍是本專案 canonical contract。

### Task 12 實作時應新增或強化的測試

1. **provider exception isolation test**
   - 建立 mock provider，在 `collect()` 直接丟 exception。
   - 預期：`ProjectScanService` 不 crash，仍回傳其他 providers 的 facts，並產生一筆 provider-level `ParseIssue` 或 stage warning。

2. **dedupe + evidence merge test**
   - 讓兩個 mock providers 回傳同一個 canonical fact key，例如 `(kind="component_signal", normalized_name="redis")`，但 evidence 來源不同。
   - 預期：最終只保留一筆 fact，evidence append 且排序穩定。

3. **deterministic ordering test**
   - 用 providers 回傳不同順序的 facts/evidence/issues。
   - 預期：`ProjectScanService` 最終排序固定，例如 facts 依 `kind`、normalized name、`file`、`path` 排；evidence 依 `file`、`path`、`rule_id`、`id` 排；issues 依 `provider`、`scan_stage`、`file`、`message` 排。

4. **strict boundary test**
   - 輸入 Docker / dependency / config facts，其中包含 `redis`、`qdrant`、`openai` 等 signal。
   - 預期：Task 12 只輸出 raw facts/evidence，不產生 `ComponentSlot.detected`、endpoint final judgment、risk final judgment；這些留給 Task 13-15。

5. **secret-safe aggregation test**
   - 讓 provider 輸入含 secret-like value。
   - 預期：最終 facts/evidence 不包含完整 secret，snapshot 也不得出現未遮罩 value。

### 實作邊界收斂

```text
Providers
  -> ProviderScanResult[]
       facts[]      low-level observed facts
       evidence[]   traceable source references
       issues[]     parse/provider failures
  -> ProjectScanService
       normalize keys
       merge duplicates
       append evidence
       preserve partial failures
       deterministic sort
  -> raw scan aggregate
       still NOT component detection
       still NOT endpoint/risk/flow derivation
```

參考來源：

- Understand-Anything `merge-batch-graphs.py`: https://github.com/Lum1104/Understand-Anything/blob/main/understand-anything-plugin/skills/understand/merge-batch-graphs.py
- Understand-Anything `/understand` skill flow: https://github.com/Lum1104/Understand-Anything/blob/main/understand-anything-plugin/skills/understand/SKILL.md
- Understand-Anything `assemble-reviewer`: https://github.com/Lum1104/Understand-Anything/blob/main/understand-anything-plugin/agents/assemble-reviewer.md
- GitDiagram README: https://github.com/ahmedkhaleel2004/gitdiagram/blob/main/README.md
- Checkov `runner_registry.py`: https://github.com/bridgecrewio/checkov/blob/main/checkov/common/runners/runner_registry.py
- OSV-Scanner project source scanning docs: https://google.github.io/osv-scanner/usage/scan-source
- OSV-Scanner output docs: https://google.github.io/osv-scanner/output/
- Trivy README: https://github.com/aquasecurity/trivy/blob/main/README.md
- Trivy reporting docs: https://trivy.dev/docs/latest/configuration/reporting/
- Trivy secret scanning docs: https://www.trivy.dev/docs/v0.55/guide/scanner/secret/
- SARIF 2.1.0 OASIS standard: https://www.oasis-open.org/standard/sarif-v2-1-0/

## 新手提示
ProjectScanService 像資料收件中心：把每個 provider 的結果收齊、排好，但還不判斷誰代表什麼 RAG 元件。

## 視覺化說明
```text
┌──────────────────────────────────────────────────────────┐
│ Task 12a: TOML Rule Catalogs                             │
│ ┌────────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│ │ dependency_    │ │ docker_image │ │ code_pattern_    │ │
│ │ manifest_rules │ │ _rules.toml  │ │ rules.toml       │ │
│ │ .toml          │ │              │ │                  │ │
│ └───────┬────────┘ └──────┬───────┘ └────────┬─────────┘ │
│         └─────────────────┼──────────────────┘           │
│                           ↓                              │
│              RuleCatalogLoader                           │
└──────────────────────────┬───────────────────────────────┘
                           ↓
┌────────────┐ ┌──────────┐ ┌──────────┐
│ Filesystem │ │ Config   │ │ Docker   │
└─────┬──────┘ └────┬─────┘ └────┬─────┘
      │             │            │
      └─────────────┼────────────┘
                    ↓
┌──────────────┐ ┌────────────────┐
│ Dependencies │ │ Code Patterns  │
└──────┬───────┘ └───────┬────────┘
       └─────────┬───────┘
                 ↓
┌──────────────────────────┐
│ ProjectScanService        │
│ (Task 12)                 │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ ScanFact / Evidence       │
│ ParseIssue                │
└──────────────────────────┘
```
