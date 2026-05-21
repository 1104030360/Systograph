# 釐清問題

GUI filter 套用時，是隱藏不符合項目，還是只高亮符合項目？

# 定位

Feature：檢視 RAG System Map。規則：GUI 必須支援指定 filter 類型。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 隱藏不符合 filter 的 nodes / edges |
| B | 保留完整 graph，只高亮符合 filter 的 nodes / edges |
| C | nodes 隱藏，edges 保留但淡化 |
| D | 由每種 filter 類型各自定義 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 GUI behavior、視覺測試、filter acceptance criteria、使用者探索 missing slots 與 risk hints 的方式。

# 優先級

Medium
- Medium：影響 UX 行為與測試斷言，但不阻礙核心 scanner schema。

---
# 解決記錄

- **回答**：B - 保留完整 graph，只高亮符合 filter 的 nodes / edges
- **更新的規格檔**：spec/features/檢視RAG系統地圖.feature
- **變更內容**：在 filter 規則新增 Example，要求套用 filter 時完整 graph 仍可見，符合項目高亮，不符合項目不隱藏。
