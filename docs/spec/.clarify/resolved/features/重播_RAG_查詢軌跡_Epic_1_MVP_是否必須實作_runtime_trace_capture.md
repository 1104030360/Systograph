# 釐清問題

Epic 1 MVP 是否必須實作 runtime trace capture，還是只需要預留資料模型與 GUI replay 設計？

# 定位

Feature：重播 RAG 查詢軌跡。規則：完整 runtime trace capture 可作為 Epic 1 進階交付或後續銜接。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | MVP 只預留資料模型與 GUI replay 設計，不做 runtime trace capture |
| B | MVP 支援 sample trace replay，但不呼叫真實 RAG endpoint |
| C | MVP 必須呼叫 detected RAG endpoint 並收集 basic trace |
| D | MVP 必須完整支援 proxy wrapper / trace hook runtime capture |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 Epic 1 MVP 邊界、實作計畫、測試 fixture、runtime dependency、GUI replay acceptance criteria 與後續 Epic 2 / observability 銜接。

# 優先級

High
- High：目前規格同時提到 GUI 應支援 trace replay 與完整 capture 可作為進階交付，需釐清 MVP 邊界。

---
# 解決記錄

- **回答**：C - MVP 必須呼叫 detected RAG endpoint 並收集 basic trace
- **更新的規格檔**：spec/features/重播RAG查詢軌跡.feature
- **變更內容**：更新 trace collection 規則，明確定義 Epic 1 MVP 需呼叫 detected RAG endpoint 並收集 basic trace；proxy wrapper 與 trace hook 保留為 advanced scope。
