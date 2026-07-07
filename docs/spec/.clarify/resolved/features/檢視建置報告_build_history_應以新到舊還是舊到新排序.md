# 釐清問題

Build history 預設應以新到舊、舊到新，還是由 client 明確指定排序方向？

# 定位

Feature：`檢視建置報告` 的「Build history 必須使用 deterministic ordering」規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 預設新到舊，最新 build 排第一 |
| B | 預設舊到新，完整呈現 lineage 順序 |
| C | API 必須要求 client 提供排序方向 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 GET build history API、frontend version selector、generated_at/build_id tie-breaker 與 contract tests。

# 優先級

Medium
- 排序欄位已定義，但方向未定義，會造成 backend/frontend 測試不一致。

---
# 解決記錄

- **回答**：A - 預設新到舊，最新 build 排第一
- **更新的規格檔**：`docs/spec/erm.dbml`、`docs/spec/features/檢視建置報告.feature`
- **變更內容**：明定 build history 預設先依 `generated_at DESC`，再依 `build_id DESC` 作 deterministic tie-breaker；Viewer／API 預設回傳最新 build 在第一筆。
