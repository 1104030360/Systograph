# Task 25: Implement Provider Config Mapping Matrix

## 目標

補齊 `ComponentDetectionService` 對明確 provider config 的 slot mapping 矩陣，讓 config-driven 專案不只依賴 Docker image 或 code pattern 才能被偵測成標準 RAG component。

## 為什麼要做

Task 13 已建立 raw facts 到 `rag-core-v1` component slots 的保守 mapping，但目前 provider config 支援還不完整：

- `providers.llm.provider: openai` 與 `providers.embedding.provider: openai` 已補上。
- `vector_store.provider: chroma` 已在 Phase 13 review fix 中補上。
- 其他明確 provider config，例如 `vector_store.provider: qdrant`、`vector_store.provider: pgvector`、`llm.provider: ollama`，仍可能被漏判。

這些漏判會讓 release-readiness report 對 config-driven 專案產生 false missing，明明使用者已在 config 明確宣告 provider，報告卻顯示對應 slot 缺失。

## 實作範圍

- 定義 provider config mapping matrix。
- 補 `ComponentDetectionService` 對支援 provider 的 slot-aware config 判斷。
- 保留 dependency-only 的 weak signal 行為，不得單獨升級成 `detected`。
- 保留 env key only 的保守行為，例如 `CHROMA_HOST` 不得單獨讓 `vector_store` detected。
- 補 regression tests 覆蓋每個支援 provider 的 positive / negative cases。

## 不包含範圍

- 不推導 endpoint、risk hints 或 flows；這些仍屬 Task 14。
- 不改 `ConfigParseProvider` 的 raw fact contract。
- 不新增尚未明確納入 Epic 1 支援矩陣的 provider。
- 不引入 LLM / AI 動態判斷 mapping。

## 建議 mapping matrix

| Config evidence | Slot | Provider | 預期 |
|---|---|---|---|
| `vector_store.provider: qdrant` | `vector_store` | `qdrant` | `detected` |
| `providers.vector_store.provider: qdrant` | `vector_store` | `qdrant` | `detected` |
| `vector_store.provider: pgvector` | `vector_store` | `pgvector` | `detected` |
| `providers.vector_store.provider: pgvector` | `vector_store` | `pgvector` | `detected` |
| `llm.provider: ollama` | `llm` | `ollama` | `detected` |
| `providers.llm.provider: ollama` | `llm` | `ollama` | `detected` |

## 測試補強

- `vector_store.provider` config 只影響 `vector_store`，不得污染 `llm` 或 `embedding_model`。
- `llm.provider` config 只影響 `llm`。
- dependency-only 仍停留在 weak signal / `unmapped_components`。
- env key only 仍不得直接 `detected`。
- 每個 detected instance 必須有 `evidence_ids`。

## 驗收標準

- `ComponentDetectionService` 支援明確 provider config 的 slot-aware mapping。
- 所有新增 mapping 都有 unit tests。
- 既有 Chroma、OpenAI、route/unmapped regression tests 持續通過。
- `pytest`、`ruff check .`、`mypy` 全部通過。

## 新手提示

Provider config mapping 的重點不是看到 provider 字串就 detected，而是同時確認：

```text
config path 指向哪個 slot
config value 指向哪個 provider
這個 provider 是否已在本階段支援矩陣中
```

## 視覺化說明

```text
ConfigParseProvider
  -> kind=config_value
  -> path=vector_store.provider
  -> value=qdrant

ComponentDetectionService
  -> slot-aware provider config mapping
  -> component:vector_store:qdrant
```
