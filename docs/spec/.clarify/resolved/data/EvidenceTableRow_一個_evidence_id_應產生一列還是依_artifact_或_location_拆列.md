# 釐清問題

`EvidenceTableRow` 對同一個 `evidence_id` 應只產生一列，還是依 artifact usage 或 location 拆成多列？

# 定位

ERM：`EvidenceTableRow` 主鍵與 `Evidence`／`EvidenceLocation` 關係。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 每個 build 的每個 `evidence_id` 固定一列，artifact refs 存在同一列 |
| B | 每個 `evidence_id + artifact_type` 一列 |
| C | 每個 `evidence_id + location` 一列，artifact refs 另建關聯 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 evidence table primary key、重複資料、drill-down、cross-artifact refs、未來 DB migration 與查詢 API。

# 優先級

Medium
- 不阻擋掃描，但會直接決定資料表正規化與 evidence 查詢語意。

---
# 解決記錄

- **回答**：A - 每個 build 的每個 `evidence_id` 固定一列，artifact refs 存在同一列
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：將 `EvidenceTableRow` 主鍵固定為 `(build_id, evidence_id)`；同一 evidence 的 artifact usage 彙整到 `artifact_types` 與 `source_artifact_refs`，不得依 artifact 或 location 拆成多列。
