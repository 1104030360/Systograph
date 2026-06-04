# 2026-06-04 Phase 25 Provider Config Mapping Report

## 實作邏輯

這次依照 `docs/work/Timmy/schedule/plan/unfinish/25-implement-provider-config-mapping-matrix.md` 補齊 `ComponentDetectionService` 的 slot-aware provider config mapping。

核心原則是同時確認三件事：

```text
config path 指向哪個 slot
config value 指向哪個 provider
provider 是否已列入 Task 25 支援矩陣
```

本階段支援的明確 mapping：

| Config evidence | Slot | Provider | 結果 |
|---|---|---|---|
| `vector_store.provider: qdrant` | `vector_store` | `qdrant` | `detected` |
| `providers.vector_store.provider: qdrant` | `vector_store` | `qdrant` | `detected` |
| `vector_store.provider: pgvector` | `vector_store` | `pgvector` | `detected` |
| `providers.vector_store.provider: pgvector` | `vector_store` | `pgvector` | `detected` |
| `llm.provider: ollama` | `llm` | `ollama` | `detected` |
| `providers.llm.provider: ollama` | `llm` | `ollama` | `detected` |

同時保留 Phase 13 的保守邊界：

- dependency-only 仍只會進 `unmapped_components`，不得單獨升級成 `detected`。
- env-key-only 仍不得直接讓 component slot `detected`。
- `vector_store.provider` 只影響 `vector_store`。
- `llm.provider` 只影響 `llm`。
- `faiss`、`lancedb`、`weaviate`、`milvus` 這類未列入 Task 25 的 provider 不新增偵測。

## 步驟

1. 依照 dev prompt 讀取 `AGENTS.md`、Linus 規則、Task 25 plan、現有 component detection 程式與測試。
2. 先補 RED tests，覆蓋 qdrant / pgvector / ollama provider config 的 positive cases。
3. 補 negative tests，確認 dependency-only 與 unsupported provider config 不會誤判。
4. 實作 slot-aware provider config matrix：
   - `VECTOR_STORE_CONFIG_PROVIDERS`
   - `LLM_CONFIG_PROVIDERS`
5. 將 `_vector_store_candidates` 與 `_llm_candidates` 接到明確 provider config 判斷。
6. 補 integration tests，確認 fixture 中的 qdrant config 會成為 vector store evidence，lancedb fixture 仍維持 missing。
7. 執行 targeted tests 與完整驗證。

## 測試方式

Targeted tests：

```bash
.venv/bin/python -m pytest tests/unit/core/test_component_detection_service.py tests/integration/test_phase13_component_detection_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 遇到的問題與解法

### 問題 1：不能只看 provider 字串

如果只看到 `ollama` 或 `qdrant` 就直接 mapping，會讓錯誤 slot 被污染，例如 `embedding.provider: ollama` 被誤判成 `llm`。

解法：provider config 必須同時檢查 path token 與 value。`llm.provider` 才能進 `llm`，`vector_store.provider` 才能進 `vector_store`。

### 問題 2：dependency-only 不可升級成 detected

`qdrant-client` 或 `ollama` dependency 只能代表專案可能支援這些 provider，不能證明系統真的使用它們。

解法：這次只新增 config-driven mapping，dependency-only 行為保持原本的 weak signal / `unmapped_components`。

### 問題 3：unsupported provider 不可偷偷納入

Task 25 明確不包含 `faiss`、`lancedb`、`weaviate`、`milvus` 等 provider。

解法：mapping 只從白名單常數讀取，不在矩陣內的 provider config 會落回 missing。

## 測試結果

- `.venv/bin/python -m pytest`：194 passed
- `.venv/bin/ruff check .`：All checks passed
- `.venv/bin/mypy`：Success, no issues found in 55 source files

## 驗收對照

- [x] `ComponentDetectionService` 支援明確 provider config 的 slot-aware mapping。
- [x] 所有新增 mapping 都有 unit tests。
- [x] qdrant / pgvector provider config 會 detected as `vector_store`。
- [x] ollama provider config 會 detected as `llm`。
- [x] `vector_store.provider` 不污染 `llm` 或 `embedding_model`。
- [x] `llm.provider` 不污染 `vector_store` 或 `embedding_model`。
- [x] dependency-only 仍停留在 weak signal / `unmapped_components`。
- [x] unsupported provider config 不會 detected。
- [x] 既有 Chroma、OpenAI、route/unmapped regression tests 持續通過。
- [x] `pytest`、`ruff check .`、`mypy` 全部通過。
