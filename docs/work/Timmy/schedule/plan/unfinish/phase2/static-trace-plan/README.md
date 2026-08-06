# Static Trace Plan（00～20，含 00A、01A、01B、03A）

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

## Contract source of truth

本 README 只維護執行順序與 gate；**HTTP 端點、request/response 欄位、錯誤碼**以
`docs/API-GUIDE.md` 為準；**欄位語意、五態、activation、artifact lifecycle、
`ViewerLoadResult` / `GraphViewModel`、Step 8 viewer load、Rescan vs Apply** 以
`docs/MODEL-CONTRACT.md` 為準；**設計意圖與 compatibility path** 以
`docs/design/epic1-phase2.md` §16 為準。JSON payload 範例見
`docs/work/Timmy/design/EPIC1/frontend-json-handoff/`。

2026-07-08 contract audit 與 grill-me 拍板摘要見
[`CONTRACT-AUDIT-2026-07-08.md`](./CONTRACT-AUDIT-2026-07-08.md)。

Phase2 primary HTTP surface（current runtime 尚未全部實作；見 API-GUIDE §2）：

```http
POST /api/projects/import
POST /api/projects/{project_id}/scan-preflights
POST /api/scans
GET  /api/projects/{project_id}/map-builds
GET  /api/projects/{project_id}/map-builds/latest
GET  /api/map-builds/{build_id}
POST /api/map-builds/{base_build_id}/apply
POST /api/map-builds/{build_id}/detail-scans
POST /api/map-builds/{build_id}/trace
```

Plan `20` 已交付 additive `POST /api/projects/{project_id}/scan-preflights`；current payload、
typed error 與 one-run selection lifecycle 以 `docs/API-GUIDE.md` 為 canonical HTTP contract。

Step 9 review / manual decision 仍使用 current runtime 的
`POST /api/mapping-proposals`、`POST /api/mapping-proposals/{proposal_id}/decision`、
`GET|POST|PATCH /api/mappings`（API-GUIDE §5–6）；confirmed decision 透過 Apply replay
materialize 成新 `build_id`，不直接 mutate 舊 map artifact。

## 2026-07-07 UA staged rollout 對齊

本 README 只擁有 **執行順序、stage 與 gate**；不修改各編號 plan 的 task、acceptance
criteria 或實作內容。Phase2 Step 3 採三階段切換：

1. **Phase A：TOML primary。** 先用現有 Systograph scan TOML providers 打通 Step 1～7 publish +
   Step 8 viewer（**B1 initial build 不必跑 Step 9**）、deterministic
   `ProfileInferenceService` 與 Apply B1→B2。Plan 03A 在此階段即使用既有 nullable
   `ScanSnapshot.ua_analysis_result` 接縫，`sidecar=null` 必須可完成 build / Apply。
2. **Phase B：UA primary + TOML parity。** Gate-1 通過後才開始 Plan 16；UA structural
   facts 成為 primary，Systograph TOML providers 暫時並跑，只產 parity report。
3. **Phase C：UA only。** Plan 14 留下通過的 UA parity / fail-closed / Apply replay report
   後，Plan 18 才退役 Systograph TOML providers 的主掃描路徑。

Step 6 在 Plan 14 前維持純 Python deterministic assessment；Plan 17
`AssessmentOrchestrator` 與 AI semantic candidate flow deferred，不阻擋 Plan 14。Apply
始終不重跑 UA；它只使用 Plan 03A `ScanSnapshot.scan_result` 的 deterministic structural
facts / evidence 重跑 Step 4～7。`ua-analysis-result` /
`ScanSnapshot.ua_analysis_result` 在 Phase2 為 reserved nullable snapshot-internal slot：
`semantic` payload **不產生、不消費**；Phase B/C 可選保存 structural wrapper 供追溯，但
Step 4～7 / Apply / Viewer 只讀 `ScanSnapshot.scan_result`。不列 public artifact，也不新增
frontend contract 欄位。

## P0 Output Mapping

補充計劃中的概念檔名與本 repo 產品檔名對應如下；不得產生兩套重複 truth。

| 補充計劃概念 | Phase2 實際 artifact | Owner |
|---|---|---|
| UA structural facts（adapter 後） | `ScanSnapshot.scan_result`（`ScanFact[]` + `Evidence[]`） | 16 adapter → Step 4～7 consumer |
| `ua-analysis-result.json` / `ScanSnapshot.ua_analysis_result` | reserved nullable snapshot-internal wrapper slot；Phase2 **semantic=null**、**無 consumer**；Phase A 整欄為 `null`；Phase B/C 可選保存 structural wrapper 供追溯，但 Step 4～7 / Apply / Viewer **只讀 `scan_result`** | 03A（slot 預留）/ 16（Phase B/C 寫入） |
| `canonical-map.json` | `ai_system_map.json` | 00A / 13 |
| `call-graph.json` | `call_graph.json` | dynamic `00`（static inferred） |
| `dataflow-hints.json` | `dataflow_hints.json` | dynamic `00`（static inferred） |
| `execution-paths.json` | `execution_paths.json` | dynamic `00`（static inferred） |
| `capability-profiles.json` | `profile_signals.json` | 02 / 03 |
| `readiness-report.json` | `readiness_report.json` | 03 |
| `evidence_table.json` | `evidence_table.json` | dynamic `00`（flattened rows writer）；Plan `03`（lifecycle / atomic publish） |
| `system-map.mmd` | `system_map.mmd` | 06 |
| `execution-map.mmd` | `execution_map.mmd` | dynamic `00` |

> **消歧：** `ua-analysis-result` 檔名 ≠ Step 4～7 的 primary input。Canonical consumer 路徑
> 永遠是 `scan_result`；wrapper 與 `semantic` payload 不列 public artifact、不進 API
> `ArtifactRef[]`。

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

### Atomic publish set（對齊 MODEL-CONTRACT）

成功 build 的 **10 public sibling artifacts**（7 JSON + 3 render）。另 **+1** ephemeral
`GraphViewModel`（Step 7 API projection，**非** atomic-publish 磁碟檔）。對外勿寫「11 sibling
artifacts」（7+3=10；舊標題為計數錯誤）。

```text
JSON（7）
  ai_system_map.json
  profile_signals.json
  readiness_report.json
  call_graph.json
  dataflow_hints.json
  execution_paths.json
  evidence_table.json

Render（3）— export / report；Viewer 主畫布不依賴；Phase2 target 為 artifact_refs lazy load
  ai_system_map.md
  system_map.mmd
  execution_map.mmd
```

**不計入 7 JSON：** `scans/{scan_id}/snapshot.json`（Step 3 scan 輸入）、
`mappings/{mapping_id}.json`（Step 9 manual mapping 決策）— 屬 project state store，非
`output/{build_id}/` siblings。詳見 Plan `03A` local JSON layout。

Writer ownership：`03` = lifecycle orchestration；[`dynamic/00`](../dynamic-trace-plan/00-implement-static-call-graph-and-execution-path-mvp.md)
= static execution + `evidence_table.json` flattened rows；`06` = `system_map.mmd`
projection input。不得把上述 JSON nest 成單一 aggregate file。

## Pipeline Bridge Alignment（對照 Phase4 ASCII Map）

`phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md` 是 Step 1～9 的視覺 source of truth。
本資料夾的計畫需依下列 ownership 分工實作，避免把 Step 4 component bridge、Step 6
capability assessment 與 Step 7 projection 混在一起。

| Pipeline step | Owner plan | 語意 | TOML / Python 邊界 |
|---|---|---|---|
| Step 2 Boundary | `19`（已實作的 inventory selection policy catalog）+ `20`（metadata-only preflight / one-run exact-file與bounded recursive-directory override）；`16` Task 2 是後續獨立 UA enrichment | Plan 19 保存 schema/digest/audit/run digest；Plan 20 只完成 default inventory、可覆寫 soft exclusion、不可覆寫 safety與final allowlist；**不接 UA** | TOML 擁有 default path policy；Python 擁有preflight、bounded directory expansion、decision overlay、safety與final inventory；frontend只回傳scope decisions；UA adapter/request/parity由Plan 16另行負責 |
| Step 3 Scan | Phase A：既有 Systograph providers；Phase B：`16`；Phase C：`18` | Phase A 以 TOML facts 打通 E2E；Phase B 改為 UA structural primary + TOML parity；Phase C 退役 TOML 主掃描路徑 | 所有階段禁止 scan layer 寫 `plane_id` / `reference_node_id` |
| Step 4 Bridge 1 | `01B` + `01` + `03A` | `rule_id + evidence` → repo component / `unmapped_components[]` / candidate input | Python `component_bridge_registry.py`；risk/next-check TOML 只放文案 |
| Step 5 Index | `05`～`09` | validated map 的 read-only lookup | 不寫檔、不 validate、不 infer capability |
| Step 6 Bridge 2 | `01A` + `02` + `10` + `11` | repo component / unmapped / confirmed non-baseline candidates ↔ 10 planes / 52 reference nodes，產五態與 profiles | `ProfileInferenceService` 以 Python 算對位、五態、coverage；Plan 17 AI candidates deferred 且非 Plan 14 前置 |
| Step 7 Projection | `06` | 依 Step 6 結果畫 fixed reference map + repo overlay | backend projection only；frontend 不重算 |
| Step 9 Review / Apply | `01` + `03A` + `04` | Viewer/API 觸發 proposal，confirmed decision 由 Apply replay 產新 build | `MappingProposalService` 不在 Step 4 呼叫；Apply 跳 Step 3/UA，**4-1 bridge replay → 4-2 confirmed mappings overlay** → Step 4～7 |

白話邊界：**Step 4 不對 10 planes / 52 格；Step 6 才做底圖對位；Step 7 只畫，不重新判斷。**

## Step 6 子步驟與 Ownership 速查（6-1～6-6）

Step 6 在 **同一 validated build context**（`scan_id` / `build_id` / `environment_id`）內完成
所有 assessment **邏輯**；sibling JSON 的 **原子寫檔** 在 Step 7（Plan `03` + Plan `06`）。
Step 5 `SystemMapIndex` 僅為記憶體 lookup，不寫檔、不產生新 facts。

| 子步 | Owner service | 輸出 artifact / 結果 | 備註 |
|------|---------------|----------------------|------|
| **6-1** | `ProfileInferenceService` | `ProfileInferenceResult` → `profile_signals.json` | 52 格五態、15 profiles、Mapping Completeness 的 **唯一定案 owner**；plans `01A` + `02` + `10` + `11` |
| **6-2** | `ReadinessReportService` | `readiness_report.json` | evidence-backed delivery findings；不寫回 canonical map；Plan `03` |
| **6-3** | `StaticCallGraphService` | `call_graph.json` | static inferred；`runtime_verified=false`；owner dynamic `00` |
| **6-4** | `ShallowDataflowService` | `dataflow_hints.json` | 元件層 dataflow hints；owner dynamic `00` |
| **6-5** | `ExecutionPathRecoveryService` | `execution_paths.json` | 有序 execution steps；owner dynamic `00`；`execution_map.mmd` 為同 plan renderer |
| **6-6** | `OutputArtifactProvider.write_evidence_table(...)` | `evidence_table.json` | flattened evidence rows；**產生邏輯** owner dynamic `00`；**lifecycle 寫檔** Plan `03` |

Step 6 **不**引入 `AssessmentOrchestrator` 或 AI semantic candidates（Plan `17` deferred）。
`ProfileInferenceService` **不得**呼叫 `MappingProposalService` / manual mapping / LLM proposal
providers。

### Profile Inference 命名三層（禁止混用）

| 層級 | 名稱 | 說明 |
|------|------|------|
| **流程 / 服務** | **Profile Inference** / `ProfileInferenceService` | Step 6 Bridge 2（6-1）executable owner |
| **型別 / 磁碟** | `ProfileInferenceResult` / `profile_signals.json` | schema `profile-signals/v1`；artifact JSON **不得**使用 `profile_inference_result` 作為 top-level key |
| **API 欄位** | `ViewerLoadResult.profile_inference_result` | 與同 build 的 `profile_signals.json` **同一份**已驗證 payload |

### Step 6 artifact 與主畫布（GraphViewModel）消費邊界

| Artifact | 是否 feed 主 canvas | Viewer 載入策略 |
|----------|---------------------|-----------------|
| `profile_signals.json` | **是**（經 Step 7 `GraphProjectionService` 投影為 52 格、repo overlay、profile attachment） | 可 inline；缺失 → degraded base graph + warning |
| `readiness_report.json` | **否**（report / findings 面板） | inline 或 ref；非 graph topology 來源 |
| `call_graph.json` | **否** | `artifact_refs`；lazy / Inspector |
| `dataflow_hints.json` | **否** | 同上 |
| `execution_paths.json` | **否** | 同上；不得當 runtime trace |
| `evidence_table.json` | **否**（debug / join；details 仍用 map evidence） | `artifact_refs`；lazy |

`GraphViewModel` 由 Step 7 **即時投影**產生，**不是** viewer load 時 merge 上述 6 份 JSON。
Static execution 三件套 **不得**合成 `GraphViewModel.edges[]` 的 runtime path edge。

### Step 6 metadata catalogs（雙 TOML，非 executable）

| 檔案 | 擁有 | 不擁有 |
|------|------|--------|
| `capability_reference_map.toml`（Plan `01A`） | 10 planes / 52 reference node 的 id、label、order、`activation_applicable` | 五態規則、regex、scan matching |
| `profile_registry.toml`（Plan `11`） | 15 MVP profile 的 label、axis、default wording | profile trigger、threshold、reference node 對位 |

兩份 TOML **互不**定義對方的 executable 語意；bridge 1 在 Step 4 Python registry；bridge 2 在
`ProfileInferenceService`。

`filters.available[]` 由 Step 7 **`GraphProjectionService`** 計算；frontend 只 render
highlight/dim，**不得**自行推導 `matches_node_ids` / `matches_edge_ids`（見 `MODEL-CONTRACT.md`
§ `GraphViewModel`）。

## 目錄結構（依執行順序，非檔案編號）

計畫檔依 **stage / track** 分資料夾；檔名仍保留原編號（`00`～`20`）以便 cross-reference。
`README.md` 留在此根目錄。

```text
static-trace-plan/
├── README.md
├── s0-contract-compatibility/       ← S0；Gate-0 前
├── s1-pipeline-core/                ← S1 主線（01→01B→01A→02→03→03A→04）
├── s1-track-a-index-projection/     ← S1 並行 Track-A（05→09）
├── s1-track-b-profile-rules/        ← S1 並行 Track-B（10→11）
├── s1-track-d-inventory/            ← S1 並行 Track-D（19；建議 Plan 16 前）
├── s1-track-d-inventory-review/     ← S1 Track-D 後續（20；依 19；UA-independent）
├── s1-v2-cutover/                   ← S1 收尾（13）；Gate-1 前
├── s2-ua-integration/               ← S2（16）；Gate-1 後
├── s3-validation/                   ← S3 驗證（14）；Gate-2 後
├── s3-retirement/                   ← S3 退役（18→15）；Gate-3 / Gate-4 後
└── deferred/                        ← 不阻擋 Plan 14（12、17）
```

## 資料夾短版導覽

1. `s0-contract-compatibility/`：先凍結 legacy `rag-core-v1` 邊界，建立 v1→v2 compatibility
   path，讓後面可以安全切到 generic `ai-system-map/v2`。
2. `s1-pipeline-core/`：打通 Phase2 主線，包含 manual review、Step 4 component bridge、
   52 格 capability assessment、profile/readiness sidecars、Apply lineage 與本機 JSON persistence。
3. `s1-track-a-index-projection/`：把 validated map 做成 read-only lookup index，並由 backend
   產出 `GraphViewModel` projection，讓 frontend 只 render 不重算。
4. `s1-track-b-profile-rules/`：整理 profile / capability metadata 的 TOML 邊界；TOML 放 label
   與文案，五態判斷仍留在 Python。
5. `s1-track-d-inventory/`：Step 2 executable inventory selection policy catalog、source mode、
   audit 與 reproducibility digest。這是 Plan 16 `files[]` provenance 前置：未來 UA request
   必須使用同一份 final inventory，並攜帶 snapshot 保存的 policy digest，不得重新列檔。
6. `s1-track-d-inventory-review/`：在 Plan 19 default policy 上新增 metadata-only preflight、
   exact-file與bounded recursive-directory one-run override、不可覆寫 safety 與 frontend decision
   handoff；current scanner只消費同一 final inventory。**Plan 20 不接 UA**；UA integration由
   Plan 16後續獨立處理。
7. `s1-v2-cutover/`：在 compatibility gate 通過後，正式把 active surface 切到 v2，退役
   legacy extension output。
8. `s2-ua-integration/`：導入 Understand-Anything structural sidecar，讓 UA 成為 Step 3 primary，
   同時保留 TOML parity report 與 fail-closed 邊界。
9. `s3-validation/`：用本機真實專案與 fixtures 做 final validation，確認 Apply、UA parity、
   static execution artifacts 與安全邊界都可回溯。
10. `s3-retirement/`：在驗證報告保存後，退役 Systograph scan TOML providers 主掃描路徑，最後完成
   legacy v1 compatibility retirement。
11. `deferred/`：放 Phase2 static MVP 不阻擋的項目，例如 runtime boundary 文件與 AI
    `AssessmentOrchestrator` candidate flow。

## 計畫一覽（依執行順序）

### S0 — `s0-contract-compatibility/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 00 | [00-define-rag-core-v1-legacy-template-boundary.md](../../../finish/s0-contract-compatibility/00-define-rag-core-v1-legacy-template-boundary.md) | 凍結 legacy v1 template / characterization boundary | 起點 |
| 00A | [00A-introduce-ai-system-map-v2-compatibility-migration.md](../../../finish/s0-contract-compatibility/00A-introduce-ai-system-map-v2-compatibility-migration.md) | v1/v2 dual-read + adapter + compatibility gate | 依 `00`；完成後通過 Gate-0 |

### S1 主線 — `s1-pipeline-core/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 01 | [01-rework-manual-mapping-capability-candidates.md](../../../finish/s1-pipeline-core/01-rework-manual-mapping-capability-candidates.md) | Manual mapping；non-baseline capability candidate | 依 `00A` |
| 01B | [01B-extract-step4-component-bridge-registry.md](../../../finish/s1-pipeline-core/01B-extract-step4-component-bridge-registry.md) | Step 4 Python component bridge registry；不新增 TOML rule DSL | 依 `00A`, `01` |
| 01A | [01A-define-ai-system-capability-map-reference-catalog.md](../../../finish/s1-pipeline-core/01A-define-ai-system-capability-map-reference-catalog.md) | 固定 10-plane / 52-node reference catalog；TOML metadata boundary | 依 `00A`, `01`, `01B` |
| 02 | [02-implement-stackable-profile-inference.md](../../../finish/s1-pipeline-core/02-implement-stackable-profile-inference.md) | Step 6 Bridge 2：Stackable profile inference + 五態 assessment policy | 依 `01A`, `01B` |
| 03 | [03-consolidate-profile-sidecar-lifecycle.md](../../../finish/s1-pipeline-core/03-consolidate-profile-sidecar-lifecycle.md) | Artifact lifecycle + readiness report | 依 `02` |
| 03A | [03A-implement-apply-build-lineage-and-local-json-persistence.md](../../../finish/s1-pipeline-core/03A-implement-apply-build-lineage-and-local-json-persistence.md) | Scan/Build identity、Apply command、local JSON persistence | 依 `01`～`03` |
| 04 | [04-separate-profile-inference-from-mapping-proposal.md](../../../finish/s1-pipeline-core/04-separate-profile-inference-from-mapping-proposal.md) | Profile vs mapping 分離 | 依 `03A` |

### S1 Track-A — `s1-track-a-index-projection/`（與主線 `04` 後並行）

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 05 | [05-add-read-only-system-map-index.md](../../../finish/s1-track-a-index-projection/05-add-read-only-system-map-index.md) | Step 5 read-only SystemMapIndex；不做橋接或對位 | 依 `04` |
| 06 | [06-deepen-graph-projection-module.md](../../../finish/s1-track-a-index-projection/06-deepen-graph-projection-module.md) | Step 7 fixed reference map + repo overlay projection | 依 `05`, `02` |
| 07 | [07-expand-system-map-index-to-shared-lookup-contract.md](../../../finish/s1-track-a-index-projection/07-expand-system-map-index-to-shared-lookup-contract.md) | Index shared lookup | 依 `06` |
| 08 | [08-migrate-mapping-consumers-to-system-map-index.md](../../../finish/s1-track-a-index-projection/08-migrate-mapping-consumers-to-system-map-index.md) | Consumer migration | 依 `07` |
| 09 | [09-consolidate-legacy-system-map-lookups.md](../../../finish/s1-track-a-index-projection/09-consolidate-legacy-system-map-lookups.md) | Legacy lookup 收斂 | 依 `08` |

### S1 Track-B — `s1-track-b-profile-rules/`（與 Track-A `05+` 並行）

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 10 | [10-define-profile-rule-catalog-boundary.md](../../../finish/s1-track-b-profile-rules/10-define-profile-rule-catalog-boundary.md) | Profile rule catalog 邊界 | 可與 `05`+ 並行 |
| 11 | [11-migrate-profile-rule-metadata-to-toml-catalog.md](../../../finish/s1-track-b-profile-rules/11-migrate-profile-rule-metadata-to-toml-catalog.md) | Profile rule TOML metadata | 依 `10` |

### S1 Track-D — `s1-track-d-inventory/`（建議 Plan 16 前完成）

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 19 | [19-add-scan-inventory-rules-toml.md](../../../finish/s1-track-d-inventory/19-add-scan-inventory-rules-toml.md) | Step 2 executable `scan_inventory_rules.toml`、audit/provenance/digest（已實作） | 無 hard gate |

### S1 Track-D Review — `s1-track-d-inventory-review/`（Plan 19 後；不接 UA）

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 20 | [20-add-user-controlled-scan-inventory-selection.md](../../../finish/s1-track-d-inventory-review/20-add-user-controlled-scan-inventory-selection.md) | Metadata-only preflight、exact-file／bounded recursive-directory per-run selection、frontend decision handoff、final inventory audit；UA deferred | 依 `19`；納入 Gate-1；不實作 UA integration |

### S1 收尾 — `s1-v2-cutover/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 13 | [13-retire-legacy-extension-contract.md](../../../finish/s1-v2-cutover/13-retire-legacy-extension-contract.md) | 00A gate 後 active v2 cutover + extension 退役（done：backend 2026-07-17、frontend handoff `25f2223` 完成，contract test 強制 `migrate` 消費者為 0） | 需 Gate-0；納入 Gate-1 E2E |

### S2 — `s2-ua-integration/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 16 | [16-implement-understand-anything-sidecar-service.md](./s2-ua-integration/16-implement-understand-anything-sidecar-service.md) | UA sidecar service、request/result schema、Step 2 enrichment、parity harness | 依 `00A`, `01B`, `03A` 且需 Gate-1 |
| 16A | [16A-q3-lv2-call-graph-flow-visualization.md](./s2-ua-integration/16A-q3-lv2-call-graph-flow-visualization.md) | Q3 決策：選 Lv2（UA call graph → flow 可視化）；一份 call 資料餵 ①context_flow ②FlowDerivation ③static execution ④frontend ⑤flow 敘事 | 決策紀錄；實作仍依 16／16C／16D |
| 16B | [16B-ua-sidecar-io-adapter-reference.md](./s2-ua-integration/16B-ua-sidecar-io-adapter-reference.md) | 技術參考（2026-07-29 查核）：三支 UA script 實測 I/O 與 runtime 需求、Systograph 側接縫錨點、adapter 三條硬規則（四元組對齊／direct 門檻／evidence id 穩定）、open questions | 參考附件；Plan 16 Task 1/3/4/6 實作前先讀 |
| 16C | [16C-component-attribution-and-edge-derivation.md](./s2-ua-integration/16C-component-attribution-and-edge-derivation.md) | 檔案層→元件層：residence index、L1 call / L2 import / L3 模板降級、relationship TOML | 依 Plan 16 Task 3 + 13.7/13.8；Gate-2 後 |
| 16D | [16D-call-priority-consumer-cutover.md](./s2-ua-integration/16D-call-priority-consumer-cutover.md) | 消費者改 call 優先：materialization 合併、static execution 同源、profile/G5c、可選關 L3、viewer 煙測 | 依 16C；建議納入 Plan 14 驗證語意 |
| 16E | [16E-ua-coverage-gaps-and-llm-boundary.md](./s2-ua-integration/16E-ua-coverage-gaps-and-llm-boundary.md) | UA 三個覆蓋缺口（函式外建構／工廠間接／外部 import）根因與確定性解法；LLM 不得進掃描路徑之裁定；證據來源硬化 | 決策 + 參考；**G3 建議先於 Plan 16 adapter 完成**，G1 影響 Plan 18 退役準則 |
| — | [s2-ua-integration/README.md](./s2-ua-integration/README.md) | 該資料夾的閱讀指南：六份文件索引、依目的的閱讀順序、名詞對照表、review 檢查點 | 入口文件；第一次接觸 S2 先讀 |

### S3 驗證 — `s3-validation/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 14 | [14-local-project-import-and-test.md](./s3-validation/14-local-project-import-and-test.md) | Real-world static validation + UA parity report | 需 Gate-2；不依賴 Plan 17 |

### S3 退役 — `s3-retirement/`

| # | 檔案 | 主題 | Gate |
|---:|---|---|---|
| 18 | [18-retire-systograph-scan-toml-providers-after-parity.md](./s3-retirement/18-retire-systograph-scan-toml-providers-after-parity.md) | Plan 14 parity gate 後退役 Systograph scan TOML providers 主掃描路徑 | 需 Gate-3 |
| 15 | [15-complete-legacy-v1-retirement-after-compatibility.md](../../refactor/15-complete-legacy-v1-retirement-after-compatibility.md) | 相容驗證後完全遷移 / v1 compatibility 退役（2026-08-06 已搬至 `refactor/`） | 需 Gate-4 |

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

S1  TOML-primary pipeline（Step 3 = 現有 Systograph scan TOML providers）
    s1-pipeline-core/: 01 -> 01B -> 01A -> 02 -> 03 -> 03A* -> 04
         ├─ s1-track-a-index-projection/: 05 -> 06 -> 07 -> 08 -> 09
         ├─ s1-track-b-profile-rules/: 10 -> 11（與 05+ 並行）
         ├─ Track-C: [dynamic/00 — static call graph & execution path MVP](../dynamic-trace-plan/00-implement-static-call-graph-and-execution-path-mvp.md)
              （03 + 05 穩定後、**Gate-1 前完成**；產出 `call_graph.json`、
              `dataflow_hints.json`、`execution_paths.json`、`evidence_table.json`、
              `execution_map.mmd`，與 Plan 03 atomic publish 對齊 `docs/MODEL-CONTRACT.md`）
         └─ Track-D: s1-track-d-inventory/: 19
                     -> s1-track-d-inventory-review/: 20
                     （default policy -> metadata-only preflight -> one-run decision -> final inventory；
                      **Gate-1 前完成**；Plan 20 到current providers/snapshot為止，**不接 UA**；
                      UA request/adapter/parity由Plan 16後續獨立實作）
    s1-v2-cutover/: 13
    ──[Gate-1: B1 Step 1～7 + Step 8 viewer（initial scan 不必 Step 9）；
         Plan 19→20 inventory policy/preflight/decision/final-allowlist E2E（UA不執行）；
         另驗 Step 9 decision + Apply B1→B2（4-1→4-2→4～7）；
         P0 static execution artifacts；`ua_analysis_result=None`；`runtime_verified=false`]──►

S2  s2-ua-integration/
    16（UA structural primary + TOML parity harness）
    ──[Gate-2: UA structural + snapshot sidecar + fail-closed + parity report]──►
    16C（檔案→元件邊推導 L1/L2/L3）
    16D（消費者 call 優先 cutover；可與 14 驗證重疊）

S3  s3-validation/ + s3-retirement/
    14（含 UA parity；建議含 16D call-priority 證據；不要求 Plan 17）
    ──[Gate-3: Plan 14 validation + UA parity report]──►
    18（退役 Systograph TOML providers 主掃描路徑）
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
| Gate-1 | **B1 path：** TOML-primary Step 1～7 publish + Step 8 viewer（**initial scan 不必跑 Step 9**）。**Inventory path：** Plan 19 default policy + Plan 20 metadata-only preflight / exact-file與bounded recursive-directory one-run decision / hard-safety revalidation 完成；current providers只讀同一final inventory，pending/stale不建立`scan_id`，target repo不被修改；**Plan 20不建立或呼叫UA request/service/parity**。**Apply path（Gate-1 必驗）：** Step 9 decision + Apply B1→B2（跳 Step 3/UA；**4-1 bridge replay → 4-2 overlay** → Step 4～7）；共用 snapshot；`ua_analysis_result=None` 可通過。Track-C `dynamic/00` 已接入 Step 6，同一 validated build 產出 P0 static execution artifacts（`call_graph.json`、`dataflow_hints.json`、`execution_paths.json`、`evidence_table.json`、`execution_map.mmd`），皆標 `runtime_verified=false` / static inferred，**不得宣稱 runtime proof** | Plan 16（另行接 UA） |
| Gate-2 | Plan 16 UA structural path、snapshot internal sidecar、fail-closed 與 parity harness 通過 | Plan 14 |
| Gate-3 | Plan 14 final validation 完成並保存 UA parity / no-UA-rerun report | Plan 18 |
| Gate-4 | Plan 18 provider retirement 通過，且 Plan 14 report 可回溯 | Plan 15 |

**Scheduling override：** 個別 plan 內容保持不變；若既有 dependency 敘事把 Plan 17 列為
Plan 14 hard prerequisite，執行排程以本 README 為準。Plan 14 使用 deterministic
`ProfileInferenceService`，AI semantic candidates 維持空集合即可。

## 產品語意（摘要）

- **Input**：AI system repo / workflow artifacts，不預設 RAG 或 Agent。
- **Legacy RAG template**：`rag-core-v1` 只作 v1 compatibility template 與 migration
  adapter input；**freeze at `@1.0.0` / 13 slots / 2 flows**；Phase2 變更在 v2 map、
  profiles、readiness，不在 `rag-core-v1.json`；active assessment surface 使用 generic v2
  map、profiles 與 readiness findings。
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
- **Component bridge（Step 4 產 map 主路徑）**：immutable scan facts 經 **確定性 Python
  bridge rule**（`component_bridge_registry`）materialize 成 generic
  `components[]` / `edges[]` / `unmapped_components[]`；每筆必須有 `evidence_ids`。
  **不是** `rag-core-v1` slot 填格；**不是**底圖 52 格對位；**不是** proposal generator。
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
