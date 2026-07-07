# 釐清問題

`inventory_digest`、`Artifact.digest` 與 `ManualMapping.digest` 是否應使用同一套 canonical serialization 與 hash 規格？

# 定位

ERM：`ScanSnapshot.inventory_digest`、`Artifact.digest`、`ManualMapping.digest`。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 全部使用同一版本化 canonical JSON + SHA-256 規格，各自定義納入欄位 |
| B | 每種 digest 各自定義演算法與 serialization |
| C | Digest 視為 adapter-owned opaque versioned string |
| Short | 提供其他簡短答案（<=5 字） |

# 影響範圍

影響 Apply idempotency、stale detection、artifact integrity、restart recovery、跨平台 deterministic serialization 與未來 DB adapter。

# 優先級

Medium
- 功能語意已存在，但缺少 deterministic digest contract 會造成不同 adapter 計算不一致。

---
# 解決記錄

- **回答**：A - 全部使用同一版本化 canonical JSON + SHA-256 規格，各自定義納入欄位
- **更新的規格檔**：`docs/spec/erm.dbml`
- **變更內容**：明定 `ScanSnapshot.inventory_digest`、`Artifact.digest` 與 `ManualMapping.digest` 共用 `canonical-json/v1 + SHA-256` 規格，但各 digest 由自身 contract 定義納入 hash 的欄位集合。
