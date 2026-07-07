# Static Trace Plan（00～19，含 00A、01A、01B、03A）

靜態 release-readiness 主線：read-only scan、Review scanner suggestions（internal
manual decision lifecycle）、profile inference、system map v2、static inferred
execution mapping、graph projection、legacy cutover、final validation。

P0 補充後，static path 不只回答「有哪些 components」，也要回答：

```text
entrypoint -> handler/service -> retriever/reranker/context builder -> LLM -> output
```

這是 **evidence-backed inferred execution map**，不是 runtime proof。所有 execution
path、call edge 與 dataflow hint 必須標示 static-only 限制，並以 evidence ids 回溯
到 source code、config 或 workflow JSON。

## 2026-07-07 UA staged rollout 對齊

本 README 只擁有 **執行順序、stage 與 gate**；不修改各編號 plan 的 task、acceptance
criteria 或實作內容。Phase2 Step 3 採三階段切換：

1. **Phase A：TOML primary。** 先用現有 KAI scan TOML providers 打通 Step 1～9、
   deterministic `ProfileInferenceService` 與 Apply B1→B2。Plan 03A 在此階段即使用既有
   nullable `ScanSnapshot.ua_analysis_result` 接縫，`sidecar=null` 必須可完成 build / Apply。
2. **Phase B：UA primary + TOML parity。** Gate-1 通過後才開始 Plan 16；UA structural
   facts 成為 primary，KAI TOML providers 暫時並跑，只產 parity report。
3. **Phase C：UA only。** Plan 14 留下通過的 UA parity / fail-closed / Apply replay report
   後，Plan 18 才退役 KAI TOML providers 的主掃描路徑。

Step 6 在 Plan 14 前維持純 Python deterministic assessment；Plan 17
`AssessmentOrchestrator` 與 AI semantic candidate flow deferred，不阻擋 Plan 14。Apply
始終不重跑 UA；它只使用 Plan 03A `ScanSnapshot.scan_result` 的 deterministic structural
facts / evidence 重跑 Step 4～7。`ua-analysis-result` semantic internal sidecar 在 Phase2 僅
保存、無消費者，不列 public artifact，也不新增 frontend contract 欄位。

## P0 Output Mapping

補充計劃中的概念檔名與本 repo 產品檔名對應如下；不得產生兩套重複 truth。

| 補充計劃概念 | Phase2 實際 artifact | Owner |
|---|---|---|
| `ua-analysis-result.json` | reserved nullable ScanSnapshot internal sidecar（非 public artifact；Phase2 active path 不產生、不消費） | 16 / 03A |
| `canonical-map.json` | `ai_system_map.json` | 00A / 13 |
| `call-graph.json` | `call_graph.json` | dynamic `00`（static inferred） |
| `dataflow-hints.json` | `dataflow_hints.json` | dynamic `00`（static inferred） |
| `execution-paths.json` | `execution_paths.json` | dynamic `00`（static inferred） |
| `capability-profiles.json` | `profile_signals.json` | 02 / 03 |
| `readiness-report.json` | `readiness_report.json` | 03 |
| `evidence_table.json` | `evidence_table.json` | 03 / dynamic `00` |
| `system-map.mmd` | `system_map.mmd` | 06 |
| `execution-map.mmd` | `execution_map.mmd` | dynamic `00` |

Capability assessment 與 profile aggregate 統一使用
`detected / partial / undetermined / not_detected / conflicted`。`not_detected` 只有在
相關 scanner 完整成功且沒有 evidence 時成立；coverage 不足使用 `undetermined`。
`inferred` 不新增為 status；static/runtime 邊界仍用 `analysis_depth`、
`evidence_strength`、`runtime_verified=false`、limitations 與 `static_inferred` 表達。

## Artifact Boundary

Phase2 P0 build 產出的是 **多個獨立 sibling artifacts**，每個 JSON 檔案都有自己的
schema、writer 與 validation gate。

- `ai_system_map.json` 是 canonical map，保留 canonical evidence refs。
- `evidence_table.json` 是獨立輸出的 flattened / debug-friendly evidence table。
- `call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、`profile_signals.json`
  與 `readiness_report.json` 各自有 schema、writer 與 validation gate。
- Phase2 後若導入資料庫，每個 JSON artifact 應可對應到獨立 table 或 table group；
  Phase2 不先把它們包成一個 aggregate JSON。

## Pipeline Bridge Alignment（對照 Phase4 ASCII Map）

`phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md` 是 Step 1～9 的視覺 source of truth。
本資料夾的計畫需依下列 ownership 分工實作，避免把 Step 4 component bridge、Step 6
capability assessment 與 Step 7 projection 混在一起。

| Pipeline step | Owner plan | 語意 | TOML / Python 邊界 |
|---|---|---|---|
| Step 2 Boundary | `19`（inventory rules TOML）+ `16` Task 2（UA enrichment） | file inventory include / ignore metadata + 語言 / category / 行數 enrichment | TOML 只放 include / ignore boundary metadata；boundary 決策與 policy overlay 在 Python |
| Step 3 Scan | Phase A：既有 KAI providers；Phase B：`16`；Phase C：`18` | Phase A 以 TOML facts 打通 E2E；Phase B 改為 UA structural primary + TOML parity；Phase C 退役 TOML 主掃描路徑 | 所有階段禁止 scan layer 寫 `plane_id` / `reference_node_id` |
| Step 4 Bridge 1 | `01B` + `01` + `03A` | `rule_id + evidence` → repo component / `unmapped_components[]` / candidate input | Python `component_bridge_registry.py`；risk/next-check TOML 只放文案 |
| Step 5 Index | `05`～`09` | validated map 的 read-only lookup | 不寫檔、不 validate、不 infer capability |
| Step 6 Bridge 2 | `01A` + `02` + `10` + `11` | repo component / unmapped / confirmed non-baseline candidates ↔ 10 planes / 52 reference nodes，產五態與 profiles | `ProfileInferenceService` 以 Python 算對位、五態、coverage；Plan 17 AI candidates deferred 且非 Plan 14 前置 |
| Step 7 Projection | `06` | 依 Step 6 結果畫 fixed reference map + repo overlay | backend projection only；frontend 不重算 |
| Step 9 Review / Apply | `01` + `03A` + `04` | Viewer/API 觸發 proposal，confirmed decision 由 Apply replay 產新 build | `MappingProposalService` 不在 Step 4 呼叫；Apply 跳 Step 3 |

白話邊界：**Step 4 不對 10 planes / 52 格；Step 6 才做底圖對位；Step 7 只畫，不重新判斷。**

## 目錄結構（依執行順序，非檔案編號）

計畫檔依 **stage / track** 分資料夾；檔名仍保留原編號（`00`～`19`）以便 cross-reference。
`README.md` 留在此根目錄。

```text
static-trace-plan/
├── README.md
├── s0-contract-compatibility/       ← S0；Gate-0 前
├── s1-pipeline-core/                ← S1 主線（01→01B→01A→02→03→03A→04）
├── s1-track-a-index-projection/     ← S1 並行 Track-A（05→09）
├── s1-track-b-profile-rules/        ← S1 並行 Track-B（10→11）
├── s1-track-d-inventory/            ← S1 並行 Track-D（19；建議 Plan 16 前）
├── s1-v2-cutover/                   ← S1 收尾（13）；Gate-1 前
├── s2-ua-integration/               ← S2（16）；Gate-1 後
├── s3-validation/                   ← S3 驗證（14）；Gate-2 後
├── s3-retirement/                   ← S3 退役（18→15）；Gate-3 / Gate-4 後
└── deferred/                        ← 不阻擋 Plan 14（12、17）
```

## 計畫一覽（依執行順序）

### S0 — `s0-contract-compatibility/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 00 | [00-define-rag-core-v1-legacy-template-boundary.md](./s0-contract-compatibility/00-define-rag-core-v1-legacy-template-boundary.md) | 凍結 legacy v1 template / characterization boundary | 起點 |
| 00A | [00A-introduce-ai-system-map-v2-compatibility-migration.md](./s0-contract-compatibility/00A-introduce-ai-system-map-v2-compatibility-migration.md) | v1/v2 dual-read + adapter + compatibility gate | 依 `00`；完成後通過 Gate-0 |

### S1 主線 — `s1-pipeline-core/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 01 | [01-rework-manual-mapping-capability-candidates.md](./s1-pipeline-core/01-rework-manual-mapping-capability-candidates.md) | Manual mapping；non-baseline capability candidate | 依 `00A` |
| 01B | [01B-extract-step4-component-bridge-registry.md](./s1-pipeline-core/01B-extract-step4-component-bridge-registry.md) | Step 4 Python component bridge registry；不新增 TOML rule DSL | 依 `00A`, `01` |
| 01A | [01A-define-ai-system-capability-map-reference-catalog.md](./s1-pipeline-core/01A-define-ai-system-capability-map-reference-catalog.md) | 固定 10-plane / 52-node reference catalog；TOML metadata boundary | 依 `00A`, `01`, `01B` |
| 02 | [02-implement-stackable-profile-inference.md](./s1-pipeline-core/02-implement-stackable-profile-inference.md) | Step 6 Bridge 2：Stackable profile inference + 五態 assessment policy | 依 `01A`, `01B` |
| 03 | [03-consolidate-profile-sidecar-lifecycle.md](./s1-pipeline-core/03-consolidate-profile-sidecar-lifecycle.md) | Artifact lifecycle + readiness report | 依 `02` |
| 03A | [03A-implement-apply-build-lineage-and-local-json-persistence.md](./s1-pipeline-core/03A-implement-apply-build-lineage-and-local-json-persistence.md) | Scan/Build identity、Apply command、local JSON persistence | 依 `01`～`03` |
| 04 | [04-separate-profile-inference-from-mapping-proposal.md](./s1-pipeline-core/04-separate-profile-inference-from-mapping-proposal.md) | Profile vs mapping 分離 | 依 `03A` |

### S1 Track-A — `s1-track-a-index-projection/`（與主線 `04` 後並行）

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 05 | [05-add-read-only-system-map-index.md](./s1-track-a-index-projection/05-add-read-only-system-map-index.md) | Step 5 read-only SystemMapIndex；不做橋接或對位 | 依 `04` |
| 06 | [06-deepen-graph-projection-module.md](./s1-track-a-index-projection/06-deepen-graph-projection-module.md) | Step 7 fixed reference map + repo overlay projection | 依 `05`, `02` |
| 07 | [07-expand-system-map-index-to-shared-lookup-contract.md](./s1-track-a-index-projection/07-expand-system-map-index-to-shared-lookup-contract.md) | Index shared lookup | 依 `06` |
| 08 | [08-migrate-mapping-consumers-to-system-map-index.md](./s1-track-a-index-projection/08-migrate-mapping-consumers-to-system-map-index.md) | Consumer migration | 依 `07` |
| 09 | [09-consolidate-legacy-system-map-lookups.md](./s1-track-a-index-projection/09-consolidate-legacy-system-map-lookups.md) | Legacy lookup 收斂 | 依 `08` |

### S1 Track-B — `s1-track-b-profile-rules/`（與 Track-A `05+` 並行）

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 10 | [10-define-profile-rule-catalog-boundary.md](./s1-track-b-profile-rules/10-define-profile-rule-catalog-boundary.md) | Profile rule catalog 邊界 | 可與 `05`+ 並行 |
| 11 | [11-migrate-profile-rule-metadata-to-toml-catalog.md](./s1-track-b-profile-rules/11-migrate-profile-rule-metadata-to-toml-catalog.md) | Profile rule TOML metadata | 依 `10` |

### S1 Track-D — `s1-track-d-inventory/`（建議 Plan 16 前完成）

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 19 | [19-add-scan-inventory-rules-toml.md](./s1-track-d-inventory/19-add-scan-inventory-rules-toml.md) | Step 2 `scan_inventory_rules.toml`（include / ignore boundary metadata） | 無 hard gate |

### S1 收尾 — `s1-v2-cutover/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 13 | [13-retire-legacy-extension-contract.md](./s1-v2-cutover/13-retire-legacy-extension-contract.md) | 00A gate 後 active v2 cutover + extension 退役 | 需 Gate-0；納入 Gate-1 E2E |

### S2 — `s2-ua-integration/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 16 | [16-implement-understand-anything-sidecar-service.md](./s2-ua-integration/16-implement-understand-anything-sidecar-service.md) | UA sidecar service、request/result schema、Step 2 enrichment、parity harness | 依 `00A`, `01B`, `03A` 且需 Gate-1 |

### S3 驗證 — `s3-validation/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 14 | [14-local-project-import-and-test.md](./s3-validation/14-local-project-import-and-test.md) | Real-world static validation + UA parity report | 需 Gate-2；不依賴 Plan 17 |

### S3 退役 — `s3-retirement/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 18 | [18-retire-kai-scan-toml-providers-after-parity.md](./s3-retirement/18-retire-kai-scan-toml-providers-after-parity.md) | Plan 14 parity gate 後退役 KAI scan TOML providers 主掃描路徑 | 需 Gate-3 |
| 15 | [15-complete-legacy-v1-retirement-after-compatibility.md](./s3-retirement/15-complete-legacy-v1-retirement-after-compatibility.md) | 相容驗證後完全遷移 / v1 compatibility 退役 | 需 Gate-4 |

### Deferred — `deferred/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 12 | [12-add-runtime-component-trace-contract.md](./deferred/12-add-runtime-component-trace-contract.md) | Static vs runtime boundary（非實作） | 不 gate static MVP |
| 17 | [17-implement-assessment-orchestrator-candidate-flow.md](./deferred/17-implement-assessment-orchestrator-candidate-flow.md) | Step 6 thin AssessmentOrchestrator candidate flow | **Deferred；不阻擋 Plan 14** |

## 建議執行順序

```text
S0  s0-contract-compatibility/
    00 -> 00A
    ──[Gate-0: legacy boundary + v2 compatibility]──►

S1  TOML-primary pipeline（Step 3 = 現有 KAI scan TOML providers）
    s1-pipeline-core/: 01 -> 01B -> 01A -> 02 -> 03 -> 03A* -> 04
         ├─ s1-track-a-index-projection/: 05 -> 06 -> 07 -> 08 -> 09
         ├─ s1-track-b-profile-rules/: 10 -> 11（與 05+ 並行）
         ├─ Track-C: dynamic/00（03 + 05 穩定後，Plan 14 前完成）
         └─ s1-track-d-inventory/: 19（建議 Plan 16 前完成）
    s1-v2-cutover/: 13
    ──[Gate-1: TOML Step 1～9 E2E + Apply B1→B2；sidecar=null 可通過]──►

S2  s2-ua-integration/
    16（UA structural primary + TOML parity harness）
    ──[Gate-2: UA structural + snapshot sidecar + fail-closed + parity report]──►

S3  s3-validation/ + s3-retirement/
    14（含 UA parity；不要求 Plan 17）
    ──[Gate-3: Plan 14 validation + UA parity report]──►
    18（退役 KAI TOML providers 主掃描路徑）
    ──[Gate-4: Plan 18 通過 + Plan 14 report 已保存]──►
    15（退役 legacy v1 compatibility）

deferred/
    17 = AssessmentOrchestrator / AI semantic candidate flow
    12 = runtime boundary 文件
    dynamic/01 = runtime trace implementation

* 03A 在 S1 即使用既有 `ua_analysis_result: UaAnalysisResult | None = None`；
  不必等待 Plan 16，且 Gate-1 必須驗證 sidecar=null 的 initial build / Apply。
```

## Do-not-start-until Gates

| Gate | 通過條件 | 解鎖 |
|---|---|---|
| Gate-0 | Plan 00 legacy characterization 與 Plan 00A v2 compatibility gate 完成 | S1 正式 v2 consumer work、Plan 13 |
| Gate-1 | TOML-primary Step 1～9 E2E；Apply B1→B2 共用 snapshot；`ua_analysis_result=None` 可通過 | Plan 16 |
| Gate-2 | Plan 16 UA structural path、snapshot internal sidecar、fail-closed 與 parity harness 通過 | Plan 14 |
| Gate-3 | Plan 14 final validation 完成並保存 UA parity / no-UA-rerun report | Plan 18 |
| Gate-4 | Plan 18 provider retirement 通過，且 Plan 14 report 可回溯 | Plan 15 |

**Scheduling override：** 個別 plan 內容保持不變；若既有 dependency 敘事把 Plan 17 列為
Plan 14 hard prerequisite，執行排程以本 README 為準。Plan 14 使用 deterministic
`ProfileInferenceService`，AI semantic candidates 維持空集合即可。

## 產品語意（摘要）

- **Input**：AI system repo / workflow artifacts，不預設 RAG 或 Agent。
- **Legacy RAG template**：`rag-core-v1` 只作 v1 compatibility template 與 migration
  adapter input；active assessment surface 使用 generic v2 map、profiles 與 readiness findings。
- **Source traceability**：citation / source mapping 不屬於 hard baseline；只作
  `readiness_report.json` 的 `source_traceability` finding。
- **Readiness findings**：`readiness_report.json.findings[]` 使用固定 shape；每個 finding
  必須有 category/status/severity，且至少有 `evidence_ids` 或 `evidence_gap`。
- **Execution map**：static inferred path；顯示 query 大致如何從 entrypoint 流向
  components/edges/output，但不得宣稱已 runtime verified。
- **Profile**：可堆疊的 capability overlay；使用者確認的是 **mapping**，不是 profile
  分類。
- **Capability map**：固定 reference map 與 repo evidence overlay 共用同一 canvas；
  reference node 永遠存在，狀態描述特定 repo/build/environment 的對應結果。
- **Component bridge**：Step 4 只把 scan facts 轉成 repo component / unmapped /
  candidate input；它不是底圖對位，也不是 proposal generator。
- **Capability bridge**：Step 6 才把 validated repo facts 對到 10 planes / 52 reference
  nodes，並產生五態、profiles 與 Mapping Completeness。
- **Mapping Completeness**：`detected=1`、`not_detected=1`、`partial=0.5`、
  `undetermined/conflicted=0`；它是判定完成度，不是 readiness 或產品品質。
- **Activation**：只對 `activation_applicable=true` 的 reference node 顯示
  `enabled/disabled/conditional/unknown/conflicted`；其餘為 `not_applicable`。
- **Review UI naming**：主要 UI 名稱使用 `Review scanner suggestions` / `檢查 scanner 建議`；
  `Manual Mapping` 只保留為 internal/durable decision lifecycle 名稱。
- **Apply confirmed decisions**：使用者按「套用 N 項確認並建立新版本」後，呼叫
  `POST /api/map-builds/{base_build_id}/apply`，沿用同一 `scan_id` 的 snapshot 建立新
  `build_id`；不得重新掃描 repo 或直接修改舊 map。
- **Phase2 persistence**：使用 repository protocols + atomic local JSON adapter 保存
  project、scan snapshot、build lineage 與 manual mappings；正式資料庫留在 Phase2 完成後。
- **Viewer assessment copy**：`已確認`、`部分確認`、`無法判斷`、`未偵測到`、
  `證據衝突`；review lifecycle 另用 `Needs review / Confirmed / Skipped`。
- **Runtime trace**：不得由 static profile 或 static execution map 假裝成實際 runtime
  path；runtime implementation 從 dynamic `01` 開始。
