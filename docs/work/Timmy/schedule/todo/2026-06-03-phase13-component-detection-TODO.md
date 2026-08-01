# 2026-06-03 Phase 13 Component Detection TODO

## 目標

實作 `ComponentDetectionService`，把 Task 12 聚合出的 raw `ScanFact[]` / `Evidence[]` 對應到 `rag-core-v1` 的 `components_by_slot`，並保留 `extensions` / `unmapped_components`。本階段核心原則是：`detected` 必須有 evidence；dependency-only 只能是 weak signal；不確定的 evidence 不可硬塞進 standard slot。

## 實作邏輯

1. 使用 TDD + BDD：先寫單元測試與 fixture 行為測試，確認 RED 後才寫 service。
2. 保留 provider 邊界：Config / Docker / Dependency / CodePattern providers 只產生 raw facts；`ComponentDetectionService` 才做 slot 判斷。
3. 使用現有 `RagTemplate` 與 `ai-system-map/v1` models：直接輸出 `ComponentSlot`、`ComponentInstance`、`ExtensionComponent`、`UnmappedComponent`。
4. 不新增 `confidence` 欄位；用 internal evidence strength 判斷 strong / weak / unknown。
5. 只做 Task 13 範圍：component slots / instances / extensions / unmapped。endpoint、risk hint、flow derivation 留給 Task 14。
6. 補最小 provider-local catalog 缺口：Chroma Docker image 與 `chromadb.HttpClient` / `AsyncHttpClient` / `PersistentClient` code pattern，讓 Task 13 的 Chroma mode detection 有足夠 raw facts。

## 步驟

1. 補 `tests/unit/core/test_component_detection_service.py`：
   - 所有 `rag-core-v1` slots 都會被初始化。
   - Docker Qdrant -> `vector_store` detected。
   - missing citation slot -> status `missing` 且 instances 為空。
   - dependency-only `chromadb` 不得讓 `vector_store` detected。
   - Chroma `HttpClient` / `PersistentClient` code pattern 可讓 `vector_store` detected。
   - OpenAI config / SDK signal 可對應 `llm` / `embedding_model`。
   - custom router evidence 不得硬塞 retriever，要進 `unmapped_components`。
   - reranker evidence 可成為 extension candidate。
   - 每個 detected instance 都有 evidence_ids。
2. 補 `tests/integration/test_phase13_component_detection_behaviors.py`：
   - `basic_qdrant_ollama_rag` raw scan 可產生 detected vector store / llm / retriever 等核心 slots。
   - `custom_router_rag` 會保留 unmapped component，不硬塞 retriever。
3. 補 rule catalog 測試：
   - `chromadb/chroma` Docker image rule。
   - `chromadb.HttpClient` / `chromadb.AsyncHttpClient` / `chromadb.PersistentClient` code pattern rules。
4. 確認 RED：
   - 新 service 尚不存在時 unit/integration tests 失敗。
   - 新 catalog 規則未補時 provider tests 失敗。
5. 實作 `src/systograph/core/services/component_detection_service.py`：
   - `ComponentDetectionResult`。
   - `ManualMappingHook` placeholder interface。
   - deterministic component ids。
   - evidence id lookup。
   - strong evidence mapping。
   - weak evidence candidates 不升級 detected。
   - unmapped / extension candidate handling。
6. 更新 `src/systograph/core/rules/code_pattern_rules.toml` 與 `docker_image_rules.toml`。
7. 跑 Phase 13 tests 與 provider regression tests。
8. 跑 full verification。
9. 建立 Phase 13 Report，記錄實作邏輯、步驟、測試方式、問題與解法、測試結果。
10. 逐一對照 Task 13 plan，確認全部落地。

## 驗證命令

```bash
.venv/bin/python -m pytest tests/unit/core/test_component_detection_service.py
.venv/bin/python -m pytest tests/integration/test_phase13_component_detection_behaviors.py
.venv/bin/python -m pytest tests/unit/core/test_code_pattern_provider.py tests/unit/core/test_docker_compose_provider.py tests/unit/core/test_rule_catalog_loader.py
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 完成狀態

- [x] 建立 TODO 文件。
- [x] 先寫 Phase 13 unit tests 並確認 RED。
- [x] 先寫 Phase 13 integration tests 並確認 RED。
- [x] 補 Chroma provider rule catalog tests 並確認 RED。
- [x] 實作 `ComponentDetectionService`。
- [x] 補 Chroma code pattern / Docker image rules。
- [x] 確認 dependency-only 不得 detected。
- [x] 確認 Docker Qdrant detected。
- [x] 確認 custom router unmapped。
- [x] 確認 extensions / manual mapping hook placeholder。
- [x] 跑 full pytest、ruff、mypy。
- [x] 建立 Phase 13 Report。
- [x] 將完成的 plan 移到 `plan/finish`。
