# Task 7: Implement Filesystem Provider Inventory

## 目標
實作 `FilesystemProvider`，建立 deterministic file inventory。它要優先使用 git-aware inventory（tracked files + unignored untracked files），非 Git repo / zip project fallback recursive listing，並記錄 skipped files 與 skip reason。

## 為什麼要先做這個
Stage 2 是後續所有 providers 的掃描邊界。設計文件明確要求後續 provider 不應重新決定掃描範圍，因此 inventory 要先穩定。

## 前置需求
- Task 6 已完成 project root 與 output policy。
- Task 5 已完成 masking service，可支援 future metadata masking。
- 已確認預設 skip list。

## 實作範圍
- 建立 `FileInventory`、`FileRecord`、`SkippedFile` models。
- 優先執行 `git ls-files -z --cached --others --exclude-standard`。
- Git repo 預設包含 tracked files 與 unignored untracked files；不要求使用者先 `git add`。
- 非 Git repo / 使用者整包 zip project 使用 `pathlib` recursive listing，並用 `pathspec` 套用 root 與 nested `.gitignore` 規則。
- 排除 `.git`、`node_modules`、`.venv`、`dist`、`build`、binary、large logs、model weights。
- 將所有 file path 正規化為 project-relative POSIX path。

## 不包含範圍
- 不讀取全部檔案內容。
- 不做 AI suspicious file review。
- 不做 Semgrep/Tree-sitter。
- 不解析 config 或 dependency。
- 不預設掃描 gitignored files；若使用者把重要 source/config 放進 `.gitignore`，這不是 baseline inventory 的責任。

## 建議實作步驟
1. 建立 `src/kai_mind/core/providers/filesystem_provider.py`。
2. 實作 git repo detection。
3. 實作 git file list fallback。
4. 實作 recursive listing fallback。
5. 實作 skip rules 與 reason enum。
6. 加入 max file size metadata，但不要讀大檔內容。
7. 寫測試：git repo、non-git repo、skip dependency/build/binary、POSIX relative path。

## 預期輸出
- `src/kai_mind/core/providers/filesystem_provider.py`
- `tests/unit/core/test_filesystem_provider.py`
- `tests/fixtures/rag_projects/*` 視需要補小型檔案

## 驗收標準
- `FileInventory.files` 只包含 eligible files。
- skipped files 每筆都有 reason。
- evidence path 永遠不是 absolute path。
- Windows-style path input 仍輸出 POSIX `/`。
- provider 不修改被掃描 repo。
- Git repo 中未 `git add`、但未被 ignore 的新檔案會被納入 inventory。
- Gitignored files 預設不被納入 inventory。
- 非 Git repo / zip project 可透過 recursive listing 產生 inventory。

## 可能風險與注意事項
- `git ls-files` 失敗不能讓整體 scan 失敗，應 fallback。
- 不要掃進 `node_modules`、`.venv`、generated outputs。
- 不要因為擔心使用者不懂 Git，就預設繞過 `.gitignore`；這會增加 secret、local DB、cache、model weights、vector index 與 build output 被掃入的風險。
- fallback matcher 不可用簡化版 `fnmatch` 取代 gitignore 語意；`**/secret.env`、`docs/**/*.log` 這類規則必須和 Git mode 一致地排除。
- Git inventory 不可因 tracked/unignored symlink 而讀取 project root 外的 target；symlink-outside-root guard 必須在 git 與 recursive mode 都生效。
- Non-Git fallback 不可只讀 root `.gitignore`；nested `.gitignore` 例如 `service/.gitignore` 也會影響 scan boundary。
- 若未來要支援被 ignore 檔案，應只透過 explicit include override，例如 `include_paths` / `include_ignored`，且仍需套用 binary、size、symlink-outside-root 與 secret-safe 保護。
- 參考依據：Git 官方 `ls-files --exclude-standard`；`pathspec` 的 gitignore matcher；ripgrep docs 的 ignore/hidden/binary behavior 可作 scan boundary 參考。

## 新手提示
FilesystemProvider 不負責理解程式碼。它只回答：「哪些檔案值得後面的人看？」

## 視覺化說明
```text
┌──────────────┐
│ project_root │
└──────┬───────┘
       ↓
┌──────────────┐
│ git repo?    │
└──────┬───┬───┘
       │   │
   yes │   │ no
       ↓   ↓
┌──────────────┐  ┌──────────────────┐
│ git ls-files │  │ recursive listing │
└──────┬───────┘  └────────┬─────────┘
       └──────────┬────────┘
                  ↓
┌──────────────────────────┐
│ apply skip rules          │
│ respect .gitignore by     │
│ default                   │
└──────┬────────────┬──────┘
       ↓            ↓
┌──────────────┐ ┌──────────────────────────┐
│ FileInventory │ │ Skipped files + reasons │
└──────────────┘ └──────────────────────────┘
```
