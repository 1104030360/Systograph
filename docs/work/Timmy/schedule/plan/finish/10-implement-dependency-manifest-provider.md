# Task 10: Implement Dependency Manifest Provider

## 目標
實作 `DependencyManifestProvider`，從 `requirements.txt`、`pyproject.toml`、`package.json` 擷取 RAG framework、LLM SDK、vector store client 等 dependency facts。

## 為什麼要先做這個
dependency manifests 是判斷專案是否使用 LangChain、LlamaIndex、OpenAI、Qdrant、Chroma、Ollama 等元件的重要 deterministic evidence。它支援 component detection，但本身不直接決定 final status。

## 前置需求
- Task 7 已完成 file inventory。
- Task 8 已可 parse TOML/JSON 或提供可重用 parser。
- Task 12 尚未完成時可先輸出 provider-local facts。

## 實作範圍
- Parse `requirements.txt`。
- Parse `pyproject.toml` dependency sections。
- Parse `package.json` dependencies/devDependencies。
- 產生 dependency facts 與 evidence。
- 初始偵測 package：`langchain`、`llama-index`、`openai`、`qdrant-client`、`chromadb`、`ollama`。

## 不包含範圍
- 不建立完整 SBOM。
- 不執行 package manager。
- 不下載 dependency。
- 不做 vulnerability scan。

## 建議實作步驟
1. 建立 `src/systograph/core/providers/dependency_manifest_provider.py`。
2. 實作 requirements line parser，忽略註解與空行，先處理 PEP 508 name-based requirement；`-r` include、editable install、VCS URL 先記成 unsupported / parse issue，不遞迴讀檔、不連網。
3. 實作 pyproject dependency extraction，優先讀 `[project].dependencies` / `[project.optional-dependencies]`，並支援 Poetry 常見的 `[tool.poetry.dependencies]` / `[tool.poetry.group.*.dependencies]`。
4. 實作 package.json dependency extraction，先讀 `dependencies` / `devDependencies`，可保留 dependency group 來源作 evidence。
5. 將 Python package name 依 PyPA normalization 規則 normalize：lowercase，並把 `.`, `_`, `-` 的連續片段歸一成 `-`。
6. 以 rule_id 標記 known RAG packages。
7. 測試 Python/Node manifests、malformed manifest、unknown package、URL/editable/recursive requirements unsupported case。

## 預期輸出
- `src/systograph/core/providers/dependency_manifest_provider.py`
- `tests/unit/core/test_dependency_manifest_provider.py`

## 驗收標準
- `qdrant-client` 產生 vector store client candidate fact。
- `openai` 產生 external LLM / embedding provider candidate fact。
- `langchain` / `llama-index` 產生 framework candidate fact。
- malformed manifest 產生 parse issue，不中止 scan。

## 可能風險與注意事項
- dependency 只能表示「可能使用」，不能單獨讓 slot detected，通常還需要 code/config/Docker evidence。
- package names 有 hyphen/underscore 差異，要 normalize。
- 參考依據：Syft SBOM docs 可作 dependency inventory 設計參考，但 Epic 1 不直接整合 Syft。

## 參考專案與查證補充

### 1. 過去已參考的專案

#### Understand-Anything

來源：
- `docs/work/Timmy/reference/understand-anything-backend-review.md`
- `docs/work/Timmy/design/epic1-scan-pipeline-research.md`
- https://github.com/Lum1104/Understand-Anything

可借鑑：
- 它的 Project Scanner 先做 deterministic discovery，再把結果交給後續分析。
- 它會保留 `package.json`、`pyproject.toml`、`requirements.txt`、`go.mod`、`Cargo.toml` 等 manifest/config 作 framework detection evidence。
- 對 Systograph 來說，重點不是照抄它的 graph pipeline，而是借它「先掃 manifest / config，產生結構化 evidence，不直接讓 LLM 猜 dependency」的邊界。

#### GitDiagram

來源：
- `docs/work/Timmy/reference/gitdiagram-backend-review.md`
- `docs/work/Timmy/design/epic1-scan-pipeline-research.md`
- https://github.com/ahmedkhaleel2004/gitdiagram

可借鑑：
- 它比較適合作 graph/path validation discipline 參考。
- 它不適合作 dependency manifest parser 的主要參考，因為 Systograph 的 release-readiness evidence 不能只靠 README / repo tree 或 AI-first diagram。

#### Syft

來源：
- https://oss.anchore.com/docs/guides/sbom/catalogers/
- https://oss.anchore.com/docs/capabilities/python/

可借鑑：
- Syft 把 package discovery 拆成 catalogers；directory scan 會同時看已安裝 package 與 declared dependency，例如 `requirements.txt`。
- Syft 官方文件也提醒 declared dependency 通常不能保證實際 installed version，這符合 Systograph 的判斷：dependency manifest 只能產生 candidate fact，不應單獨讓 component slot detected。
- Epic 1 不直接整合 Syft；只借 lightweight SBOM / dependency inventory 的 fact 邊界。

### 2. Python dependency parser 參考

#### ScanCode Toolkit

來源：
- https://scancode-toolkit.readthedocs.io/en/latest/reference/scancode-supported-packages.html

可借鑑：
- 它支援大量 package manifests / lockfiles，包含 pip requirements、Poetry pyproject、一般 pyproject 等。
- 適合作「manifest coverage 與 parser 邊界」參考，不建議在 Epic 1 直接引入成 runtime dependency，避免 scanner 過重。

#### dparse

來源：
- https://pypi.org/project/dparse/

可借鑑：
- 它是 Python dependency files parser，支援 `requirements.txt` 與 `pyproject.toml`。
- 適合作 requirements edge cases 的輕量參考，例如 hash、marker、constraint 等格式。
- Epic 1 不一定要引入 dparse；若只要 initial known RAG package detection，可先自實作小範圍 parser。

#### pip-audit / PyPA requirement grammar

來源：
- https://github.com/pypa/pip-audit
- https://pip.pypa.io/en/stable/reference/requirements-file-format/
- https://pip.pypa.io/en/stable/reference/requirement-specifiers/
- https://packaging.pypa.io/en/stable/requirements.html

可借鑑：
- `pip-audit` 可 audit requirements file 與 local Python project，並支援 `pyproject.toml` project files；但它是 vulnerability audit 工具，不是 Systograph Epic 1 要整合的 dependency manifest provider。
- requirements 語法比單純 `name==version` 複雜，包含 marker、extras、direct URL、pip options、recursive include 等。
- 實作時可優先用 `packaging.requirements.Requirement` 的語法模型解析單行 name-based requirement；遇到 pip option、`-r`、editable、VCS URL 等先輸出 parse issue / unsupported evidence，不執行、不下載、不遞迴。

### 3. 目前任務採用的最小實作策略

- `package.json`：使用 Python 內建 `json`，讀 `dependencies` 與 `devDependencies`；不執行 npm，不讀 `node_modules`。
- `pyproject.toml`：使用 Python 3.11+ 內建 `tomllib`，讀 `[project].dependencies`、`[project.optional-dependencies]`、Poetry dependency sections；不執行 build backend 或 Poetry。
- `requirements.txt`：逐行處理，移除空白與安全的註解，優先用 PEP 508 / `packaging.requirements.Requirement` 能理解的 requirement line 取 package name；不支援的 pip 指令或 URL 型態保留為 parse issue。
- package name normalization：Python package 使用 PyPA normalization；Node package 保留 scope，例如 `@scope/name`，並 lowercase 做 comparison。
- output policy：輸出 candidate dependency facts + evidence，不輸出完整 secret，不把 dependency fact 當成 final readiness status。

## 查證來源

- Syft package catalogers: https://oss.anchore.com/docs/guides/sbom/catalogers/
- Syft Python capability: https://oss.anchore.com/docs/capabilities/python/
- ScanCode supported package manifests: https://scancode-toolkit.readthedocs.io/en/latest/reference/scancode-supported-packages.html
- dparse supported files: https://pypi.org/project/dparse/
- pip-audit examples and project-file support: https://github.com/pypa/pip-audit
- pip requirements format: https://pip.pypa.io/en/stable/reference/requirements-file-format/
- pip requirement specifiers: https://pip.pypa.io/en/stable/reference/requirement-specifiers/
- Packaging `Requirement`: https://packaging.pypa.io/en/stable/requirements.html
- PyPA pyproject specification: https://packaging.python.org/en/latest/specifications/pyproject-toml/
- PyPA package name normalization: https://packaging.python.org/en/latest/specifications/name-normalization/
- Python `tomllib`: https://docs.python.org/3/library/tomllib.html
- npm `package.json`: https://docs.npmjs.com/cli/v11/configuring-npm/package-json/

## 新手提示
Dependency provider 像看購物清單：知道專案買了哪些工具，但不代表每個工具真的有用上。

## 視覺化說明
```text
┌──────────────────────────┐
│ requirements / pyproject  │
│ package.json              │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ DependencyManifestProvider │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ Dependency facts          │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ ComponentDetection later  │
└──────────────────────────┘
```
