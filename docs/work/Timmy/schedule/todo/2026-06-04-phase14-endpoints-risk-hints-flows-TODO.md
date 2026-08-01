# 2026-06-04 Phase 14 Endpoints / Risk Hints / Flows TODO

## 目標

實作 `EndpointDetectionService`、`RiskHintService` 與 `FlowDerivationService`，把 Task 12 的 raw facts / evidence 和 Task 13 的 confirmed components 轉成 `ai-system-map/v1` 可驗證的 endpoints、risk hints 與 indexing / query_answer flows。

## 實作邏輯

1. 使用 TDD + BDD：每個服務先寫失敗測試，確認 RED 後才補實作。
2. 保持 evidence-based：endpoint、risk hint、flow edge 都必須引用 valid evidence 或 valid component / slot，不自行捏造節點。
3. 保持 scanner read-only：不呼叫 endpoint、不查 Docker runtime、不 import / exec / eval 使用者程式。
4. 保持 Task 13 / Task 14 邊界：Task 13 只判斷 component / slot；Task 14 才推導 endpoint、risk 與 flow。
5. Risk rules 採 Python typed logic：Epic 1 不引入 external scanner engine，也不實作 TOML condition DSL。
6. Secret handling 只使用已 masking 的 evidence value；risk hint 與 endpoint 不輸出完整 secret。

## 步驟

1. 補 `tests/unit/core/test_endpoint_detection_service.py`：
   - Docker short syntax `6333:6333` 產生 Qdrant host-published endpoint。
   - Docker loopback binding `127.0.0.1:6333:6333` 產生 local-bound endpoint。
   - Docker service env reference `http://qdrant:6333` 只產生 internal endpoint，不產生 host-published exposure。
   - OpenAI config / provider evidence 產生 external endpoint。
   - Chroma `HttpClient(host=..., port=...)` 產生 endpoint；`PersistentClient(path=...)` 不產生 external endpoint。
2. 補 `tests/unit/core/test_risk_hint_service.py`：
   - published port 產生 `docker_published_port_exposure`。
   - loopback port 使用 lower-risk / local-bound wording。
   - internal endpoint 不產生 published-port risk。
   - OpenAI external endpoint 產生 `external_provider_detected` 且不洩漏 secret。
   - parse issue 產生 `config_parse_error`。
   - secret-like config key 產生 `secret_like_config_key_detected`。
   - missing required slot 產生 `missing_required_slot`。
   - Chroma HTTP / local persistence / server published port 產生 provider-specific hint。
3. 補 `tests/unit/core/test_flow_derivation_service.py`：
   - 根據 `rag-core-v1` template 產生 indexing / query_answer flows。
   - flow edges 只連 valid slots 與 detected component instances。
   - flow edge 引用 valid evidence ids。
4. 補整合測試：
   - sample RAG fixture 經 ProjectScanService -> ComponentDetectionService -> Task 14 services 後，endpoint / risk hint / flow 可通過 `SystemMapValidationService`。
5. 實作 `src/systograph/core/services/endpoint_detection_service.py`。
6. 實作 `src/systograph/core/services/risk_hint_service.py`。
7. 實作 `src/systograph/core/services/flow_derivation_service.py`。
8. 跑 targeted tests，確認新增服務通過。
9. 跑 full verification。
10. 建立 Phase 14 Report。
11. 逐一對照 Task 14 plan，確認全部落地。

## 驗證命令

```bash
.venv/bin/python -m pytest tests/unit/core/test_endpoint_detection_service.py
.venv/bin/python -m pytest tests/unit/core/test_risk_hint_service.py
.venv/bin/python -m pytest tests/unit/core/test_flow_derivation_service.py
.venv/bin/python -m pytest tests/integration/test_phase14_endpoints_risk_hints_flows_behaviors.py
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/mypy
```

## 完成狀態

- [x] 建立 TODO 文件。
- [x] 先寫 EndpointDetectionService tests 並確認 RED。
- [x] 實作 `EndpointDetectionService` 並確認 GREEN。
- [x] 先寫 RiskHintService tests 並確認 RED。
- [x] 實作 `RiskHintService` 並確認 GREEN。
- [x] 先寫 FlowDerivationService tests 並確認 RED。
- [x] 實作 `FlowDerivationService` 並確認 GREEN。
- [x] 補 Phase 14 integration behavior test。
- [x] 確認 `SystemMapValidationService` 可驗證 Task 14 產物。
- [x] 跑 full pytest、ruff、mypy。
- [x] 建立 Phase 14 Report。
- [x] 將完成的 plan 移到 `plan/finish`。
