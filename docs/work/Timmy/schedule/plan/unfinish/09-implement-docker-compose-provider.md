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
- 尋找 `docker-compose.yml`、`docker-compose.yaml`。
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
1. 建立 `src/kai_mind/core/providers/docker_compose_provider.py`。
2. 從 `FileInventory` 選出 compose files。
3. 使用 safe YAML parser 讀檔。
4. 將每個 service 轉成 `ScanFact` candidate。
5. 對 `qdrant/qdrant`、`ollama/ollama`、published ports 產生明確 rule ids。
6. parse error 轉為 `ParseIssue` 與 evidence。
7. 測試 Qdrant image、Ollama image、`6333:6333` port、malformed compose。

## 預期輸出
- `src/kai_mind/core/providers/docker_compose_provider.py`
- `tests/core/test_docker_compose_provider.py`

## 驗收標準
- Qdrant service image 產生 `docker_service` evidence。
- Published port 產生 `published_port` evidence。
- Malformed compose 不 crash，產生 parse issue。
- Environment secret-like value 已遮罩。

## 可能風險與注意事項
- Compose spec 很大，Epic 1 只需要 high-signal fields。
- `ports` 可能是 string 或 object form，兩者都要處理。
- 參考依據：Docker Compose services 官方文件確認 `image`、`ports`、`environment`、`env_file`、`depends_on` 是 service-level fields。

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
