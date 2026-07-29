# Understand-Anything Sidecar Service 實作計畫

Status: planned — **blocked until Gate-1 passes**（2026-07-07 UA-primary 決策）

> **執行者注意：** 逐 task 實作本計畫。步驟使用 checkbox（`- [ ]`）語法以便追蹤。

## 目標

新增 `UnderstandAnythingAnalysisService`，讓 KAI-Mind 在 Step 2 boundary 完成後呼叫
Understand-Anything sidecar，取得 deterministic structural facts；semantic sidecar slot 保持
nullable deferred。
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

- [ ] `NodeRuntimePreflight` 檢查 Node executable、script path、版本與執行權限；缺失時
  fail closed。
- [ ] `UnderstandAnythingSubprocessRunner` 使用固定 argument list、`shell=False`、timeout、
  bounded stdout/stderr 與 redaction。
- [ ] `UnderstandAnythingResultValidator` 驗證 schema、path allowlist、line ranges、stats 與
  batch completion。
- [ ] `UaStructuralAdapter` 將 import map、symbols、endpoints、resources、call hints 轉成
  KAI `ScanFact` / `Evidence` / `Issue`。
- [ ] UA structural facts 的 `rule_id` 使用穩定前綴，例如 `ua_import_*`、
  `ua_symbol_*`、`ua_endpoint_*`、`ua_call_hint_*`。

## Task 4：新增 `kai-mind-analyze.mjs` wrapper

**Files**

- Create: `ref-opensource/understand-anything/kai-mind-analyze.mjs` 或實際 vendored sidecar path
- Test: `tests/integration/test_understand_anything_sidecar_contract.py`

**Steps**

- [ ] Wrapper 接收 `--project-root`、`--inventory`、`--work-dir`、`--output`。
- [ ] Wrapper 只分析 request `files[]` allowlist，不自行 walk target repo。
- [ ] Orchestrate Phase2 active path：`extract-import-map -> compute-batches ->
  extract-structure`。
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

## 邊界 / 不做事項

- 不採用 UA Phase 3～7、dashboard、`knowledge-graph.json` 作為 KAI canonical truth。
- 不把 UA semantic nodes/edges 直接寫入 `ai_system_map.json`。
- 不新增 frontend contract 欄位。
- 不把 existing KAI scan TOML providers 立即刪除；退役由 Plan 18 在 parity gate 後處理。
- 不執行 target app、不安裝 target repo dependencies、不修改 target repo。
