# Future: Page-Aware RAG Product Assistant

## 最新狀態（2026-06-12）

目前前端已經有 `ChatPanel` UI，但它仍是 placeholder：

- drawer 標題是 `Local model`。
- input disabled。
- 文案寫明「Waiting for local model API」與「selected node and scan context can be sent here」。
- 尚未有正式 assistant API、RAG retrieval、page context collector 或 tool/action confirmation flow。

因此本任務要把現有 AI 入口升級成 page-aware RAG product assistant。它不是 EPIC1 收尾必做，應放在 future / EPIC2 產品助理方向。

## 目標

讓使用者在 KAI-Mind viewer 裡遇到名詞不懂、圖上節點/邊不懂、或不知道下一步怎麼操作時，可以直接問頁面上的 AI assistant。

Assistant 必須能理解目前使用者所在頁面，例如：

- 目前是 sample mode 或 API mode。
- 目前選到哪個 node / edge / trace step。
- 目前開的是 overview、L2 component detail、L3 code path、mapping proposal 或 boundary decision UI。
- 目前 scan 狀態、filter、selected project、latest map summary。
- 目前 UI 可以執行哪些安全操作。

## 為什麼不是 EPIC1 必做

EPIC1 的 minimum viable scope 是讓使用者可以完成：

```text
project import
  -> scan
  -> boundary decision
  -> map viewer
  -> proposal/detail scan 基本互動
```

Page-aware assistant 是體驗加值與產品化能力。它需要 RAG corpus、assistant API、頁面 context 壓縮、隱私邊界、動作確認與測試，若塞進 EPIC1 會干擾核心閉環收尾。

## 建議產品分期

### Phase 1：Explain-only assistant

只回答與目前頁面相關的解釋問題，不替使用者操作產品。

可回答：

- 「這個 node 是什麼？」
- 「embedding model 是什麼意思？」
- 「為什麼這個元件被標成 unmapped？」
- 「我現在要怎麼處理 boundary decision？」
- 「L2 component detail 和 L3 code path 差在哪？」
- 「這個 risk hint 代表什麼？」

不可做：

- 不自動開始 scan。
- 不自動接受 mapping proposal。
- 不自動執行 query trace。
- 不讀 raw source file。
- 不顯示 raw secret 或完整本機絕對路徑。

### Phase 2：Guided action suggestions

Assistant 可以回傳「建議操作」，但只是一個 suggestion，不直接執行。

範例：

```json
{
  "answer": "你現在選到的是未對應元件，下一步可以先產生 mapping proposal。",
  "suggested_actions": [
    {
      "type": "open_panel",
      "label": "切到 Mapping Proposal",
      "target": "mapping_proposal"
    },
    {
      "type": "request_confirmation",
      "label": "產生 proposal",
      "requires_user_confirmation": true
    }
  ]
}
```

前端可以把 suggestion 呈現成按鈕，但按下後仍要進入原本的正式 UI flow。

### Phase 3：Confirmed product actions

只有在使用者明確確認後，assistant 才能幫忙觸發產品操作。

可考慮支援：

- focus node / edge。
- 切換 detail tab。
- 開啟 boundary decision modal。
- 觸發 detail scan。
- 建立 mapping proposal。
- 送出 query trace request。

高風險或會改變狀態的操作必須二次確認：

- 開始 project scan。
- 送出 boundary decisions。
- accept / edit / reject mapping proposal。
- 執行 query trace。

## 建議架構

```text
Frontend ChatPanel
  -> collect page context
  -> POST /api/assistant/messages
       user question
       page context summary
       selected node/edge/trace ids
       project_id / scan_id if available
       allowed capabilities
  -> Assistant service
       retrieve product docs + API contract + map summary
       generate answer + suggested actions
  -> Frontend renders answer
       suggestions require normal UI confirmation
```

## Page Context Collector

前端應建立明確的 page context payload，不要把整份 DOM 或整份 `ai_system_map` 直接丟給模型。

建議欄位：

- `route_or_view`: 目前頁面或主要 view。
- `data_source_mode`: `sample` / `api`。
- `project_id`: 若存在。
- `scan_id`: 若存在。
- `selected`: node / edge / trace target id。
- `detail_mode`: overview / component / code_path。
- `active_filters`: filter ids。
- `scan_summary`: status、counts、warnings summary。
- `visible_panel`: sidebar / detail / boundary_modal / chat。
- `available_actions`: 前端目前允許 assistant 建議的 action。
- `redacted_context`: 已遮罩的 label、slot、risk title、evidence title。

不可放入：

- raw secret。
- raw source file content。
- 完整 `.env`、token、private key。
- 未遮罩的本機絕對路徑。
- 使用者未同意的 runtime query。

## RAG 來源

第一版 RAG corpus 建議只放產品與目前 map 的安全摘要：

- `docs/work/Meeting-Sync/frontend_sync_2026_06_12.md`
- `frontend/API_CONTRACT.md`
- `docs/API-GUIDE.md`
- viewer UI 操作說明摘要。
- `graph_view_model` 的 node/edge labels、types、slots、risk titles、evidence titles。
- `ai_system_map.scan_summary` 與已遮罩 evidence metadata。

暫不放：

- raw project source code。
- raw snippets。
- raw local path。
- unmasked provider config。

## 後端 API 草案

```http
POST /api/assistant/messages
Content-Type: application/json
```

Request:

```json
{
  "project_id": "project:...",
  "scan_id": "scan:...",
  "message": "這個 unmapped 是什麼意思？",
  "page_context": {
    "data_source_mode": "api",
    "selected": {
      "kind": "node",
      "id": "node:unmapped:..."
    },
    "detail_mode": "overview",
    "available_actions": ["focus_node", "open_detail_panel", "create_mapping_proposal"]
  }
}
```

Response:

```json
{
  "answer": "unmapped 代表 scanner 找到一個可能重要的程式區塊，但還不能安全映射到 rag-core-v1 的固定 slot。",
  "citations": [
    {
      "source_type": "product_doc",
      "title": "Frontend sync",
      "locator": "mapping proposal"
    }
  ],
  "suggested_actions": [
    {
      "type": "open_detail_panel",
      "label": "看這個元件的 evidence",
      "requires_user_confirmation": false
    }
  ],
  "safety_notes": []
}
```

## 前端實作範圍

- 將 `ChatPanel` 從 disabled placeholder 改成可送訊息。
- 新增 assistant message state：messages、loading、error、citations、suggested actions。
- 建立 `collectPageContext()`，從 viewer store 與目前 payload 產生最小必要 context。
- 建立 assistant API client。
- 在回答中顯示 citations / source labels，避免看起來像無根據聊天。
- Suggested action 只呼叫現有 UI handler，不直接繞過正式產品流程。
- 所有會改變資料或觸發 runtime call 的 action 都要顯示確認。

## 後端實作範圍

- 建立 assistant request/response schemas。
- 建立 RAG corpus builder：產品 docs + API guide + map summary。
- 建立 retriever：先 deterministic keyword / section retrieval，再接 embedding/vector store。
- 建立 assistant generation service，可先用 local model 或既有 LLM provider adapter。
- 建立 safety filter：禁止 raw secret、raw path、raw source、未授權操作。
- 建立 route：`POST /api/assistant/messages`。
- 建立 tests：context redaction、citation presence、suggested action allowlist、dangerous action requires confirmation。

## 不包含範圍

- 不做通用 chatbot。
- 不替使用者直接修改專案程式碼。
- 不讓 assistant 自己掃 filesystem。
- 不讓 assistant 自動執行 backend tool 或 runtime trace。
- 不把 assistant 回答寫回 canonical `ai_system_map.json`。
- 不用 assistant 產生 scanner facts；scanner truth 仍來自 deterministic providers + validated artifact。

## 驗收標準

- 使用者可以在 ChatPanel 問目前頁面上的名詞，assistant 能根據 page context 回答。
- 回答至少包含來源或依據標籤，不能只有無引用的泛用回答。
- 選到 node/edge 時，assistant 能說明該元素的 slot、type、risk/evidence 摘要。
- 使用者問「下一步怎麼做」時，assistant 能給操作建議，但不直接改資料。
- 任何 scan、trace、mapping decision 類 action 都必須使用者確認。
- 不會把 raw secret、raw local path、raw source code 放進 prompt、logs 或 response。

## 與其他任務關係

- 依賴 `24b`：需要正式 project/scan workflow，assistant 才能知道目前 project/scan context。
- 依賴 `20a` / `21a`：assistant 的 suggested action 應該接到正式 proposal/detail UI，而不是自建旁路。
- 可受益於 `28`：若有 OpenAPI generated client，assistant suggested actions 的 typed contract 會更穩。
- 可受益於 `27`：未來若要做長期 assistant memory 或 embedding index，需要 DB/vector storage；第一版不需要。
