# 釐清問題

Scan boundary 的 skipped audit trail 應透過哪個介面提供給使用者檢視？

# 定位

Feature：`掃描專案` 的「Deterministic hard-skip targets 必須保留 audit trail」規則。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 放在 `POST /api/scans` response 的 bounded skipped items |
| B | 提供 project/scan-scoped audit endpoint |
| C | 寫入 build manifest／artifact，由 Viewer 讀取 |
| D | 只寫安全 logs，不提供產品 UI |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 ScanCreateResponse、snapshot/build metadata、Viewer、path redaction、auditability 與 API tests。

# 優先級

Medium
- Audit trail 已要求保存，但目前沒有可觀察的產品 contract。

---
# 解決記錄

- **回答**：A - 放在 `POST /api/scans` response 的 bounded skipped items
- **更新的規格檔**：`docs/spec/features/掃描專案.feature`
- **變更內容**：明定 deterministic hard-skip targets 的 audit trail 透過 `POST /api/scans` response 的 bounded `skipped_items` 提供；內容必須使用 project-relative 或 redacted path representation，且不得建立 persisted skipped audit artifact。
