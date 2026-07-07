# 釐清問題

Detail Scan 成功建立 child build 後，是否立即更新 project 的 `latest_build_id` 與 Viewer？

# 定位

Feature：`執行詳細掃描` 的「Detail Scan 必須建立 immutable child build」規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 成功 atomic publish 後立即更新 latest 與 Viewer |
| B | 保留原 latest，使用者需另行 promote child build |
| C | 只有 code-path detail scan 更新 latest，component detail scan 不更新 |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 B2→B3 lineage、latest pointer、Viewer reload、restart recovery、stale-base Apply 與 API response。

# 優先級

High
- 規格明確建立 child build，但未定義它是否成為新的 active build。

---
# 解決記錄

- **回答**：A - 成功 atomic publish 後立即更新 latest 與 Viewer
- **更新的規格檔**：`docs/spec/erm.dbml`、`docs/spec/features/執行詳細掃描.feature`
- **變更內容**：明定 `detail_scan` child build 成功 atomic publish 後必須立即成為 `Project.latest_build_id`，並由 Detail Scan response 原子更新 Viewer。
