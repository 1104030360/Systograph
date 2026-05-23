# 釐清問題

Evidence 的 `file` path 在 Windows 與 macOS 之間應如何正規化？

# 定位

ERM：`Evidence.file`、`Project.root_path`。AGENTS.md 要求 CLI 行為同時適用 Windows 與 macOS，Epic 1 要保存 source file evidence。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | `Evidence.file` 一律使用 project-relative POSIX path，`Project.root_path` 保留輸入 root |
| B | `Evidence.file` 保留作業系統原生 path 格式 |
| C | 同時保存 normalized path 與 native path |
| D | 只保存檔名，不保存相對路徑 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 scanner output、JSON snapshot tests、Windows/macOS CLI 相容性、GUI source path 顯示與 clickable source path 行為。

# 優先級

Medium
- Medium：影響跨平台測試與 evidence 可追溯性。

---
# 解決記錄

- **回答**：A - `Evidence.file` 一律使用 project-relative POSIX path，`Project.root_path` 保留輸入 root
- **更新的規格檔**：spec/erm.dbml, spec/features/建立RAG系統地圖.feature
- **變更內容**：更新 `Evidence.file` 與 `Project.root_path` 定義，新增 evidence file path 格式 Example，要求跨 Windows/macOS 一律使用 project-relative POSIX path。
