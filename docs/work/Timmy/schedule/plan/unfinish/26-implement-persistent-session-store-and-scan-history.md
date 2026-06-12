# Task 26: Implement Persistent Session Store and Scan History

## 最新狀態校正（2026-06-12）

- 程式碼現況：`create_app()` 仍以 `InMemorySessionStore` 組裝 local API；未看到 persistent session/history routes、restart reload、retention cleanup、storage config、SQLite/DB repository 或 scan history service。artifact 仍以目前 map build/output artifact 為主要 truth。
- 判斷：本任務尚未完成，但不是 EPIC1 核心閉環的必要條件。EPIC1 若以單機、單次 scan、即時 viewer / report 為完成標準，in-memory session 可以接受。
- 近期處置：保留在 `unfinish`，建議從 EPIC1 minimum viable scope 延後到 EPIC2 或 post-EPIC1 品質/產品化階段。若採用 DB-backed storage，應先完成 Task 27 再回頭接 scan history。
- EPIC1 邊界：EPIC1 收尾前只需要確保 scan 結果 artifact 可讀、API response 不洩漏 secret、前端能載入最新 scan map；不需要 process restart 後的完整 history。

## 目標
實作 persistent session store 與 scan history，讓 local web API 在 process restart 後仍能查詢 project import、scan result、artifact path、status history。若未來需要 multi-user，必須在本任務定義隔離、retention、masking 與 migration 規則。

## 為什麼要獨立做這個
Task 16 只需要 in-memory session shell 來打通 API contract。持久化 session 會引入資料庫/檔案儲存、schema migration、artifact retention、敏感資料遮罩、使用者隔離、history cleanup 等產品與隱私決策，不應阻塞 L1 map build。

## 承接 Task 16 延後功能
- 承接 Task 16 「不做 persistent multi-user session store / scan history」的延後範圍。
- Task 16 的 in-memory `project_id` / `scan_id` 只用於 MVP API flow；本任務才把它變成 process restart 後仍可查的 persistent history。
- 若 Task 25 已支援 upload，本任務可以保存 upload metadata，但不得保存 raw source code 或 unmasked secret。
- Multi-user 只能在有 namespace / isolation / retention 規則後宣稱支援；否則只能標註 local-only single-user。

## 前置需求
- Task 16 已完成 `project_id`、`scan_id`、basic status API shape。
- Task 19 已有 KAI-Mind-managed store pattern。
- Task 23 已完成 logging/snapshot secret safety hardening。
- Task 25 若要保存 uploaded project metadata，需先完成 upload ingestion safety。

## 實作範圍
- 建立 `SessionStore` model 與 repository/provider。
- 支援 project import records：`project_id`、source type、safe display name、created_at、last_scan_id。
- 支援 scan records：`scan_id`、project_id、status、started_at、completed_at、artifact paths、error summary。
- 支援 artifact retention policy：保留最新 N 次或依天數清理。
- 支援 process restart 後讀回 session/scan history。
- 支援 local-only single-user 預設；若要 multi-user，必須先有 user/session namespace，不可混用 artifact。
- 建立 FastAPI history routes，例如 `GET /api/projects`、`GET /api/projects/{project_id}`、`GET /api/scans/{scan_id}`。
- 更新 API guide，記錄 persistence、retention、masking、migration 規則。

## 不包含範圍
- 不做 cloud sync。
- 不做 team sharing。
- 不做 authentication provider。
- 不保存 raw source code、raw query、full secret。
- 不改 `ai-system-map/v1` canonical schema 來塞 session metadata。
- 不讓 persistent store 成為 scanner source of truth；scanner truth 仍是 validated map artifact。

## 建議實作步驟
1. 建立 `src/kai_mind/core/models/session.py`。
2. 建立 `src/kai_mind/config/session_store.py` 或等價 provider，預設使用 OS app data directory，測試可注入 temp path。
3. 選擇 JSONL / SQLite / small local database；若選 SQLite，需寫 schema version 與 migration policy。
4. 實作 create/list/get/update project record。
5. 實作 create/list/get/update scan record。
6. 將 Task 16 in-memory session shell 替換為 persistent repository adapter。
7. 實作 retention cleanup，避免 artifact 無限成長。
8. 建立 history routes。
9. 更新 API guide。
10. 寫測試：restart reload、artifact path masking、retention cleanup、invalid project/scan id rejected、不同 namespace 不互相讀取。

## 預期輸出
- `src/kai_mind/core/models/session.py`
- `src/kai_mind/config/session_store.py`
- `src/kai_mind/core/services/session_history_service.py`
- `src/kai_mind/web/routes/history_routes.py`
- 更新 `docs/work/Timmy/design/epic1-local-api-guide.md`
- `tests/unit/core/test_session_history_service.py`
- `tests/web/test_history_routes.py`

## 驗收標準
- process restart 後可查詢過去 project import 與 scan status。
- `scan_id` 可查到 artifact paths，但 response 不含 raw secret 或 raw source content。
- retention policy 可清理過期 artifact/history。
- store root 可在測試注入，不寫真實 user home。
- local API route 只透過 session service，不直接讀寫 store files。
- API guide 已同步記錄 persistence mode、retention、multi-user 限制、migration rule。

## 可能風險與注意事項
- 如果沒有身份隔離，不要宣稱支援真正 multi-user production。
- Scan history 很容易變成 sensitive metadata；path、query、error summary 都要遮罩或限制。
- 不要把 session store 當 canonical map schema 的一部分。
- 若選 SQLite，migration 必須測試；若選 JSON/JSONL，concurrent write 必須有明確限制。

## 新手提示
Task 16 的 in-memory session 像暫存便條紙，重開服務就沒了。Persistent session store 是正式的紀錄本，所以要先想清楚保存多久、保存什麼、誰可以看。

## 視覺化說明
```text
┌──────────────────────┐
│ Project import        │
│ Scan request          │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ SessionHistoryService │
└──────┬────────┬──────┘
       │        │
       ↓        ↓
┌──────────────┐ ┌──────────────────────┐
│ Project      │ │ Scan record           │
│ records      │ │ status/artifacts      │
└──────┬───────┘ └──────────┬───────────┘
       └──────────┬─────────┘
                  ↓
┌──────────────────────┐
│ Persistent store      │
│ + retention cleanup   │
└──────────────────────┘
```
