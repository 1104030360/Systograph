# 釐清問題

`Project.canonical_path_digest` 在 macOS 與 Windows 上應使用哪一套 resolved path 正規化與大小寫規則？

# 定位

ERM：`Project.canonical_path_digest`；Feature：`匯入專案` 的 re-import reuse。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 使用平台原生 resolved path 與平台檔案系統大小寫語意後計算 digest |
| B | 統一轉 project-relative POSIX 字串且保持大小寫後計算 digest |
| C | 不依賴路徑字串，改用 repo identity metadata 計算 digest |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響相同路徑 project reuse、symlink、case-insensitive filesystem、orphan mappings、跨平台測試與 path privacy。

# 優先級

High
- 錯誤正規化會把不同 project 合併，或讓同一 project 在 restart/re-import 後產生新 identity。

---
# 解決記錄

- **回答**：A - 使用平台原生 resolved path 與平台檔案系統大小寫語意後計算 digest
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：明定 project identity digest 必須以平台解析後的真實路徑與實際檔案系統大小寫語意正規化；原始絕對路徑只限本機使用，不得輸出至 API、報告或 artifacts。
