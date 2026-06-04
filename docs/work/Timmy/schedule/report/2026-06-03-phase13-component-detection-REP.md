# 2026-06-03 Phase 13 Component Detection REP

## 實作邏輯

本階段建立 `ComponentDetectionService`，把 Task 12 的 raw facts 轉成 `rag-core-v1` component slots。資料流如下：

```text
ProjectScanResult
  -> ScanFact[] + Evidence[]
  -> ComponentDetectionService
  -> components_by_slot
  -> extensions
  -> unmapped_components
```

核心規則：

- `detected` slot 必須有 component instance。
- 每個 detected instance 必須有 `evidence_ids`。
- dependency-only 是 weak signal，不可單獨讓 slot 變成 `detected`。
- custom router / dependency-only 等不確定 evidence 要保留到 `unmapped_components`，不可硬塞進 standard slot。
- reranker 這類非 baseline RAG 元件先輸出 extension candidate。
- endpoint、risk hint、flow derivation 不在 Task 13 做，留給 Task 14。

## 實作步驟

1. 建立 `docs/work/Timmy/schedule/todo/2026-06-03-phase13-component-detection-TODO.md`。
2. 先寫 `tests/unit/core/test_component_detection_service.py`，鎖定：
   - all slots 初始化。
   - Docker Qdrant -> `vector_store` detected。
   - citation slot missing 時 instances 為空。
   - `chromadb` dependency-only 不得 detected。
   - Chroma `HttpClient` / `PersistentClient` code pattern 可 detected。
   - OpenAI embedding / LLM code pattern 可 detected。
   - custom router 進 `unmapped_components`，不硬塞 retriever。
   - reranker 進 extension candidate。
3. 先寫 `tests/integration/test_phase13_component_detection_behaviors.py`，用 fixtures 驗證：
   - `basic_qdrant_ollama_rag` 可 detected vector store / LLM / retriever / API。
   - `custom_router_rag` 保留 unmapped component。
   - `reranker_extension_rag` 產生 extension candidate。
4. 先補 provider rule RED tests：
   - `tests/unit/core/test_code_pattern_provider.py::test_collect_emits_chromadb_client_mode_facts`
   - `tests/unit/core/test_docker_compose_provider.py::test_collect_recognizes_chromadb_chroma_image`
5. RED 階段確認：
   - `ComponentDetectionService` 尚不存在，unit / integration tests 失敗於 `ModuleNotFoundError`。
   - Chroma code pattern / Docker image rule 尚未加入，provider tests 失敗於 missing rule id。
6. 建立 `src/kai_mind/core/services/component_detection_service.py`：
   - `ComponentDetectionResult`
   - `ManualMappingHook` placeholder
   - deterministic component ids
   - evidence lookup
   - slot status fill
   - strong evidence mapping
   - weak dependency / router unmapped handling
   - reranker extension candidate handling
7. 補 `src/kai_mind/core/rules/code_pattern_rules.toml`：
   - `code_pattern_vector_store_chroma_http`
   - `code_pattern_vector_store_chroma_async_http`
   - `code_pattern_vector_store_chroma_persistent`
8. 補 `src/kai_mind/core/rules/docker_image_rules.toml`：
   - `docker_chromadb_chroma_image_detected`
9. 修正 ruff 行長與 mypy literal / helper return type 問題。
10. 將 Task 13 plan 從 `plan/unfinish` 移到 `plan/finish`。

## 測試方式

RED 階段：

```bash
.venv/bin/python -m pytest tests/unit/core/test_component_detection_service.py
.venv/bin/python -m pytest tests/integration/test_phase13_component_detection_behaviors.py
.venv/bin/python -m pytest tests/unit/core/test_code_pattern_provider.py::test_collect_emits_chromadb_client_mode_facts tests/unit/core/test_docker_compose_provider.py::test_collect_recognizes_chromadb_chroma_image
```

GREEN 後針對 Phase 13：

```bash
.venv/bin/python -m pytest tests/unit/core/test_component_detection_service.py
.venv/bin/python -m pytest tests/integration/test_phase13_component_detection_behaviors.py
.venv/bin/python -m pytest tests/unit/core/test_code_pattern_provider.py::test_collect_emits_chromadb_client_mode_facts tests/unit/core/test_docker_compose_provider.py::test_collect_recognizes_chromadb_chroma_image
```

Provider / service regression：

```bash
.venv/bin/python -m pytest tests/unit/core/test_component_detection_service.py tests/integration/test_phase13_component_detection_behaviors.py tests/unit/core/test_code_pattern_provider.py tests/unit/core/test_docker_compose_provider.py tests/unit/core/test_rule_catalog_loader.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 遇到的問題與解法

### 1. Sandbox 無法提供 pytest temporary directory

第一次跑 RED tests 時，pytest 在 sandbox 內失敗：

```text
FileNotFoundError: No usable temporary directory found
```

這是執行環境限制，不是 repo regression。

解法：用正常 filesystem 權限重跑相同 pytest 指令，取得真正 RED failure。

### 2. Chroma rules 缺口被測試確認

新增 provider tests 後，`CodePatternProvider` 找不到：

```text
code_pattern_vector_store_chroma_http
```

`DockerComposeProvider` 也把 `chromadb/chroma` 當成 generic image：

```text
docker_service_image_detected
```

解法：在 TOML rule catalogs 補上 Chroma client mode 與 Docker image rule。Provider 程式碼不用改。

### 3. mypy 對 `ComponentSlot.status` 要求 Literal

初版用一般 `str` 設定 status，mypy 無法確認符合 `SlotStatus`。

解法：把 status constants 標成 `Final`，並在 `_build_slots()` 中宣告 `status: SlotStatus`。

## 測試結果

```text
.venv/bin/python -m pytest
183 passed in 1.91s

.venv/bin/ruff check .
All checks passed!

.venv/bin/mypy
Success: no issues found in 55 source files
```

## 驗收對照

- 建立 `ComponentDetectionService`：已完成。
- 定義 rule input：template + facts + evidence：已完成，`detect(template, facts, evidence)`。
- Docker Qdrant -> `vector_store`：已完成。
- Ollama -> `llm`：已完成，Docker Ollama image 可 detected。
- OpenAI SDK/config -> `llm` / `embedding_model`：已完成，OpenAI code pattern 與 OpenAI config 可 detected。
- Chroma code pattern / Docker image 補強：已完成。
- all slots status：已完成，detected / missing / not_applicable 會依 evidence 與 required hint 填入。
- 無 evidence 不可 detected：已完成，空 facts 時 required slots 是 `missing`，optional slots 是 `not_applicable`。
- dependency-only 不可 detected：已完成，`chromadb` dependency-only 進 `unmapped_components`。
- custom router 不硬塞 retriever：已完成。
- reranker extension candidate：已完成。
- manual mapping extension hook 先留 interface，Task 19 再實作：已完成，`ManualMappingHook` placeholder。
- JSON 不含 `confidence`：已遵守，service 未新增任何 confidence 欄位。
- 每個 detected instance 都有 evidence_ids：已完成，unit tests 覆蓋。
- Full verification 通過：已完成。
