# Phase 2 S1 Pipeline Core TODO

## 目標

完成 Phase 3 指定的 S1 pipeline core：將 Step 4 deterministic bridge、Step 6
profile inference、artifact lifecycle、scan/build lineage 與 mapping proposal boundary
落成可測試的後端契約，並保持既有 v1 API/CLI 行為可用。

## 範圍決策

- 2026-07-11 使用者將本階段收斂為 **backend only**。
- 本次曾產生的 `frontend/` 程式碼與測試已全部還原；`frontend/` 最終無 tracked
  diff、也無 untracked 檔案。
- Frontend handoff JSON 仍作為後端契約範例；UI、Zod、store 與 Apply button 實作留待
  frontend owner 後續處理。

## 實作邏輯

1. Step 3 只產生 raw facts/evidence；Step 4 的 Python bridge 將其分成 canonical
   component、review item 或 non-baseline capability signal。
2. confirmed mapping 是 durable decision；Apply 必須從 immutable scan snapshot 重播
   Step 4 至 Step 7，不能重掃 filesystem 或直接 patch 舊 map。
3. Capability reference catalog 只存 10-plane/52-node display metadata；profile status、
   evidence、readiness 與 graph projection 一律由 Python 產生。
4. `profile_signals.json`、`readiness_report.json` 與 map artifacts 共用同一個
   `project_id`/`scan_id`/`build_id` lineage，sidecar 失敗時 viewer 以 degraded mode
   載入 base graph。

## 執行步驟

- [x] 盤點 Phase 3 七份計畫、核心程式碼、現有 tests 與 API contract。
- [x] 執行 baseline：`.venv/bin/pytest -q`（588 passed）。
- [x] 建立 capability candidate model、10-plane/52-node reference catalog 與 loader。
- [x] 將 Step 4 rule table 從 `ComponentDetectionService` 抽到 typed Python bridge。
- [x] 建立 profile signal model、validation 與 deterministic inference。
- [x] 建立 profile/readiness artifact lifecycle 與 build-scoped API payload。
- [x] 建立 scan snapshot、build lineage、local JSON repositories 與 Apply replay routes。
- [x] 將 proposal lifecycle 與 profile inference runtime dependency 分離。
- [x] 補齊 unit、integration、web/CLI BDD scenarios，逐段執行 red-green-refactor。
- [x] 執行後端全量 tests、ruff、mypy、lock check 與 API/CLI manual QA。
- [x] 還原本次全部 frontend 程式碼／測試變更並確認 `frontend/` diff 為空。
- [x] 寫入完成 report，並逐項更新本 TODO。

## 驗收重點

- `scan_id` 代表一次 read-only snapshot，`build_id` 代表一次 immutable materialization。
- Apply 不重掃 filesystem，並且只將 confirmed mappings 納入 `applied_mapping_ids`。
- legacy v1 `NEW_EXTENSION` 相容路徑仍可讀；新的 non-baseline decision 不產生 extension。
- capability catalog 不含 detector DSL 或 profile/graph decision logic。
- 所有新行為都有 Given/When/Then 測試與至少一條經由 API 或 CLI 的可觀察流程。

## 最終驗證摘要

- Baseline：588 passed。
- Backend full suite：715 passed。
- Backend Ruff：`ruff check src tests` 通過。
- Mypy：231 source files，無問題。
- `uv lock --check`：通過，55 packages。
- Live API／CLI lineage、restart、bad input 與 malformed typed ID：通過。
- Whole-repo bare `ruff check` 仍會掃到 `ref-opensource/` 與未修改的
  `scripts/dev.py` 既有 lint debt；不屬本次 backend diff，詳見 report。
