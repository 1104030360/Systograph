# Task 9: Implement Docker Compose Provider

## 目標
實作 `DockerComposeProvider`，從 Docker Compose 檔案解析 services、images、ports、environment、volumes、depends_on。這些 facts 會支援 vector store、local LLM runtime、endpoint 與 network exposure hint。

## 為什麼要先做這個
Docker Compose 是 local RAG 系統中最穩定的 infrastructure evidence。Qdrant、Ollama、Redis、Postgres、published port 等訊號可以直接支撐 component detection 與 risk hints。

## 前置需求
- Task 5 已完成 secret masking。
- Task 7 已完成 file inventory。
- Task 8 已建立 parse issue pattern。

## 實作範圍
- 尋找 `docker-compose.yml`、`docker-compose.yaml`、`compose.yml`、`compose.yaml`。
- parse `services.*.image`、`ports`、`environment`、`env_file`、`volumes`、`depends_on`。
- 產生 Docker facts 與 evidence。
- malformed compose 產生 parse issue，不中止 scan。
- 對 env values 使用 masking。

## 不包含範圍
- 不啟動 Docker。
- 不執行 `docker compose`。
- 不做完整 network security scan。
- 不判斷 final component slot。

## 建議實作步驟
1. 建立 `src/systograph/core/providers/docker_compose_provider.py`。
2. 從 `FileInventory` 選出 compose files。
3. 使用 safe YAML parser 讀檔。
4. 將每個 service 轉成 `ScanFact` candidate。
5. 對 `qdrant/qdrant`、`ollama/ollama`、published ports 產生明確 rule ids。
6. 若 `ParseIssue.scan_stage` 仍只接受 `config_parse`，先擴充為可表達 `docker_compose_parse`，避免 Docker parse error 被錯誤歸類成 config parse。
7. parse error 轉為 `ParseIssue` 與 evidence。
8. 測試 Qdrant image、Ollama image、`6333:6333` port、malformed compose。

## 預期輸出
- `src/systograph/core/providers/docker_compose_provider.py`
- `tests/unit/core/test_docker_compose_provider.py`

## 驗收標準
- Qdrant service image 產生 `docker_service` evidence。
- Published port 產生 `published_port` evidence。
- Malformed compose 不 crash，產生 parse issue。
- Environment secret-like value 已遮罩。

## 可能風險與注意事項
- Compose spec 很大，Epic 1 只需要 high-signal fields。
- `ports` 可能是 string 或 object form，兩者都要處理。
- `environment` 可能是 map 或 list form，兩者都要 normalize；只有 key/value facts 可輸出，value 必須先經過 `SecretMaskingService`。
- `env_file` 先當成 service-level reference fact；若要讀 env file 內容，只能讀 `FileInventory` 已納入且仍在 project root 內的 eligible file，不可因 compose path 重新擴張掃描邊界。
- `depends_on` 可能是 list short form 或 map long form；第一版只需要 normalize 出 dependency service names，不解讀健康檢查語意。
- published port 只是 network exposure hint，不等於已證明公開暴露；後續 Task 14 才推導 endpoint/risk，並且要保留不確定性。
- 參考依據：Docker Compose services 官方文件確認 `image`、`ports`、`environment`、`env_file`、`depends_on` 是 service-level fields。

## Refined 開源參考與落地結論

你原本的方向大致正確：Task 9 應該做「唯讀、deterministic、容錯」的 Docker Compose static parser，而不是呼叫 Docker 或把 Compose 完整語意重做一遍。不過參考專案要收斂成設計原則，避免把外部工具的完整 scanner 能力搬進 Epic 1。

### 1. Checkov：可參考 static IaC scanner 思維，不作為 runtime dependency
- 可參考點：Checkov 屬於 IaC / static-analysis scanner，適合拿來對齊「讀檔分析、輸出 rule-based findings、遇到壞檔不拖垮整體掃描」的思路。
- 套用方式：`DockerComposeProvider` 每個 compose file 獨立 parse；`yaml.YAMLError` 或 root shape 不符合預期時，轉成 `ParseIssue` + `parse_error` evidence，繼續處理其他檔案。
- 不套用：不安裝或呼叫 Checkov，也不要把 Checkov 的完整 policy engine、graph engine、secret scanner 帶進本 task。

### 2. Trivy / gitleaks：已在 Task 5 轉成 shared masking path
- 可參考點：安全掃描工具的共同重點是「可以偵測 sensitive signal，但輸出不可洩漏 raw secret」。
- 本 repo 對應：Task 5 已完成 `SecretMaskingService`，Task 9 只需要重用 `mask_value()` / `mask_text()`，不要在 provider 內自建第二套 masking 規則。
- `services.*.environment` 的 dict form 與 list form 都要先 normalize 成 key/value，再用 key 輔助 masking，例如 `OPENAI_API_KEY`、`PASSWORD`、`TOKEN`。

### 3. Docker Compose spec：只支援 high-signal subset
- Compose 官方 spec 確認 `environment` 可用 map 或 array，`ports` 有 short syntax 與 long syntax，`env_file` 可為字串、list 或帶 `path` 的 object，`depends_on` 有 short list 與 long map。
- Task 9 第一版只需要 normalize：
  - service image：`services.<name>.image`
  - published ports：string short form 與 object long form
  - environment：map 與 `KEY=VALUE` list；無值的 key 只記錄 key，不猜測 runtime value
  - env_file：記錄 reference path；讀內容必須受 `FileInventory` 邊界限制
  - volumes：記錄 service-level mount reference，不做 host filesystem security scan
  - depends_on：記錄 dependency service names，不判斷 startup readiness

### 4. Understand-Anything：只借 deterministic extraction pattern
- 可參考點：先用 deterministic extractor 產生 structure facts，再讓後續 mapping/normalization 判斷 graph。
- 套用方式：`DockerComposeProvider` 只輸出可追溯 facts/evidence，不直接決定 final component slot。`qdrant/qdrant`、`ollama/ollama`、`pgvector/pgvector` 這類 image 可以給明確 rule_id，留給 Task 13 做 component detection。

## 設計結論

`DockerComposeProvider` 應延續 Task 7 / Task 8 的 provider pattern：
- Input 只吃 `FileInventory`，不自行遞迴掃描。
- YAML 使用既有 PyYAML `safe_load()`，不使用 unsafe loader。
- Output 使用 `ProviderScanResult`，包含 `ScanFact[]`、`Evidence[]`、`ParseIssue[]`。
- Evidence path 一律是 project-relative POSIX path，例如 `services.qdrant.ports[0]`。
- 所有 env value、parse error message、evidence value 都不可包含完整 secret。
- 不啟動 Docker、不執行 `docker compose config`，因此不做 Compose interpolation / merge / profile evaluation。
- 對 unsupported 或 ambiguous Compose feature 保留原始 masked reference 與 uncertainty，不猜測 runtime final state。

## 建議補充測試

- `docker-compose.yml` 與 `compose.yaml` 都會被選中；一般 `config.yaml` 仍由 `ConfigParseProvider` 處理。
- `ports: ["6333:6333", "127.0.0.1:11434:11434", {"target": 5432, "published": "5432"}]` 都能產生 normalized published port facts。
- `environment` dict/list 兩種格式都遮罩 secret-like values，且 full fake secret 不出現在 facts/evidence/issues。
- `env_file` 只記錄 reference；若測試讀取 env file，必須證明該 env file 來自 `FileInventory`。
- malformed compose 只產生該檔案的 parse issue，不影響另一個 compose file 的 facts。
- `depends_on` list/map 都 normalize 成 dependency service names。

## 新手提示
這個 provider 不需要懂 Docker 全部功能。第一版只抓對 RAG system map 有用的服務、port、env、volume。

## 視覺化說明
```text
┌──────────────────────┐
│ docker-compose.yml    │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ DockerComposeProvider │
└──────┬───────┬───────┘
       │       │
       ↓       ↓
┌──────────────┐ ┌──────────────────┐
│ service      │ │ published port   │
│ image facts  │ │ facts            │
└──────────────┘ └────────┬─────────┘
                          ↓
┌──────────────┐ ┌──────────────────┐
│ env/volume   │ │ Endpoint/Risk    │
│ facts        │ │ later            │
└──────────────┘ └──────────────────┘
```
