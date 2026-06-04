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
- `tests/unit/core/test_endpoint_detection_service.py`
- `tests/unit/core/test_risk_hint_service.py`
- `tests/unit/core/test_flow_derivation_service.py`

## 驗收標準
- `6333:6333` 產生 Qdrant endpoint 與 network exposure risk hint。
- OpenAI provider 產生 external endpoint/risk hint，secret masked。
- 每個 risk hint 都引用 valid evidence。
- flow edges 只引用 valid slots 或 confirmed extension。

## 可能風險與注意事項
- network exposure 只能是 hint，要寫 uncertainty。
- 不要自行升級 severity 成 final verdict。
- 參考依據：Docker Compose services docs 的 `ports`/`environment`；OpenInference/OpenTelemetry GenAI docs 可作 replay/step vocabulary 與 sensitive IO 注意事項。

## Chroma endpoint 與 local persistence 補強

這段補強屬於 Task 14，不放在 Task 13。Task 13 只負責判斷 `vector_store` 是否可由 evidence 映射成 detected component；Task 14 才負責把 Chroma HTTP/server config 轉成 endpoint，或把 local persistence 轉成 release-readiness risk hint。

來源：
- https://docs.trychroma.com/reference/python/client
- https://docs.trychroma.com/docs/run-chroma/clients
- https://docs.trychroma.com/reference/server-env-vars
- https://cookbook.chromadb.dev/core/storage-layout/

Task 14 應處理：
- `chromadb.HttpClient(host=..., port=...)` / `chromadb.AsyncHttpClient(...)` 的 code evidence 若包含可安全解析的 literal host/port，可推導 Chroma external/local endpoint。
- `.env` / config 出現 `CHROMA_HOST`、`CHROMA_ENDPOINT`、`CHROMA_API_KEY`、`CHROMA_TENANT`、`CHROMA_DATABASE`，且 Task 13 已確認 Chroma component 時，可推導 external provider / cloud vector store endpoint hint；secret-like values 只能使用 masked evidence。
- Docker / server config 出現 `CHROMA_PORT`、`CHROMA_LISTEN_ADDRESS`、`CHROMA_PERSIST_PATH`，只有在 Docker image 或 Chroma server context 明確時，才推導 server endpoint 或 persistence hint。
- `chromadb.PersistentClient(path=...)` 或 Chroma storage path evidence 可產生 local persistence risk hint，但 wording 必須保守：這是「local vector store data exists / may require privacy, backup, and cleanup review」，不是直接宣告不安全。

不應處理：
- 不呼叫 `heartbeat()`。
- 不送 HTTP request 驗證 Chroma server 是否在線。
- 不查 `docker ps`。
- 不因為看到 `CHROMA_*` 單一 key 就產生 final risk verdict。

建議 risk hint：

| Rule id | 觸發條件 | Target | Rationale | Uncertainty |
|---|---|---|---|---|
| `chroma_http_endpoint_detected` | Task 13 已確認 Chroma component，且有 HTTP host/port/endpoint evidence | endpoint 或 component_instance | Chroma vector store appears to be accessed over HTTP/server mode | Static scan does not verify runtime reachability |
| `chroma_local_persistence_detected` | `PersistentClient(path=...)` 或明確 local Chroma persist path | component_instance 或 file | Local Chroma persistence may store embeddings, metadata, or documents on disk | Static scan does not inspect stored data contents |
| `chroma_server_published_port` | Docker Chroma service published port | component_instance / endpoint | Published Chroma port may expose vector store service beyond localhost | Compose port binding does not prove firewall or runtime exposure |

測試補強：
- `HttpClient(host="localhost", port=8000)` 產生 endpoint，並引用 valid evidence。
- `PersistentClient(path="./chroma")` 產生 local persistence risk hint，且不產生 external endpoint。
- Docker `chromadb/chroma` + `ports: ["8000:8000"]` 產生 endpoint / network exposure hint。
- `CHROMA_API_KEY` 或 cloud env evidence 不得輸出完整 secret value。

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
