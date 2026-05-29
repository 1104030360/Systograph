# 2026-05-28 Phase 2 AI System Map Schema and Core Models Report

## 實作邏輯

- 以 `ai_system_map.json` 作為 Epic 1 canonical contract。
- 以 Pydantic v2 models 作為 JSON Schema 的唯一來源，避免 schema 與 runtime model 雙邊漂移。
- JSON Schema 驗證欄位形狀與 enum；`SystemMapValidationService` 驗證 cross-reference invariants。
- Contract fixtures 放在 `tests/fixtures/ai_system_map/`，contract tests 直接讀取 fixture。
- Rich fixture 只抽出 frontend handoff sample 的 `viewer_load_result.ai_system_map`，沒有把 viewer response wrapper 當作 canonical map。

## 步驟

1. 建立 Phase 2 TODO。
2. 先寫 contract tests 與 core runtime validation tests。
3. 建立手寫 `valid_minimal.v1.json`。
4. 建立 minimal invalid fixtures：`confidence`、detected without evidence、invalid status、absolute evidence path。
5. 從 frontend JSON sample 抽出 `valid_rich_frontend_sample.v1.json`。
6. 實作 `RagSystemMap` 與 nested Pydantic models。
7. 產生 `schemas/ai-system-map.v1.schema.json`。
8. 實作 `SystemMapValidationService`。
9. 跑 focused tests、full tests 與 Ruff。

## 測試方式

- RED：`uv run pytest tests/contracts tests/core`
  - 初始失敗原因：`kai_mind.core.models.system_map` 與 `system_map_validation_service` 尚未存在。
- GREEN focused：`uv run pytest tests/contracts tests/core`
  - 結果：12 passed。
- Full test：`uv run pytest`
  - 結果：15 passed。
- Lint：`uv run ruff check .`
  - 結果：All checks passed。

## 遇到的問題與解法

- 問題：rich frontend sample 有 `Evidence.line_start`、`Evidence.line_end`、`Evidence.snippet`、detail scan `code_path`、`RiskHint.target_type = evidence`，初版 model 沒列入。
  - 解法：明確把這些已交付給前端的 contract 欄位加入 Pydantic models，保留 `extra="forbid"`，不放寬未知欄位。
- 問題：rich frontend sample 的 detail scan target 可以是 edge id。
  - 解法：runtime validator 的 detail scan target 集合加入 existing edge ids。
- 問題：sandbox 不允許 `uv` 建立 cache。
  - 解法：測試與 schema generation 使用已核准的 escalated command 執行。

## Task 2 驗收確認

- `schemas/ai-system-map.v1.schema.json` 已建立，包含 `$schema` 與 `$id`。
- `valid_minimal.v1.json` 可通過 Pydantic、JSON Schema、runtime invariant validation。
- `valid_rich_frontend_sample.v1.json` 可通過 Pydantic、JSON Schema、runtime invariant validation。
- Contract tests 直接讀取 `tests/fixtures/ai_system_map/*.json`。
- Checked-in schema 與 Pydantic generated schema 一致。
- `confidence` validation 失敗。
- `detected` slot 沒有 evidence 時 validation 失敗。
- absolute evidence path validation 失敗。
- invalid fixtures 各自只測一個錯誤點。

## 最後測試結果

```text
uv run pytest
15 passed in 0.24s

uv run ruff check .
All checks passed!
```
