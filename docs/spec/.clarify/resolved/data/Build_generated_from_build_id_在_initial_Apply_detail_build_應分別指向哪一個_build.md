# 釐清問題

`generated_from_build_id` 在 `initial_scan`、`apply_confirmations` 與 `detail_scan` build 的 sibling artifacts 中，應分別指向哪一個 build？

# 定位

ERM：`Build.generated_from_build_id`、`Artifact.generated_from_build_id`、`CanonicalMap.generated_from_build_id`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 每個 artifact 都填目前正在產生它的 `build_id`；parent lineage 只使用 `based_on_build_id` |
| B | Initial artifact 填自己的 build；child artifact 填 parent build |
| C | 同一 snapshot 的所有 artifacts 都填第一個 initial build id |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 Build lineage、Apply／Detail Scan、cross-artifact validation、frontend B1/B2/B3 顯示與未來資料庫關聯。

# 優先級

High
- 若語意不一致，同一 build 的 artifacts 會產生互相矛盾的 lineage。

---
# 解決記錄

- **回答**：A - 每個 artifact 都填目前正在產生它的 `build_id`；parent lineage 只使用 `based_on_build_id`
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：將 Build、Artifact 與 CanonicalMap 的 `generated_from_build_id` 設為必填，並明定其值必須等於目前 `build_id`；parent lineage 僅由 `based_on_build_id` 表示。
