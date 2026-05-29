# 2026-05-28 Phase 2 AI System Map Schema and Core Models TODO

## 目標

依照 `docs/work/Timmy/schedule/dev-prompt/phase2.md` 與 Task 2 plan，使用 TDD + BDD 實作 `ai-system-map/v1` 的 core models、schema artifact、runtime validation service、contract fixtures 與 contract tests。

## 實作邏輯

- 以 `ai_system_map.json` 作為唯一 canonical contract。
- 以 Pydantic v2 models 作為 JSON Schema 的唯一定義來源。
- JSON Schema 負責欄位形狀與 enum，runtime validator 負責 cross-reference invariants。
- Contract fixtures 放在 `tests/fixtures/ai_system_map/`，contract tests 必須直接讀取 fixtures。
- 前端 handoff sample 只能抽出 `viewer_load_result.ai_system_map` 作為 rich canonical fixture，不可把整包 viewer response 當作 system map。

## 步驟

1. 建立 fixture-driven contract tests，先確認 RED。
2. 建立 runtime invariant tests，先確認 RED。
3. 建立 `valid_minimal.v1.json` 與 minimal invalid fixtures。
4. 從 frontend sample 抽出 `valid_rich_frontend_sample.v1.json`。
5. 實作 Pydantic core models，禁止未知欄位。
6. 產生 deterministic `schemas/ai-system-map.v1.schema.json`。
7. 實作 `SystemMapValidationService`。
8. 跑 `uv run pytest` 與 `uv run ruff check .`。
9. 逐項確認 Task 2 驗收標準。
10. 寫 Phase 2 report。

## 測試策略

- Contract tests：valid fixtures 必須通過 Pydantic、JSON Schema、runtime validation。
- Contract tests：checked-in schema 必須與 Pydantic 產生 schema 一致。
- Core tests：拒絕 `confidence`、detected without evidence、invalid status、absolute evidence path、dangling references。
- Smoke tests：既有 import 與 CLI help tests 必須維持通過。

## 注意事項

- 不實作 provider 掃描、Markdown、viewer、query trace execution 或真實 map build。
- 不輸出完整 secret values。
- 不回復使用者既有未提交變更。
