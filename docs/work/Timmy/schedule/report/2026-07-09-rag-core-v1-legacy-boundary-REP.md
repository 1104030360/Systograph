# 2026-07-09 RAG Core V1 Legacy Boundary REP

## 目標

執行 phase2 第一個 contract compatibility 階段：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s0-contract-compatibility/00-define-rag-core-v1-legacy-template-boundary.md`。

本階段目標是把 `rag-core-v1` 固定成 legacy template input，補上
characterization / regression guard，並新增 read-only deterministic 的 v1-to-v2
adapter boundary。現行 active v1 build path 不做 silent cutover。

## 實作邏輯

- 不修改 `rag-core-v1.json` 的 slots、flows 或 version，避免破壞既有 v1 artifacts。
- 在 `RagTemplateService` 增加 boundary metadata，讓 code 層明確知道
  `rag-core-v1` 不是 active readiness、profile 或 frontend summary surface。
- 新增 compatibility v2 model 與 adapter service，讓後續 00A 可以從 validated
  `RagSystemMap` 取得 generic components / edges / evidence / endpoints / risks /
  unmapped facts / candidate facts。
- adapter 僅轉換 in-memory model，不讀 filesystem、不呼叫 LLM、不寫 artifact。
- adapter 不產生 `release_verdict`、`profiles` 或任何 compatibility-derived product
  verdict。

## 步驟

1. 讀取 `phase1.md`、target plan、`AGENTS.md`、Linus rule、工程 / 測試 / 文件 prompt。
2. 用 codegraph 與 repo 搜尋確認現況：
   - `MapBuildService` 仍載入 `RagTemplateService.load("rag-core-v1")`。
   - `SystemMapNormalizeService` 仍輸出 `ai-system-map/v1`。
   - `ViewerSessionService` 仍投影 v1 map 成 `GraphViewModel`。
3. 建立 TODO：`docs/work/Timmy/schedule/todo/2026-07-09-rag-core-v1-legacy-boundary-TODO.md`。
4. 補 `RagTemplateService.boundary_metadata()` 與 regression tests。
5. 新增 `src/kai_mind/core/models/ai_system_map_v2.py`。
6. 新增 `src/kai_mind/core/services/system_map_v1_to_v2_adapter.py`。
7. 新增 `tests/unit/core/test_system_map_v1_to_v2_adapter.py`。
8. 補上 evidence 全集合與同 slot multi-instance regression tests。
9. 跑 targeted tests、全套 pytest、mypy、ruff scope、diff check。

## 2026-07-10 Review 更正

- `generic v2 map + profiles + readiness findings` 是 Phase2 **target contract**，不是
  current runtime 已完成的 active contract。
- Current `MapBuildService`、CLI/API 與 viewer 仍使用 `ai-system-map/v1`；Plan 13 才負責
  active v2 cutover。
- Plan 00 的 active surface、frontend cutover 與 staged retirement gate 已改回未完成，
  避免把 target state 誤標為本輪完成。
- Adapter 的「不遺失」驗證縮窄為明確 compatibility facts，並新增完整
  `evidence[]` equality 與 multi-instance preservation tests。

## 測試方式

- `.venv/bin/pytest tests/contracts/test_ai_system_map_schema.py tests/unit/core/test_system_map_validation.py tests/unit/core/test_viewer_session_service.py tests/unit/core/test_rag_template_service.py tests/unit/core/test_system_map_v1_to_v2_adapter.py -q`
- `.venv/bin/pytest -q`
- `.venv/bin/mypy`
- `.venv/bin/ruff check src tests`
- `.venv/bin/ruff check .`
- `git diff --check`

## 測試結果

- Targeted tests：67 passed。
- Full pytest：531 passed。
- Full mypy：Success，148 source files。
- `ruff check src tests`：All checks passed。
- `git diff --check`：通過。
- `ruff check .`：失敗，原因是既有 `ref-opensource/Understand-Anything` 與
  `scripts/dev.py` lint 問題；本次修改範圍已用 `ruff check src tests` 驗證通過。

## 遇到的問題與解法

- 問題：兩個初始 subagent 綁定的模型在目前 ChatGPT 帳號不可用。
  - 解法：改派可用的 `backend-developer` 與 `architecture-design` 類 agent，並用
    codegraph / repo 搜尋直接驗證 code path。
- 問題：`ruff check .` 會掃到 reference workspace 與既有 script lint 問題。
  - 解法：不修改 unrelated reference code；改以 `ruff check src tests` 驗證本 repo
    code/test 範圍，並在本 report 記錄全域 lint 的既有失敗。
- 問題：adapter 新檔初次 lint 有 import 與長行問題。
  - 解法：使用 `ruff --fix` 整理 import，再手動斷行；修正後 scoped ruff 通過。

## 驗收對照

- `rag-core-v1` 仍可讀取既有 v1 artifacts：通過，v1 schema / validation /
  viewer load tests 維持通過。
- legacy-only boundary：通過，`RagTemplateService.boundary_metadata()` 明確標示
  `legacy_template_input`，且不是 active readiness / profile / frontend summary。
- v1-to-v2 adapter：通過，新增 read-only deterministic adapter；完整 evidence
  collection 與 multi-instance preservation 另有 regression tests。
- 不輸出 compatibility-derived verdict：通過，adapter test 驗證沒有
  `release_verdict` 與 `profiles`。
- 不修改 active build output：通過，未改 `MapBuildService` active v1 pipeline。
- Active assessment surface cutover：**尚未完成**，由 Plan 13 負責；本輪不得宣稱
  Capability Map / profile / readiness findings 已是 current active surface。

## 剩餘風險與後續

- 尚未建立 `CanonicalMapLoader` / dual-read loader；這屬於後續 00A。
- 尚未新增 checked-in `ai-system-map.v2.schema.json`；本輪先建立 compatibility model。
- frontend 仍有 legacy scan-template mock/page 與 v1 sample，Plan 13 cutover 前需要清理
  active product copy。
- Target product contract 與 current runtime 必須持續分開描述；在 Plan 13 runtime probe
  證明 v2 + profiles + readiness payload 前，不得把 active surface 驗收勾選完成。
- `candidate_facts` 目前只涵蓋 legacy extensions；non-baseline capability candidates
  應由後續 Capability Map / proposal pipeline 接手。
