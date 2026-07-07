# 釐清問題

Explicit rescan 建立新 snapshot 時，既有 confirmed mappings 應如何 replay 與處理 stale evidence？

# 定位

Feature：`掃描專案` 的「Explicit rescan 必須建立新的 scan、snapshot 與 initial build」規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 自動 replay 仍可驗證的 mappings；stale mappings 保留 warning 但不套用 |
| B | 任一 mapping stale 就阻擋 build，要求使用者先處理 |
| C | 每次 rescan 都要求使用者重新選擇 mappings |
| D | Rescan 完全不 replay mappings，只有 Apply 才使用 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 rescan initial build、mapping durability、readiness/overlay continuity、warning UX、applied_mapping_ids 與 regression tests。

# 優先級

High
- 不同策略會直接改變同一 project 在 rescan 後的報告與人工決策保存語意。

---
# 解決記錄

- **回答**：A - 自動 replay 仍可驗證的 mappings；stale mappings 保留 warning 但不套用
- **更新的規格檔**：`docs/spec/erm.dbml`、`docs/spec/features/掃描專案.feature`
- **變更內容**：明定 explicit rescan 建立新的 `initial_scan` build 時，same-project 且能由新 snapshot evidence 重新驗證的 confirmed mappings 會自動 replay；stale mappings 只輸出 warning，不寫入新 build 的 `applied_mapping_ids`。
