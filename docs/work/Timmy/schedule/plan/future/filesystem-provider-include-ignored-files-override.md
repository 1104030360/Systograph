# Future: Filesystem Provider Include Ignored Files Override

## 來源
Task 7 (Implement Filesystem Provider Inventory) 在「可能風險與注意事項」中明確提到：

> 若未來要支援被 ignore 檔案，應只透過 explicit include override，例如 `include_paths` / `include_ignored`，且仍需套用 binary、size、symlink-outside-root 與 secret-safe 保護。

## 目的
讓使用者可以明確指定將被 `.gitignore` 排除的檔案重新納入 scan inventory。某些使用者可能把重要 config 或 source 放在 `.gitignore` 中，需要有安全的方式讓 scanner 存取。

## 觸發條件
- 使用者回報重要 config 被 `.gitignore` 排除，scanner 無法偵測關鍵 RAG component。
- 使用者把 `.env`（非 `.env.example`）或 local config 放在 `.gitignore` 中。
- 需要掃描被 ignore 的 Docker volume、local vector index 路徑等。

## 設計約束
- 只能透過 explicit include override（例如 `include_paths` / `include_ignored`），不可預設繞過 `.gitignore`。
- 即使 include，仍需套用：
  - Binary file filter
  - File size 上限
  - Symlink-outside-root guard
  - Secret-safe 保護（不可因 include 而把 secret 掃入 output）
- 設定檔格式需有 schema validation。

## 與既有任務關係
- Task 7：已建立 `FilesystemProvider` 與 skip rules。
- Task 23：hardening 階段可驗證 include override 的安全性。
- Task 16：`MapBuildService` 需要傳遞 include override 設定。

## 不做事項
- 不預設掃描 gitignored files。
- 不掃描 `.git` 目錄本身。
- 不繞過 binary、size、symlink 保護。
