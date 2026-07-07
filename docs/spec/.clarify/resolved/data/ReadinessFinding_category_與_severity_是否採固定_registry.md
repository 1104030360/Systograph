# 釐清問題

`ReadinessFinding.category` 與 severity 是否需要固定、版本化的 registry？

# 定位

ERM：`ReadinessFinding.category`，目前尚未定義 severity 欄位；Feature：Readiness 顯示與排序。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | Category 與 severity 都使用固定版本化 enum |
| B | Category 使用固定 registry，不提供 severity |
| C | Category 允許開放字串，severity 使用固定 enum |
| D | Category 與 severity 都由 rule metadata 開放提供 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 readiness schema、finding grouping、release policy、frontend filter/sort、compatibility 與 analytics。

# 優先級

Medium
- 已確認 `source_traceability` 與 network exposure 類型，但整體 vocabulary 與優先序尚未定義。

---
# 解決記錄

- **回答**：A - Category 與 severity 都使用固定版本化 enum
- **更新的規格檔**：`docs/spec/erm.dbml`、`docs/spec/features/檢視Readiness報告.feature`
- **變更內容**：新增 `ReadinessReport.finding_registry_version` 與 `ReadinessFinding.severity`；明定 Phase2 使用 `readiness-finding-registry/v1`，category 固定為 `source_traceability`、`network_exposure`、`artifact_integrity`、`schema_contract`、`evidence_gap`、`static_uncertainty`、`manual_review`，severity 固定為 `blocker`、`high`、`medium`、`low`、`info`，不得由 rule metadata 輸出開放字串。
