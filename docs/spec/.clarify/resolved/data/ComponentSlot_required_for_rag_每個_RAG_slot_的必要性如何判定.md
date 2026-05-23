# 釐清問題

每個 RAG component slot 的 `required_for_rag` 值應如何判定？

# 定位

ERM：`ComponentSlot.required_for_rag`。目前 `epic1.md` 有 Required / Priority 描述，但 `erm.dbml` 尚未明確定義每個 slot 的必要性規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 只將 P0 且 Usually yes 的核心 slot 標記為 `required_for_rag = true`，其他 slot 為 `false` |
| B | 將所有 RAG reference architecture slots 都標記為 `required_for_rag = true` |
| C | `required_for_rag` 不固定，由 scanner 根據 project evidence 判定 |
| D | 移除 `required_for_rag`，只保留 `status` |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 `ComponentSlot` 資料模型、slot coverage 測試、missing slot 的 Markdown summary、GUI filter，以及後續 checker 如何判讀缺失元件。

# 優先級

High
- High：阻礙核心資料模型與 slot coverage 驗證。

---
# 解決記錄

- **回答**：C - `required_for_rag` 不固定，由 scanner 根據 project evidence 判定
- **更新的規格檔**：spec/erm.dbml
- **變更內容**：更新 `ComponentSlot.required_for_rag` 的 note，並在 `ComponentSlot` Table Note 中新增不變條件：`required_for_rag` 由 scanner 根據 project evidence 判定。
