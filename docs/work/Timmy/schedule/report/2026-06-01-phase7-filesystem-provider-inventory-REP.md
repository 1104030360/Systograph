# 2026-06-01 Phase7 Filesystem Provider Inventory Report

## 實作摘要

本階段依照 `07-implement-filesystem-provider-inventory.md` 實作 Stage 2
filesystem inventory。這一層只決定「哪些檔案值得後續 providers 掃」，
不解析 config、不讀完整檔案內容、不做 AI review。

本次新增：

- `FileInventory`、`FileRecord`、`SkippedFile` models。
- `FileInventorySource` 與 `SkipReason` enums。
- `FilesystemProvider.build_inventory(project_root)`。
- Git repo 優先使用 `git ls-files -z --cached --others --exclude-standard`。
- 非 Git repo / zip project fallback recursive listing。
- 預設尊重 `.gitignore`，不掃 gitignored files。
- Non-Git fallback 使用 `pathspec` 套用 gitignore 規則，避免 `**` 規則和
  Git mode 行為不一致。
- path 全部輸出成 project-relative POSIX path。
- skip dependency/build/virtualenv/cache/binary/large log/model weight/generated
  files，且記錄 skip reason。
- symlink 指到 project root 外時 skip，避免讀到 repo 外資料。

## 實作邏輯

這次用 TDD + BDD vertical slice 實作：

1. 先寫 unit tests，讓測試因缺少 `kai_mind.core.models.filesystem`
   失敗，確認 RED。
2. 補最小 models 與 provider，讓 git-aware inventory、recursive
   inventory、path normalization 先通過。
3. 補 fallback、symlink、read-only behavior 測試。
4. 修正 symlink path normalization：skipped path 應記錄 repo 內 symlink
   名稱，不應 resolve 到 repo 外。
5. 補 BDD-style integration test，使用既有 RAG fixture 驗證真實 sample
   project 會產出安全、相對、POSIX 的 file inventory。
6. 跑 targeted tests、ruff、mypy，再跑 full pytest、full ruff、full mypy。

核心設計決策：

- Git mode 不是只掃 tracked files，而是 tracked + unignored untracked
  files，因此使用者沒 `git add` 的新檔案仍會被掃到。
- Gitignored files 預設不掃。這是 project boundary，不是 scanner 應自動
  繞過的限制。
- Future explicit include override 可以再做，但不屬於 Phase7 baseline。
- Directory-level skip 會記錄 `node_modules/`、`.venv/`、`dist/` 這類
  summary，不展開 dependency/build 目錄底下所有檔案。
- `.gitignore` 規則交給 `pathspec`，不維護手寫 `fnmatch` matcher。
- Binary 判斷只讀前 4096 bytes，不讀完整檔案。
- Large file 使用 `stat()` 判斷，避免讀取大檔內容。
- `FileInventory` 是後續 config/docker/dependency/code pattern providers 的
  共用輸入，不讓每個 provider 重新決定 scan boundary。

## 實作步驟

### 1. 建立 TODO

新增：

- `docs/work/Timmy/schedule/todo/2026-06-01-phase7-filesystem-provider-inventory-TODO.md`

內容包含：

- 實作邏輯
- 步驟
- 驗收清單

### 2. 建立 unit tests

新增：

- `tests/unit/core/test_filesystem_provider.py`

測試覆蓋：

- Git repo 包含 tracked files。
- Git repo 包含未 `git add`、但未被 ignore 的 untracked files。
- Gitignored files 預設不進入 inventory，並記錄 `gitignored` reason。
- Non-Git fallback 支援 `**/secret.env`、`docs/**/*.log` 這類 gitignore
  規則。
- Non-Git / zip project 使用 recursive inventory。
- `node_modules`、`.venv`、`dist` 使用 directory-level skip。
- model weight、large log、binary files 會 skip with reason。
- path normalization 輸出 project-relative POSIX path。
- Windows-style path input 會轉成 `/`。
- `git ls-files` 失敗會 fallback recursive inventory。
- symlink 指到 project root 外會 skip。
- provider 不在被掃描 project root 寫入 artifact。

### 3. 建立 BDD-style integration test

新增：

- `tests/integration/test_phase7_filesystem_provider_behaviors.py`

測試情境：

- `basic_qdrant_ollama_rag` fixture 會產生安全 inventory。
- inventory 包含 README、Docker Compose、requirements、source files、
  `.env.example` 這些 scanner signal。
- inventory path 都不是 absolute path。
- inventory path 都是 POSIX `/`。
- inventory 不包含 `node_modules` 或 `.venv`。

### 4. 建立 models

新增：

- `src/kai_mind/core/models/filesystem.py`

主要型別：

- `FileInventorySource`
- `SkipReason`
- `FileRecord`
- `SkippedFile`
- `FileInventory`

### 5. 建立 provider

新增：

- `src/kai_mind/core/providers/filesystem_provider.py`

主要行為：

- `build_inventory(project_root)`。
- `normalize_project_relative_path(path, project_root=...)`。
- Git work tree detection。
- Git inventory by `git ls-files -z --cached --others --exclude-standard`。
- Gitignored skipped files recording by `git check-ignore -z --stdin`。
- Recursive inventory fallback。
- `pathspec` gitignore matcher for non-Git / zip project。
- Hard skip directories。
- File-level skip reason classification。
- Safe size and binary metadata checks。

## 遇到的問題與解法

### 1. Read-only sandbox 無可用 temporary directory

第一次執行 pytest 時，sandbox 回傳：

```text
No usable temporary directory found
```

這是執行環境限制，不是程式碼錯誤。後續驗證改用已核准的 escalated
command 執行 `.venv/bin/python -m pytest`。

### 2. `.bin` 被過度分類成 model weight

第一輪測試發現 `binary.bin` 被分類為 `model_weight`。這太粗，會把一般
binary file 誤判成模型權重。

解法：

- 移除 `.bin` model weight suffix。
- 明確模型權重保留 `.gguf`、`.ggml`、`.onnx`、`.pt`、`.pth`、
  `.safetensors`。
- 一般 binary 交給 NUL-byte prefix 判斷。

### 3. Symlink outside root 不能先 resolve 再取 relative path

symlink 指到 root 外時，如果先 `resolve()`，會導致 path relative_to
project root 失敗。

解法：

- 記錄 skipped path 時優先用 symlink 在 repo 內的 lexical path。
- 判斷是否指到 root 外時才使用 resolved target。

### 4. Non-Git fallback 的 `fnmatch` matcher 會漏掉 `**` gitignore 語意

後續檢查發現 non-Git / zip project fallback 原本使用簡化版
`fnmatch` matcher。這會讓 `**/secret.env`、`docs/**/*.log` 這類
`.gitignore` 規則和 Git mode 不一致，部分本該被 ignore 的檔案會進入
inventory。

解法：

- 先新增 regression test，確認 `secret.env`、`nested/secret.env`、
  `docs/scan.log`、`docs/deep/scan.log` 在 fallback mode 都會被 skip。
- 將 runtime dependency 增加 `pathspec>=1.1,<2`。
- `uv lock` 更新 `uv.lock`，讓 runtime dependency 和 lock 一致。
- 移除手寫 `fnmatch` matcher，改用
  `PathSpec.from_lines("gitignore", lines)` 與 `match_file(path)`。

## 測試方式

Targeted tests：

```bash
.venv/bin/python -m pytest tests/unit/core/test_filesystem_provider.py tests/integration/test_phase7_filesystem_provider_behaviors.py
```

Targeted lint/type checks：

```bash
.venv/bin/ruff check src/kai_mind/core/models/filesystem.py src/kai_mind/core/providers/filesystem_provider.py tests/unit/core/test_filesystem_provider.py tests/integration/test_phase7_filesystem_provider_behaviors.py
.venv/bin/mypy src/kai_mind/core/models/filesystem.py src/kai_mind/core/providers/filesystem_provider.py tests/unit/core/test_filesystem_provider.py tests/integration/test_phase7_filesystem_provider_behaviors.py
```

Full validation：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 測試結果

- Targeted pytest：`7 passed`
- Follow-up regression pytest：`1 passed`
- Follow-up targeted pytest：`8 passed`
- Targeted ruff：`All checks passed`
- Targeted mypy：`Success: no issues found in 4 source files`
- Full pytest：`102 passed`
- Full ruff：`All checks passed`
- Full mypy：`Success: no issues found in 34 source files`

## Plan 驗收確認

- `FileInventory.files` 只包含 eligible files：已完成，unit + integration
  tests 覆蓋。
- skipped files 每筆都有 reason：已完成，`SkippedFile.reason` 為 enum。
- evidence path 永遠不是 absolute path：已完成，unit + integration tests
  覆蓋。
- Windows-style path input 仍輸出 POSIX `/`：已完成，unit test 覆蓋。
- provider 不修改被掃描 repo：已完成，unit test 覆蓋。
- Git repo 未 `git add`、但未被 ignore 的新檔案會被納入 inventory：已
  完成，unit test 覆蓋。
- Gitignored files 預設不被納入 inventory：已完成，unit test 覆蓋。
- 非 Git repo / zip project 可透過 recursive listing 產生 inventory：已
  完成，unit test 覆蓋。
- Non-Git fallback 支援 `**` gitignore 規則：已完成，unit regression test
  覆蓋。
- `git ls-files` 失敗不能讓整體 scan 失敗：已完成，fallback unit test
  覆蓋。
- 不掃進 `node_modules`、`.venv`、generated outputs：已完成，unit +
  integration tests 覆蓋。
- 不讀取全部檔案內容：已完成，binary check 只讀前 4096 bytes，大檔使用
  `stat()` metadata。
- 不做 AI suspicious file review：已遵守。
- 不做 Semgrep/Tree-sitter：已遵守。
- 不解析 config 或 dependency：已遵守。

## 後續注意

- 後續 providers 應接收 `FileInventory` 作為輸入，不應重新走 project root
  自行決定掃描範圍。
- Explicit include override、AI-assisted scan boundary review 應留到後續
  phase，不能混進 Phase7 baseline。
