# 2026-07-09 RAG Core V1 Legacy Boundary TODO

## 目標

執行第一個 phase2 contract compatibility 階段，對齊實際 target plan：
`/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s0-contract-compatibility/00-define-rag-core-v1-legacy-template-boundary.md`。

本階段要把 `rag-core-v1` 固定成 legacy migration input，補上
characterization / regression guard，並新增 deterministic、read-only 的 v1-to-v2
adapter boundary。現行 active v1 build path 不做 silent cutover。

## 實作邏輯

- 以 plan 文件已寫明的 boundary 為唯一來源；只做 legacy boundary 與
  migration adapter，不把 active build path 直接切到 v2。
- 先補測試，再補 production code：
  - `rag-core-v1` 必須能被載入，且保留 13 slots / 2 flows / `1.0.0`。
  - template metadata 必須明確標記 legacy-only，且不得宣稱可作
    readiness verdict、profile status 或 frontend summary。
  - adapter 必須接收 validated `RagSystemMap`，輸出 generic v2 compatibility view。
- adapter 只搬移與保留 facts：components、edges、evidence、endpoints、risk hints、
  unmapped facts 與 legacy extension candidate facts。
- adapter 不讀 filesystem、不呼叫 LLM、不寫 artifact、不產生 compatibility-derived
  product verdict。
- frontend 既有 legacy mock/page 暫不切換；Plan 13 前保留 compatibility path，並在
  report 中記錄此為後續 cutover 風險。

## 步驟

1. 讀取 `phase1.md`、target plan、`AGENTS.md`、Linus rule、core/testing/docs prompt。
2. 盤點現行 code path：
   - `MapBuildService` 仍直接載入 `RagTemplateService.load("rag-core-v1")`。
   - `SystemMapNormalizeService` 仍輸出 `ai-system-map/v1`。
   - `ViewerSessionService` 仍從 v1 map 投影 `GraphViewModel`。
3. 建立本 TODO，先記錄 phase scope 與測試策略。
4. 補 template service regression：
   - `RagTemplateService.boundary_metadata("rag-core-v1")` 回傳
     `legacy_template_input`。
   - metadata 明確標記不是 active readiness/profile/frontend summary surface。
5. 補 v1-to-v2 adapter：
   - 新增 compatibility v2 models。
   - 新增 `SystemMapV1ToV2Adapter`。
   - 使用 rich v1 fixture 驗證 compatibility facts 不遺失，且不產生 verdict/profile。
   - 完整比對 source/adapted `evidence[]`，涵蓋 location 與 snippet 欄位。
   - 建立同一 slot 多 instance 案例，驗證 instance 與明確 edge target 不被 collapse。
6. 執行 target tests、全套 pytest、mypy、ruff scope 與 diff check。
7. 建立階段 report，記錄測試結果與剩餘風險。

## 測試策略

- Unit tests：
  - `tests/unit/core/test_rag_template_service.py`
  - `tests/unit/core/test_system_map_v1_to_v2_adapter.py`
- Contract / runtime characterization：
  - `tests/contracts/test_ai_system_map_schema.py`
  - `tests/unit/core/test_system_map_validation.py`
  - `tests/unit/core/test_viewer_session_service.py`
- 全套 regression：
  - `.venv/bin/pytest -q`
  - `.venv/bin/mypy`
  - `.venv/bin/ruff check src tests`
  - `git diff --check`
- `ruff check .` 會掃到 `ref-opensource/Understand-Anything` 與 `scripts/dev.py` 的既有
  lint 問題；本階段以 `src tests` 作為本 repo code/test 驗證範圍。

## 驗收條件

- [x] 已建立 `docs/work/Timmy/schedule/todo/2026-07-09-rag-core-v1-legacy-boundary-TODO.md`。
- [x] 文件內容使用繁體中文，且段落清楚可供其他人直接接手。
- [x] 文件明確引用實際 target plan 路徑：
      `/Users/linjunting/Local_AI_Health_Doctor/docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/s0-contract-compatibility/00-define-rag-core-v1-legacy-template-boundary.md`
- [x] `rag-core-v1` 有 service-level legacy-only boundary metadata。
- [x] 新增 regression test，避免 v1 slot completeness 被宣稱為 active
      readiness/profile/frontend summary surface。
- [x] 新增 deterministic read-only v1-to-v2 adapter boundary。
- [x] adapter 保留完整 evidence collection、multi-instance components、endpoints、risk
      hints、unmapped facts 與 legacy extension candidate facts。
- [x] adapter 不輸出 release verdict、profiles 或 active product assessment。
- [x] 文件明確區分 Phase2 target contract 與 current v1 runtime。
- [ ] Capability Map / profile / readiness findings 已完成 active cutover；此項由 Plan 13
      負責，目前不可視為完成。
- [x] target tests、全套 pytest、mypy、`ruff check src tests` 與 `git diff --check`
      已通過。

## 風險

- 這次沒有接入 `CanonicalMapLoader` 或 active build/API path；這是為了避免 Plan 13
  前 silent cutover，後續 00A 仍需做 dual-read loader 與 v2 schema gate。
- Phase2 target product contract 已定義為 v2 + profiles + readiness findings，但 current
  runtime 仍是 v1；Plan 00 不宣稱 active assessment surface 已切換。
- frontend 仍保留 legacy scan-template mock/page 與 v1 sample；後續 cutover 必須清理
  active product copy，避免使用者把 `rag-core-v1` 誤解成新產品分類。
- `candidate_facts` 目前只涵蓋 legacy extensions；non-baseline capability candidates
  應由後續 Capability Map / proposal pipeline 接手。
- `ruff check .` 仍會因 reference workspace 與既有 script lint 失敗；本次變更範圍的
  `src tests` 已通過。
