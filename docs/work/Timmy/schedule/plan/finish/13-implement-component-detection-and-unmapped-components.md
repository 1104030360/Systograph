# Task 13: Implement Component Detection and Unmapped Components

## 目標
實作 `ComponentDetectionService`，將 raw facts 映射到 `rag-core-v1` component slots、component instances、extensions、unmapped components。此任務要守住 detected 必須有 evidence、不確定時不要硬塞 slot 的規則。

## 為什麼要先做這個
Stage 5 是從 facts 走向 system map 的核心。沒有 component detection，就無法建立 `components_by_slot`、flows、viewer graph，也無法處理 custom RAG architecture。

## 前置需求
- Task 3 已完成 `rag-core-v1` template。
- Task 12 已完成 raw facts aggregation。
- Task 2 已完成 component/evidence models。

## 實作範圍
- 建立 component detection rules。
- 初始支援 Qdrant、Chroma、Ollama、OpenAI、LangChain/LlamaIndex signals。
- 建立 all slots status：detected/missing/not_configured/not_applicable。
- 對 ambiguous router/reranker facts 輸出 `unmapped_components` 或 extension candidate。
- 套用 manual mapping 的 extension hook 先留 interface，Task 19 再實作。

## 不包含範圍
- 不使用 AI mapping proposal。
- 不寫 user mapping store。
- 不做 risk hints。
- 不做 query trace mapping。

## 建議實作步驟
1. 建立 `src/kai_mind/core/services/component_detection_service.py`。
2. 定義 rule input：template + facts + evidence。
3. 實作 direct evidence mapping：Docker Qdrant -> vector_store、Ollama -> llm、OpenAI SDK/config -> llm/embedding candidate。
4. 實作 missing slot fill：沒有 evidence 時 status 不得 detected。
5. 實作 unmapped output：有 evidence 但無安全 slot 時 status `needs_confirmation`。
6. 寫測試：Qdrant detected、citation missing、custom router unmapped。
7. 寫測試：無 evidence 不可 detected。

## 預期輸出
- `src/kai_mind/core/services/component_detection_service.py`
- `tests/unit/core/test_component_detection_service.py`

## 驗收標準
- Qdrant fixture 產生 detected vector_store instance。
- missing citation slot instances count = 0。
- custom router 不被硬塞進 retriever。
- JSON 不含 `confidence`。
- 每個 detected instance 都有 evidence_ids。

## 可能風險與注意事項
- Dependency evidence 通常只能當 supporting signal，不應單獨 detected。
- 不要把 AI wording 或猜測寫進 facts。
- LangChain/LlamaIndex concepts 可參考官方 RAG/retrieval docs，但 mapping rule 要保守。

## 外部查證補充

### 查證結論

原研究方向大致正確，但需要修正幾個措辭：

- OpenTelemetry 的類比應引用 `opentelemetry-collector-contrib` 的 `servicegraphconnector`，不是 core collector 本體。
- OTel virtual node 是 runtime trace topology 的概念，不能直接等同 KAI-Mind 的 static scan；對 Task 13 只能借鑑「只有 client-side signal 時，不把 server-side component 當成 confirmed」的保守判斷。
- Backstage 的 `validateEntityKind` 可作為 SlotValidator 類比；它會驗證 known entity kind 與 schema。不過 Backstage 對已知 kind 的 `spec` unknown fields 通常可保留，所以 KAI-Mind 不應寫成「所有未知欄位都丟棄」，而應寫成「未知 slot / 不合 canonical slot 的 mapping 不可進入 `components_by_slot`，但原始 evidence 要保留到 `unmapped_components`」。
- OSV-Scanner / Trivy 的參考重點是 vulnerability scanner 對 package name、version、ecosystem、SBOM metadata 的依賴；缺上下文會造成不準確或無法可靠比對。不要過度表述成它們一定會把缺版本資料列成 `unknown`。

### 可借鑑的外部機制

#### OpenTelemetry Service Graph Connector

來源：
- https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/connector/servicegraphconnector
- https://raw.githubusercontent.com/open-telemetry/opentelemetry-collector-contrib/main/connector/servicegraphconnector/README.md

可借鑑：
- Service Graph Connector 會從 traces 建立服務拓撲，透過 client/server span pair 產生 edge。
- 它支援 `virtual_node_peer_attributes`，當 client span 有 `peer.service`、`db.name`、`db.system` 等資訊時，可建立 virtual server node 代表未完整 instrumentation 的遠端節點。
- 對 KAI-Mind 的對應原則：如果只有 dependency / client library signal，沒有 Docker / config / code pattern 等強證據，不得把 slot 標為 `detected`。這類 signal 應進入 slot hint、candidate，或 `unmapped_components`，等待使用者確認。

例子：

```text
requirements.txt 有 chromadb
  -> weak client-side signal
  -> 不足以讓 vector_store = detected

docker-compose.yml 有 image: chromadb/chroma
  -> strong deployment/config evidence
  -> 可以讓 vector_store = detected，且 instance 必須引用 evidence_ids
```

#### Backstage Catalog Processor

來源：
- https://backstage.io/docs/features/software-catalog/extending-the-model/
- https://backstage.io/api/stable/classes/_backstage_plugin-catalog-backend.index.BuiltinKindsEntityProcessor.html

可借鑑：
- Backstage 在 entity 進入 catalog 前，會經過 processor chain 的 `validateEntityKind`，確認 entity 是已知 kind 並符合 schema。
- `BuiltinKindsEntityProcessor.validateEntityKind` 對 known kind 且 valid 回傳 true；對不是該 processor 認得的 kind 回傳 false；對 known kind 但不 valid 則 rejected。
- 對 KAI-Mind 的對應原則：`ComponentDetectionService` 寫入 `components_by_slot` 前必須經過嚴格 slot 驗證。不能安全對應到 `rag-core-v1` slot 的 fact，不可硬塞，必須保留為 `unmapped_components` 或等 Task 19 的 manual mapping / extension flow。

#### Lyft Cartography

來源：
- https://cartography-cncf.github.io/cartography/dev/writing-intel-modules.html
- https://cartography-cncf.github.io/cartography/references/orm.html

可借鑑：
- Cartography intel module 的 sync flow 明確拆成 `get`、`transform`、`load`、`cleanup`。
- `get` 應保持單純，只回傳 provider API 的 raw dicts；`transform` 負責整理資料；`load` 透過 schema object 寫入 graph。
- 對 KAI-Mind 的對應原則：Provider 只產生 `ScanFact` / `Evidence`，不要直接決定 slot。`ComponentDetectionService` 才負責把 facts 映射到 canonical map，而且要受 template slot 與 validation service 約束。

#### OSV-Scanner / Trivy

來源：
- https://github.com/google/osv-scanner
- https://trivy.dev/docs/dev/guide/target/sbom/

可借鑑：
- OSV-Scanner 會把 package name、version、ecosystem 等資料送到 OSV.dev API 做漏洞比對。
- Trivy 官方文件提醒：掃描由其他工具產生的 SBOM 可能不準，因為 Trivy 依賴 SBOM 內的 custom properties 來做準確偵測。
- 對 KAI-Mind 的對應原則：evidence quality 必須分級。缺少部署/config/code usage context 的 dependency fact 只能當 supporting signal，不可單獨升級為 `detected` component。

#### Understand-Anything

來源：
- https://github.com/Lum1104/Understand-Anything

可借鑑：
- Understand-Anything README 描述其 deterministic parser 會抽取 wikilinks / categories；對 codebase 則以 Tree-sitter 做 deterministic structural extraction，再由 LLM 產生 semantic summary、tags、architecture layer 等補充。
- 對 KAI-Mind 的對應原則：Task 13 的 slot mapping 必須以 deterministic rules 與 evidence 為主。LLM 或語意描述不能創造 component，也不能讓 slot 變成 `detected`。

### Evidence 強弱分級建議

建議在 `ComponentDetectionService` 內部使用明確的 evidence strength，而不是用 `confidence`：

| Strength | 例子 | 可否單獨 detected |
|---|---|---|
| Strong | `docker-compose.yml` service image 為 `qdrant/qdrant`、`chromadb/chroma`、`ollama/ollama`；明確 provider config；bounded code pattern 顯示實際 client 初始化與呼叫 | 可以，但 detected instance 必須有 `evidence_ids` |
| Weak | `requirements.txt` / `pyproject.toml` / `package.json` 只有 `chromadb`、`qdrant-client`、`langchain`、`llama-index` 等 dependency | 不可以，只能當 supporting signal / candidate / hint |
| Unknown | 無法解析、動態載入、名稱像自訂 router / reranker / cache 但無安全 slot | 不可以，保留 parse issue、`unmapped_components` 或後續 mapping proposal |

### Chroma 依賴的判斷邊界

來源：
- https://cookbook.chromadb.dev/core/clients/
- https://cookbook.chromadb.dev/core/storage-layout/
- https://cookbook.chromadb.dev/running/running-chroma/
- https://docs.trychroma.com/reference/python/client
- https://docs.trychroma.com/docs/run-chroma/clients
- https://docs.trychroma.com/reference/server-env-vars

Chroma 官方文件同時描述 local `PersistentClient`、HTTP/server、Docker compose 等使用方式。這代表只看到 `chromadb` dependency 時，KAI-Mind 只能知道專案可能具備使用 Chroma 的能力，不能知道它是：

- project 自己用 Docker 跑 `chromadb/chroma`；
- 連到外部 Chroma server / SaaS；
- 用 `PersistentClient` 寫到本機資料夾與 `chroma.sqlite3`；
- 實際上安裝了但沒有使用。

因此 Task 13 應採用以下判斷：

```text
只有 dependency evidence:
  vector_store.status != detected
  記錄 candidate / supporting hint，或進入 unmapped_components

有 Docker / config / bounded code pattern 強證據:
  vector_store.status = detected
  component instance = Chroma / Qdrant / other provider
  必須引用 evidence_ids
```

### 實作提醒

- 不需要在本地執行 `docker compose up` 或查 `docker ps`；KAI-Mind map scan 是 read-only static scan。
- 「Server evidence」在 Task 13 代表靜態檔案中有足夠部署或設定證據，例如 Docker Compose service、Dockerfile、明確 env/config endpoint、bounded source code 初始化。
- `unmapped_components` 不是錯誤桶；它是「有 evidence，但尚未能安全映射」的正式 contract。
- 規則可以先放在 Python 常數或 TOML/JSON，但無論放哪裡，都要測試：dependency-only 不得 detected、Docker Qdrant 可 detected、custom router 不得硬塞 retriever、每個 detected instance 都有 `evidence_ids`。

### Chroma mode detection 補強

這段補強屬於 Task 13。Task 11/12a 已完成 provider 與 TOML rule catalog，若 Task 13 發現現有 provider-local rules 不足，可以在 Task 13 的變更範圍內補 `src/kai_mind/core/rules/code_pattern_rules.toml` 與對應測試；不需要把已完成的 Task 11 / Task 12a plan 移回 unfinish。

目前 repo 觀察：
- `src/kai_mind/core/rules/code_pattern_rules.toml` 只有 `code_pattern_vector_store_chroma`，regex 是 `\bChroma\s*\(`，主要覆蓋 LangChain / `langchain_chroma.Chroma(...)` 類型呼叫。
- 目前沒有 `chromadb.PersistentClient(...)`、`chromadb.HttpClient(...)`、`chromadb.AsyncHttpClient(...)` 的 code pattern rule。
- `ConfigParseProvider` 會把 `.env`、YAML、JSON、TOML scalar 拆成 `config_value` facts，但不解讀 key 名稱語意。也就是 `CHROMA_HOST`、`CHROMA_API_KEY`、`vector_store.provider: chroma` 這類語意應由 `ComponentDetectionService` 判斷。

建議新增的 provider-local code pattern rules：

```toml
[[patterns]]
rule_id = "code_pattern_vector_store_chroma_http"
kind = "vector_store_client"
languages = ["python"]
extensions = [".py"]
regex = "\\bchromadb\\.HttpClient\\s*\\("
snippet_group = ""

[[patterns]]
rule_id = "code_pattern_vector_store_chroma_async_http"
kind = "vector_store_client"
languages = ["python"]
extensions = [".py"]
regex = "\\bchromadb\\.AsyncHttpClient\\s*\\("
snippet_group = ""

[[patterns]]
rule_id = "code_pattern_vector_store_chroma_persistent"
kind = "vector_store_client"
languages = ["python"]
extensions = [".py"]
regex = "\\bchromadb\\.PersistentClient\\s*\\("
snippet_group = ""
```

先用 `chromadb.` 前綴，比單純 `\bHttpClient\s*\(` / `\bPersistentClient\s*\(` 保守，避免把其他 library 的同名 client 誤判成 Chroma。若後續要支援 `from chromadb import PersistentClient` 後直接呼叫 `PersistentClient(...)`，應放到 `docs/work/Timmy/schedule/plan/future/code-pattern-provider-ast-and-rule-engine-evolution.md`，用 import-aware AST / Tree-sitter / ast-grep 規則處理；不要在 Task 13 用過寬 regex 犧牲 precision。

Task 13 的 Chroma 判斷矩陣：

| Evidence 組合 | Task 13 判斷 | 說明 |
|---|---|---|
| 只有 `chromadb` dependency | 不得 `detected` | 只能作 candidate / supporting signal |
| Docker image `chromadb/chroma` | `vector_store` 可 `detected`，provider/name = Chroma | 表示 project 靜態部署設定中有 Chroma server |
| `chromadb.HttpClient(...)` 或 `chromadb.AsyncHttpClient(...)` | `vector_store` 可 `detected`，kind 可標成 HTTP/server-backed vector store | 表示程式碼明確連 Chroma server；endpoint 由 Task 14 從 host/port/config 推導 |
| `chromadb.PersistentClient(...)` | `vector_store` 可 `detected`，kind 可標成 local persistent vector store | 表示 embedded/local persistent Chroma；local persistence risk hint 留給 Task 14 |
| `CHROMA_HOST` / `CHROMA_ENDPOINT` / `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE` 或 config path 類似 `vector_store.provider: chroma` | 有 Chroma dependency 或 Chroma code pattern 時可支撐 `detected`；單獨出現時偏 candidate / needs_confirmation | 現行 Chroma docs 描述 Cloud / client env vars；但單一 env key 可能未被程式使用，要避免過度推論 |
| `CHROMA_PORT` / `CHROMA_LISTEN_ADDRESS` / `CHROMA_PERSIST_PATH` | 只能在 Docker / server config context 下支撐 Chroma server detection | 這些是 self-hosted server operator env vars；若孤立出現在一般 `.env`，不要直接判定 client 使用 Chroma |

測試補強：
- `chromadb` dependency-only 不得讓 `vector_store` detected。
- `chromadb.HttpClient(host="...", port=...)` 可讓 `vector_store` detected，且 instance 有 code pattern evidence。
- `chromadb.PersistentClient(path="...")` 可讓 `vector_store` detected，且 instance 有 code pattern evidence。
- `.env` 只有 `CHROMA_HOST` 但沒有 dependency / code pattern 時，不得直接 detected；可進 candidate / `unmapped_components` 或 supporting hint。
- `.env` 有 `CHROMA_HOST` 且 dependency / code pattern 也指向 Chroma 時，可支撐 detected 或 endpoint derivation，但 secret-like values 必須維持 masked。

## 新手提示
這一步像把收集到的線索貼到 RAG 架構圖上。貼不上去的線索不能丟掉，要放到 unmapped 等使用者確認。

## 視覺化說明
```text
┌──────────────┐
│ Scan facts   │
└──────┬───────┘
       ↓
┌──────────────────────┐
│ clear slot match?     │
└──────┬───────┬───────┘
       │       │
 yes   │       │ clear custom
       ↓       ↓
┌──────────────┐ ┌──────────────┐
│ components   │ │ extensions   │
│ detected     │ │              │
└──────┬───────┘ └──────┬───────┘
       │                │
 uncertain path         │
       ↓                │
┌──────────────┐        │
│ unmapped     │        │
│ components   │        │
└──────┬───────┘        │
       └────────┬───────┘
                ↓
┌──────────────────────┐
│ Validation later      │
└──────────────────────┘
```
