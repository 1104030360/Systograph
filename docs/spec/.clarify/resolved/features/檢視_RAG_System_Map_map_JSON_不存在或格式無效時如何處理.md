# 釐清問題

執行 `kai-mind viewer <map_json>` 時，如果 map JSON 不存在或格式無效，GUI 應如何處理？

# 定位

Feature：檢視 RAG System Map。規則：使用者可以用 viewer command 載入 map JSON。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗，不啟動 GUI |
| B | 啟動 GUI 並顯示錯誤狀態 |
| C | 啟動 GUI 並顯示空 graph |
| D | 嘗試 partial load，可讀部分照常顯示 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 viewer CLI、GUI error state、browser/UI 測試、invalid JSON fixtures 與使用者回饋。

# 優先級

High
- High：viewer 的核心前置條件失敗行為尚未定義。

---
# 解決記錄

- **回答**：B - 啟動 GUI 並顯示錯誤狀態
- **更新的規格檔**：spec/features/檢視RAG系統地圖.feature
- **變更內容**：在 viewer command 規則新增 map JSON 不存在或格式無效的 Example，要求 GUI 顯示 error state、包含 map_json 與 error_reason，並且不顯示 graph。
