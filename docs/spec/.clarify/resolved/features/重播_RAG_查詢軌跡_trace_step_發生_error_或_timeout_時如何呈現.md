# 釐清問題

Query trace 的某個 step 發生 error 或 timeout 時，GUI replay 應如何呈現？

# 定位

Feature：重播 RAG 查詢軌跡。規則：Detail panel 必須顯示 trace step 資料；`QueryTraceEvent.error` 已存在但行為未明確。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 保留 partial replay，錯誤 step 高亮並顯示 error |
| B | 整次 query trace 操作失敗，不顯示 replay |
| C | 跳過錯誤 step，繼續顯示後續 steps |
| D | 將 error / timeout 轉為 risk hint |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 query trace data model、GUI replay behavior、錯誤案例測試、runtime observability 銜接與使用者除錯體驗。

# 優先級

Medium
- Medium：影響錯誤邊界測試與 GUI 行為。

---
# 解決記錄

- **回答**：A - 保留 partial replay，錯誤 step 高亮並顯示 error
- **更新的規格檔**：spec/features/重播RAG查詢軌跡.feature
- **變更內容**：新增 trace step error / timeout 的 Example，要求保留 partial replay、錯誤 step 高亮、detail panel 顯示 error，且不丟棄 replay。
