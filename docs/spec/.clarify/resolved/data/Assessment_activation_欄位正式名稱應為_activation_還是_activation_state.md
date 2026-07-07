# 釐清問題

Assessment、Profile、API 與 frontend contract 的正式欄位名稱應統一為 `activation` 還是 `activation_state`？

# 定位

ERM：`ReferenceAssessment.activation`、`ProfileSignal.activation`；Feature：Viewer 顯示 activation。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 全部統一為 `activation_state` |
| B | 全部統一為 `activation` |
| C | Persisted JSON 使用 `activation_state`，projection/UI 使用 `activation` |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 Pydantic models、JSON Schema、DB 欄位、GraphViewModel、frontend parser、fixtures 與 migration。

# 優先級

Medium
- 目前術語混用會造成相同概念出現兩套欄位名稱。

---
# 解決記錄

- **回答**：B - 全部統一為 `activation`
- **更新的規格檔**：`docs/spec/erm.dbml`、`docs/spec/features/檢視建置報告.feature`
- **變更內容**：明定 Assessment、Profile、API 與 frontend contract 的正式欄位名稱一律為 `activation`，不得使用 `activation_state` 作為 persisted 或 projection 欄位名稱；既有 Viewer feature 已使用 `activation`，不需改名。
