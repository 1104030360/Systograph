# 2026-06-02 Phase10 Dependency Manifest Provider Report

## 階段目標

依照
`docs/work/Timmy/schedule/plan/unfinish/10-implement-dependency-manifest-provider.md`
完成 `DependencyManifestProvider`，讓 scanner 可以唯讀解析
`requirements.txt`、`pyproject.toml`、`package.json`，輸出 RAG framework、
LLM SDK、vector store client 的 candidate dependency facts 與 evidence。

本階段沒有執行 package manager、沒有下載 dependency、沒有建立完整 SBOM，也沒有把
dependency facts 直接轉成 final component detection 或 readiness status。

## 實作邏輯

1. Provider 延續 inventory-first 邊界：
   `DependencyManifestProvider.collect()` 只讀 `FileInventory.files` 已納入的
   manifest files，不自行掃描 project root。
2. Output 延續 provider-local contract：
   回傳 `ProviderScanResult`，包含 `ScanFact[]`、`Evidence[]`、
   `ParseIssue[]`。
3. `requirements.txt` parser：
   - 忽略空行與註解。
   - 使用 `packaging.requirements.Requirement` 解析 PEP 508 name-based
     requirement。
   - `-r` include、editable install、VCS URL、pip option 先產生 unsupported
     parse issue。
4. `pyproject.toml` parser：
   - 使用 Python 內建 `tomllib`。
   - 讀 `[project].dependencies`。
   - 讀 `[project.optional-dependencies]`。
   - 讀 Poetry `[tool.poetry.dependencies]`。
   - 讀 Poetry `[tool.poetry.group.*.dependencies]`。
   - 跳過 Poetry `python` runtime constraint。
5. `package.json` parser：
   - 使用 Python 內建 `json`。
   - 讀 `dependencies` 與 `devDependencies`。
6. Package name normalization：
   - Python 使用 PyPA normalization：lowercase，且把 `.`, `_`, `-` 的連續片段歸一成 `-`。
   - Node 保留 npm scope 並 lowercase。
7. Known package rules：
   - `langchain` -> RAG framework candidate。
   - `llama-index` / `llama-index-*` -> RAG framework candidate。
   - `openai` -> external LLM / embedding provider candidate。
   - `qdrant-client` -> vector store client candidate。
   - `chromadb` -> vector store client candidate。
   - `ollama` -> local LLM provider candidate。

## 實作步驟

1. 先寫 unit tests：
   `tests/unit/core/test_dependency_manifest_provider.py`。
2. 先寫 BDD-style integration tests：
   `tests/integration/test_phase10_dependency_manifest_provider_behaviors.py`。
3. 執行 targeted pytest，確認 RED：
   provider module 尚未存在，測試收集失敗。
4. 新增：
   `src/kai_mind/core/providers/dependency_manifest_provider.py`。
5. 擴充：
   `src/kai_mind/core/models/scan.py` 的 `ParseIssue.scan_stage`，增加
   `dependency_manifest_parse`。
6. 在 `pyproject.toml` 增加 runtime direct dependency：
   `packaging>=26,<27`。
7. 執行 `uv lock` 同步 `uv.lock`。
8. 補 `malformed_config_rag/package.json`，作為 malformed dependency manifest
   fixture。
9. 將 TODO 驗收清單全部勾選完成。

## 測試方式

Targeted verification：

```bash
.venv/bin/python -m pytest tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py
.venv/bin/ruff check src/kai_mind/core/models/scan.py src/kai_mind/core/providers/dependency_manifest_provider.py tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py
.venv/bin/mypy src/kai_mind/core/models/scan.py src/kai_mind/core/providers/dependency_manifest_provider.py tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 遇到的問題與處理方式

### 1. Read-only sandbox 無法讓 pytest 建立 temp file

第一次執行 pytest 時，sandbox 沒有可用 temp directory，pytest 還沒進入 test
collection 就失敗。這不是程式碼 regression。

處理方式：
- 使用 escalated pytest 重新執行。
- 重新執行後得到真正的 TDD RED：provider module 尚未存在。

### 2. 一個 unit test 錯誤假設 parse error evidence 一定在最後

實作後 targeted pytest 有 1 個測試失敗。原因是測試用 `result.evidence[-1]`
假設 parse error evidence 在最後，但 provider 會繼續處理下一個 manifest，所以順序不是行為 contract。

處理方式：
- 改成搜尋 `kind == "parse_error"` 的 evidence。
- 不改 provider 行為。

## 測試結果

Targeted verification：

- `.venv/bin/python -m pytest tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py`
  - 結果：`9 passed`
- `.venv/bin/ruff check src/kai_mind/core/models/scan.py src/kai_mind/core/providers/dependency_manifest_provider.py tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py`
  - 結果：`All checks passed!`
- `.venv/bin/mypy src/kai_mind/core/models/scan.py src/kai_mind/core/providers/dependency_manifest_provider.py tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py`
  - 結果：`Success: no issues found in 4 source files`

Full verification：

- `.venv/bin/python -m pytest`
  - 結果：`138 passed`
- `.venv/bin/ruff check .`
  - 結果：`All checks passed!`
- `.venv/bin/mypy`
  - 結果：`Success: no issues found in 43 source files`

## 驗收結果

- `requirements.txt` parser：完成。
- `pyproject.toml` parser：完成。
- `package.json` parser：完成。
- dependency facts / evidence：完成。
- known RAG packages rule mapping：完成。
- malformed manifest parse issue：完成。
- unsupported requirements parse issue：完成。
- scanner read-only / no network / no package manager execution：完成。
- targeted verification：通過。
- full verification：通過。
