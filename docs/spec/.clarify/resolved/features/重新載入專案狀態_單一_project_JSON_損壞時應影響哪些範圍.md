# 釐清問題

單一 project 的 local JSON state 損壞時，應只阻擋該 project、阻擋整個 state store，還是自動回復上一份有效資料？

# 定位

Feature：`重新載入專案狀態` 的「Corrupted local JSON state 必須 fail closed」規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 只阻擋受損 project，其他 projects 繼續可用 |
| B | 整個 local state store fail closed |
| C | 自動回復同 project 最近一份已驗證備份 |
| D | 隔離損壞檔案並重建 safe metadata，但不自動恢復 artifacts |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 repository adapter、startup behavior、錯誤回應、資料修復、備份策略與多 project 可用性。

# 優先級

High
- Fail-closed 的 blast radius 未定義，會影響所有 restart recovery 實作。

---
# 解決記錄

- **回答**：A - 只阻擋受損 project，其他 projects 繼續可用
- **更新的規格檔**：`docs/spec/erm.dbml`、`docs/spec/features/重新載入專案狀態.feature`
- **變更內容**：明定單一 project 的 persisted local JSON state 損壞時，只能 fail closed 該 project；其他驗證通過的 project 必須仍可重新載入，且受損 project 的 `latest_build_id` 不得被覆寫。
