# Task 12a: Extract Provider Rule Catalogs

## 目標

將 provider 中會持續成長的 deterministic detection rules，整理成
package-bundled TOML rule catalogs，讓後續新增 AI/RAG package、Docker image、
code pattern 時，不必每次都直接修改 provider Python 檔案。

本任務只處理「provider-local rule catalog」：

- dependency package rules。
- Docker image rules。
- code pattern rules。

它不處理 final component detection，也不改 `ai-system-map/v1` JSON contract。

## 為什麼排在 Task 11 後、Task 12 前

Task 10 已完成 `DependencyManifestProvider`，目前 package rules 還是硬編碼在
provider 裡。

Task 9 的 `DockerComposeProvider` 也有類似問題：Qdrant、Ollama、pgvector
image rule 目前硬編碼在 `_image_rule_id()`。

Task 11 會新增 `CodePatternProvider`，它也會有 regex / pattern rules。

因此不要現在只抽 Task 10 的 dependency rules。應等 Task 11 做完後，一次整理：

```text
Task 9  Docker image rules
Task 10 Dependency package rules
Task 11 Code pattern rules
        ↓
Task 12a Extract Provider Rule Catalogs
        ↓
Task 12 Aggregate Raw Scan Facts
```

這樣 Task 12 的 `ProjectScanService` 只需要收集穩定的 facts/evidence/issues，
不用知道 rule 是從 Python dict 還是 TOML catalog 來。

## 為什麼使用 TOML

採 TOML，不採 JSON / YAML。

理由：

- Python 3.11+ 內建 `tomllib`，讀 TOML 不需要新增 dependency。
- TOML 支援 comments，適合長期由人維護 rule catalog。
- TOML 結構比 JSON 更適合 config，比 YAML 更窄，較不容易引入不必要語法彈性。
- 本 repo 已經多處使用 `pyproject.toml` / `tomllib`，符合現有技術棧。

## 前置需求

- Task 9 已完成 `DockerComposeProvider`。
- Task 10 已完成 `DependencyManifestProvider`。
- Task 11 已完成 `CodePatternProvider`。
- Task 5 已完成 `SecretMaskingService`。
- Task 7 已完成 `FileInventory` 掃描邊界。

## 實作範圍

### 1. Dependency package rule catalog

將 Task 10 目前硬編碼的 package rules 移到 TOML：

- Python packages：
  - `langchain`
  - `llama-index`
  - `openai`
  - `qdrant-client`
  - `chromadb`
  - `ollama`
- Node packages：
  - `langchain`
  - `llama-index`
  - `openai`

後續可增加：

- `langchain-openai`
- `langchain-community`
- `pymilvus`
- `milvus`
- `weaviate-client`
- `faiss-cpu`
- `sentence-transformers`
- `lancedb`

### 2. Docker image rule catalog

將 Task 9 目前硬編碼的 Docker image rules 移到 TOML：

- `qdrant/qdrant`
- `ollama/ollama`
- `pgvector/pgvector`

後續可增加：

- `milvusdb/milvus`
- `weaviate`
- `chromadb/chroma`
- `postgres`
- `redis`

### 3. Code pattern rule catalog

將 Task 11 的 regex / pattern rules 移到 TOML：

- rule id。
- language / file extensions。
- fact kind。
- regex pattern。
- optional group name。
- snippet policy。

### 4. Rule loader

建立共用 loader，例如：

```text
src/systograph/core/rules/
  dependency_manifest_rules.toml
  docker_image_rules.toml
  code_pattern_rules.toml

src/systograph/core/services/rule_catalog_loader.py
```

Provider 預設使用 package-bundled catalogs；測試可注入 custom catalog path。

### 5. Rule schema validation

載入 rule catalog 時必須 validate：

- 必填欄位存在。
- `rule_id` 不可空白。
- package / image / regex 不可空白。
- ecosystem / rule type 必須是允許值。
- duplicate package/image/pattern 不可靜默覆蓋。
- duplicate `rule_id` 不可靜默覆蓋。
- prefix match 必須明確設定，不可靠猜。
- regex rule 必須能 compile。

## 不包含範圍

- 不外部化 `SecretMaskingService` rules。
- 不做 remote rule download。
- 不讓被掃描 repo 自行提供 scanner rules。
- 不讓使用者 runtime 任意覆蓋 scanner rules。
- 不改 `ai-system-map/v1` schema。
- 不改 final component detection decision。
- 不把 dependency / image / code pattern fact 直接升級成 detected slot。

## 建議 TOML 形狀

### dependency_manifest_rules.toml

```toml
[[python]]
package = "langchain"
rule_id = "dependency_rag_framework_langchain"
match_prefix = true

[[python]]
package = "qdrant-client"
rule_id = "dependency_vector_store_client_qdrant"
match_prefix = false

[[node]]
package = "openai"
rule_id = "dependency_external_llm_embedding_openai"
match_prefix = false
```

### docker_image_rules.toml

```toml
[[images]]
repository = "qdrant/qdrant"
rule_id = "docker_qdrant_image_detected"

[[images]]
repository = "ollama/ollama"
rule_id = "docker_ollama_image_detected"
```

### code_pattern_rules.toml

```toml
[[patterns]]
rule_id = "code_qdrant_client_detected"
kind = "code_pattern"
languages = ["python"]
extensions = [".py"]
regex = "\\bQdrantClient\\b"
snippet_group = ""
```

## 建議實作步驟

1. 建立 `src/systograph/core/rules/` 目錄。
2. 建立三份 TOML catalogs：
   - `dependency_manifest_rules.toml`
   - `docker_image_rules.toml`
   - `code_pattern_rules.toml`
3. 建立 rule model：
   - `DependencyPackageRule`
   - `DockerImageRule`
   - `CodePatternRule`
4. 建立 `RuleCatalogLoader`，使用 `importlib.resources` 讀 package-bundled TOML。
5. 支援測試注入 custom catalog path。
6. 實作 catalog validation。
7. 重構 `DependencyManifestProvider`：移除 `PYTHON_RULES` / `NODE_RULES`
   硬編碼，改讀 dependency rule catalog。
8. 重構 `DockerComposeProvider`：移除 `_image_rule_id()` 中的 hardcoded
   image if/else，改讀 Docker image rule catalog。
9. 重構 `CodePatternProvider`：改讀 code pattern rule catalog。
10. 保留 deterministic ordering，避免 facts/evidence snapshot 漂移。
11. 寫 unit tests：
    - valid catalog loads。
    - malformed TOML rejected。
    - missing required field rejected。
    - duplicate package/image/rule_id rejected。
    - regex compile failure rejected。
    - injected test catalog works。
12. 寫 provider regression tests：
    - Task 9 / 10 / 11 原本 facts/evidence 不變。
    - prefix match 行為不變。
    - unknown package/image/pattern 不產生 known rule fact。

## 預期輸出

- `src/systograph/core/rules/dependency_manifest_rules.toml`
- `src/systograph/core/rules/docker_image_rules.toml`
- `src/systograph/core/rules/code_pattern_rules.toml`
- `src/systograph/core/services/rule_catalog_loader.py`
- `tests/unit/core/test_rule_catalog_loader.py`
- 更新：
  - `src/systograph/core/providers/dependency_manifest_provider.py`
  - `src/systograph/core/providers/docker_compose_provider.py`
  - `src/systograph/core/providers/code_pattern_provider.py`

## 驗收標準

- Provider 預設可從 package-bundled TOML rule catalogs 載入 rules。
- 測試中可注入 custom TOML catalog。
- `DependencyManifestProvider` 不再硬編碼 package mapping dict。
- `DockerComposeProvider` 不再用 hardcoded image if/else 判斷 Qdrant/Ollama/pgvector。
- `CodePatternProvider` 不再把主要 regex rules 全部硬編碼在 provider 檔案。
- Rule catalog malformed 時會明確失敗，不會靜默 fallback。
- Duplicate package/image/rule_id 會明確失敗，不會靜默覆蓋。
- Regex rule 無法 compile 時會明確失敗。
- 原本 Task 9 / 10 / 11 的 provider behavior tests 全部通過。
- Full verification 通過：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 可能風險與注意事項

- 不要把 rule catalog 做成可由被掃描 repo 提供，否則 scanner truth 會被 target repo 影響。
- 不要把 secret masking rules 一起外部化；secret masking 是安全核心，應先保持 fail-closed。
- TOML catalog 只應是 package-bundled deterministic rules，不是 user policy。
- Rule catalog loader 必須使用 package resource loading，不可依賴 current working directory。
- Rule id 是後續 component detection / risk / evidence 對應的重要 contract，重構時不能隨便改名。
- 若新增更多 provider rules，要先補 fixtures 或 provider-level tests，避免 rule catalog 變成無測試的清單。

## 新手提示

Rule catalog 就像 scanner 的「偵測字典」。Provider 還是負責讀檔、parse、產生
facts；catalog 只是把「哪些 package / image / pattern 算是重要訊號」從 Python
程式碼移到可 review 的設定檔。

## 視覺化說明

```text
┌──────────────────────────┐
│ package-bundled TOML      │
│ rule catalogs             │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ RuleCatalogLoader         │
│ validate + normalize      │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ Providers                 │
│ dependency / docker / code│
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ ScanFact + Evidence       │
└──────────┬───────────────┘
           ↓
┌──────────────────────────┐
│ Task 12 aggregation       │
└──────────────────────────┘
```
