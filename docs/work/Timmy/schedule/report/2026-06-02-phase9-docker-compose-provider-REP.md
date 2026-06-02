# 2026-06-02 Phase9 Docker Compose Provider Report

## 實作摘要

本階段依照
`docs/work/Timmy/schedule/plan/unfinish/09-implement-docker-compose-provider.md`
完成 `DockerComposeProvider`，讓 scanner 可以從 `FileInventory` 中唯讀解析
Docker Compose 檔案，產生 service image、published port、environment、
env_file、volume、depends_on facts 與 evidence。

本次新增與修改：

- `src/kai_mind/core/providers/docker_compose_provider.py`
- `src/kai_mind/core/models/scan.py`
- `tests/unit/core/test_docker_compose_provider.py`
- `tests/integration/test_phase9_docker_compose_provider_behaviors.py`
- `docs/work/Timmy/schedule/todo/2026-06-02-phase9-docker-compose-provider-TODO.md`

核心成果：

- 建立 `DockerComposeProvider.collect(inventory)`。
- 支援 `docker-compose.yml`、`docker-compose.yaml`、`compose.yml`、
  `compose.yaml`。
- YAML parser 使用既有 PyYAML `safe_load()`。
- 每個 compose file 獨立 parse，壞檔不會中止整體 scan。
- `ParseIssue.scan_stage` 擴充支援 `docker_compose_parse`。
- Qdrant / Ollama / pgvector images 會產生明確 rule id。
- `ports` short syntax 與 long syntax 都會產生 `published_port`
  facts/evidence。
- `environment` map/list form 都會 normalize，secret-like values 會先遮罩。
- `env_file` 只記錄 service-level reference，不讀取 inventory 外檔案。
- `volumes` 與 `depends_on` 會產生 service-level facts/evidence。
- provider 不啟動 Docker、不執行 `docker compose`。

## 實作邏輯

這次維持 inventory-first 與 provider-local result 的既有架構。

1. `DockerComposeProvider` 只接收 `FileInventory`，不自行遞迴搜尋 project
   root。
2. candidate compose files 只依檔名判斷：
   `docker-compose.yml`、`docker-compose.yaml`、`compose.yml`、
   `compose.yaml`。
3. 每個檔案用 `yaml.safe_load()` 讀取；parse failure 或 root/services shape
   不符合預期時，轉成 `ParseIssue` 與 `parse_error` evidence。
4. 每個 service 依欄位拆成穩定 path：
   - `services.<service>.image`
   - `services.<service>.ports[i]`
   - `services.<service>.environment.<KEY>`
   - `services.<service>.env_file[i]`
   - `services.<service>.volumes[i]`
   - `services.<service>.depends_on[i]`
5. facts 與 evidence 使用相同 kind/rule_id，保留後續 Task 13/14
   component detection、endpoint detection、risk hint 可以追溯來源。
6. `environment` values 全部經過 `SecretMaskingService.mask_value(...)` 與
   `mask_text(...)`，避免 raw secret 進入輸出。
7. published port 在本階段只是 static evidence；不判斷是否真的公開暴露，
   後續 Task 14 再產生 endpoint/risk uncertainty。

## 實作步驟

### 1. 先補 TODO

新增：

- `docs/work/Timmy/schedule/todo/2026-06-02-phase9-docker-compose-provider-TODO.md`

內容包含：

- 階段目標
- 實作邏輯
- TDD / BDD 步驟
- Targeted / full verification commands
- 驗收清單

### 2. RED：先寫 failing tests

新增 unit tests：

- `tests/unit/core/test_docker_compose_provider.py`

覆蓋行為：

- 只讀 inventory 中的 compose files，不讀一般 `config.yaml`。
- Qdrant / Ollama image 產生 `docker_service` evidence 與明確 rule id。
- short syntax port `"6333:6333"` 產生 `published_port` evidence。
- long syntax port `{target, published, host_ip, protocol}` 會 normalize。
- `environment` map/list form secret values 會遮罩。
- `env_file` reference、volumes、depends_on map form 會產生 facts。
- malformed compose 不影響另一個 compose file 的 facts。

新增 BDD-style integration tests：

- `tests/integration/test_phase9_docker_compose_provider_behaviors.py`

覆蓋情境：

- `basic_qdrant_ollama_rag` fixture 產生 Qdrant / Ollama / port facts。
- `malformed_config_rag` fixture 產生 `docker_compose_parse` issue。
- `openai_external_provider_rag` 沒有 compose file 時回傳空結果。

RED 驗證結果：

```bash
.venv/bin/python -m pytest tests/unit/core/test_docker_compose_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py
```

在正常 temp/cache 權限下，測試因
`ModuleNotFoundError: No module named 'kai_mind.core.providers.docker_compose_provider'`
失敗，確認測試先抓到尚未實作的 Task 9 缺口。

### 3. GREEN：實作 provider 與 scan stage

修改：

- `src/kai_mind/core/models/scan.py`

調整：

- `ParseIssue.scan_stage` 從只接受 `config_parse`，擴充為接受
  `docker_compose_parse`。

新增：

- `src/kai_mind/core/providers/docker_compose_provider.py`

主要行為：

- `collect(inventory)` 篩選 compose file names。
- 每個 file 獨立 parse。
- image / ports / environment / env_file / volumes / depends_on 分別轉成
  `ScanFact` + `Evidence`。
- parse error 只產生 `ParseIssue` + evidence，不塞進 `ScanFact`，維持
  Task 8 pattern。

## 遇到的問題與解法

### 1. Read-only sandbox 讓 pytest 無法使用 temp/cache

第一次跑 pytest 時遇到：

```text
No usable temporary directory found
```

這是 sandbox temp/cache 權限問題，不是程式碼錯誤。

解法：

- 使用正常 temp/cache 權限重跑 pytest / ruff / mypy。

### 2. Parse error 一開始被放進 `ScanFact`

第一輪 targeted pytest 有 1 個失敗：

```text
result.facts == []
```

實作一開始把 parse error 同時放進 fact/evidence，但 Task 8 pattern 是
`ParseIssue` + `parse_error` evidence，不應混入 raw facts。

解法：

- 調整 `_append_parse_error(...)`，只加入 `ParseIssue` 與 `Evidence`。
- 重跑 targeted pytest 後通過。

### 3. Ruff line length

Targeted ruff 抓到 3 個超過 79 字元的行。

解法：

- 只調整換行，不改行為。

## 測試方式

Targeted verification：

```bash
.venv/bin/python -m pytest tests/unit/core/test_docker_compose_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py
.venv/bin/ruff check src/kai_mind/core/models/scan.py src/kai_mind/core/providers/docker_compose_provider.py tests/unit/core/test_docker_compose_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py
.venv/bin/mypy src/kai_mind/core/models/scan.py src/kai_mind/core/providers/docker_compose_provider.py tests/unit/core/test_docker_compose_provider.py tests/integration/test_phase9_docker_compose_provider_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 測試結果

Targeted verification：

```text
9 passed in 0.34s
All checks passed!
Success: no issues found in 4 source files
```

Full verification：

```text
129 passed in 3.16s
All checks passed!
Success: no issues found in 40 source files
```

## Plan 驗收對照

- 尋找 `docker-compose.yml`、`docker-compose.yaml`、`compose.yml`、
  `compose.yaml`：已完成。
- parse `services.*.image`：已完成。
- parse `ports`：已完成，支援 string short form 與 object long form。
- parse `environment`：已完成，支援 map 與 list form。
- parse `env_file`：已完成，僅記錄 reference，不擴張掃描邊界。
- parse `volumes`：已完成，支援 string 與 object form reference。
- parse `depends_on`：已完成，支援 list short form 與 map long form。
- 產生 Docker facts 與 evidence：已完成。
- malformed compose 產生 parse issue，不中止 scan：已完成。
- 對 env values 使用 masking：已完成。
- 不啟動 Docker：已遵守。
- 不執行 `docker compose`：已遵守。
- 不做完整 network security scan：已遵守。
- 不判斷 final component slot：已遵守。
