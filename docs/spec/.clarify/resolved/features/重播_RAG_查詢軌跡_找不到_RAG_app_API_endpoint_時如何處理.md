# 釐清問題

使用者輸入測試問題時，如果 RAG System Map 找不到 app / API endpoint，query trace 應如何處理？

# 定位

Feature：重播 RAG 查詢軌跡。規則：KAI-Mind 必須找到 RAG app / API endpoint 才能送出 query。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗，顯示 endpoint_not_found 狀態 |
| B | 禁用 query trace controls |
| C | 允許使用者載入 sample trace |
| D | 改用 static System Map replay，不送出 query |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 GUI error state、query trace feature tests、missing endpoint scenario、sample trace workflow 與 Runtime Readiness 銜接。

# 優先級

High
- High：query trace 的前置條件失敗行為尚未定義。

---
# 解決記錄

- **回答**：A - 操作失敗，顯示 endpoint_not_found 狀態
- **更新的規格檔**：spec/features/重播RAG查詢軌跡.feature
- **變更內容**：在 endpoint 前置條件規則新增找不到 RAG app / API endpoint 的 Example，要求操作失敗、顯示 `endpoint_not_found`，且不送出 query。
