# 釐清問題

`order_index`、`rank` 與 `sequence_index` 的起始值、連續性及 parent scope 內唯一性規則為何？

# 定位

ERM：`ReferencePlane.order_index`、`ReferenceNode.order_index`、`MappingCandidate.rank`、`ExecutionStep.sequence_index`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 全部使用 0-based、連續且 parent scope 內唯一 |
| B | 全部使用 1-based、連續且 parent scope 內唯一 |
| C | 使用正整數 sparse ordering，只要求 parent scope 內唯一 |
| D | Display order、candidate rank、execution sequence 各自定義規則 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 catalog validation、proposal candidate ordering、execution replay、deterministic serialization 與邊界測試。

# 優先級

Medium
- 數值欄位已有用途，但邊界與重複值處理尚未明確。

---
# 解決記錄

- **回答**：A - 全部使用 0-based、連續且 parent scope 內唯一
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：明定 `ReferencePlane.order_index`、`ReferenceNode.order_index`、`MappingCandidate.rank` 與 `ExecutionStep.sequence_index` 全部從 0 開始、不可跳號，且在各自 parent scope 內唯一；補上 plane/node display order 的唯一索引。
