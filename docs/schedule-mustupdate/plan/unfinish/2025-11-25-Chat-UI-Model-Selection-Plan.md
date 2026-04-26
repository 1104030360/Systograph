# Chat UI 模型選擇與 Fallback 狀態顯示 - 實作計畫

## 需求摘要

在現有 Chat UI 頁面上實作：

1. **Provider/Model 選擇 UI** - 三種來源類型（AI Builder / Cloud Ollama / Local Ollama）與對應模型選單
2. **即時 Fallback 狀態顯示** - 使用 SSE 串流顯示「正在嘗試 AI Builder... 失敗，切換到 Cloud Ollama...」

### 設計決策（已確認）

- Provider 選擇為「偏好」而非強制，失敗後仍自動 fallback
- 所有 Cloud Ollama 模型來自同一個 endpoint
- 需即時顯示切換過程（不只是最終結果）

---

## 一、架構概念與資料流

### 現有流程（同步）

```text
Frontend POST /api/v2/chat {query, chat_id, model}
    ↓
chat_routes.py → rag_service.query() → gptChat.run_offline_gpt()
    ↓
(Fallback 在後端內部發生，僅 log 到 console)
    ↓
Response: {answer, sources, chat_id} ← 無 provider/model 資訊
```

### 新流程（SSE 串流）

```text
Frontend GET /api/v2/chat/stream?query=...&preferred_provider=...&preferred_model=...

    ↓

chat_routes.py (新 SSE endpoint)

    ↓

SSE Stream (text/event-stream):
    event: status → {"provider": "ai_builder", "status": "trying"}
    event: status → {"provider": "ai_builder", "status": "failed"}
    event: status → {"provider": "cloud_ollama", "status": "trying"}
    event: status → {"provider": "cloud_ollama", "status": "success"}
    event: complete → {"answer": "...", "active_provider": "cloud_ollama", "active_model": "gpt-oss:120b"}
    ↓
Frontend 即時更新狀態指示器
```

---

## 二、前端 UI 設計

### 2.1 Provider/Model 選擇器

**位置**：取代現有 `chat.html` 第 84-91 行的 model selector

**設計模式**：兩層級聯下拉選單（Provider → Model）

```html
<div class="provider-model-selector">
  <!-- Provider 下拉選單 -->
  <div class="selector-group">
    <label class="selector-label">Provider</label>
    <select id="providerSelect" class="provider-select">
      <option value="auto">Auto (Fallback)</option>
      <option value="ai_builder">AI Builder</option>
      <option value="cloud_ollama">Cloud Ollama</option>
      <option value="local_ollama">Local Ollama</option>
    </select>
  </div>

  <!-- Model 下拉選單（依 provider 動態變化）-->
  <div class="selector-group">
    <label class="selector-label">Model</label>
    <select id="modelSelect" class="model-select">
      <!-- 根據 provider 動態填充 -->
    </select>
  </div>
</div>
```

### 2.2 各 Provider 的模型選項

```javascript
const PROVIDER_MODELS = {
  auto: [
    { value: 'auto', label: 'Auto-select (System Default)' }
  ],
  ai_builder: [
    { value: 'default', label: 'AI Builder Default' }
  ],
  cloud_ollama: [
    { value: 'gpt-oss:120b-cloud', label: 'GPT-OSS 120B (Recommended)' },
    { value: 'gpt-oss:20b-cloud', label: 'GPT-OSS 20B (Fast)' },
    { value: 'glm-4.6:cloud', label: 'GLM-4.6' },
    { value: 'deepseek-v3.1:671b-cloud', label: 'DeepSeek V3.1 671B' },
    { value: 'minimax-m2:cloud', label: 'MiniMax M2' },
    { value: 'kimi-k2:1t-cloud', label: 'Kimi K2 1T' },
    { value: 'gemini-3-pro-preview:latest', label: 'Gemini 3 Pro Preview' },
    { value: 'kimi-k2-thinking:cloud', label: 'Kimi K2 Thinking' },
    { value: 'cogito-2.1:671b-cloud', label: 'Cogito 2.1 671B' }
  ],
  local_ollama: [] // 動態從 Ollama API 取得
};

// 動態取得 Local Ollama 模型清單
async function fetchLocalOllamaModels() {
  try {
    const res = await fetch('/api/v2/local-ollama/models');
    const data = await res.json();
    return data.models.map(m => ({
      value: m.name,
      label: `${m.name} (${formatSize(m.size)})`
    }));
  } catch (e) {
    console.warn('Failed to fetch local models:', e);
    return [{ value: 'llama3.2:latest', label: 'Llama 3.2 (Default - Fallback)' }];
  }
};
```

### 2.3 Fallback 狀態列

```html
<div class="fallback-status-bar" id="fallbackStatusBar" style="display: none;">
  <div class="status-timeline">
    <div class="status-step" id="step-ai_builder">
      <span class="step-icon">●</span>
      <span class="step-label">AI Builder</span>
    </div>
    <div class="status-step" id="step-cloud_ollama">
      <span class="step-icon">●</span>
      <span class="step-label">Cloud Ollama</span>
    </div>
    <div class="status-step" id="step-local_ollama">
      <span class="step-icon">●</span>
      <span class="step-label">Local Ollama</span>
    </div>
  </div>
  <div class="status-message" id="statusMessage">Initializing...</div>
</div>
```

**CSS 狀態**：

- `.status-step.pending` - 灰色圓點，等待中
- `.status-step.trying` - 黃色圓點 + 脈衝動畫
- `.status-step.success` - 綠色圓點 + 勾號
- `.status-step.failed` - 紅色圓點 + 叉號
- `.status-step.skipped` - 灰色圓點，已跳過

---

## 三、前端狀態管理

### 3.1 狀態變數

```javascript
const ChatState = {
  // Provider/Model 選擇
  preferredProvider: 'auto',      // 'auto' | 'ai_builder' | 'cloud_ollama' | 'local_ollama'
  preferredModel: 'auto',         // 選擇的模型 ID

  // Fallback 狀態
  isStreaming: false,             // SSE 連線進行中
  fallbackChain: [],              // 已嘗試的 providers 陣列
  activeProvider: null,           // 最終成功的 provider
  activeModel: null,              // 最終使用的 model

  // EventSource 實例
  eventSource: null
};
```

### 3.2 狀態流程

1. **使用者選擇 provider** → 更新 `preferredProvider` → 刷新 model 下拉選單
2. **使用者選擇 model** → 更新 `preferredModel`
3. **使用者送出查詢**：

   - 設定 `isStreaming = true`
   - 顯示狀態列
   - 建立 EventSource 連線到 `/api/v2/chat/stream`

4. **收到 SSE 'status' 事件**：

   - 解析 provider, status, message
   - 更新對應步驟的 UI 狀態

5. **收到 SSE 'complete' 事件**：

   - 設定 `activeProvider`, `activeModel`
   - 渲染 bot 訊息（含 provider badge）
   - 關閉 EventSource

### 3.3 LocalStorage 持久化

```javascript
// 儲存偏好
localStorage.setItem('chat_preferred_provider', ChatState.preferredProvider);
localStorage.setItem('chat_preferred_model', ChatState.preferredModel);

// 載入偏好
ChatState.preferredProvider = localStorage.getItem('chat_preferred_provider') || 'auto';
```

---

## 四、後端 API 介面

### 4.1 新 SSE Endpoint

**路徑**: `GET /api/v2/chat/stream`

**Query Parameters**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| query | string | Yes | 使用者查詢 |
| chat_id | string | Yes | 對話 session ID |
| chat_title | string | No | 對話標題 |
| preferred_provider | string | No | 'auto' \| 'ai_builder' \| 'cloud_ollama' \| 'local_ollama' |
| preferred_model | string | No | 模型識別碼 |

### 4.2 SSE 事件格式

**status 事件**（fallback 過程中多次發送）:

```json
{
  "provider": "ai_builder",
  "status": "trying",
  "message": "Connecting to AI Builder..."
}
```

```json
{
  "provider": "ai_builder",
  "status": "failed",
  "message": "AI Builder failed: timeout after 120s"
}
```

**complete 事件**（請求完成時發送一次）:

```json
{
  "answer": "Based on the knowledge base...",
  "sources": [],
  "chat_id": "20251125_143022_abcd_chat",
  "active_provider": "cloud_ollama",
  "active_model": "gpt-oss:120b",
  "fallback_chain": [
    {"provider": "ai_builder", "status": "failed"},
    {"provider": "cloud_ollama", "status": "success"}
  ]
}
```

**error 事件**（發生錯誤時）:

```json
{
  "code": "ALL_PROVIDERS_FAILED",
  "message": "All AI providers unavailable"
}
```

### 4.3 後端修改點

1. **api/chat_routes.py** - 新增 SSE endpoint
2. **services/rag_service.py** - 新增 `query_with_status()` 方法，接受 `status_callback`
3. **gptChat.py** - 新增 `run_offline_gpt_with_status()`，在每個 fallback 階段呼叫 callback

---

## 五、實作步驟

### Phase 1: 後端基礎（優先）

| 步驟 | 檔案 | 說明 | 完成標準 |
|------|------|------|----------|
| 1.1 | `api/chat_routes.py` | 建立 SSE endpoint `/chat/stream` | curl 測試回傳有效 SSE 串流 |
| 1.2 | `api/chat_routes.py` | 新增 `/local-ollama/models` endpoint | 回傳本地已安裝的模型清單 |
| 1.3 | `services/rag_service.py` | 新增 `query_with_status()` | 方法接受 callback 並傳遞給 gptChat |
| 1.4 | `gptChat.py` | 新增 `run_offline_gpt_with_status()` | 在每個 fallback 階段發送狀態 |
| 1.5 | `gptChat.py` | 修改現有 fallback 函數支援 callback | 不影響原有行為（callback 可選） |

### Phase 2: 前端 UI 元件

| 步驟 | 檔案 | 說明 | 完成標準 |
|------|------|------|----------|
| 2.1 | `templates/chat.html` | 替換 model selector 為 provider/model UI | 兩個下拉選單正確渲染 |
| 2.2 | `static/js/chat_ui.js` | 新增 PROVIDER_MODELS 常數 | 切換 provider 時 model 選單正確更新 |
| 2.2b | `static/js/chat_ui.js` | 實作 `fetchLocalOllamaModels()` | 動態取得本地 Ollama 模型清單 |
| 2.3 | `static/js/chat_ui.js` | 新增 ChatState 物件 | 所有狀態變數正確初始化 |
| 2.4 | `static/css/chat_ui.css` | 新增選擇器樣式 | iOS Liquid Glass 風格與現有一致 |
| 2.5 | `templates/chat.html` | 新增 fallback 狀態列 HTML | 狀態列正確渲染 |
| 2.6 | `static/css/chat_ui.css` | 新增狀態列動畫 | trying 狀態有脈衝動畫 |

### Phase 3: SSE 整合

| 步驟 | 檔案 | 說明 | 完成標準 |
|------|------|------|----------|
| 3.1 | `static/js/chat_ui.js` | 建立 EventSource 連線處理 | SSE 成功連線 |
| 3.2 | `static/js/chat_ui.js` | 處理 'status' 事件 | UI 即時更新狀態 |
| 3.3 | `static/js/chat_ui.js` | 處理 'complete' 事件 | Bot 訊息顯示 provider badge |
| 3.4 | `static/js/chat_ui.js` | 處理 'error' 事件 | 錯誤 toast 顯示 |
| 3.5 | `static/js/chat_ui.js` | 連線清理邏輯 | 完成/錯誤時正確關閉 EventSource |

### Phase 4: Provider Badge 與收尾

| 步驟 | 檔案 | 說明 | 完成標準 |
|------|------|------|----------|
| 4.1 | `static/js/chat_ui.js` | Bot 訊息加上 provider badge | 顯示「Cloud Ollama / gpt-oss:120b」|
| 4.2 | `static/js/chat_ui.js` | LocalStorage 偏好保存/載入 | 重新整理後保留選擇 |
| 4.3 | `api/chat_routes.py` | 保持原 `/chat` endpoint 運作 | 向下相容 |

### Phase 5: 多步驟狀態支援（主流程）

| 步驟 | 檔案 | 說明 | 完成標準 |
|------|------|------|----------|
| 5.1 | `gptChat.py` | 修改 `_call_llm_with_status()` 加入 step 參數 | 函數接受 step/step_label |
| 5.2 | `gptChat.py` | 更新主流程 4 個 `_call_llm_with_status()` 呼叫 | 傳入 classification/rewrite/tool_select/final_answer |
| 5.3 | `api/chat_routes.py` | 更新 `status_callback` 簽名與 JSON 格式 | SSE 事件包含 step 欄位 |
| 5.4 | `templates/chat.html` | 替換狀態列為折疊式步驟容器 | HTML 結構支援動態步驟行 |
| 5.5 | `static/css/chat_ui.css` | 新增步驟行樣式 | 折疊/展開動畫、狀態顏色 |
| 5.6 | `static/js/chat_ui.js` | 新增 `StepState` 與相關函數 | `handleStatusEvent()` 正確處理 step 事件 |
| 5.7 | `static/js/chat_ui.js` | 實作 `createStepRow()`, `toggleStepDetail()` | 動態生成步驟行、展開收合 |

### Phase 6: Agent 內部狀態支援（完整展開）

| 步驟 | 檔案 | 說明 | 完成標準 |
|------|------|------|----------|
| 6.1 | `gptChat.py` | 修改 `autogen_dispatch()` 傳遞 callback 給 Agent | Agent 可接收 status_callback |
| 6.2 | `agents/sql_agent.py` | 修改 `handle()` 接受 status_callback | 7 個 LLM 呼叫點發送狀態 |
| 6.3 | `agents/sql_agent.py` | 修改 `_call_ollama_generate()` 支援 callback | 內部 LLM 呼叫發送 trying/success/failed |
| 6.4 | `agents/semantic_agent.py` | 修改 `handle()` 接受 status_callback | 5 個 LLM 呼叫點發送狀態 |
| 6.5 | `agents/semantic_agent.py` | 修改 `_run_with_fallback()` 支援 callback | fallback 過程發送狀態 |
| 6.6 | `agents/hybridquery_agent.py` | 修改 `handle()` 接受 status_callback | 6 個呼叫點發送狀態 |
| 6.7 | `agents/hybridquery_agent.py` | 傳遞 callback 給子 Agent | SQL/Semantic Agent 呼叫時繼續發送狀態 |

### Phase 7: 前端 UI 優化

| 步驟 | 檔案 | 說明 | 完成標準 |
|------|------|------|----------|
| 7.1 | `static/js/chat_ui.js` | 步驟分組顯示邏輯 | 主流程步驟與 Agent 步驟視覺區分 |
| 7.2 | `static/css/chat_ui.css` | 階層縮排樣式 | Agent 步驟縮排顯示 |
| 7.3 | `static/js/chat_ui.js` | 自動展開當前 Agent 區塊 | 進入 Agent 時自動展開 |
| 7.4 | `static/js/chat_ui.js` | 完成後自動收合 | 步驟完成後收合詳細資訊 |

---

## 六、測試情境

### Test 1: 正常流程 - Cloud Ollama 成功

- **設定**: AI Builder 未設定，Cloud Ollama 可用
- **操作**: 選擇 Auto，送出查詢
- **預期**:
  - 狀態列：AI Builder (紅) → Cloud Ollama (綠)
  - Bot 訊息 badge：「Cloud Ollama / gpt-oss:120b」

### Test 2: 偏好 Provider - 跳到 Local

- **設定**: 選擇 Local Ollama 作為偏好
- **操作**: 送出查詢
- **預期**:
  - 狀態列：直接嘗試 Local Ollama（跳過 AI Builder 和 Cloud）
  - Badge：「Local Ollama / llama3.2:latest」

### Test 3: 完整 Fallback 鏈

- **設定**: AI Builder timeout、Cloud 斷線、Local 可用
- **預期**:
  - 狀態列依序顯示三層嘗試
  - 最終使用 Local Ollama
  - Response 包含完整 fallback_chain

### Test 4: 所有 Provider 失敗

- **設定**: 所有 providers 不可用
- **預期**:
  - 三個步驟都顯示紅色失敗
  - Error toast：「所有 AI 服務暫時無法使用」

### Test 5: SSE 連線中斷

- **設定**: 請求進行中網路中斷
- **預期**:
  - 顯示連線錯誤 toast
  - 送出按鈕重新啟用
  - 狀態列清除

---

## 七、需修改的關鍵檔案

| 檔案 | 修改類型 | 說明 |
|------|----------|------|
| `api/chat_routes.py` | 新增 | SSE endpoint `/chat/stream` |
| `services/rag_service.py` | 修改 | 新增 `query_with_status()` 方法 |
| `gptChat.py` | 修改 | 新增 `run_offline_gpt_with_status()` |
| `templates/chat.html` | 修改 | Provider/model 選擇器 + 狀態列 |
| `static/js/chat_ui.js` | 修改 | EventSource、狀態管理、UI 更新邏輯 |
| `static/css/chat_ui.css` | 修改 | 選擇器樣式、狀態列動畫 |

---

## 八、已知問題與修正方案

### 問題 1: SSE Callback Generator 未執行（已修復）

**問題**: `status_callback` 使用 `yield` 但被同步呼叫，generator 從未被迭代。

**修復**: 使用 Queue + Thread 架構（已在 `api/chat_routes.py` 實作）

---

### 問題 2: 多次 LLM 呼叫導致重複 Fallback 狀態（待修復）

**問題**: `run_offline_gpt_with_status` 在一次查詢中呼叫 `_call_llm_with_status` 4-5 次：

1. RAG 判斷
2. 非 RAG 回答 或 改寫問題
3. 工具選擇
4. 最終回答

每次都觸發完整 fallback 嘗試，前端看到多組 `trying → failed → success` 循環。

**解決方案**: 加入 `step` 欄位區分不同階段，前端使用折疊式多行 UI

#### 新 SSE 事件格式

```json
{
  "step": "classification",
  "step_label": "判斷問題類型",
  "step_index": 1,
  "total_steps": 4,
  "provider": "cloud_ollama",
  "status": "trying",
  "message": "正在連線 Cloud Ollama..."
}
```

**Step 定義（完整版 - 10-15 步）**:

### 主流程步驟 (gptChat.py)

| step | step_label | 說明 |
|------|------------|------|
| `classification` | 判斷問題類型 | 判斷是否為 RAG 問題 |
| `rewrite` | 改寫問題 | 重新組織問題以利搜尋 |
| `tool_select` | 選擇工具 | 決定使用哪個 Agent |
| `final_answer` | 產生回答 | 生成最終答案 |

### SQL Agent 步驟 (agents/sql_agent.py)

| step | step_label | 說明 |
|------|------------|------|
| `sql.split_question` | 拆解問題 | 將問題分為 SQL 提示和分析提示 |
| `sql.generate_sql` | 生成 SQL | 產生 SQL 查詢語句（含重試） |
| `sql.generate_pandas` | 生成 Pandas | 產生 DataFrame 過濾代碼 |
| `sql.execute` | 執行查詢 | 執行 SQL/Pandas 查詢（非 LLM） |
| `sql.summarize` | 摘要結果 | 將查詢結果摘要為自然語言 |
| `sql.review` | 審查答案 | 審查答案品質 |
| `sql.summary_type` | 判斷摘要類型 | 決定返回原始數據或摘要 |

### Semantic Agent 步驟 (agents/semantic_agent.py)

| step | step_label | 說明 |
|------|------------|------|
| `semantic.determine_topk` | 決定搜尋數量 | 根據查詢複雜度決定 top_k |
| `semantic.vector_search` | 向量搜尋 | FAISS 相似度搜尋（非 LLM） |
| `semantic.filter` | 過濾不相關 | 過濾語義檢索結果 |
| `semantic.summarize` | 摘要結果 | 將檢索結果摘要 |
| `semantic.merge` | 合併摘要 | 遞歸合併多個摘要 |

### Hybrid Agent 步驟 (agents/hybridquery_agent.py)

| step | step_label | 說明 |
|------|------------|------|
| `hybrid.plan_pipeline` | 規劃管道 | 將查詢拆解為多步 pipeline |
| `hybrid.decompose` | 分解查詢 | 拆解複雜查詢為子問題 |
| `hybrid.execute_step` | 執行子步驟 | 呼叫 SQL 或 Semantic Agent |
| `hybrid.summarize` | 合併結果 | 提取關鍵發現與建議 |

#### 後端修改

**gptChat.py `_call_llm_with_status()`**:

```python
def _call_llm_with_status(
    prompt: str,
    preferred_provider: str = 'auto',
    preferred_model: str = None,
    status_callback=None,
    step: str = None,           # 新增
    step_label: str = None,     # 新增
    step_index: int = None,     # 新增
    total_steps: int = None     # 新增
) -> dict:
    def emit_status(provider, status, message):
        if status_callback:
            status_callback(
                provider=provider,
                status=status,
                message=message,
                step=step,
                step_label=step_label,
                step_index=step_index,
                total_steps=total_steps
            )
```

**gptChat.py `run_offline_gpt_with_status()` 呼叫範例**:

```python
# RAG 判斷
check_result = _call_llm_with_status(
    rag_check_prompt,
    preferred_provider,
    preferred_model,
    status_callback,
    step="classification",
    step_label="判斷問題類型",
    step_index=1,
    total_steps=4
)
```

**api/chat_routes.py `status_callback`**:

```python
def status_callback(provider, status, message, step=None, step_label=None, step_index=None, total_steps=None):
    event_data = json.dumps({
        'step': step,
        'step_label': step_label,
        'step_index': step_index,
        'total_steps': total_steps,
        'provider': provider,
        'status': status,
        'message': message
    }, ensure_ascii=False)
    event_queue.put(('status', event_data))
```

#### 前端修改

**templates/chat.html 新 HTML 結構**:

```html
<div class="fallback-status-bar" id="fallbackStatusBar" style="display: none;">
  <div class="steps-container" id="stepsContainer">
    <!-- 動態生成的步驟行 -->
  </div>
</div>
```

**每個步驟行（動態生成）**:

```html
<div class="step-row" id="step-classification" data-step="classification">
  <div class="step-header" onclick="toggleStepDetail('classification')">
    <span class="step-number">1/4</span>
    <span class="step-label">判斷問題類型</span>
    <span class="step-status-icon">●</span>
    <span class="step-expand-icon">▼</span>
  </div>
  <div class="step-detail collapsed">
    <div class="provider-status" data-provider="ai_builder">
      <span class="provider-icon">●</span>
      <span class="provider-name">AI Builder</span>
      <span class="provider-status-text">Failed</span>
    </div>
    <div class="provider-status" data-provider="cloud_ollama">
      <span class="provider-icon">●</span>
      <span class="provider-name">Cloud Ollama</span>
      <span class="provider-status-text">Success</span>
    </div>
  </div>
</div>
```

**CSS 狀態樣式**:

```css
.step-row { border-bottom: 1px solid rgba(255,255,255,0.1); }
.step-row.active { background: rgba(255,204,0,0.1); }
.step-row.success .step-status-icon { color: #34c759; }
.step-row.failed .step-status-icon { color: #ff3b30; }
.step-detail.collapsed { display: none; }
.step-detail.expanded { display: block; }
```

**JavaScript 狀態管理**:

```javascript
const StepState = {
  steps: {},  // { classification: { status: 'success', providers: {...} }, ... }
  currentStep: null
};

function handleStatusEvent(data) {
  const { step, step_label, step_index, total_steps, provider, status, message } = data;

  // 確保步驟行存在
  if (!StepState.steps[step]) {
    createStepRow(step, step_label, step_index, total_steps);
    StepState.steps[step] = { status: 'pending', providers: {} };
  }

  // 更新 provider 狀態
  StepState.steps[step].providers[provider] = status;
  updateProviderUI(step, provider, status);

  // 更新步驟整體狀態
  if (status === 'success') {
    StepState.steps[step].status = 'success';
    updateStepUI(step, 'success');
  } else if (status === 'failed' && allProvidersFailed(step)) {
    StepState.steps[step].status = 'failed';
    updateStepUI(step, 'failed');
  }

  // 標記當前活躍步驟
  setActiveStep(step);
}
```

---

## 九、風險與緩解

| 風險 | 影響 | 緩解方案 |
|------|------|----------|
| SSE 被代理/防火牆阻擋 | 狀態無法即時顯示 | 備用方案：fallback 到原有 POST endpoint |
| 長時間請求 SSE 斷線 | 使用者看不到結果 | 每 30 秒發送 heartbeat event |
| callback 影響現有流程 | RAG 功能異常 | callback 設為可選（None default）|
| 折疊式 UI 佔用過多空間 | 覆蓋聊天內容 | 預設收合，僅顯示步驟標題 |

---

## 十、實作記錄

### 2025-11-26: Phase 6.7, 6.8, 6.9 完成 ✅

**問題診斷**：

用戶反饋 Agent 內部狀態無法在前端 multi-step UI 正確顯示。經分析：

1. Agent 的 `_emit_step()` 呼叫缺少 `step_index` 和 `total_steps` 參數
2. 前端 `handleStatusEvent()` 檢查 `const hasStepInfo = step && step_index;`，沒有 `step_index` 就 fallback 到舊版 3-segment 顯示
3. Provider 名稱 "ollama" 在 `PROVIDER_LABELS` 中不存在，顯示原始字串

**選擇方案**：

- **方案 B（StepTracker 閉包）**：僅修改 `gptChat.py` 的 wrapper 函數，使用閉包在呼叫 Agent 前包裝 callback，自動注入 `step_index`/`total_steps`
- **前端加入 ollama label**：不在後端轉換 provider 名稱，直接在前端 `PROVIDER_LABELS` 加入 "ollama" 映射

#### Phase 6.8: 修改 StepTracker.next_step() 增加 step_name 參數

**檔案**: `gptChat.py:70-130`

**修改內容**:

1. 新增 `_last_step_name` 屬性追蹤上一個步驟名稱
2. `next_step(step_name)` 接受可選 step 名稱參數，防止同一步驟 trying → success 重複計數
3. `reset()` 同步重置 `_last_step_name`

```python
class StepTracker:
    def __init__(self, initial_total: int = 4):
        self.current_index = 0
        self.estimated_total = initial_total
        self.agent_base_index = 0
        self._last_step_name = None  # 新增

    def next_step(self, step_name: str = None) -> tuple:
        """
        Args:
            step_name: 可選步驟識別碼，避免同一步驟重複計數
        """
        # 避免同一步驟重複計數 (trying → success)
        if step_name and step_name == self._last_step_name:
            return self.current_index, self.estimated_total

        self._last_step_name = step_name
        self.current_index += 1
        return self.current_index, self.estimated_total

    def reset(self):
        self.current_index = 0
        self.estimated_total = 4
        self.agent_base_index = 0
        self._last_step_name = None  # 新增
```

#### Phase 6.7: 修改 3 個 wrapper 函數加入 wrapped_callback

**檔案**: `gptChat.py:170-321`

**修改內容**:

為 `semantic_agent_handle()`、`sql_agent_handle()`、`HybridQuery_agent_handle()` 加入 `wrapped_callback` 閉包：

```python
def semantic_agent_handle(message: str) -> str:
    print(f"🟦 semantic_agent_handle called with message: {message}")
    status_callback = get_status_callback_context()
    tracker = get_step_tracker()
    tracker.enter_agent("semantic", 2)  # Semantic 有 ~2 步

    # Phase 6.7: 建立 wrapped_callback 注入 step_index/total_steps
    def wrapped_callback(provider, status, msg, step=None, step_label=None, **kwargs):
        if status_callback:
            idx, total = tracker.next_step(step)  # 傳入 step 防止重複計數
            status_callback(
                provider=provider,
                status=status,
                message=msg,
                step=step,
                step_label=step_label,
                step_index=idx,
                total_steps=total
            )

    result = semantic_agent.handle(message, status_callback=wrapped_callback)
    # ...
```

同樣模式套用到 `sql_agent_handle()` 和 `HybridQuery_agent_handle()`。

#### Phase 6.9: 前端 PROVIDER_LABELS 加入 ollama

**檔案**: `static/js/chat_ui.js:355-360`

**修改內容**:

```javascript
const PROVIDER_LABELS = {
  ai_builder: 'AI Builder',
  cloud_ollama: 'Cloud Ollama',
  local_ollama: 'Local Ollama',
  ollama: 'Ollama'  // 新增：Generic fallback for agents using "ollama" as provider
};
```

#### 行為變化

| 修改前 | 修改後 |
|--------|--------|
| Agent `_emit_step()` 只發送 step/step_label，無 step_index | wrapped_callback 自動注入 step_index/total_steps |
| 前端 `hasStepInfo` 為 false，使用舊版 3-segment UI | `hasStepInfo` 為 true，啟用 multi-step 折疊式 UI |
| Provider "ollama" 顯示原始字串 | 顯示為 "Ollama" |
| 同一步驟 trying → success 計為 2 步 | next_step(step) 識別同步驟，只計 1 步 |

#### 驗證

```bash
python -m py_compile gptChat.py
# ✅ 語法檢查通過
```

#### 待測試項目

1. 發送查詢，觀察 Agent 步驟是否正確顯示 step_index
2. 確認 multi-step UI 啟用縮排顯示
3. 確認 "ollama" 顯示為 "Ollama"
4. 確認同一步驟 trying → success 不會重複計數

---

### 2025-11-26: error_step 傳遞修正 ✅

**問題**：`run_offline_gpt_with_status` 回傳值未附帶 `error_step`，SSE complete 事件永遠是 `error_step=None`。

**檔案**: `gptChat.py:1267-1272, 1379-1394`

**修改內容**:

兩個 return 點都加入 `error_step` 傳遞：

```python
# 非 RAG 分支 (line 1267-1272)
return {
    "answer": result.get("response", "⚠️ 沒有收到模型回應。"),
    "active_provider": result.get("active_provider"),
    "active_model": result.get("active_model"),
    "error_step": result.get("error_step")  # 新增
}

# RAG 分支 (line 1389-1394)
error_step = final_result.get("error_step")  # 新增
return {
    "answer": reply,
    "active_provider": active_provider,
    "active_model": active_model,
    "error_step": error_step  # 新增
}
```

**資料流**:

```text
_call_llm_with_status (失敗時回傳 error_step)
    ↓
run_offline_gpt_with_status (傳遞 error_step)
    ↓
RAGService.query_with_status (透傳 result)
    ↓
chat_routes.py SSE complete 事件 (包含 error_step)
    ↓
前端 handleCompleteEvent (顯示「步驟 X 所有服務均失敗」)
```

**驗證**:

```bash
python -m py_compile gptChat.py
# ✅ 語法檢查通過
```

---

### 2025-11-26: wrapped_callback 參數名稱修正 ✅

**問題**：Agent 內部步驟沒有顯示在 UI，只看到主流程 4 步。

**根因**：`wrapped_callback` 參數名稱與 Agent `_emit_step` 傳入的關鍵字參數不匹配。

| Agent 傳入 | wrapped_callback 原本 |
|------------|----------------------|
| `message=...` | `msg` |

**修正**：

```python
# 修正前
def wrapped_callback(provider, status, msg, step=None, step_label=None, **kwargs):

# 修正後 - 使用關鍵字參數預設值
def wrapped_callback(provider=None, status=None, message=None, step=None, step_label=None, **kwargs):
```

**影響檔案**: `gptChat.py:199, 251, 305`（三個 wrapper 函數）

**修正後行為**：

```
主流程 4 步 + Agent 內部步驟（動態擴展）

例如 SQL Agent：
✓ 1/10  判斷問題類型
✓ 2/10  改寫問題
✓ 3/10  選擇工具 → SQLAgent
◐ 4/10  sql.split_question - 拆解問題    ← Agent 內部步驟
○ 5/10  sql.generate_sql - 生成 SQL
○ 6/10  sql.execute - 執行查詢
...
○ 10/10 產生回答
```

---

### 2025-11-26: 階層式子步驟顯示 (Phase 6.8 Enhancement) ✅

**問題診斷**：

用戶反饋步驟顯示順序混亂，主流程步驟 (1/4, 2/4, 3/4, 4/4) 與 Agent 內部步驟 (1/7, 2/7...) 交錯顯示：

```
判斷問題類型 1/4 ✓
拆解問題 1/7 ✓          ← Agent 步驟夾在中間
改寫問題 2/4 ✓
生成 SQL 2/7 ✓          ← 順序混亂
選擇工具 3/4 ✓
...
```

**根本原因**：
1. 主流程使用**硬編碼** `step_index=1,2,3,4`（不使用 StepTracker）
2. Agent 流程使用 `StepTracker.next_step()` 從 0 開始計數
3. 兩套完全獨立的計數系統，前端按 `step_index` 排序導致交錯

**用戶選擇**：巢狀子步驟顯示（Agent 步驟作為主流程「選擇工具」步驟的子項目）

#### 後端修改

**1. gptChat.py - 3 個 wrapper 函數新增 parent_step 和 is_substep**

**檔案**: `gptChat.py:215-230, 270-285, 327-342`

```python
# semantic_agent_handle, sql_agent_handle, HybridQuery_agent_handle
def wrapped_callback(provider=None, status=None, message=None, step=None, step_label=None, **kwargs):
    if status_callback:
        idx, total = tracker.next_step(step)
        status_callback(
            provider=provider,
            status=status,
            message=message,
            step=step,
            step_label=step_label,
            step_index=idx,
            total_steps=total,
            parent_step="tool_select",  # 🆕 Agent 步驟是「選擇工具」的子項目
            is_substep=True             # 🆕 標記為子步驟
        )
```

**2. api/chat_routes.py - status_callback 新增參數**

**檔案**: `api/chat_routes.py:231-285`

```python
def status_callback(
    provider: str,
    status: str,
    message: str,
    step: str = None,
    step_label: str = None,
    step_index: int = None,
    total_steps: int = None,
    parent_step: str = None,      # 🆕
    is_substep: bool = False      # 🆕
):
    event_data = json.dumps({
        'step': step,
        'step_label': step_label,
        'step_index': step_index,
        'total_steps': total_steps,
        'provider': provider,
        'status': status,
        'message': message,
        'parent_step': parent_step,   # 🆕
        'is_substep': is_substep      # 🆕
    }, ensure_ascii=False)
    event_queue.put(('status', event_data))
```

#### 前端修改

**3. static/js/chat_ui.js - StepState 擴展支援階層追蹤**

**新增屬性**:
- `parentStep`: 父步驟 ID
- `isSubstep`: 是否為子步驟
- `substeps`: 子步驟 ID 陣列
- `substepIndex`: 子步驟在父級內的索引
- `mainFlowTotalSteps`: 主流程總步數（固定為 4）

**新增方法**:
- `areAllSubstepsComplete(parentStepId)`: 檢查父步驟的所有子步驟是否完成

**4. static/js/chat_ui.js - handleStatusEvent 更新**

```javascript
function handleStatusEvent(data) {
  const { step, step_label, step_index, total_steps, provider, status, message, parent_step, is_substep } = data;

  // 傳遞 parent_step 和 is_substep 給 StepState
  const stepData = StepState.updateStep(
    step, step_label, step_index, total_steps, provider, status, message, parent_step, is_substep
  );

  // 如果是子步驟，也更新父步驟以刷新子步驟數量
  if (is_substep && parent_step) {
    const parentData = StepState.getStep(parent_step);
    queueStepUIUpdate(parent_step, parentData);
  }
}
```

**5. static/js/chat_ui.js - createStepRow 支援子步驟樣式**

```javascript
function createStepRow(stepId, stepData) {
  const substepClass = stepData.isSubstep ? 'substep' : '';
  row.className = `step-row ${stepData.status} ${substepClass}`;
  row.dataset.isSubstep = stepData.isSubstep ? 'true' : 'false';
  row.dataset.parentStep = stepData.parentStep || '';

  // 子步驟顯示樹狀前綴
  const substepPrefix = stepData.isSubstep ? '<span class="substep-prefix">├</span>' : '';

  // 父步驟顯示子步驟數量
  const substepCountHtml = hasSubsteps
    ? `<span class="substep-count">(${stepData.substeps.length} 子步驟)</span>`
    : '';
}
```

**6. static/js/chat_ui.js - 新增階層式插入函數**

- `insertMainStepRow()`: 主步驟按 index 排序插入
- `insertSubstepRow()`: 子步驟插入到父步驟下方

**7. static/css/chat_ui.css - 子步驟樣式（~120 行）**

```css
/* 子步驟縮排與邊框 */
.step-row.substep {
  margin-left: 1.5rem;
  border-left: 2px solid rgba(0, 122, 255, 0.3);
  background: rgba(118, 118, 128, 0.03);
}

/* 樹狀連接符 */
.substep-prefix {
  font-size: 0.8rem;
  color: rgba(0, 122, 255, 0.5);
}

/* 子步驟數量標籤 */
.substep-count {
  font-size: 0.6rem;
  color: var(--ios-blue);
  background: rgba(0, 122, 255, 0.08);
  border-radius: 4px;
}

/* 子步驟狀態顏色 */
.step-row.substep.active { border-left-color: rgba(255, 204, 0, 0.6); }
.step-row.substep.success { border-left-color: rgba(52, 199, 89, 0.5); }
.step-row.substep.failed { border-left-color: rgba(255, 59, 48, 0.5); }

/* 深色模式支援 */
[data-theme="dark"] .step-row.substep { ... }
```

#### 修正後顯示效果

```
判斷問題類型 1/4 ✓
改寫問題 2/4 ✓
選擇工具 3/4 ◐ (5 子步驟)
  ├ 拆解問題 1/5 ✓
  ├ 生成 SQL 2/5 ✓
  ├ 決定摘要類型 3/5 ✓
  ├ 摘要結果 4/5 ◐
  └ 審查答案 5/5
產生回答 4/4
```

**關鍵改進**：
- 主流程維持 1/4, 2/4, 3/4, 4/4 編號
- Agent 子步驟巢狀在步驟 3（選擇工具）下方
- 子步驟使用獨立編號 1/n, 2/n...
- 父步驟顯示子步驟數量標籤
- 子步驟視覺縮排並以藍色邊框區分

#### 驗證

```bash
python -m py_compile gptChat.py && python -m py_compile api/chat_routes.py
# ✅ Python 語法檢查通過

wc -l static/js/chat_ui.js static/css/chat_ui.css
# 1485 static/js/chat_ui.js (+190 行)
# 1522 static/css/chat_ui.css (+120 行)
```

#### 檔案變更摘要

| 檔案 | 變更行數 | 說明 |
|------|----------|------|
| `gptChat.py` | +6 行 | 3 個 wrapper 新增 parent_step/is_substep |
| `api/chat_routes.py` | +8 行 | status_callback 新增參數與 JSON 欄位 |
| `static/js/chat_ui.js` | +190 行 | StepState 擴展、階層插入邏輯 |
| `static/css/chat_ui.css` | +120 行 | 子步驟縮排、樹狀前綴、狀態顏色 |
