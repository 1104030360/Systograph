# 2026-06-02 Phase10 Dependency Manifest Provider TODO

## 階段目標

依照
`docs/work/Timmy/schedule/plan/unfinish/10-implement-dependency-manifest-provider.md`
實作 `DependencyManifestProvider`，讓 scanner 可以從 `FileInventory` 中唯讀解析
dependency manifests，產生 RAG framework、LLM SDK、vector store client 等
candidate dependency facts 與 evidence。

本階段只做 deterministic static parsing：

- 不執行 package manager。
- 不下載 dependency。
- 不遞迴解析 `-r` requirements include。
- 不建立完整 SBOM。
- 不做 vulnerability scan。
- 不判斷 final component slot 或 final readiness status。
- 不讓 raw secret 進入 facts、evidence、issues、logs 或 test snapshots。

## 實作邏輯

1. 延續 Task 7 的 inventory-first 邊界：
   `DependencyManifestProvider` 只處理 `FileInventory.files` 中已納入的
   manifest files，不自行遞迴搜尋 project root。
2. 延續 Task 8 / Task 9 的 provider-local output pattern：
   回傳 `ProviderScanResult`，包含 `ScanFact[]`、`Evidence[]`、
   `ParseIssue[]`。
3. `requirements.txt` 逐行 parse：
   - 忽略空行與註解。
   - 支援 PEP 508 name-based requirement、extras、version specifier、
     environment marker。
   - `-r` include、editable install、VCS URL、pip option 先輸出
     unsupported parse issue，不遞迴、不連網。
4. `pyproject.toml` 使用 Python 3.11+ 內建 `tomllib`：
   - 讀 `[project].dependencies`。
   - 讀 `[project.optional-dependencies]`。
   - 讀 `[tool.poetry.dependencies]`。
   - 讀 `[tool.poetry.group.*.dependencies]`。
   - 跳過 Poetry 的 `python` runtime constraint。
5. `package.json` 使用內建 `json`：
   - 讀 `dependencies`。
   - 讀 `devDependencies`。
   - 保留 dependency group 來源在 fact path / evidence path。
6. Python package name 使用 PyPA normalization：
   lowercase，並把 `.`, `_`, `-` 的連續片段歸一成 `-`。
7. Node package name 保留 npm scope，例如 `@scope/name`，並 lowercase 做
   comparison。
8. known RAG packages 先支援：
   - `langchain`
   - `llama-index`
   - `openai`
   - `qdrant-client`
   - `chromadb`
   - `ollama`

## TDD / BDD 步驟

### 1. RED：先寫 unit tests

- 測 `requirements.txt` 解析 `qdrant-client`、`openai`、`langchain`。
- 測 Python package normalization：`qdrant_client` 與 `qdrant-client`
  等價。
- 測 `pyproject.toml` 的 `[project].dependencies` /
  `[project.optional-dependencies]`。
- 測 Poetry `[tool.poetry.dependencies]` /
  `[tool.poetry.group.*.dependencies]`。
- 測 `package.json` 的 `dependencies` / `devDependencies`。
- 測 malformed manifest 不 crash，且另一個 manifest 仍可產生 facts。
- 測 unsupported requirements line 產生 parse issue，不連網、不遞迴。

### 2. GREEN：實作最小 provider

- 新增 `src/systograph/core/providers/dependency_manifest_provider.py`。
- 擴充 `ParseIssue.scan_stage`，增加 `dependency_manifest_parse`。
- 實作 manifest path 判斷。
- 實作 safe JSON / TOML parse。
- 實作 requirements line parse。
- 實作 known package rule mapping。
- 實作 fact/evidence builder、parse issue builder。

### 3. BDD-style integration tests

- 使用 `basic_qdrant_ollama_rag` fixture 驗證 Qdrant/Ollama dependency
  facts。
- 使用 `openai_external_provider_rag` fixture 驗證 OpenAI dependency fact。
- 使用 `malformed_config_rag` fixture 驗證 malformed manifest 產生
  parse issue。

### 4. Verification

Targeted verification：

```bash
.venv/bin/python -m pytest tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py
.venv/bin/ruff check src/systograph/core/models/scan.py src/systograph/core/providers/dependency_manifest_provider.py tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py
.venv/bin/mypy src/systograph/core/models/scan.py src/systograph/core/providers/dependency_manifest_provider.py tests/unit/core/test_dependency_manifest_provider.py tests/integration/test_phase10_dependency_manifest_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 驗收清單

- [x] `DependencyManifestProvider` 只吃 `FileInventory`。
- [x] `requirements.txt` 可解析 supported requirement lines。
- [x] `pyproject.toml` 可解析 PEP 621 dependencies。
- [x] `pyproject.toml` 可解析 Poetry dependencies。
- [x] `package.json` 可解析 `dependencies` / `devDependencies`。
- [x] `qdrant-client` 產生 vector store client candidate fact。
- [x] `openai` 產生 external LLM / embedding provider candidate fact。
- [x] `langchain` / `llama-index` 產生 framework candidate fact。
- [x] `chromadb` 產生 vector store client candidate fact。
- [x] `ollama` 產生 local LLM provider candidate fact。
- [x] package names 有 hyphen/underscore 差異時會 normalize。
- [x] Malformed manifest 不 crash，產生 parse issue。
- [x] Unsupported requirements lines 產生 parse issue，不遞迴、不連網。
- [x] Parse issue 使用 `dependency_manifest_parse` scan stage。
- [x] 不執行 package manager。
- [x] 不下載 dependency。
- [x] 所有 targeted verification 通過。
- [x] 所有 full verification 通過。
