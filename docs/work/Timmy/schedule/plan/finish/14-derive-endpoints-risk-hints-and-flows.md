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
1. 建立 `src/systograph/core/services/endpoint_detection_service.py`。
2. 建立 `src/systograph/core/services/risk_hint_service.py`。
3. 建立 `src/systograph/core/services/flow_derivation_service.py` 或放在 normalize 前的獨立 helper。
4. 實作 Docker Compose published port parser：支援 short syntax 與 long syntax，辨識 host binding 是否省略、`0.0.0.0`、`127.0.0.1`、`localhost`。
5. 實作 Docker port -> endpoint / network exposure risk hint。
6. 實作 Compose service-name internal endpoint hint：沒有 `ports` 時只能標示 container-network internal endpoint，不產生 host-published exposure risk。
7. 實作 external provider -> endpoint/risk hint。
8. 實作 parse issue -> risk hint。
9. 寫測試：Qdrant port risk、OpenAI external endpoint、malformed compose parse risk、loopback-bound port lower-risk wording、service-name internal endpoint 不產生 published-port risk。

## 預期輸出
- `src/systograph/core/services/endpoint_detection_service.py`
- `src/systograph/core/services/risk_hint_service.py`
- `src/systograph/core/services/flow_derivation_service.py`
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

## 外部查證校正（2026-06-04）

根據最新官方文件與主要開源專案 README / docs，Task 14 research 的大方向正確，但需要幾個措辭校正：

- Docker Compose `ports: ["6333:6333"]` 的判斷正確。Compose short syntax 若省略 host IP，會 bind 到所有 network interfaces (`0.0.0.0`)；long syntax 的 `host_ip` 省略時也同理。這可以產生 network exposure risk hint，但仍要保留 uncertainty，因為 static scan 不驗證 host firewall、runtime 狀態或實際 public IP。
- Docker Compose 沒有 `ports` 不代表服務不存在 endpoint。Compose 預設會建立 project network，同 network 服務可用 service name 互相連線；這應視為 container-network internal endpoint / flow evidence，不應產生 host-published port exposure risk。
- GitDiagram 可借鏡「LLM 產生 graph 後再用實際 file tree 驗證、bad path / invalid connection retry」的做法；但它不是純 deterministic scanner。不要把 GitDiagram 寫成完全不依賴 LLM 幻覺的 deterministic extraction 範例。
- Understand-Anything 可借鏡 staged pipeline、project scan、file/function/class/dependency graph、dashboard exploration。若要引用「merge 階段丟棄 dangling edges」或 `importMap` recovery，必須先看該 repo 具體程式碼或先前保存的 evidence；不能只根據 README 推論。
- Checkov、Bandit、Semgrep 都適合作為 rule-based / policy-as-code 參考，但不建議在 Epic 1 Task 14 直接引入為 runtime dependency。Checkov 官方重點是 IaC static scan 與 custom policies；Bandit 使用 AST plugin 概念；Semgrep 支援 YAML-defined custom rules。這些支持「規則可測、可迭代」的架構方向，不代表 Systograph 需要接它們的引擎。
- Python `ast` 適合做 read-only literal endpoint extraction，但要有防呆：不 import / exec / eval 使用者程式；只接受 literal string/number kwargs；`ast.parse()` 失敗或遇到超大/複雜輸入時要回到 unknown evidence，不可中止整體 map。
- PyYAML 應維持 `yaml.safe_load()`。不要使用 `yaml.load()` / unsafe Loader 解析 project-owned config 或 Compose 檔。

查證來源：
- Docker Compose services `ports` reference: https://docs.docker.com/reference/compose-file/services/
- Docker Compose networking: https://docs.docker.com/compose/how-tos/networking/
- Python `ast` docs: https://docs.python.org/3/library/ast.html
- PyYAML docs: https://pyyaml.org/wiki/PyYAMLDocumentation
- Checkov docs: https://www.checkov.io/1.Welcome/What%20is%20Checkov.html
- Bandit plugin docs: https://bandit.readthedocs.io/en/latest/plugins/
- Semgrep rule docs: https://semgrep.dev/docs/writing-rules/overview
- GitDiagram repo: https://github.com/ahmedkhaleel2004/gitdiagram
- Understand-Anything repo: https://github.com/Lum1104/Understand-Anything

## Endpoint / risk 補強分層原則

Chroma endpoint 與 local persistence 補強是 provider-specific 補強範例，不代表 Task 14 只處理 Chroma。Task 14 應先實作通用 endpoint / risk derivation framework，再針對已經有明確 mode evidence 的 provider 補 provider-specific wording 或 rule。

通用規則應優先處理：
- `docker_published_port_exposure` 適用所有可連回 component 的 Docker published port，不限 Chroma。Qdrant、pgvector、Ollama、Chroma、app service 只要有 service image/component evidence 加上 published port evidence，都可以產生 endpoint 與 network exposure risk hint。
- `external_provider_detected` 適用 OpenAI 或其他已確認 external provider component。OpenAI LLM / embedding provider 可產生 external endpoint 與 egress/data handling hint，但 API key 類 evidence 只能使用 masked value。
- `secret_like_config_key_detected` 適用所有 secret-like config key，不限 OpenAI 或 Chroma。
- `config_parse_error` 適用所有 config / compose parse issue，代表 partial scan / incomplete evidence。
- `missing_required_slot` 適用所有 `rag-core-v1` required slot，不限 vector store。

Provider-specific 補強只在 evidence 有特殊語意時加入：

| Provider / 類型 | 目前 evidence | Task 14 落點 | 注意事項 |
|---|---|---|---|
| Qdrant | `docker_qdrant_image_detected` + `docker_published_port_detected`；`QdrantClient(...)` code pattern | Docker port 先走通用 `docker_published_port_exposure`；若從 `QdrantClient(url=...)` 安全解析 URL，可補 client endpoint rule | 不要只因 dependency `qdrant-client` 產生 endpoint 或 risk |
| pgvector | `docker_pgvector_image_detected` + `docker_published_port_detected` | 產生 database endpoint / published DB port risk hint | wording 應是 PostgreSQL/pgvector database port，不要寫 HTTP vector endpoint |
| Ollama | `docker_ollama_image_detected` + `docker_published_port_detected`；`llm.provider: ollama` config | Docker port 可產生 local LLM runtime endpoint / published runtime API risk hint | config-only provider 不等於 runtime port 已公開 |
| OpenAI | OpenAI SDK/code/config/base URL/API key evidence | 產生 external provider endpoint / risk hint；secret-like config 另走 secret rule | 不得輸出完整 API key；dependency-only 應保守 |
| Chroma | `chromadb.HttpClient(...)`、`AsyncHttpClient(...)`、`PersistentClient(...)`、`chromadb/chroma` Docker image、Chroma env/config | 依下方 Chroma-specific rules 補 HTTP endpoint、local persistence、server published port | Chroma 有 local persistent / HTTP server mode 差異，因此需要額外 rule |

不應新增的範圍：
- 不因為看到 vector DB dependency-only evidence 就產生 endpoint 或 risk hint。
- 不在 Task 14 一次補齊所有未支援 vendor，例如 LanceDB、FAISS、Milvus、Weaviate、Pinecone；除非前面 provider/component detection 已有可追溯 strong evidence。
- 不把通用 Docker published port rule 拆成大量重複 provider-specific rules；只有 rationale / uncertainty 需要 provider-specific wording 時才分支。

## Docker endpoint parsing 細節

Docker Compose `ports` 必須分清楚 host-published endpoint 與 container-network internal endpoint：

| Evidence | Endpoint 類型 | Risk hint | 備註 |
|---|---|---|---|
| short syntax `"6333:6333"` | host-published service address；bind host evidence = `0.0.0.0`，published port = `6333` | `docker_published_port_exposure` | `0.0.0.0` 是 bind address，不是使用者應呼叫的 URL；endpoint/risk wording 要分清楚 |
| short syntax `"127.0.0.1:6333:6333"` | `http://127.0.0.1:6333` | 可產生 lower-severity / local-bound wording，或只產生 endpoint | loopback binding 仍是 published port，但不是同等外部暴露 |
| long syntax `host_ip=127.0.0.1,published=5432,target=5432` | `127.0.0.1:5432` | local-bound wording | 目前 `DockerComposeProvider` 已 normalize long syntax value |
| service image exists, no `ports`, other service env references `http://qdrant:6333` | internal endpoint / flow evidence | 不產生 `docker_published_port_exposure` | 同 Compose network 內 service discovery，不代表 host 可連 |
| only `expose` or Dockerfile `EXPOSE` | internal / documentation hint only | 不產生 host-published exposure risk | Docker image exposed port 可被同 network 容器看到，但不是 host published port |

Port parser 建議：
- 不用呼叫 `docker compose config` 或 `docker compose port`，避免 runtime / environment dependency。
- short syntax 先支援常見 IPv4 / hostname forms：`CONTAINER`、`HOST:CONTAINER`、`IP:HOST:CONTAINER`、`HOST:CONTAINER/protocol`。
- IPv6 bracket form 與 port range 可先保守保留 raw value，產生 endpoint evidence 但加上 uncertainty；不要硬拆錯。
- endpoint value 不應包含 secret query string 或 credential。若 URL 內有 credential-like fragment，必須使用已 masked evidence 或直接省略敏感片段。

## Python endpoint literal extraction

Task 14 若要從 Python code 推導 `chromadb.HttpClient(host=..., port=...)`、`QdrantClient(url=...)`、OpenAI-compatible `base_url`，只能做 bounded static parsing：

- 不 import 使用者 module。
- 不執行 `eval()` / `exec()`。
- 不呼叫 SDK method，例如 Chroma `heartbeat()`、Qdrant health check、OpenAI model list。
- 優先使用既有 `CodePatternProvider` evidence；若 evidence snippet 不足，新增 bounded AST helper 或回到 provider-local rule 補 arg facts。
- 只接受 literal string / number kwargs，例如 `host="localhost"`、`port=8000`、`url="http://localhost:6333"`。
- `os.getenv("OLLAMA_URL") + "/api/generate"`、f-string、變數拼接、function return value 等 dynamic endpoint 一律標成 unknown / variable reference，不自行推斷值。
- `ast.parse()` 要 catch `SyntaxError`、`ValueError`、`RecursionError`；若 parser 失敗，產生 partial evidence / uncertainty，不中止 scan。

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
- Docker / server config 出現 `CHROMA_PORT`、`CHROMA_LISTEN_ADDRESS`、`CHROMA_PERSIST_PATH` 或 `PERSIST_DIRECTORY`，只有在 Docker image 或 Chroma server context 明確時，才推導 server endpoint 或 persistence hint。
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

## 架構決策紀錄（ADR）

### ADR-14-01：Risk rules 實作方式

**問題**：Risk hint rules 要 hard code 在 Python、放 TOML catalog，還是用本地 AI 動態生成？

**決策**：**觸發邏輯 hard code 在 Python service，rule metadata 可用 Python 常數或 TOML 補充說明。不使用本地 AI 動態生成 risk hints。**

**理由**：

業界主流 SAST 工具（Semgrep、Bandit、SonarQube）的設計都是「規則邏輯預先定義好，metadata 可設定」，不是動態生成：
- Semgrep：YAML 宣告式 pattern，本質上仍是人工定義後固定的
- Bandit：Python plugin 寫死邏輯，pyproject.toml 只控制開關
- SonarQube：6,500+ rules 全部是人工撰寫的 Java plugin

**不使用本地 AI 動態生成的原因**：

| 問題 | 影響 |
|---|---|
| LLM 輸出非確定性 | 同一 evidence 每次可能產生不同 risk hint，無法寫穩定 unit test |
| 無法追溯 evidence | `RiskHint.evidence_id` 是必填欄位，AI 無法保證引用 valid ID |
| 不了解威脅模型 | LLM 不知道 Systograph 的 RAG slot 定義與 Epic 1 scope |
| 違反 evidence-based 原則 | GEMINI.md 明訂 evidence-based findings，AI 生成的 hint 無來源 |
| 違反 read-only 原則 | 引入本地 AI 增加不必要的運算與維運複雜度 |

**「Rules 永遠不完整」的正確處理方式**：

Epic 1 的 5 條初始 rules 是有意識的 scope 決定，不是設計缺陷。
- 使用 `uncertainty` 欄位說明每條 hint 的局限性
- 版本迭代補充；Semgrep / Checkov 這類工具也都是透過 registry / policy set 持續累積規則，而不是一次寫完
- 不在 Epic 1 追求完整性，先追求可測試、可追溯、可信賴

**Secret masking 分工**：`SecretMaskingService` 在 provider scan 階段（Task 12）就已對 Evidence value 做 mask，`RiskHintService` 只讀取已 masked 的 Evidence，不需要自行再做 mask。

**TOML 外部化分工**：長期可以把 risk rule metadata 抽到 TOML，但 Task 14 不應把觸發條件抽成 TOML condition DSL。Epic 1 的正確落點是：
- trigger logic / target selection / evidence cross-reference validation 留在 typed Python service。
- rule id、type、default severity、rationale template、uncertainty template 可先用 Python 常數或 dataclass 集中管理。
- 等 Task 14 的 rules 穩定、規則數量增加、metadata 重複明顯時，再用後續 plan 抽成 `risk_hint_rules.toml`。

原因：
- Semgrep 的 YAML rules 適合 pattern matching / dataflow 類規則，但 Task 14 risk hints 需要同時看 facts、components、endpoints、evidence refs 和 target validity。
- Checkov 同時支援 Python custom policies 與 YAML policies，代表業界不是「所有 rule 都必須 YAML/TOML」。
- Bandit 的 detection logic 是 Python AST plugins，TOML/INI/YAML 主要用於設定與排除，不是把所有安全邏輯寫成 TOML。
- 若現在把 `condition = "component == 'qdrant' AND has_port == true"` 這類語法放進 TOML，就等於要在 Epic 1 自製小型 rule language，會拖慢 MVP 且增加測試負擔。

### ADR-14-02：Task 14 不引入外部 scanner engine

**問題**：是否要直接呼叫 Checkov、Bandit、Semgrep、OPA/Rego、Tree-sitter、LibCST 等外部套件來完成 endpoint / risk hint derivation？

**決策**：**Epic 1 Task 14 不新增外部 scanner engine dependency。維持使用既有 `PyYAML`、`jsonschema`、Pydantic models、provider facts/evidence，以及 Python stdlib `ast` 作為可選 bounded parser。**

**理由**：

| 候選工具 | 可借鏡處 | 不直接引入的原因 |
|---|---|---|
| Checkov | IaC static scan、Python/YAML custom policies、policy metadata | 對 Task 14 的 5 條初始 rules 過重；需要把 Systograph facts 轉成 Checkov resource model |
| Bandit | AST plugin / visitor pattern，不 import 使用者程式 | Bandit 是 Python security scanner，不是 RAG endpoint/risk mapper；直接嵌入會增加 rule/context adapter 成本 |
| Semgrep | YAML-defined rules、registry、iterative rule growth | 導入 engine 會增加安裝與跨平台成本；目前 code pattern provider 已有 deterministic rule catalog |
| OPA/Rego | Policy-as-code | Task 14 evidence/target validation 比一般 policy eval 更依賴 local contract，MVP 用 Python 條件更容易測試 |
| Tree-sitter / LibCST | 更完整的 cross-language parsing | Epic 1 目前 Python backend + bounded patterns 足夠；新增 parser dependency 會增加 packaging 與跨平台維護成本 |

未來如果 Task 14 之後要支援大量 language / provider-specific endpoint extraction，可以另開 future plan 評估 AST / Tree-sitter / Semgrep-style rule engine；不要把這個決策塞進 Epic 1 MVP。

## 視覺化說明
```text
┌────────────────────────────────────────────────────────────┐
│ Task 12 raw facts + evidence                               │
│ config / compose / dependency / code pattern evidence       │
└──────────────────────────────┬─────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────┐
│ Task 13 ComponentDetectionResult                            │
│ detected components / extensions / unmapped_components      │
└──────────────────────────────┬─────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────┐
│ Task 14 derivation input                                    │
│ facts + evidence + confirmed components                     │
└───────┬──────────────────────┬──────────────────────┬──────┘
        │                      │                      │
        ↓                      ↓                      ↓
┌────────────────┐    ┌───────────────────┐   ┌──────────────────┐
│ Docker /       │    │ Provider config /  │   │ Bounded code     │
│ Compose facts  │    │ env facts          │   │ literal parsing  │
└───────┬────────┘    └─────────┬─────────┘   └────────┬─────────┘
        │                       │                      │
        ↓                       ↓                      ↓
┌────────────────┐    ┌───────────────────┐   ┌──────────────────┐
│ ports parser   │    │ external provider │   │ AST / snippet    │
│ short / long   │    │ + secret masking  │   │ literal args only│
└───────┬────────┘    └─────────┬─────────┘   └────────┬─────────┘
        │                       │                      │
        ├──────────────┬────────┴──────────────┬───────┘
        ↓              ↓                       ↓
┌──────────────┐ ┌────────────────┐   ┌──────────────────────────┐
│ host-        │ │ container-     │   │ external / client        │
│ published    │ │ network        │   │ endpoint evidence        │
│ endpoint     │ │ internal hint  │   │                          │
└──────┬───────┘ └────────┬───────┘   └────────────┬─────────────┘
       │                  │                        │
       ↓                  ↓                        ↓
┌────────────────────────────────────────────────────────────┐
│ EndpointDetectionService                                    │
│ endpoint ids + values + endpoint_type + component refs       │
└──────────────────────────────┬─────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────┐
│ RiskHintService                                             │
│ generic rules: published port / external provider / parse    │
│ error / secret-like config / missing required slot           │
│ provider-specific: Chroma HTTP / local persistence, etc.     │
└──────────────────────────────┬─────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────┐
│ FlowDerivationService                                       │
│ build indexing + query_answer edges only when slots or       │
│ confirmed extension targets exist                            │
└──────────────────────────────┬─────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────┐
│ Canonical ai-system-map/v1 additions                         │
│ endpoints / risk_hints / flows / recommended_next_checks      │
└──────────────────────────────┬─────────────────────────────┘
                               ↓
┌────────────────────────────────────────────────────────────┐
│ SystemMapValidationService                                  │
│ reject missing evidence refs, dangling component refs,        │
│ invalid risk targets, invalid flow edges                      │
└────────────────────────────────────────────────────────────┘
```
