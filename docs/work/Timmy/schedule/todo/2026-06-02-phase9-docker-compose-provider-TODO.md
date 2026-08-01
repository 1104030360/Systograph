# 2026-06-02 Phase9 Docker Compose Provider TODO

## 階段目標

依照
`docs/work/Timmy/schedule/plan/unfinish/09-implement-docker-compose-provider.md`
實作 `DockerComposeProvider`，讓 scanner 可以從 `FileInventory` 中唯讀解析
Docker Compose 檔案，產生 service image、published port、environment、
env_file、volume、depends_on facts 與 evidence。

本階段只做 deterministic static parsing：

- 不啟動 Docker。
- 不執行 `docker compose`。
- 不做完整 network security scan。
- 不判斷 final component slot。
- 不讓 raw secret 進入 facts、evidence、issues、logs 或 test snapshots。

## 實作邏輯

1. 延續 Task 7 的 inventory-first 邊界：
   `DockerComposeProvider` 只處理 `FileInventory.files` 中已納入的 compose
   files，不自行遞迴搜尋 project root。
2. 延續 Task 8 的 provider-local output pattern：
   回傳 `ProviderScanResult`，包含 `ScanFact[]`、`Evidence[]`、
   `ParseIssue[]`。
3. YAML parser 使用既有 PyYAML `safe_load()`，禁止 unsafe loader。
4. 每個 compose file 獨立 parse，壞檔只產生該檔案的 parse issue，不中止整體
   scan。
5. service-level fields normalize 成穩定 facts：
   - `services.<name>.image`
   - `services.<name>.ports[i]`
   - `services.<name>.environment.<KEY>`
   - `services.<name>.env_file[i]`
   - `services.<name>.volumes[i]`
   - `services.<name>.depends_on[i]`
6. `environment` values 全部走 `SecretMaskingService`。
7. published port 只輸出 evidence，不直接產生 final endpoint 或 risk hint；後續
   Task 14 再處理 exposure uncertainty。

## TDD / BDD 步驟

### 1. RED：先寫 unit tests

- 測 `docker-compose.yml` / `compose.yaml` 會被選中。
- 測 Qdrant / Ollama image facts。
- 測 short syntax port，例如 `"6333:6333"`。
- 測 long syntax port，例如 `{target: 5432, published: "5432"}`。
- 測 `environment` dict / list form secret masking。
- 測 `env_file` 只記 reference。
- 測 `depends_on` list / map form normalize。
- 測 malformed compose 不 crash，且另一個 compose file 仍可產生 facts。

### 2. GREEN：實作最小 provider

- 新增 `src/systograph/core/providers/docker_compose_provider.py`。
- 若 `ParseIssue.scan_stage` 仍只接受 `config_parse`，擴充為
  `docker_compose_parse`。
- 實作 candidate compose path 判斷。
- 實作 safe YAML parse、fact/evidence builder、parse issue builder。
- 實作 service fields normalize。

### 3. BDD-style integration tests

- 使用 `basic_qdrant_ollama_rag` fixture 驗證 Qdrant/Ollama compose facts。
- 使用 `malformed_config_rag` fixture 驗證 malformed compose 產生 parse issue。
- 確認 provider 不讀 non-compose config。

### 4. Verification

Targeted verification：

```bash
.venv/bin/python -m pytest tests/unit/core/test_docker_compose_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py
.venv/bin/ruff check src/systograph/core/models/scan.py src/systograph/core/providers/docker_compose_provider.py tests/unit/core/test_docker_compose_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py
.venv/bin/mypy src/systograph/core/models/scan.py src/systograph/core/providers/docker_compose_provider.py tests/unit/core/test_docker_compose_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 驗收清單

- [x] `DockerComposeProvider` 只吃 `FileInventory`。
- [x] Qdrant service image 產生 `docker_service` evidence。
- [x] Ollama service image 產生 `docker_service` evidence。
- [x] Published port 產生 `published_port` evidence。
- [x] `ports` string/object form 都可處理。
- [x] `environment` map/list form 都可處理，且 secret-like value 已遮罩。
- [x] `env_file` reference 有 fact/evidence，且不擴張掃描邊界。
- [x] `volumes` 有 service-level fact/evidence。
- [x] `depends_on` list/map form 都 normalize 成 dependency service names。
- [x] Malformed compose 不 crash，產生 parse issue。
- [x] Parse issue 使用 `docker_compose_parse` scan stage。
- [x] 不執行 Docker / docker compose。
- [x] 所有 targeted verification 通過。
- [x] 所有 full verification 通過。
