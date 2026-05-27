# Task 14: Derive Endpoints, Risk Hints, and Flows

## 目標
實作 `EndpointDetectionService`、`RiskHintService` 與初始 flow derivation。這個任務把 components/facts 轉成 local/external endpoints、network exposure hints、indexing/query_answer flows。

## 為什麼要先做這個
System map 不只是元件清單，還要能讓使用者看到元件關係與 release-readiness 初步風險。這些資料也支援後續 viewer graph 與 query trace。

## 前置需求
- Task 12 已有 raw facts/evidence。
- Task 13 已有 components/slots/unmapped。
- Task 3 已有 flow slot order。

## 實作範圍
- 從 Docker published ports 推導 local endpoints。
- 從 OpenAI/provider config 推導 external endpoints。
- 初始 risk rules：`docker_published_port_exposure`、`external_provider_detected`、`config_parse_error`、`secret_like_config_key_detected`、`missing_required_slot`。
- 建立 indexing/query_answer flow edges。
- risk hint 必須含 evidence_id、rule_id、rationale、uncertainty。

## 不包含範圍
- 不做完整 security scan。
- 不決定 final READY/RISKY/NOT_READY。
- 不呼叫 endpoint。
- 不做 runtime health check。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/endpoint_detection_service.py`。
2. 建立 `src/kai_mind/core/services/risk_hint_service.py`。
3. 建立 `src/kai_mind/core/services/flow_derivation_service.py` 或放在 normalize 前的獨立 helper。
4. 實作 Docker port -> endpoint。
5. 實作 external provider -> endpoint/risk hint。
6. 實作 parse issue -> risk hint。
7. 寫測試：Qdrant port risk、OpenAI external endpoint、malformed compose parse risk。

## 預期輸出
- `src/kai_mind/core/services/endpoint_detection_service.py`
- `src/kai_mind/core/services/risk_hint_service.py`
- `src/kai_mind/core/services/flow_derivation_service.py`
- `tests/core/test_endpoint_detection_service.py`
- `tests/core/test_risk_hint_service.py`
- `tests/core/test_flow_derivation_service.py`

## 驗收標準
- `6333:6333` 產生 Qdrant endpoint 與 network exposure risk hint。
- OpenAI provider 產生 external endpoint/risk hint，secret masked。
- 每個 risk hint 都引用 valid evidence。
- flow edges 只引用 valid slots 或 confirmed extension。

## 可能風險與注意事項
- network exposure 只能是 hint，要寫 uncertainty。
- 不要自行升級 severity 成 final verdict。
- 參考依據：Docker Compose services docs 的 `ports`/`environment`；OpenInference/OpenTelemetry GenAI docs 可作 replay/step vocabulary 與 sensitive IO 注意事項。

## 新手提示
Risk hint 是「提醒你可能有風險」，不是正式安全掃描結論。Epic 1 只提供 evidence-based hint。

## 視覺化說明
```text
┌──────────────────────┐
│ Components + facts    │
└──────┬────────┬──────┘
       │        │
       ↓        ↓
┌──────────────┐ ┌──────────────┐
│ Endpoint     │ │ RiskHint     │
│ Detection    │ │ Service      │
└──────┬───────┘ └──────┬───────┘
       ↓                ↓
┌──────────────┐ ┌──────────────┐
│ endpoints    │ │ risk_hints   │
└──────────────┘ └──────────────┘
       │
       ↓
┌──────────────┐
│ Flow         │
│ Derivation   │
└──────┬───────┘
       ↓
┌──────────────┐
│ flows/edges  │
└──────────────┘
```
