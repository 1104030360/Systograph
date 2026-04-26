# Phase 2 – Cloud Ollama Migration Plan

## 目標
將所有代理元件（SQLAgent / SemanticAgent / HybridQueryAgent / gptChat orchestration）從本地 `ollama` CLI 呼叫改為使用雲端 Ollama REST API，以便在 macOS 環境與 CI 中穩定運作。

## 雲端 Ollama 假設
- **雲端服務為第一優先**：所有代理預設走雲端 Ollama REST API，內建重試 / timeout。
- **驗證目標**：目前階段只需確認請求送到雲端 Ollama 並取得回覆即可。
- Power Automate 僅作為備援，僅在雲端 Ollama 無法連線時才啟用；如果未設定 URL，可暫時跳過，不列入測試範圍。
- 透過 HTTP REST Endpoint 存取（預設 `/api/generate` 與 `/api/chat`）。
- 需要 API Key / Token 與 Base URL。
- 支援 streaming / 非 streaming 呼叫；初期先以非 streaming 為主。
- 模型名稱維持現有配置（`deepseek-coder-v2:latest` 等），由雲端端負責提供。

新增環境變數（`.env` 與 `config_loader`）：
- `OLLAMA_CLOUD_BASE_URL`
- `OLLAMA_CLOUD_API_KEY`
- `OLLAMA_TIMEOUT_SECONDS`（可選）
- `OLLAMA_DEFAULT_MODEL`（可覆寫現有預設）

## 受影響模組
| 模組 | 目的 | 變更摘要 |
|------|------|----------|
| `gpt_utils.py` | 目前混和 Power Automate + 本地 Ollama | 建立共用 `call_ollama_cloud()` / `stream_ollama_cloud()`，負責 HTTP 認證、錯誤處理、重試與快取整合 |
| `gptChat.py` | 多代理 orchestrator，頻繁使用 `subprocess.run` | 改為呼叫新的 Ollama 客戶端；調整回傳格式、錯誤訊息 |
| `agents/sql_agent.py` | `_split_user_question`、`_generate_pandas_filter`、`_run_with_fallback` 等函式 | 用共用客戶端替換所有 `subprocess.run`，統一錯誤處理與 timeout |
| `agents/semantic_agent.py` | `_run_with_fallback`、摘要流程 | 同上，此外調整 request payload 以符合雲端 API |
| `agents/hybridquery_agent.py` | pipeline 規劃與 summary | 改用 HTTP 客戶端，保留 Power Automate fallback |
| `tests/unit/agents/*` | 目前 patch `subprocess.run` | 更新為 patch `gpt_utils.call_ollama_cloud` / `requests.post` |
| `tests/unit/utils/test_kb_loader.py` 及其他 | 若載入 SentenceTransformer 仍需 stub | 確認不受影響，但需確保雲端調用在測試中 mock 掉 |
| `config_loader.py` / `docs` | 載入新環境變數 | 說明設定方式與預設值 |

## 執行步驟
### 完成情況快照（2025-?? 更新）
- ✅ 建立雲端 Ollama 共用客戶端並整合 `ConfigLoader` 新設定。
- ✅ SQL / Semantic / Hybrid Agents 及 `gptChat.py` 全數改為雲端優先（以 `utils.ollama_client` 取代本地 `subprocess`）。
- ✅ 單元測試改寫為 mock 雲端呼叫；新增 `tests/unit/utils/test_ollama_client.py`，並在 `tests/unit/agents/test_hybrid_agent.py` 增補 `sentence_transformers` stub 以避免 mac 上載入 Torch。
- ✅ README 與 `.env.example` 等文件補齊雲端設定與 API Key 注意事項。
- ✅ 於 macOS venv 安裝 `requirements_mac.txt`、`requirements-test.txt` 後執行 `python -m pytest -q`；全部 599 項測試通過（含 2 個既有 skip）。 

### 1. 基礎建設
1. 建立 `utils/ollama_client.py`（或於 `gpt_utils.py`）
   - 封裝 POST 請求、header、payload、timeout
   - 支援：`generate(prompt, model, options)`、`chat(messages, model)`、錯誤回傳格式標準化
   - 遇到 401/403/5xx 時，記錄 log 並回傳具體錯誤給呼叫端
   - 參考官方呼叫範例：

```python
import os
from ollama import Client

client = Client(
    host="https://ollama.com",
    headers={'Authorization': 'Bearer ' + os.environ.get('OLLAMA_API_KEY')}
)

messages = [
  {
    'role': 'user',
    'content': 'Why is the sky blue?',
  },
]

for part in client.chat('gpt-oss:120b', messages=messages, stream=True):
  print(part['message']['content'], end='', flush=True)
```

   - 專案內可比照實作 HTTP 呼叫；注意需從 `.env` 讀取 `OLLAMA_API_KEY`，避免硬編碼敏感資訊。
2. 更新 `config_loader`，提供上述環境變數的 getter；缺值時可以選擇性 fallback 至 Power Automate，但不再呼叫本地 CLI。

### 2. 代理程式碼重構
1. **SQLAgent**
   - `_split_user_question`：改用 `ollama_client.generate`，payload 改為 prompt + system/context
   - `_generate_pandas_filter`：HTTP 呼叫/修復迴圈，內建錯誤重試
   - `_run_with_fallback` / `_summarize_sql_with_llm`：整合新的 HTTP 客戶端，支援 streaming 或 chunk 回傳
   - 清理 CLI-specific log（如 `subprocess` stderr）
2. **SemanticAgent**
   - `_run_with_fallback`、`_summarize_retrieved_kb` 先使用雲端 Ollama；僅在雲端 API 無法回應時再退回 Power Automate
   - Power Automate 失敗 → 回傳原資料（避免進一步 fallback 至本地 CLI）
3. **HybridQueryAgent**
   - `plan_pipeline`、`summarize_with_ai_builder`、`_run_with_fallback` 先呼叫雲端 Ollama；保留 Power Automate 作為次要備援
4. **gptChat.py**
   - 取代所有 `subprocess.run` (`ollama run`)；整合 conversation state, history, streaming (如需)
   - 更新 prompt 組裝流程，確保雲端 API 接受

### 3. 例外處理與落地細節
- 全域 timeout（例如 60 秒）可透過 `OLLAMA_TIMEOUT_SECONDS` 控制。
- 先行重試雲端 Ollama（可考慮指數退避），若多次失敗才嘗試 Power Automate。
- 明確處理雲端 API 回傳結構（`{response: str, error: ...}` 或 streaming token）。
- 在 mac 上無法連接雲端時，回傳友善錯誤；僅在必要時呼叫 Power Automate。

### 4. 測試調整
- Agents 單元測試改為 patch 新的 HTTP 客戶端函式，回傳假資料。
- 建立雲端錯誤情境測試（4xx/5xx → raise `RuntimeError` or custom exception）。
- Integration 測試 mock `requests.post` 以確保 deterministic。
- Power Automate 不需測試實際回覆（暫無有效 URL）；只需單元測試確認未設定時會跳過或回傳友善訊息。

### 5. 文件與設定
- 更新 `README.md`、`CLAUDE.md`、`docs/schedule` 相關說明
- 新增 `.env.example` 條目（包含 `OLLAMA_CLOUD_BASE_URL`、`OLLAMA_API_KEY` 等敏感設定），提醒務必透過 `.env` 管理 API key
- 若需全域快取，於 `gpt_utils` 說明雲端回應不快取 / how to

### 6. 後續觀察
- 建議於 Stage D 前共用 HTTP session / keep-alive
- 若需 streaming 回傳，再行評估 SSE / websockets

## 驗證計畫
1. `pytest tests/unit/agents -q`
2. `pytest tests/integration/test_api_routes.py -q`
3. 模擬雲端 4xx/5xx，確認錯誤訊息對使用者友善
4. 手動呼叫 gptChat 主流程（mock 雲端回應）確保輸出一致

## 風險 / 注意事項
- 雲端 API latency 不可控 → 需設定 timeout 與重試機制。
- 需確保 API Key/URL 未寫死；加於 `.env` 並透過 config loader。
- mac 無 pywin32：不影響本次變更，但須在文件中再次註記。
- 測試環境無法實際連雲端 → 必須全程 mock HTTP call。
- Power Automate 僅作為備援路徑，應在文件中註明優先順序。

## 未來延伸
- 規劃 Stage D 時同步建構 coverage summary (`tests/_artifacts/coverage_summary.md`)
- 若雲端 Ollama 提供 streaming，可再將 `_summarize_sql_with_llm`、`gptChat` 改為邊串流邊回傳
