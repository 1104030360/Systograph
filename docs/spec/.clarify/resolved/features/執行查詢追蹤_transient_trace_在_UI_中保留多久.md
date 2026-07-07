# 釐清問題

Transient Query Trace 結果在 UI 中應保留多久？

# 定位

Feature：`執行查詢追蹤` 的「Query Trace 結果必須保持 transient」規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 只存在於單次 API response，不保存於 session |
| B | 保留於目前 Viewer session，頁面 reload 後消失 |
| C | 保留於 process memory，backend restart 後消失 |
| D | 使用明確 bounded TTL，逾時自動刪除 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 trace replay UX、記憶體上限、privacy、reload behavior、session store 與測試清理。

# 優先級

Medium
- 已確定不可持久化為 artifact，但 session lifetime 尚未定義。

---
# 解決記錄

- **回答**：B - 保留於目前 Viewer session，頁面 reload 後消失
- **更新的規格檔**：`docs/spec/features/執行查詢追蹤.feature`
- **變更內容**：明定 Query Trace result 只保留於目前 Viewer session；同一 session 可檢視 Trace panel，頁面 reload 後必須清除，且不得產生 persisted trace artifact。
