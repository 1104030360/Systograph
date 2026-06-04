# 2026-06-04 Phase 14 Endpoints / Risk Hints / Flows REP

## 實作邏輯

本階段建立三個 Task 14 services，把 Task 12 raw scan 與 Task 13 component detection 結果轉成 canonical `ai-system-map/v1` 可驗證的 endpoints、risk hints 與 flows。

資料流如下：

```text
ProjectScanResult
  -> ScanFact[] + Evidence[] + ParseIssue[]
  -> ComponentDetectionService
  -> EndpointDetectionService
  -> RiskHintService
  -> FlowDerivationService
  -> SystemMapValidationService
```

核心原則：

- Endpoint / RiskHint / Flow 都必須引用 valid evidence、component 或 slot。
- Docker `ports` 只代表 host-published endpoint hint，不代表 runtime 可連或 public exposure。
- Compose service-name URL 只視為 container-network internal endpoint，不產生 host-published exposure risk。
- OpenAI/provider endpoint 不輸出 secret value。
- Python endpoint literal extraction 僅解析 bounded evidence snippet，不 import / exec / eval 使用者程式。
- Flow 只連兩端都有 detected component 的相鄰 template slots，避免 dangling edge。
- 目前 repo 尚無 canonical map builder 服務；本階段先落地獨立 services 與 integration validated map，不硬改 `ProjectScanService` 的 raw-scan 邊界。

## 實作步驟

1. 建立 `docs/work/Timmy/schedule/todo/2026-06-04-phase14-endpoints-risk-hints-flows-TODO.md`。
2. 先寫 `tests/unit/core/test_endpoint_detection_service.py`，確認 RED 後建立 `EndpointDetectionService`：
   - Docker `6333:6333` -> Qdrant local endpoint。
   - Docker `127.0.0.1:6333:6333` -> loopback endpoint。
   - Compose env `http://qdrant:6333` -> internal endpoint。
   - OpenAI API key / base URL config -> external endpoint，不含 secret。
   - Chroma `HttpClient(host=..., port=...)` -> HTTP endpoint。
   - Chroma `PersistentClient(path=...)` 不產生 external endpoint。
3. 先寫 `tests/unit/core/test_risk_hint_service.py`，確認 RED 後建立 `RiskHintService`：
   - `docker_published_port_exposure`
   - `external_provider_detected`
   - `config_parse_error`
   - `secret_like_config_key_detected`
   - `missing_required_slot`
   - `chroma_http_endpoint_detected`
   - `chroma_local_persistence_detected`
   - `chroma_server_published_port`
4. 先寫 `tests/unit/core/test_flow_derivation_service.py`，確認 RED 後建立 `FlowDerivationService`：
   - 依 `rag-core-v1` template 產生 `flow:indexing` 與 `flow:query_answer`。
   - 只連 detected adjacent slots。
   - edge 帶兩端 component refs 與合併後 evidence ids。
5. 補 `tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py`：
   - `basic_qdrant_ollama_rag` 可產生 Qdrant endpoint、published port risk、query flow edge，且可通過 `SystemMapValidationService`。
   - `openai_external_provider_rag` 可產生 external endpoint / risk hint，且 endpoint 不洩漏 `sk-`。
6. 修正 ruff 長行、forward annotation 與 unused import。
7. 修正 mypy 型別問題：
   - `urlparse` return type 改為 `ParseResult`。
   - test helper 補 `list[Endpoint]`、`list[RiskHint]`、`list[Flow]` return type。

## 測試方式

RED 階段：

```bash
.venv/bin/python -m pytest tests/unit/core/test_endpoint_detection_service.py
.venv/bin/python -m pytest tests/unit/core/test_risk_hint_service.py
.venv/bin/python -m pytest tests/unit/core/test_flow_derivation_service.py
```

Targeted GREEN：

```bash
.venv/bin/python -m pytest tests/unit/core/test_endpoint_detection_service.py tests/unit/core/test_risk_hint_service.py tests/unit/core/test_flow_derivation_service.py tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py
```

Full verification：

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 遇到的問題與解法

### 1. ruff 長行與 annotation cleanup

新增服務與測試初版通過 pytest，但 ruff 找到 line length、forward annotation quotes 與 unused import。

解法：用 `ruff check . --fix` 處理可自動修正項，再手動拆長行。未改行為。

### 2. mypy 不接受 `urlparse` 當 type

初版 `_first_url()` 寫成 `urlparse | None`，mypy 判定 `urlparse` 是 function 不是 type。

解法：改用 `urllib.parse.ParseResult`。

### 3. Map builder 邊界

repo 目前沒有負責組裝完整 `RagSystemMap` 的 production builder；`ProjectScanService` 的測試也明確要求它只輸出 raw scan，不含 `components_by_slot`。

解法：維持現有分層，不把 Task 14 硬塞進 `ProjectScanService`。用 integration test 組出 canonical map dict 並通過 `SystemMapValidationService`，證明三個 services 產物可接到後續 builder。

## 測試結果

```text
.venv/bin/python -m pytest
213 passed in 1.58s

.venv/bin/ruff check .
All checks passed!

.venv/bin/mypy
Success: no issues found in 62 source files
```

## 驗收對照

- 建立 `EndpointDetectionService`：已完成。
- 建立 `RiskHintService`：已完成。
- 建立 `FlowDerivationService`：已完成。
- Docker published ports 推導 local endpoints：已完成，short syntax / loopback / long syntax parser 有覆蓋。
- Compose service-name internal endpoint：已完成，不產生 host-published risk。
- OpenAI/provider config 推導 external endpoints：已完成，secret 不進 endpoint。
- `docker_published_port_exposure`：已完成。
- `external_provider_detected`：已完成。
- `config_parse_error`：已完成。
- `secret_like_config_key_detected`：已完成。
- `missing_required_slot`：已完成。
- Chroma HTTP endpoint / local persistence / server published port hints：已完成。
- 建立 indexing / query_answer flow edges：已完成。
- 每個 risk hint 都引用 valid evidence：已完成，unit + integration validation 覆蓋。
- flow edges 只引用 valid slots / components：已完成，unit + integration validation 覆蓋。
- 不呼叫 endpoint、不做 runtime health check、不查 Docker runtime：已遵守。
- Full verification 通過：已完成。
