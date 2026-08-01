# 2026-05-30 Phase 3 rag-core-v1 Reference Template TODO

## 目標
完成 Task 3：建立 Epic 1 內建 `rag-core-v1` reference architecture template，讓後續 scanner facts 可以對應到固定 RAG slots、flows、allowed statuses 與 requiredness hints。

## 實作邏輯
- 不修改 `ai-system-map/v1` canonical JSON schema。
- Template 是 internal reference template，不是正式 `ai_system_map.json`。
- Slot id 必須完全沿用 Task 2 已固定的 13 個 snake_case slot id。
- Flow 使用 bare id：`indexing`、`query_answer`。
- Allowed statuses 必須等於 Task 2 `SlotStatus`：`detected`、`missing`、`not_configured`、`not_applicable`。
- Service 只讀取與驗證內建 template，不做 remote import，不執行 template 內任何 code。

## 步驟
1. 先寫 `tests/core/test_rag_template_service.py`，用 TDD 鎖定 loader、slot、flow、status 與 validation failure 行為。
2. 執行目標測試，確認因為 `RagTemplateService` 尚未存在而失敗。
3. 建立 `src/systograph/core/models/template.py`，定義 template model 與 validation 需要的欄位。
4. 建立 `src/systograph/core/templates/rag-core-v1.json`，填入 13 個 slots、allowed statuses、requiredness hints 與兩條 flow slot order。
5. 建立 `src/systograph/core/services/rag_template_service.py`，實作內建 template 載入與 validation。
6. 執行目標測試，確認 template service 測試通過。
7. 執行完整測試，確認沒有破壞既有 schema / validator 行為。
8. 逐項比對 Task 3 驗收標準，確認全部完成。
9. 撰寫 phase3 report，記錄實作邏輯、步驟、測試方式、遇到的問題與測試結果。

## 驗收重點
- `RagTemplateService.load("rag-core-v1")` 回傳 valid template。
- 所有 13 個設計文件指定 slots 都存在且名稱正確。
- Flow 中引用的 slot 都存在。
- Template flow id 不使用 `flow:` prefix。
- Allowed statuses 與 Task 2 `SlotStatus` 完全一致。
- Template validation 失敗時會丟出明確錯誤，不產生 canonical map。
- `schemas/ai-system-map.v1.schema.json` 不被修改。
