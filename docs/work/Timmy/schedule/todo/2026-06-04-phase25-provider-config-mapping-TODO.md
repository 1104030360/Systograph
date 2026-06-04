# 2026-06-04 Phase 25 Provider Config Mapping TODO

## 目標

依照 `docs/work/Timmy/schedule/plan/unfinish/25-implement-provider-config-mapping-matrix.md`，補齊 `ComponentDetectionService` 對明確 provider config 的 slot-aware mapping。

## 實作邏輯

本階段只處理 Task 25 明確列入矩陣的 provider config：

- `vector_store.provider: qdrant`
- `providers.vector_store.provider: qdrant`
- `vector_store.provider: pgvector`
- `providers.vector_store.provider: pgvector`
- `llm.provider: ollama`
- `providers.llm.provider: ollama`

保留既有保守邊界：

- dependency-only 仍是 weak signal，不得單獨 `detected`。
- env key only 仍不得單獨 `detected`。
- `vector_store.provider` 只影響 `vector_store`。
- `llm.provider` 只影響 `llm`。
- 不新增 faiss、lancedb、weaviate、milvus 等未列入 Task 25 矩陣的 provider。

## 步驟

1. 讀取 `AGENTS.md`、Phase 25 dev prompt、Task 25 plan、現有 `ComponentDetectionService` 與 tests。
2. 先補 RED tests：
   - qdrant / pgvector provider config detected as `vector_store`。
   - ollama provider config detected as `llm`。
   - provider config 不污染其他 slots。
   - qdrant / ollama dependency-only 不得單獨 detected。
3. 實作最小 GREEN：
   - 建立 slot-aware provider config matrix。
   - 讓 `_vector_store_candidates` 與 `_llm_candidates` 共用矩陣判斷。
   - 保留既有 Chroma / OpenAI / route / unmapped regression 行為。
4. 跑 targeted tests。
5. 跑完整驗證：
   - `.venv/bin/python -m pytest`
   - `.venv/bin/ruff check .`
   - `.venv/bin/mypy`
6. 更新 report，逐項對照 Task 25 驗收標準。

## 驗收標準

- [x] `ComponentDetectionService` 支援 Task 25 provider config mapping matrix。
- [x] 每個新增 mapping 都有 unit tests。
- [x] dependency-only 與 env-key-only negative tests 維持通過。
- [x] 既有 Chroma、OpenAI、route/unmapped tests 維持通過。
- [x] `pytest` 全部通過。
- [x] `ruff check .` 通過。
- [x] `mypy` 通過。
- [x] 建立 Phase 25 report。
