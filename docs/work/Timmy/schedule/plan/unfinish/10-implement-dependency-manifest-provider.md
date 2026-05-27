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
1. 建立 `src/kai_mind/core/providers/dependency_manifest_provider.py`。
2. 實作 requirements line parser，忽略註解與空行。
3. 實作 pyproject dependency extraction。
4. 實作 package.json dependency extraction。
5. 將 package name normalize 成 lowercase。
6. 以 rule_id 標記 known RAG packages。
7. 測試 Python/Node manifests、malformed manifest、unknown package。

## 預期輸出
- `src/kai_mind/core/providers/dependency_manifest_provider.py`
- `tests/core/test_dependency_manifest_provider.py`

## 驗收標準
- `qdrant-client` 產生 vector store client candidate fact。
- `openai` 產生 external LLM / embedding provider candidate fact。
- `langchain` / `llama-index` 產生 framework candidate fact。
- malformed manifest 產生 parse issue，不中止 scan。

## 可能風險與注意事項
- dependency 只能表示「可能使用」，不能單獨讓 slot detected，通常還需要 code/config/Docker evidence。
- package names 有 hyphen/underscore 差異，要 normalize。
- 參考依據：Syft SBOM docs 可作 dependency inventory 設計參考，但 Epic 1 不直接整合 Syft。

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
