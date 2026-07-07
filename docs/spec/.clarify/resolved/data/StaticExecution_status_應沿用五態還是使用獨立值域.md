# 釐清問題

Static call edge、dataflow hint、execution path 與 execution step 的 `status` 應沿用五態、使用三態子集合，還是採獨立值域？

# 定位

ERM：`StaticCallEdge.status`、`DataflowHint.status`、`ExecutionPath.status`、`ExecutionStep.status`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 全部沿用五態：`detected / partial / undetermined / not_detected / conflicted` |
| B | 只允許 `detected / undetermined / not_detected` |
| C | 使用 artifact 狀態：`complete / partial / failed`，推論強度另放其他欄位 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響四個 static execution schemas、Profile supporting refs、frontend legend、limitations 與 fixtures。

# 優先級

High
- 目前 active assessment 是五態，但 static execution plan 仍出現三態片段，不能讓 schema 分歧。

---
# 解決記錄

- **回答**：A - 全部沿用五態：`detected / partial / undetermined / not_detected / conflicted`
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：將 StaticCallEdge、DataflowHint、ExecutionPath 與 ExecutionStep 的 `status` 固定為共用五態；Artifact 完整性仍由 Build／Artifact validation 表達。
