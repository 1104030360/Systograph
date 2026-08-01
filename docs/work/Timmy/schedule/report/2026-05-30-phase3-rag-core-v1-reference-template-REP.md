# 2026-05-30 Phase 3 rag-core-v1 Reference Template Report

## 實作邏輯

- 建立內建 `rag-core-v1` reference template，作為後續 scanner / detection / normalization 的標準地圖底稿。
- 不修改 `ai-system-map/v1` canonical JSON schema；template 不是正式 `ai_system_map.json`。
- Slot id 完全沿用 Task 2 已固定的 13 個 snake_case slot id。
- Allowed statuses 完全沿用 Task 2 `SlotStatus`：`detected`、`missing`、`not_configured`、`not_applicable`。
- Template flow 使用 bare id：`indexing`、`query_answer`，不在 template 內使用 `flow:` prefix。
- `RagTemplateService` 只讀取與驗證本機內建 JSON，不做 remote import，也不執行 template 內任何 code。

## 步驟

1. 建立 Phase 3 TODO。
2. 先寫 `tests/core/test_rag_template_service.py`，鎖定 template loader、slot、flow、status 與 validation failure 行為。
3. 執行目標測試確認 RED。
4. 建立 `src/systograph/core/models/template.py`，定義 template Pydantic models。
5. 建立 `src/systograph/core/templates/rag-core-v1.json`，填入 13 個 slots、allowed statuses、requiredness hints 與兩條 flow slot order。
6. 建立 `src/systograph/core/services/rag_template_service.py`，實作內建 template 載入與 validation。
7. 執行目標測試與完整測試。
8. 執行 Ruff 與 mypy，確認格式與 strict typing。

## 測試方式

- RED：`.venv/bin/python -m pytest tests/core/test_rag_template_service.py -q`
  - 初始失敗原因：`systograph.core.services.rag_template_service` 尚未存在。
- GREEN focused：`.venv/bin/python -m pytest tests/core/test_rag_template_service.py -q`
  - 結果：8 passed。
- Full test：`.venv/bin/python -m pytest -q`
  - 結果：34 passed。
- Lint：`.venv/bin/python -m ruff check .`
  - 結果：All checks passed。
- Type check：`.venv/bin/python -m mypy`
  - 結果：Success: no issues found in 15 source files。

## 遇到的問題與解法

- 問題：直接使用系統 `pytest` 時，使用者環境中的 global `pytest_asyncio` plugin 與 pytest 版本不相容，導致測試還沒載入專案就失敗。
  - 解法：改用專案 `.venv/bin/python -m pytest`，確保依賴版本與專案一致。
- 問題：sandbox 不允許 pytest 建立暫存檔。
  - 解法：測試指令使用 escalated command 執行，讓 pytest 能建立暫存目錄。
- 問題：template validation 測試需要壞 template fixtures，但不應污染 repo。
  - 解法：測試使用 `tmp_path` 建立臨時 template directory，驗證 duplicate slot、unknown slot、status drift、prefixed flow id 都會被拒絕。

## Task 3 驗收確認

- `RagTemplateService.load("rag-core-v1")` 可回傳 valid template。
- 13 個設計文件指定 slots 都存在且順序固定。
- Flow 中引用的 slot 都能在 template slots 中找到。
- Template `flows` 使用 `indexing`、`query_answer` bare ids，不使用 `flow:indexing`、`flow:query_answer`。
- Allowed statuses 與 Task 2 `SlotStatus` 完全一致。
- `required_for_rag_hint` 沒有把所有 slot 都標成 required；`guardrails`、`observability` 等 optional slot 為 false。
- Template validation 失敗時會丟出 `RagTemplateValidationError`，不產生 canonical map。
- `schemas/ai-system-map.v1.schema.json` 未修改。

## 最後測試結果

```text
.venv/bin/python -m pytest tests/core/test_rag_template_service.py -q
8 passed in 0.87s

.venv/bin/python -m pytest -q
34 passed in 1.08s

.venv/bin/python -m ruff check .
All checks passed!

.venv/bin/python -m mypy
Success: no issues found in 15 source files
```
