# Understand-Anything Sidecar Service 實作計畫

Status: planned — **blocked until Gate-1 passes**（2026-07-07 UA-primary 決策）

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。
>
> **相關決策（2026-07-29 Q3）：** 選 **Lv2**——UA call graph 經 Adapter 變成 direct
> evidence 後，同一份資料升級 `context_flow`、FlowDerivation、靜態執行產物與前端 flow
> 可視化。詳見
> [`16A-q3-lv2-call-graph-flow-visualization.md`](./16A-q3-lv2-call-graph-flow-visualization.md)。
> Plan 16 本體仍以 sidecar + adapter + parity 為界；FlowDerivation／profile wiring 升級
> 依 16A §6 後續落地，不阻塞本 plan 的 Gate-2 structural path。
>
> **技術參考（2026-07-29 查核後新增）：** 三支 UA script 的實測 I/O、runtime 需求、
> KAI 側接縫錨點（含 `scan_routes.py:294` 預留孔位）、adapter 三條硬規則與
> open questions，見
> [`16B-ua-sidecar-io-adapter-reference.md`](./16B-ua-sidecar-io-adapter-reference.md)。
> Task 1/3/4/6 實作前先讀。
>
> **⚠️ 前置計畫（2026-07-29 查核後新增，兩者皆不依賴 UA、可在 Gate-1 前完成）：**
>
> | 前置 | 不做的後果（實測） |
> |------|--------------------|
> | [`../s1-v2-cutover/13.7.md`](../s1-v2-cutover/13.7.md) — bridge kind → 52 格字彙對齊 | UA 只替換 fact 來源，元件仍以 bridge kind 表示；`_TYPE_TO_NODES` 未補齊時，UA 掃得再準 52 格照樣點不亮（今天 4/52 靠 legacy slot 撐，拆掉後 1/52） |
> | [`../s1-v2-cutover/13.8.md`](../s1-v2-cutover/13.8.md) — profile relationship 端點約束 | 關係查表不驗邊的端點；UA 產出的邊數量級遠大於現有 12 條，無約束時任何同名邊都會點亮卡片（假陽性已實證） |
>
> 另見 16A §7.2：12 張 profile 卡的關係語意需求清單，是 adapter call hints
> 設計的驗收輸入。**UA 端不得自創同義關係名**（會重演 G5 字彙漂移）。

## 目標

新增 `UnderstandAnythingAnalysisService`，讓 KAI-Mind 在 Step 2 boundary 完成後呼叫
Understand-Anything sidecar，取得 deterministic structural facts（含 **call hints /
誰呼叫誰**，以支援 16A Lv2）；semantic sidecar slot 保持 nullable deferred。
Gate-1 後的 Phase B 由 UA 擔任 Step 3 primary 掃描來源；既有 KAI scan TOML providers
在過渡期只做 parity 對比。Gate-1 前的 Phase A 仍由現有 KAI providers 擔任 primary。

## 架構

```text
Step 2 FileInventory（KAI boundary owner）
  + inventory enrichment（語言 / fileCategory / 行數，移植自 scan-project）
  -> UnderstandAnythingAnalysisService
       NodeRuntimePreflight
       UnderstandAnythingSubprocessRunner
       UnderstandAnythingResultValidator
       UaStructuralAdapter
  -> kai-mind-analyze.mjs
       extract-import-map
       compute-batches
       extract-structure
       file-analyzer（bounded LLM）deferred；不執行
       ua-analysis-result.json（Phase B/C 可選保存；semantic=null）
       structural -> UaStructuralAdapter -> ScanSnapshot.scan_result（Step 4～7 consumer）
       semantic   -> reserved nullable slot；Phase2 不執行 file-analyzer、不產生、不消費
```

Sidecar request / result schema：

```text
kai-mind-ua-request/v1
kai-mind-ua-result/v1
```

`scan-project.mjs` 不執行；只移植其 enrichment 邏輯。UA work-dir 由 KAI-Mind 提供，
不得寫入 target repo。

## 依賴

- **Do not start until Gate-1 passes：** TOML-primary 的 **initial scan 驗 Step 1～7 publish +
  Step 8 viewer（initial scan 不必跑 Step 9）**；**Step 9 decision 與 Apply B1→B2
  （跳 Step 3/UA；4-1 bridge replay → 4-2 overlay → Step 4～7）共用 snapshot 由 Apply path
  另行驗證**；以及 `ua_analysis_result=None` 的 initial build / Apply regression 必須全部通過。
  Gate-1 未通過時，本計畫維持 blocked，不得提前把 UA 切成 primary。
  （拆法以 `static-trace-plan/README.md` 的執行順序與 Gate 表為準；原本寫「Step 1～9 E2E」會
  讓 Gate-1 驗收時對「initial scan 要不要跑 Step 9」各說各話。）
- 依賴 `00A`：generic v2 map 與 evidence contract。
- 依賴 `01B`：UA `rule_id` 必須能進 Step 4 bridge registry。
- 依賴 `03A`：`ScanSnapshot` 預留 nullable `ua-analysis-result` internal sidecar slot，但
  Phase2 Apply 只使用 `ScanSnapshot.scan_result`；semantic sidecar 不產生、不消費。
- Structural path 必須在 Plan 14 final validation 前完成。

## Task 1：定義 UA request / result schema

**Files**

- Create: `src/kai_mind/core/models/ua_analysis.py`
- Create: `schemas/kai-mind-ua-request.v1.schema.json`
- Create: `schemas/kai-mind-ua-result.v1.schema.json`
- Test: `tests/unit/core/test_ua_analysis_models.py`
- Test: `tests/contracts/test_ua_analysis_schema.py`

**Steps**

- [ ] 定義 `UaAnalysisRequest`，包含 `schema_version`、`project_root`、`files[]`、
  `inventory_digest` 與 work-dir safe metadata。
- [ ] `files[]` 必須使用 project-relative path，含 `language`、`file_category`、
  `size_lines`、content digest 或 fingerprint。
- [ ] 定義 `UaAnalysisResult`，包含 `structural`、`semantic`、`warnings`、`stats` 與
  `status`；禁止 raw full source、absolute local path 與 secret values。
- [ ] Schema validation fail closed；unknown fields 預設拒絕，避免 sidecar contract drift。

## Task 2：實作 Step 2 inventory enrichment

**Files**

- Modify: `src/kai_mind/core/providers/filesystem_provider.py`
- Modify: `src/kai_mind/core/models/scan.py`
- Test: `tests/unit/core/test_filesystem_provider.py`
- Test: `tests/contracts/test_secret_snapshot_safety.py`

**Steps**

- [ ] 將 `scan-project.mjs` 有價值的 enrichment 移植到 Python inventory：語言偵測、
  `file_category`、行數統計。
- [ ] Enrichment 不改變 boundary policy；可掃描檔案仍由 KAI Step 2 決定。
- [ ] 對 binary、large、generated、ignored files 維持 skip audit trail。
- [ ] Windows/macOS path normalization 與 encoding fallback 有 focused tests。

## Task 3：建立 `UnderstandAnythingAnalysisService`

**Files**

- Create: `src/kai_mind/core/services/understand_anything_analysis_service.py`
- Create: `src/kai_mind/core/services/ua_structural_adapter.py`
- Test: `tests/unit/core/test_understand_anything_analysis_service.py`
- Test: `tests/unit/core/test_ua_structural_adapter.py`

**Steps**

- [ ] `NodeRuntimePreflight` 檢查 Node executable、script path、版本與執行權限，
  以及 `@understand-anything/core` build 產物是否存在（submodule 目前未 build，
  `packages/core/dist/` 缺失時三支 script 必死於 module load，見 16B §3.4）；
  缺失時 fail closed。
- [ ] `UnderstandAnythingSubprocessRunner` 使用固定 argument list、`shell=False`、timeout、
  bounded stdout/stderr 與 redaction。
- [ ] `UnderstandAnythingResultValidator` 驗證 schema、path allowlist、line ranges、stats 與
  batch completion。
- [ ] `UaStructuralAdapter` 將 import map、symbols、endpoints、resources、call hints 轉成
  KAI `ScanFact` / `Evidence` / `Issue`。
- [ ] UA structural facts 的 `rule_id` 使用穩定前綴，例如 `ua_import_*`、
  `ua_symbol_*`、`ua_endpoint_*`、`ua_call_hint_*`。
- [ ] **Lv2（16A）：** call hints 必須帶可追溯 path/line，且可標成 `evidence_kind=direct`
  （真 call-site）；禁止用「兩端 component 證據聯集」假裝成 call wiring。call facts
  是後續 `context_flow` / FlowDerivation / static execution 的共同原料。
- [ ] **Adapter 三條硬規則（16B §5.1，違反任一整條路白接）：**
  （A）每個 `ScanFact` 必須配一筆 `(file, path, kind, rule_id)` 四元組完全一致的
  `Evidence`——join 不到時 Step 4 bridge 回 `NO_MATCH`，fact 被**靜默丟棄**；
  （B）UA 自帶行號的欄位（functions/classes/exports/endpoints/services/callGraph）
  必須填 `Evidence.line_start` 才會被判為 `direct`（五態的 `detected` 只認 direct）；
  `import_map` 無行號者誠實維持 indirect，**不得捏造行號**；
  （C）evidence id 由內容決定（deterministic），同一 repo 狀態跨次重跑必須相同——
  Apply 的 `ManualMapping.evidence_ids` 子集檢查依賴此穩定性。

## Task 4：新增 `kai-mind-analyze.mjs` wrapper

**Files**

- Create: `kai-mind-analyze.mjs`——**位置未定案**（原寫 `ref-opensource/understand-anything/`
  與 `ref-opensource/CLAUDE.md`「該目錄不放 KAI 產品碼」衝突；且三支 script 對
  `pluginRoot` 有相對位置依賴，不可直接複製出樹外。裁定見 16B §6 Q1）
- Test: `tests/integration/test_understand_anything_sidecar_contract.py`

**Steps**

- [ ] Wrapper 接收 `--project-root`、`--inventory`、`--work-dir`、`--output`。
- [ ] Wrapper 只分析 request `files[]` allowlist，不自行 walk target repo。
- [ ] Orchestrate Phase2 active path：`extract-import-map -> compute-batches ->
  extract-structure`。
- [ ] Fork `compute-batches.mjs`：改掉寫死的 `<target>/.understand-anything/intermediate/`
  輸入輸出（加 `--input`/`--output`/`--work-dir`），並**保留 source-root 參數**
  （它會讀原始碼抽 export 符號，不只是讀 JSON；見 16B §3.2）。
  fork 形式（local fork / patch / 上游 PR）見 16B §6 Q2。
- [ ] Wrapper 膠水責任（16B §4）：決定性合成 `scan-result.json`（`files` + `importMap`
  原樣傳遞、不得增刪改）、snake_case⇄camelCase 轉換、每步呼叫前 `mkdir -p` work dir
  （三支 script 都不自建目錄）、以 `batchIndex` 收 per-batch 輸出、stderr 全量收集
  限量後轉入 warnings。
- [ ] `file-analyzer` bounded LLM / semantic graph / `kai-mind-ua-result/v1` 保持
  deferred；本計畫只預留 nullable sidecar slot，不執行 LLM。
- [ ] Intermediate artifacts 全部寫入 KAI work-dir，不寫 target repo `.understand-anything/`。

## Task 5：read-only / path safety / secret masking

**Files**

- Modify: `src/kai_mind/core/services/path_safety_service.py`
- Modify: `src/kai_mind/core/services/secret_masking_service.py`
- Test: `tests/contracts/test_secret_snapshot_safety.py`
- Test: `tests/unit/core/test_understand_anything_analysis_service.py`

**Steps**

- [ ] 驗證 UA result 所有 path 都落在 approved inventory。
- [ ] 拒絕 `..`、absolute path injection、symlink escape、NUL 與跨 drive path。
- [ ] stdout/stderr、warnings、semantic summaries 都套用 secret masking 與 path redaction。
- [ ] Sidecar 不得把 full source、raw prompts、secret-like values 寫入 public artifact。

## Task 6：fail-closed behavior

**Files**

- Test: `tests/unit/core/test_understand_anything_analysis_service.py`
- Test: `tests/integration/test_map_build_service.py`

**Steps**

- [ ] Node runtime 缺失時，scan 不進 Step 4。
- [ ] `ua-analysis-result` schema invalid 時，scan 不進 Step 4。
- [ ] 必要 batch 失敗、missing output、dangling path 或 evidence mismatch 時，scan 不進 Step 4。
- [ ] **`scriptCompleted: true` 不得單獨視為成功**：tree-sitter 全滅時 UA 仍 exit 0、
  importMap 全空——Validator 需另以 `stats.totalEdges` 與 stderr warnings 判斷降級
  並 fail closed（16B §3.4）。
- [ ] Failures 回穩定 error code / finding，不產出可被 viewer 當成功載入的 partial build。

## Task 7：parity 對比 harness

**Files**

- Create: `src/kai_mind/core/services/ua_parity_service.py`
- Create: `tests/integration/test_ua_parity_service.py`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/14-local-project-import-and-test.md`

**Steps**

- [ ] 過渡期並跑 KAI `code_pattern`、`dependency_manifest`、`docker_image`、config patterns。
- [ ] 將 UA structural facts 與 KAI provider facts 分類為 equivalent / missing / extra /
  intentionally-degraded。
- [ ] Parity report 不影響 canonical facts，但會成為 Plan 14 gate 與 Plan 18 退役依據。
- [ ] Phase4 31 fixtures 轉為 parity corpus 的第一批資料來源。

## Acceptance Criteria

- [ ] `UnderstandAnythingAnalysisService` 可從 KAI approved inventory 產生 UA request。
- [ ] `kai-mind-analyze.mjs` 不執行 `scan-project.mjs`，不寫 target repo。
- [ ] `kai-mind-ua-request/v1` 與 `kai-mind-ua-result/v1` schema 通過 contract tests。
- [ ] Structural result 可轉成 KAI facts / evidence / issues，且 evidence path/line 可追溯。
- [ ] `ScanSnapshot.ua_analysis_result` 為 reserved nullable internal slot（`03A` 預留）；
  Phase2 active path **不產生、不消費** semantic payload；`semantic` 欄位維持 `null`。
- [ ] Phase B/C 可選保存 structural wrapper JSON 於 snapshot 內供追溯，但 Step 4～7 / Apply /
  Viewer 只讀 `ScanSnapshot.scan_result`，不列 public artifact、不新增 API artifact path。
- [ ] Node 缺失、schema invalid、必要 batch 失敗全部 fail closed，不進 Step 4。
- [ ] Parity harness 可產生可追溯 diff，供 Plan 14 / Plan 18 使用。

## Plan 13.8 移交：12 張卡的關係語意驗收清單

**來源**：`../s1-v2-cutover/13.8.md` Task 3（2026-07-29 逐張複核，
`basic_qdrant_ollama_rag` 全管線實測）。與 16A §7.2 同一份清單，此處為
Plan 16 的**驗收面**版本：UA adapter 的 call hints 若無法表達下列語意，
這 12 張卡在 UA 落地後仍會停在 `undetermined` / `partial`。

15 張卡中，`rag-grounding` 屬純命名不一致（13.8 Task 2 已用過渡 alias
`context_flow ≡ {provides_retrieved_context, prompts_llm}` 處理），
`agentic-control` 與 `memory` 無 `required_relationship`；其餘 **12 張**
都必須等 UA 提供語意相符的邊。

| profile_id | 需要的關係語意 | UA call hint 應能證明什麼 |
|---|---|---|
| tool-calling | `tool_call` | agent loop 呼叫了工具函式／工具註冊表 |
| workflow-orchestration | `workflow_transition` | orchestrator 節點之間的狀態轉移呼叫 |
| hybrid-retrieval | `retrieval_fusion` | 兩種以上 retriever 的結果被合併／加權 |
| reranking | `rerank` | retriever 結果流入 rerank 函式後才進下游 |
| corrective-retrieval | `fallback_route` | 檢查失敗後走另一條檢索分支 |
| self-reflection | `self_critique` | 生成結果回饋進同一 agent loop 再評估 |
| graph-retrieval | `graph_retrieval` | 圖查詢 API 的呼叫進入檢索路徑 |
| hierarchical-retrieval | `hierarchical_flow` | 索引層級之間的父子檢索呼叫 |
| contextual-retrieval | `context_enrichment` | metadata 抽取結果併入 context 組裝 |
| multimodal-grounding | `multimodal_retrieval` | 非文字模態的檢索呼叫 |
| modular-composition | `component_selection` | orchestrator 依條件選擇不同元件 |
| multi-query-retrieval | `query_route` | query 分類結果決定走哪條檢索路徑 |

**驗收時必須同時滿足的三個條件**（缺一張卡就不會翻）：

1. **關係名一致**：UA 端不得自創同義新名，必須用
   `profile_rule_definitions.py` 既有字串；要換名就同步改 profile 規則或
   13.8 的 alias 表（否則重演 G5 的字彙漂移）。
2. **端點落點**：13.8 Task 1 已為 relationship 閘門加上端點約束——邊的
   `source`/`target` 至少一端必須落在該卡 `required_node_ids` 對應的元件
   上。只產出關係名而落點不對的 call hint 一律不採計。
3. **node gate 先過**：這 12 張卡**沒有一張**的 required 節點今天能被自動
   掃描點亮到齊。13.7 後自動可達集合只有
   `{api_server, dense_retriever, embedder, index_builder, llm_answerer,
   prompt_builder}` 6 個；本清單需要而不可達的節點為
   `agent_loop`、`tool_using_generator`、`orchestrator`、`router`、
   `hybrid_retriever`、`reranker`、`conflict_checker`、`graph_retriever`、
   `context_composer`、`metadata_extractor`、`rag_anything_system`、
   `query_classifier`。**UA 必須同時補上元件偵測與關係語意**，只補其一
   不會有任何一張卡改變狀態。

**回歸守門**：`tests/integration/test_profile_card_status_baseline.py`
釘住今天 15 張卡的 status 快照（`rag-grounding` / `hierarchical-retrieval`
= `partial`，其餘 13 張 = `undetermined`）。UA 落地讓任何一張卡轉綠時，
該測試會轉紅並在 diff 指名卡片——這是**預期的**，更新快照時要一併說明是
哪一條真實 call-site 證據讓它翻的。

**Final review 移交補記（2026-07-29，13.7/13.8 whole-branch review）**：

- **candidate observed_kind 字彙面未對位**：`component_bridge_registry.py`
  會產出 `observed_kind="reranker_candidate"` / `"router_like_evidence"`
  的 capability candidates，而 `capability_type_node_map.toml`（39 key）
  無此二 key，故 candidates 永遠無法把 `reranker`／`router` 抬到
  `partial`。此為 13.7 前即存在（舊 dict 亦無）、行為中性，但它是
  「bridge 規則 kind 之外的第二個字彙面」，不在 13.7 護欄測試的迭代
  範圍內——UA 字彙工作需一併裁定是否對位並補護欄。
- **rag-grounding 誤亮偵測器**：13.8 待裁定的 `prompts_llm` 風險目前
  無主動偵測器。第一個 full-template（13-slot）fixture 落地時，必須
  同時釘住該 fixture 上 `rag-grounding` 的期望 status——那就是觸發
  條件「UA 前發現真實 repo 誤亮」的檢知點。

## Open Questions（動工前需裁定；詳見 16B §6）

- [ ] Q1：`kai-mind-analyze.mjs` 的落腳位置與 script 路徑解析策略。
- [ ] Q2：`compute-batches.mjs` fork 形式（local fork / patch layer / 上游 PR）。
- [ ] Q3：`kai-mind-ua-result/v1` 的 `stats` / `warnings` 內部形狀（Task 1 定案）。
- [ ] Q4：CLI `kai-mind map` 是否走 UA（該路徑目前無 boundary gate、無 snapshot）。
- [ ] Q5：UA submodule 的 `pnpm install + build` 屬安裝時一次性動作或 preflight 檢查項
  （preflight 只檢查、不現場 build）。

## 邊界 / 不做事項

- 不採用 UA Phase 3～7、dashboard、`knowledge-graph.json` 作為 KAI canonical truth。
- 不把 UA semantic nodes/edges 直接寫入 `ai_system_map.json`。
- 不新增 frontend contract 欄位。
- 不把 existing KAI scan TOML providers 立即刪除；退役由 Plan 18 在 parity gate 後處理。
- 不執行 target app、不安裝 target repo dependencies、不修改 target repo。
