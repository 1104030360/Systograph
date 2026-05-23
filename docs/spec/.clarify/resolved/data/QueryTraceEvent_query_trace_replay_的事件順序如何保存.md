# 釐清問題

Query trace / replay 的事件順序應如何保存？

# 定位

ERM：`QueryTraceEvent`。目前有 input、output、latency、error、retrieved_chunks，但沒有明確順序欄位；Feature 要求 pause、step forward、step backward、replay。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 新增 `sequence_index int`，用整數順序控制 replay |
| B | 新增 `timestamp string`，用事件時間排序 |
| C | 同時新增 `sequence_index int` 與 `timestamp string` |
| D | 不新增欄位，依 JSON array 順序 replay |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 `QueryTraceEvent` 資料模型、query trace replay 測試、GUI 播放控制與 trace event serialization。

# 優先級

High
- High：沒有順序定義會阻礙 replay 行為驗證。

---
# 解決記錄

- **回答**：C - 同時新增 `sequence_index int` 與 `timestamp string`
- **更新的規格檔**：spec/erm.dbml, spec/features/重播RAG查詢軌跡.feature
- **變更內容**：在 `QueryTraceEvent` 新增 `sequence_index` 與 `timestamp`，並更新 trace detail panel example，要求顯示這兩個欄位。
