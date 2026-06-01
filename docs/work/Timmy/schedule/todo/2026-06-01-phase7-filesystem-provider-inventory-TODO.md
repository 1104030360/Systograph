# Phase7 Filesystem Provider Inventory TODO

## 目標

實作 `FilesystemProvider`，建立 deterministic file inventory，讓後續 provider 共用同一個掃描邊界。

## 實作邏輯

- Git repo 優先使用 `git ls-files -z --cached --others --exclude-standard`。
- Git inventory 代表 tracked files + unignored untracked files，不要求使用者先 `git add`。
- 非 Git repo / zip project fallback 到 recursive listing。
- 預設尊重 `.gitignore`，不掃 gitignored files。
- 所有輸出 path 都轉成 project-relative POSIX path。
- dependency、build、virtualenv、binary、large logs、model weights、generated/minified files 都要 skip with reason。
- Provider 只建立 inventory，不讀完整檔案內容、不解析 config、不做 AI review。

## 步驟

1. 先寫 unit tests，覆蓋 git-aware inventory、non-Git recursive listing、skip rules、POSIX path normalization。
2. 補 BDD-style integration test，確認 sample project 可產生安全 inventory。
3. 建立 `FileInventory`、`FileRecord`、`SkippedFile` 與 skip reason/source mode enum。
4. 實作 `FilesystemProvider.build_inventory(project_root)`。
5. 逐步跑 targeted tests，確保每個 TDD slice 都先紅再綠。
6. 跑 `.venv/bin/python -m pytest`、`.venv/bin/ruff check .`、`.venv/bin/mypy`。
7. 完成後寫 Phase7 report，逐項核對 plan 驗收標準。

## 驗收清單

- [x] `FileInventory.files` 只包含 eligible files。
- [x] skipped files 每筆都有 reason。
- [x] evidence path 永遠不是 absolute path。
- [x] Windows-style path input 仍輸出 POSIX `/`。
- [x] provider 不修改被掃描 repo。
- [x] Git repo 中未 `git add`、但未被 ignore 的新檔案會被納入 inventory。
- [x] Gitignored files 預設不被納入 inventory。
- [x] 非 Git repo / zip project 可透過 recursive listing 產生 inventory。
- [x] 非 Git repo / zip project 的 `.gitignore` 支援 `**` gitignore 規則。
- [x] `git ls-files` 失敗時 fallback，不讓整體 scan 失敗。
- [x] 不掃進 `node_modules`、`.venv`、generated outputs、binary、large logs、model weights。
