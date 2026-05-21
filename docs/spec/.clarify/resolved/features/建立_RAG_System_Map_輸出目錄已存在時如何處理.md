# 釐清問題

`outputs/` 已存在且包含舊的 `ai_system_map.json` 或 `ai_system_map.md` 時，`kai-mind map` 應如何處理？

# 定位

Feature：建立 RAG System Map。規則：使用者可以用 map command 輸入 project folder；Expected Output 指向 `outputs/`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 覆寫同名輸出檔 |
| B | 產生 timestamped output directory |
| C | 操作失敗，要求使用者清空或指定輸出位置 |
| D | 保留舊檔，只輸出不存在的檔案 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 CLI idempotency、測試 fixture 清理策略、CI artifacts 與使用者重跑 map command 的行為。

# 優先級

Medium
- Medium：影響重跑掃描與 CI artifact 管理。

---
# 解決記錄

- **回答**：B - 產生 timestamped output directory
- **更新的規格檔**：spec/features/建立RAG系統地圖.feature
- **變更內容**：在 map command 規則新增 outputs 已存在時的 Example，要求輸出到 timestamped output directory，並保留既有輸出檔。
