# Audit A — web 基礎設施層現況稽核（READ-ONLY）

**分區**：`src/kai_mind/web/app.py`、`middleware.py`、`session_store.py`、`web/__init__.py`、`web/routes/__init__.py`
**日期**：2026-07-27　**Repo 未被修改**（`git status` 與稽核前一致）

## 與 Plan 1 的關係

`docs/work/Timmy/schedule/plan/unfinish/phase2.5/1.md` 已完整涵蓋：
- `create_app()` 138-237 行的服務組裝 → `web/app_services.py` 的 `AppServices` + `build_app_services()`
- `app.state` 是 mypy 盲區、`dependencies.py` 17 個 `cast()`
- `shared_scanner` 注入時失去共用、`elif` 分支讀參數而非組好的服務（Plan 1 明列為「刻意不做」）

以上一律 **[已被 Plan 1 涵蓋]**，本報告不展開。下面 15 條全部是 Plan 1 之外的問題。

**需要特別提醒主 agent 的一點**：Plan 1 Task 1 Step 4 把 `nvidia_nim_provider_from_env(env_file=env_file or Path(".env"))` 原封不動搬進 `build_app_services()`，所以 A-9 / A-10 這兩條在 Plan 1 執行完之後**依然存在**，只是換了檔案位置。

---

## 實測環境

```
uv 專案 .venv、Python 3.11、FastAPI + Starlette
量測腳本置於 scratchpad/exp/（不在 repo 內）
```

實測得到的真實 ASGI stack（`probe_stack2.py`，強制 `TestClient` 建好 middleware_stack 後逐層印出 `.app`）：

```
CORSMiddleware          <- create_app() 手動包的最外層
  -> ServerErrorMiddleware
  -> RequestSizeLimitMiddleware
  -> SafeUnhandledExceptionMiddleware
  -> ExceptionMiddleware
  -> AsyncExitStackMiddleware
  -> APIRouter
```

這張圖是後面 A-1 / A-2 / A-7 / A-8 的共同前提。

---

### A-1. `RequestSizeLimitMiddleware` 遇到 `http.disconnect` 會無窮迴圈，並且完全餓死 event loop

- **位置**：`src/kai_mind/web/middleware.py:47-68`

- **現況**

```python
        buffered: list[Message] = []
        total_bytes = 0
        while True:
            message = await receive()
            buffered.append(message)
            if message["type"] != "http.request":
                continue
            total_bytes += len(message.get("body", b""))
```

- **為什麼是問題**

  ASGI 規範下，client 斷線後 server 的 `receive()` 會**持續**回傳 `{"type": "http.disconnect"}`。uvicorn 的 `RequestResponseCycle.receive()` 在 `self.disconnected` 為真時是直接 `return message`，**沒有任何 await**。這個 `while True` 只在 `message["type"] == "http.request"` 且 `more_body` 為 False 時才 `break`（第 64-65 行），`http.disconnect` 走 `continue`（第 52-53 行）→ 永遠不會離開迴圈。

  兩個後果：(a) `buffered` 無上限成長 → 記憶體耗盡；(b) 因為 `await receive()` 是一個不 yield 的 coroutine，整個 asyncio event loop 被卡死 → **整台 local API 停止回應**，不只是這一條 request。

  這違反 `AGENTS.md` 的 release-readiness / 可用性關注點，也是唯一一條「單一 client 按下 Ctrl+C 就能弄垮 server」的路徑。

  實測（`scratchpad/exp/probe_disconnect2.py`，把 `receive()` 換成永遠回 `http.disconnect` 的 fake）：

```
$ uv run python .../probe_disconnect2.py
receive() called 200001 times without ever exiting the loop
watchdog done? False  (False => event loop starved)
buffered list would hold 200001 messages -> unbounded growth
```

  `watchdog` 是一個只做 `await asyncio.sleep(0)` 的 task，它從頭到尾沒被排到 → 證明 event loop 真的被餓死。
  另外先跑的 `probe_disconnect.py` 用 `asyncio.wait_for(..., timeout=2.0)` 包住，**timeout 也觸發不了**（指令被 harness 以 120s 超時移到背景），這本身就是「迴圈不 yield」的第二個證據。

- **建議改法**

  `src/kai_mind/web/middleware.py`，`RequestSizeLimitMiddleware.__call__`：

  1. 迴圈內加終止條件：
     ```python
     if message["type"] == "http.disconnect":
         buffered.append(message)
         break
     ```
     （或更直接：`if message["type"] != "http.request": break`，把非 body 訊息交給下游處理）
  2. 額外加 `Content-Length` 提早拒絕（見 A-15），避免任何 buffering。
  3. 更根本的做法是不要自己實作：改用 `starlette.middleware.base.BaseHTTPMiddleware` 或直接在 `_ReplayReceive` 裡做 lazy 計數（邊轉發邊累加，超過就送 413），不需要先全部讀進 `buffered`。

- **影響面**
  - `src/kai_mind/web/app.py:240-243`（唯一掛載點）
  - 所有 POST/PATCH 路由：`src/kai_mind/web/routes/map_routes.py:23`、`map_build_routes.py`、`detail_scan_routes.py`、`scan_routes.py`、`mapping_routes.py`、`mapping_proposal_routes.py`、`trace_routes.py`、`viewer_routes.py:20`
  - 不動任何 route 簽名，純 middleware 內部修正

- **相關測試**
  - **新增**：`tests/web/test_local_api_hardening.py` → `test_request_size_limit_stops_on_client_disconnect`（unit 級：直接建 `RequestSizeLimitMiddleware`，餵一個永遠回 `http.disconnect` 的 `receive`，斷言在有限次呼叫內返回）。必須是 unit 級 —— 用 `TestClient` 模擬不出 disconnect。
  - **不需修改**現有 `test_large_request_returns_413_with_cors_header`（`tests/web/test_local_api_hardening.py:13`）。

- **嚴重度**：P1（可用性 / DoS）

- **風險**：**低**。修正是在既有 `while` 內多一個 break 分支，正常 request 路徑（只送 `http.request`）行為完全不變。

---

### A-2. `SafeUnhandledExceptionMiddleware` 沒有 `response_started` 保護，也不 re-raise —— 對 SSE 端點會把「route bug」變成「ASGI 協定違規」

- **位置**：`src/kai_mind/web/middleware.py:83-121`（尤其 105-121）

- **現況**

```python
        try:
            await self.app(scope, receive, send)
        except InvalidStateIdError:
            ...
        except Exception as exc:  # noqa: BLE001
            safe_log_event(
                logger,
                logging.ERROR,
                "local_api_unhandled_exception",
                stage="local_api",
                exception_type=exc.__class__.__name__,
            )
            if scope["type"] != "http":
                raise
            await _json_response(
                {"detail": "internal_server_error"},
                status_code=500,
                scope=scope,
                receive=receive,
                send=send,
            )
```

  對照 Starlette 自己的 `ServerErrorMiddleware.__call__`（`inspect.getsource` 實際印出）：

```python
        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started, send
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception as exc:
            ...
            if not response_started:
                await response(scope, receive, send)
            # We always continue to raise the exception.
            raise exc
```

- **為什麼是問題**

  1. **繞過 Starlette 標準做法**：Starlette 對「例外 → 統一回應」的官方機制是 `app.add_exception_handler(ExcType, handler)`（走 `ExceptionMiddleware`），或 `ServerErrorMiddleware(handler=...)`。這裡自己手寫了一個第三種機制，因此拿不到上述兩個保護。

  2. **response 已開始時會炸掉**：repo 有真實的 streaming 端點 —— `src/kai_mind/web/routes/scan_routes.py:354-359` 的 `GET /api/scan/events`（`EventSourceResponse`）。如果 generator 在第一個 chunk 之後拋例外，這段 code 會嘗試送出第二個 `http.response.start`。實測（`scratchpad/exp/probe_started.py`）：

```
$ uv run python .../probe_started.py
local_api_unhandled_exception
propagated: RuntimeError: ASGI protocol violation: response already started
messages sent: ['http.response.start', 'http.response.body']
```

     真正的 `RuntimeError("db handle died mid-stream")` 被**替換成**一個 ASGI 協定錯誤 —— 原始死因徹底消失。

  3. **不 re-raise = silent failure**：Starlette 註解明說 re-raise 的目的是「allows servers to log the error, or allows test clients to optionally raise the error within the test case」。這裡吞掉例外的結果是：uvicorn 永遠不會印 traceback，`TestClient(app)`（預設 `raise_server_exceptions=True`）也永遠看不到真正的例外 —— 所有 web 測試都只會看到 500 JSON。

- **建議改法**

  `src/kai_mind/web/middleware.py`：

  ```python
  class SafeUnhandledExceptionMiddleware:
      async def __call__(self, scope, receive, send) -> None:
          if scope["type"] != "http":
              await self.app(scope, receive, send)
              return
          response_started = False

          async def _send(message: Message) -> None:
              nonlocal response_started
              if message["type"] == "http.response.start":
                  response_started = True
              await send(message)
          ...
  ```
  每個 `except` 分支改成 `if not response_started: await _json_response(...)`；`except Exception` 分支在送出遮蔽回應後仍 `raise`（讓 uvicorn / TestClient 看得到）。

  更符合框架慣例的替代方案：把 `InvalidStateIdError` → 404、`ProjectStateBusyError` → 503 這兩條改成 `app.add_exception_handler(...)`（在 `create_app()` 內註冊），只留「最後一道遮蔽網」給 middleware。這也順便把 A-7 的順序問題解掉。

- **影響面**
  - `src/kai_mind/web/app.py:239`（唯一掛載點）
  - `src/kai_mind/web/routes/scan_routes.py:354-359`（唯一的 streaming 端點，是這條 bug 的實際觸發面）
  - 若改成 re-raise：**所有** `TestClient(create_app())` 且沒帶 `raise_server_exceptions=False` 的測試在遇到 500 時行為會變（現在吞、改後拋）。實際上目前會 500 的測試都已經帶了 `raise_server_exceptions=False`（`tests/web/test_local_api_hardening.py:15,47,72,105`）。

- **相關測試**
  - **修改**：`tests/web/test_local_api_hardening.py:34` `test_unhandled_error_response_is_masked_and_keeps_cors_header` —— 若採用 re-raise，此測試已有 `raise_server_exceptions=False`，斷言不用動；但要**新增**一條斷言「原始例外有被 re-raise」（用 `raise_server_exceptions=True` + `pytest.raises(RuntimeError)`）。
  - **新增**：`tests/web/test_local_api_hardening.py` → `test_streaming_response_failure_does_not_double_start`（unit 級，直接組 middleware + 一個先送 `http.response.start` 再拋例外的假 app）。
  - **新增**：`tests/web/test_local_api_hardening.py` → `test_scan_events_stream_failure_is_masked`（route 級，monkeypatch `scan_routes` 的 generator 讓它中途拋）。
  - `tests/web/test_map_routes.py:160` `test_scan_events_returns_sse_completed_event` 會涵蓋 happy path，**不需改**。

- **嚴重度**：P1（正確性 + 可觀測性；streaming 路徑會回傳半截 response）

- **風險**：**中**。`response_started` guard 本身零風險；「改回 re-raise」會讓所有預設 `TestClient` 在遇到 500 時改成拋例外，需要先全跑一次 `uv run pytest -m web` 確認沒有測試在依賴「500 被吞掉」。

---

### A-3. 遮蔽後的 500 在預設 logging 設定下留不下任何可查的線索（實機重現）

- **位置**：`src/kai_mind/web/middleware.py:106-112`

- **現況**

```python
            safe_log_event(
                logger,
                logging.ERROR,
                "local_api_unhandled_exception",
                stage="local_api",
                exception_type=exc.__class__.__name__,
            )
```

  `safe_log_event` 的實作（`src/kai_mind/core/services/logging_service.py:36`）是：

```python
    logger.log(level, event, extra={"event_data": event_data})
```

  也就是 **message 只有事件名字串**，`exception_type` / `stage` 全部放在 `extra["event_data"]` —— 預設 `logging.Formatter` 不會輸出 `extra`。

- **為什麼是問題**

  這台機器上實測（`scratchpad/exp/probe_stack2.py`，`logging.basicConfig(level=DEBUG)`，用真實的 `~/.kai-mind`）：

```
ERROR:kai_mind.web.middleware:local_api_unhandled_exception
INFO:httpx:HTTP Request: GET http://testserver/api/map "HTTP/1.1 500 Internal Server Error"
GET /api/map -> 500 {"detail":"internal_server_error"}
```

  開發者拿到的全部資訊就是 `local_api_unhandled_exception` 這 30 個字元 —— 沒有例外類別、沒有 route、沒有 file/line。這與 `CLAUDE.md`「Findings must be evidence-based, traceable to file/line/config」的專案精神相衝突（雖然該條原本講的是 scan finding，但一個 release-readiness gate 自己的 500 更不該無跡可循）。

  這條與「不得 leak stack trace 給 client」不衝突：**回應**遮蔽是對的，**本機 log** 應該有 traceback。`redact_local_paths` + `SecretMaskingService` 已經存在，正是為了讓 log 可以既詳細又安全。

  （對比：`src/kai_mind/web/middleware.py` 目前把 `exc` 完全丟棄，連 `exc_info=` 都沒傳。）

- **建議改法**

  1. `logging_service.safe_log_event` 增加 `exc_info: BaseException | None = None` 參數，轉傳給 `logger.log(..., exc_info=exc_info)`；或
  2. 在 `middleware.py` 直接補 `request_path=scope.get("path")`、`request_method=scope.get("method")`、`exception_message=str(exc)`（後者一定要走 `safe_log_event` 的 masking / path redaction，不能自己 `logger.error(str(exc))`）。
  3. 搭配 A-2 的 re-raise，uvicorn 自身的 `ServerErrorMiddleware` 就會補上完整 traceback，這是成本最低的一條。

- **影響面**
  - `src/kai_mind/core/services/logging_service.py:15-37`（若改簽名，需確認其他呼叫端）
  - `grep -rn "safe_log_event" src/` 的所有呼叫端（新增參數用預設值可保持相容）

- **相關測試**
  - **新增**：`tests/web/test_local_api_hardening.py` → `test_unhandled_exception_log_carries_route_and_type_without_secrets`（用 `caplog`，斷言 log record 有 path/method/exception_type，且不含 `sk-live-...` 與 `/Users/`）。
  - 現有 `test_unhandled_error_response_is_masked_and_keeps_cors_header` 已驗證**回應**不含 secret，**不需改**。

- **嚴重度**：P2（可觀測性；不是安全洞，但讓 P1 級 bug 無法診斷）

- **風險**：**低**。純新增欄位，回應體不變。改動 `logging_service.py` 屬於 `core/`，但只是加一個 optional 參數。

---

### A-4. `PersistentSessionStore.latest_viewer_payload()` 會丟掉 `POST /api/viewer/load` 的結果 —— 破壞 API-GUIDE 契約（e2e 已重現）

- **位置**：`src/kai_mind/web/session_store.py:191-198`（對照 `70-131` 的 `InMemorySessionStore:118-122`）

- **現況**

```python
    def save_viewer_payload(self, payload: ViewerPayload) -> None:
        self._latest_viewer_payload = payload

    def latest_viewer_payload(self) -> ViewerPayload:
        result = self.latest_build_result()
        if result is not None and result.viewer_load_result is not None:
            return ViewerPayload(viewer_load_result=result.viewer_load_result)
        return self._latest_viewer_payload
```

  `InMemorySessionStore` 對同一個 Protocol method 的實作是：

```python
    def latest_viewer_payload(self) -> ViewerPayload:
        return self._latest_viewer_payload
```

- **為什麼是問題**

  `docs/API-GUIDE.md:598` 對 `POST /api/viewer/load` 寫的是：「載入磁碟上既有的 `ai_system_map.json`，重新 validate 後**成為最新 viewer payload**。」

  但只要 state dir 裡任何 project 有帶 `viewer_load_result` 的 build，`latest_viewer_payload()` 就永遠回 build 的結果，`save_viewer_payload()` 寫進去的東西被無聲丟棄。

  e2e 實測（把探測檔暫時放進 `tests/web/`，跑完立刻刪除，repo 已還原）：

```
$ uv run pytest tests/web/test_zz_probe_e2e.py -q -s
>       assert latest == loaded, "API-GUIDE says viewer/load becomes the latest payload"
E       AssertionError: API-GUIDE says viewer/load becomes the latest payload
E       assert {'viewer_load...': True, ...}} == {'viewer_load...': True, ...}}
FAILED tests/web/test_zz_probe_e2e.py::test_viewer_load_is_discarded_after_a_build
```

  流程是：`POST /api/map/build`（fixture `basic_qdrant_ollama_rag`）→ `POST /api/viewer/load`（fixture map）→ `GET /api/map`，結果 `GET /api/map` 回的是 build 的 graph，不是剛載入的。

  單元層對照（`scratchpad/exp/probe_viewer.py`，同一個 Protocol，兩個實作結果相反）：

```
PersistentSessionStore   after POST /api/viewer/load, GET /api/map -> FROM_BUILD
InMemorySessionStore     after POST /api/viewer/load, GET /api/map -> FROM_VIEWER_LOAD
```

  **既有測試為什麼沒抓到**：`tests/web/test_viewer_routes.py:19` `test_viewer_load_route_updates_latest_payload` 正好斷言 `client.get("/api/map").json() == payload`，但它沒有先做 build，而 `tests/conftest.py:38-43` 的 autouse fixture 每個 test 都給一個空的 `tmp_path` state dir → `latest_build_result()` 永遠 `None` → 走 fallback 分支。**測試只覆蓋了 `if` 的 False 邊**。

- **建議改法**

  決定契約後二選一（要先跟 `docs/MODEL-CONTRACT.md` / `frontend/API_CONTRACT.md` 對齊）：

  - **(A) 依照 API-GUIDE**：`PersistentSessionStore.latest_viewer_payload()` 改成單純 `return self._latest_viewer_payload`，並在 `__init__` 之外新增一個「開機時從 latest pointer 還原一次」的明確步驟（例如 `def hydrate_from_latest(self) -> None`），由 `create_app()` / `build_app_services()` 呼叫一次，而不是每次讀取都重算。
  - **(B) 改契約**：若「build 永遠壓過 viewer/load」才是想要的行為，則 `docs/API-GUIDE.md:596-614` 必須改寫，且 `viewer_routes.load_viewer_map`（`src/kai_mind/web/routes/viewer_routes.py:33`）不該再呼叫 `store.save_viewer_payload()`（現在那行是純無效呼叫）。

- **影響面**
  - `src/kai_mind/web/routes/viewer_routes.py:33`（`store.save_viewer_payload(viewer_payload)`）
  - `src/kai_mind/web/routes/map_routes.py:42` `GET /api/map`、`:80` `GET /map`
  - `docs/API-GUIDE.md:596-614`
  - `src/kai_mind/web/session_store.py:42`（Protocol 宣告）

- **相關測試**
  - **修改**：`tests/web/test_viewer_routes.py:19` `test_viewer_load_route_updates_latest_payload` —— 現況只覆蓋空 state。要加 build-then-load 的變體。
  - **新增**：`tests/web/test_viewer_routes.py` → `test_viewer_load_after_build_still_wins`（或 `..._is_overridden_by_build`，看採 A 還是 B），內容即上面的 e2e 探測。
  - **新增**：`tests/unit/web/test_session_store.py`（目前**不存在**這個檔）→ `test_two_session_store_impls_agree_on_latest_viewer_payload`，用同一組操作序列跑兩個實作。

- **嚴重度**：P1（契約破壞；`AGENTS.md` 把 schema/contract 破壞列為 P1）

- **風險**：**中**。改 (A) 會讓 `GET /api/map` 在「重開後尚未 build」的情境行為改變，需同時檢查 `tests/web/test_local_json_restart_recovery.py:57` `test_project_mapping_and_latest_build_survive_restart` 是否依賴目前這個 side effect。

---

### A-5. `PersistentSessionStore.build_result()` 是有副作用的 getter，會污染 `latest_build_result()`

- **位置**：`src/kai_mind/web/session_store.py:200-228`

- **現況**

```python
    def latest_build_result(self) -> MapBuildResult | None:
        if self._latest_build_result is not None:
            return self._latest_build_result
        candidates = []
        for project in self._repository.list_projects():
            pointer = self._repository.get_latest_pointer(project.project_id)
            if pointer is not None:
                candidates.append(pointer)
        if not candidates:
            return None
        pointer = max(
            candidates,
            key=lambda item: (item.updated_at, item.latest_build_id),
        )
        return self.build_result(pointer.project_id)

    def build_result(self, project_id: str) -> MapBuildResult | None:
        ...
        result = self._manifest_service.load(manifest)
        self._latest_build_result = result   # <- getter 寫快取
        return result
```

- **為什麼是問題**

  `build_result(project_id)` 是「查某個 project 的 build」，卻順手把 `_latest_build_result` 蓋掉。而 `latest_build_result()` 第一件事就是「快取非空就直接回」（200-202 行），所以**任何一次跨 project 查詢都會讓「最新」變成「最後查到的」**。

  實測（`scratchpad/exp/probe_store.py`，A 是舊 build、B 是新 build）：

```
1. fresh latest_build_result -> B (expected B, the newest)
2. after build_result('project:A'), latest_build_result -> A (expected B)
3. after build_results(), latest_build_result -> B
4. save_build_result(project_id='project:A') then build_result('project:A') reads repo, ignoring what was saved: A
```

  第 2 行就是 bug。實際觸發序列（同一個 backend process）：

  - `POST /api/detail-scans`（`src/kai_mind/web/routes/detail_scan_routes.py:58` → `store.build_result(payload.project_id)`）
  - 或 `POST /api/trace`（`trace_routes.py:46`）
  - 或 `POST /api/mapping-proposals/...`（`mapping_proposal_routes.py:126`）

  之後任何 `GET /api/map`（`map_routes.py:42` → `latest_viewer_payload()` → `latest_build_result()`）或 `GET /api/map/report`（`map_routes.py:51`）都會回**那個被查過的 project**，而不是最新的。

  第 3 行回 B 只是巧合 —— `build_results()`（230-236 行）依 `list_projects()` 順序逐一呼叫 `build_result()`，快取最後停在**清單最後一個 project**，跟時間新舊無關。

- **建議改法**

  `src/kai_mind/web/session_store.py`：

  1. 從 `build_result()` 移除第 227 行的快取寫入（getter 不該有副作用）。
  2. `_latest_build_result` 改名為 `_pending_build_result`，語意收斂成「本 process 內剛剛 `save_build_result()` 寫入、尚未落盤的結果」，只由 `save_build_result()` 寫。
  3. 或更乾脆：完全移除這個欄位，`latest_build_result()` 每次都走 pointer 比較（`max(updated_at, latest_build_id)`），由 `LocalJsonStateProvider` 那層負責快取。

- **影響面**
  - `src/kai_mind/web/routes/map_routes.py:42`、`:51`、`:80`
  - `src/kai_mind/web/routes/detail_scan_routes.py:58`、`:153`
  - `src/kai_mind/web/routes/trace_routes.py:46`
  - `src/kai_mind/web/routes/mapping_proposal_routes.py:126`
  - `src/kai_mind/web/session_store.py:185`（`save_build_result` 寫同一欄位）

- **相關測試**
  - **新增**：`tests/unit/web/test_session_store.py`（不存在）→ `test_build_result_lookup_does_not_change_latest_build_result`
  - **新增**：`tests/web/test_map_routes.py` → `test_api_map_still_returns_newest_build_after_detail_scan_of_older_project`（route 級：build 兩個 project，對舊的做 detail-scan，再 `GET /api/map`）
  - **檢查**：`tests/web/test_local_json_restart_recovery.py:57` `test_project_mapping_and_latest_build_survive_restart`、`:190` `test_committed_detail_scan_survives_restart` —— 這兩條可能正好在依賴目前的快取行為，需逐條確認是修改還是保留。

- **嚴重度**：P1（正確性；使用者看到別的專案的地圖）

- **風險**：**中**。移除快取後每次 `latest_build_result()` 都會讀檔 + 驗 digest，`GET /api/map` 延遲會上升；同時會讓 A-6 的例外更常被觸發，所以**兩條必須一起修**。

---

### A-6. `BuildArtifactLoadError` 在 session store 讀取路徑完全沒被處理 —— 一個過期 build 就讓整個 viewer 500（本機直接重現）

- **位置**：`src/kai_mind/web/session_store.py:216-228`（`build_result`）與 `230-236`（`build_results`）

- **現況**

```python
    def build_result(self, project_id: str) -> MapBuildResult | None:
        pointer = self._repository.get_latest_pointer(project_id)
        if pointer is None:
            return None
        manifest = self._repository.get_build_manifest(
            project_id,
            pointer.latest_build_id,
        )
        if manifest is None:
            return None
        result = self._manifest_service.load(manifest)
        ...

    def build_results(self) -> tuple[tuple[str, MapBuildResult], ...]:
        results: list[tuple[str, MapBuildResult]] = []
        for project in self._repository.list_projects():
            result = self.build_result(project.project_id)
```

- **為什麼是問題**

  `BuildManifestService.load()` 會在 artifact digest 不符時丟 `BuildArtifactLoadError`（`src/kai_mind/core/services/build_manifest_service.py:290`）。`grep -rn "BuildArtifactLoadError" src/` 顯示 **`web/` 底下沒有任何一處捕捉它**（只有 `core/` 定義 + `tests/integration/test_build_manifest_service.py` 用到）。

  這台機器現在就是這個狀態。實測（`scratchpad/exp/probe_root.py`，直接對真實 `~/.kai-mind` 呼叫 `latest_viewer_payload()`）：

```
  File ".../core/services/build_manifest_service.py", line 128, in load
    self._require_valid_digest(manifest, "ai_system_map.json", map_path)
  File ".../core/services/build_manifest_service.py", line 290, in _require_valid_digest
    raise BuildArtifactLoadError(
kai_mind.core.services.build_manifest_service.BuildArtifactLoadError: required artifact is invalid: ai_system_map.json
```

  走 HTTP 的結果（`probe_stack2.py`）：

```
GET /api/map -> 500 {"detail":"internal_server_error"}
```

  也就是說：**只要開發者手動刪過或改過 outputs 目錄下的 artifact，整個 viewer 就掛掉**，而且（因為 A-3）log 裡看不出原因。

  更糟的是 `build_results()`（230-236 行）沒有 per-project 保護，任何**一個** project 的 build 壞掉，`GET /api/detail-scans/{id}`（`detail_scan_routes.py:153`）對**所有** project 都會 500。

  對照：寫入端 `save_committed_build_projection`（53-67 行）反而有防禦性 try/except。讀取端沒有 —— 防禦方向反了。

- **建議改法**

  1. `src/kai_mind/web/session_store.py`：`build_result()` 捕捉 `BuildArtifactLoadError`，回 `None`（語意 = 「這個 build 的 artifact 已失效，等同沒有」），並用 `safe_log_event` 記一筆 `build_artifact_invalid`。
  2. `build_results()` 改成 per-project try/except，跳過壞掉的 project 而不是整批失敗。
  3. `src/kai_mind/web/routes/map_routes.py` 的 `GET /api/map/report` 已經對 `result is None` 回 404（53-61 行），改完自動正確。
  4. 若希望前端能顯示「artifact 已失效」而不是靜靜當作沒有，則改成在 `map_routes` 加 `except BuildArtifactLoadError -> HTTPException(409, "build_artifacts_invalid")`，並同步 `docs/API-GUIDE.md`。

- **影響面**
  - `src/kai_mind/web/routes/map_routes.py:42`、`:51`、`:80`
  - `src/kai_mind/web/routes/detail_scan_routes.py:58`、`:153`
  - `src/kai_mind/web/routes/trace_routes.py:46`
  - `src/kai_mind/web/routes/mapping_proposal_routes.py:126`
  - 若走 4.，需動 `docs/API-GUIDE.md` 的錯誤碼表

- **相關測試**
  - **新增**：`tests/unit/web/test_session_store.py` → `test_build_result_returns_none_when_artifacts_are_invalid`
  - **新增**：`tests/unit/web/test_session_store.py` → `test_build_results_skips_projects_with_invalid_artifacts`
  - **新增**：`tests/web/test_map_routes.py` → `test_api_map_does_not_500_when_latest_build_artifacts_are_tampered`（build 之後把 `ai_system_map.json` 改掉，再 `GET /api/map`）
  - 可重用 `tests/integration/test_build_manifest_service.py:286` 既有的 tamper 手法

- **嚴重度**：P1（正確性 / 可用性；本機已可重現）

- **風險**：**低**。從「拋例外」變成「回 None」，所有下游都已經有 `None` 分支。

---

### A-7. `RequestSizeLimitMiddleware` 掛在 `SafeUnhandledExceptionMiddleware` **外面** —— 它自己的錯誤不會被遮蔽，錯誤格式不一致

- **位置**：`src/kai_mind/web/app.py:239-243`

- **現況**

```python
    app.add_middleware(SafeUnhandledExceptionMiddleware)
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_body_bytes=max_request_body_bytes,
    )
```

- **為什麼是問題**

  Starlette 的 `add_middleware` 是 `self.user_middleware.insert(0, ...)`，也就是**後掛的在外層**。實測 `app.user_middleware`（`probe_mw.py`）：

```
A) user_middleware on inner FastAPI: ['RequestSizeLimitMiddleware', 'SafeUnhandledExceptionMiddleware']
```

  真實 stack（`probe_stack2.py`）確認 `RequestSizeLimitMiddleware` 在 `SafeUnhandledExceptionMiddleware` **外面**。後果：`RequestSizeLimitMiddleware` 內部任何例外（含 A-1 那條路徑上的變體）都不會被遮蔽，而是落到 Starlette 的 `ServerErrorMiddleware`，回傳 **`text/plain` 的 `Internal Server Error`**，而不是專案統一的 `{"detail": "internal_server_error"}` JSON。

  實測（`probe_cors2.py`，用一個會拋例外的 stand-in 取代 `RequestSizeLimitMiddleware`）：

```
manual wrap (current)    -> 500 'Internal Server Error' acao='http://127.0.0.1:5173'
```

  body 是 `Internal Server Error`（plain text），不是 JSON。前端 `frontend/src/services/viewerApi.ts` 用 `zod` 驗回應，遇到這個會是 parse error 而非可辨識的錯誤碼。

  另外，這個順序看起來像是「寫的時候沒意識到 `add_middleware` 是反序」而不是刻意設計 —— 註解與 docstring 都沒有解釋為什麼 size limit 要在遮蔽層外面。

- **建議改法**

  `src/kai_mind/web/app.py`：對調兩行，讓 `SafeUnhandledExceptionMiddleware` 在最外層：

  ```python
  app.add_middleware(
      RequestSizeLimitMiddleware,
      max_request_body_bytes=max_request_body_bytes,
  )
  app.add_middleware(SafeUnhandledExceptionMiddleware)
  ```
  並在該處加一行註解說明「`add_middleware` 後掛者在外，此順序 = Safe 包住 SizeLimit」。

  更根本的做法見 A-2 建議：把 Safe 換成 `ServerErrorMiddleware(handler=...)`，那它天生就在最外層，順序問題自然消失。

- **影響面**
  - 只有 `src/kai_mind/web/app.py:239-243`。route 層完全不受影響。
  - 對調後 413 回應仍會經過 Safe（Safe 不攔 `_json_response` 已送出的回應），行為不變。

- **相關測試**
  - **不需修改** `tests/web/test_local_api_hardening.py:13` `test_large_request_returns_413_with_cors_header`（413 仍是 413，CORS header 仍在）。
  - **新增**：`tests/web/test_local_api_hardening.py` → `test_size_limit_middleware_failure_is_masked_as_json`（monkeypatch 讓 `RequestSizeLimitMiddleware` 內部拋例外，斷言回 `{"detail": "internal_server_error"}` 而非 plain text）。

- **嚴重度**：P2（錯誤格式一致性；不是 hot path）

- **風險**：**低**。兩行對調，正常路徑完全不變。

---

### A-8. `LocalApiApp.__getattr__ -> Any` 是完整的型別黑洞；而「CORS 必須手動包在最外層」的既有理由只在一種窄情境成立

- **位置**：`src/kai_mind/web/app.py:90-113`（wrapper）、`253-264`（手動包 CORS）

- **現況**

```python
class LocalApiApp:
    """ASGI app wrapper that keeps FastAPI attributes discoverable in tests."""
    ...
    def __getattr__(self, name: str) -> Any:
        return getattr(self.app, name)
```

```python
    cors_wrapped_app = CORSMiddleware(
        app,
        allow_origins=list(origins),
        allow_credentials=False,
        allow_methods=["GET", "PATCH", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type"],
    )
    return LocalApiApp(
        app,
        cors_wrapped_app,
        allowed_origins=origins,
    )
```

- **為什麼是問題**

  **(1) mypy 完全放行任何屬性**（實測 `scratchpad/exp/probe_types.py`）：

```
$ uv run mypy --strict .../probe_types.py
probe_types.py:5: note: Revealed type is "Any"       # app.state
probe_types.py:6: note: Revealed type is "Any"       # app.totally_made_up_attribute
probe_types.py:7: note: Revealed type is "Any"       # app.router  <- FastAPI 上其實有型別
probe_types.py:9: note: Revealed type is "kai_mind.web.app.LocalApiApp"
Success: no issues found in 1 source file
```

  第 8 行寫的是 `app.totally_made_up_attribute.nope().also_nope`，mypy 一聲不吭。注意 **`app.router` 也變成 `Any`** —— FastAPI 本身是有型別標註的，wrapper 把它全部抹掉了。

  這比 Plan 1 處理的 `app.state` 黑洞更廣：Plan 1 修好 `app.state.X` 之後，**只要還走 `LocalApiApp`，`create_app().anything` 依然是 `Any`**。`tests/e2e/test_apply_confirmations_build_lineage.py:62` 就是回傳 `LocalApiApp` 的 fixture，該檔所有 `app.xxx` 都不受 mypy 保護。

  **(2) 手動包 CORS 的既有理由部分不成立。**
  `docs/work/Timmy/learn/snapshot_safety_and_path_contract_learning.md:159-161` 記載的理由是：

  > 如果直接在 FastAPI 實例上呼叫 `app.add_middleware(CORSMiddleware)`，一旦內層的限制 Middleware 提前丟出 413 錯誤，或是發生 500 未捕獲崩潰，回傳的 Response 會直接跳過內層的 CORS 中介軟體。

  **實測結果與此不符**（`probe_mw.py`，同一組 middleware，只差 CORS 掛法）：

```
C) manual-wrap (current)    /boom -> 500 '{"detail":"internal_server_error"}' acao='http://127.0.0.1:5173'
D) manual-wrap (current)    /ok    -> 200 acao='http://127.0.0.1:5173'
C) add_middleware           /boom -> 500 '{"detail":"internal_server_error"}' acao='http://127.0.0.1:5173'
D) add_middleware           /ok    -> 200 acao='http://127.0.0.1:5173'
```

  原因是 `add_middleware` 會把 CORS 插到 `user_middleware[0]`，也就是**所有自訂 middleware 的最外層**，因此 413 與遮蔽後的 500 都拿得到 CORS header。413 的部分 `tests/web/test_local_api_hardening.py:13` 也已經在驗這件事。

  **唯一真正的差異**是「例外逃出所有 user middleware、落到 Starlette 內建 `ServerErrorMiddleware`」的情況（實測 `probe_cors2.py`）：

```
manual wrap (current)    -> 500 'Internal Server Error' acao='http://127.0.0.1:5173'
add_middleware           -> 500 'Internal Server Error' acao=None
```

  所以 wrapper 換來的實際好處只有這一條窄情境（而這條情境本身就是 A-7 要消滅的 bug）。

- **建議改法**

  兩種方向，擇一：

  - **(A) 移除 wrapper**（推薦）：`create_app()` 改回 `-> FastAPI`，用 `app.add_middleware(CORSMiddleware, ...)`，並把「例外逃出 user middleware」這條路徑用 `ServerErrorMiddleware(handler=...)` 補上（見 A-2）。`allowed_origins` 改放 `app.state.allowed_origins`（或 Plan 1 的 `AppServices`）。回傳型別變成真正的 `FastAPI`，`app.router` / `app.state` / `app.dependency_overrides` 全部恢復型別。
  - **(B) 保留 wrapper 但補型別**：`class LocalApiApp` 加上明確的 `state: State`、`router: APIRouter`、`dependency_overrides: dict[...]` 等 property（各自 `return self.app.xxx`），**刪掉 `__getattr__`**。這樣測試需要的屬性仍在，但打錯字會被 mypy 抓到。

  無論哪一種，都建議在 `create_app()` 或 `LocalApiApp` docstring 裡把「為什麼要包」的**實測理由**寫清楚，並修正 `docs/work/Timmy/learn/snapshot_safety_and_path_contract_learning.md:159-161` 的錯誤說明。

- **影響面**
  - `src/kai_mind/web/app.py:137`（回傳型別標註）
  - `tests/e2e/test_apply_confirmations_build_lineage.py:22`（`from kai_mind.web.app import LocalApiApp`）、`:62`（fixture 回傳型別）
  - `tests/web/test_map_routes.py:155`（`app.allowed_origins` —— 選 (A) 要改成 `app.state.allowed_origins`）
  - `tests/web/test_local_api_hardening.py:45,70`（`app.include_router(router)` 走 `__getattr__`）
  - `tests/web/test_nvidia_provider_app_wiring.py:19,38`（`app.state.mapping_proposal_service`）
  - `docs/API-GUIDE.md:76`、`scripts/dev.py:53`（`kai_mind.web.app:create_app --factory` —— 兩者都不看回傳型別，不用改）
  - `docs/work/Timmy/learn/architecture.md:55`、`docs/work/Timmy/meeting/web-adapter/01-app-factory-and-session.md:120-122`、`docs/work/Timmy/meeting/arch/02-web-api.md:57-59`（文件描述）

- **相關測試**
  - **修改**：`tests/web/test_map_routes.py:152` `test_local_api_cors_does_not_use_wildcard_origin`（`app.allowed_origins` 的讀取位置）
  - **修改**：`tests/e2e/test_apply_confirmations_build_lineage.py:62` 的 fixture 型別標註
  - **新增**：`tests/web/test_local_api_hardening.py` → `test_cors_header_present_on_error_escaping_user_middleware`（把 A-8 實測第二段固化成回歸測試，確保換掉 wrapper 之後這個保證還在）
  - **建議新增**（型別回歸）：`tests/web/test_app_typing.py` 之類，或直接在 Plan 1 的 `tests/web/test_app_services.py` 裡加一條 mypy 探測（Plan 1 Task 3 Step 4 已經示範過這種寫法）

- **嚴重度**：P2（維護性 / 型別安全；不是正確性 bug）

- **風險**：**中**。選 (A) 會改變 `create_app()` 的回傳型別，是公開 API 變更；但實際呼叫端只有測試與 uvicorn factory，兩者都能承受。**建議排在 Plan 1 之後**，避免兩份改動在 `app.py` 上打架。

---

### A-9. module-level `app = create_app()` 沒有任何消費者，卻在 import 時建整棵服務樹、讀 `.env`、並產生持有真實 API key 的 provider

- **位置**：`src/kai_mind/web/app.py:267`

- **現況**

```python
app = create_app()
```

- **為什麼是問題**

  **(1) 沒有任何人用它。** 全 repo 搜尋（含 `pyproject.toml`、`scripts/`、`docs/`、`.github/`）：

```
$ grep -rn "web\.app:app\|app:app\|from kai_mind.web.app import app" ... 
（無輸出）
```

  真正的啟動方式都是 factory：
  - `scripts/dev.py:53-54`：`"kai_mind.web.app:create_app", "--factory"`
  - `docs/API-GUIDE.md:76`：`.venv/bin/uvicorn kai_mind.web.app:create_app --factory ...`
  - `pyproject.toml:34-35` 的 `[project.scripts]` 只有 `kai-mind = "kai_mind.cli.main:main"`

  **(2) import 成本。** 實測（`probe_cost.py`）：

```
import (incl. module-level create_app): 0.806s
second create_app() (all caches warm):  0.035s
```

  也就是 **`import kai_mind.web.app` 這一行本身就要 0.8 秒**，其中大部分是 module-level `create_app()` 觸發的 TOML rule catalog 載入。有 20 個測試檔 `from kai_mind.web.app import create_app`（`tests/web/` 全部 + `tests/e2e/` 2 個 + `tests/integration/test_v2_active_cutover.py` + `tests/unit/core/test_profile_inference_boundaries.py`），每個 pytest session 都白付這 0.8 秒。

  **(3) import 時的副作用清單**（實測 `probe_import.py`，攔截 `open` / `Path.open` / `Path.home`）：

```
import kai_mind.web.app took 2.020s
module-level app object: LocalApiApp
Path.home() called during import: 1 time(s)
files opened at import time (filtered):
    .../core/rules/capability_reference_map.toml
    .../core/configs/llm_proposal.toml
    .env                                        <- CWD 相對路徑
    .../core/rules/docker_image_rules.toml
    .../core/rules/dependency_manifest_rules.toml
    .../core/rules/code_pattern_rules.toml
    .../core/rules/risk_hint_rules.toml
    .../core/rules/recommended_next_check_rules.toml
    .../core/rules/profile_registry.toml
routes registered on module-level app: 27
```

  **(4) 最嚴重的一點：import 時就構造出持有真實 API key 的 LLM provider。** 這台機器的 repo root `.env` 同時有 `KAI_MIND_ENABLE_NVIDIA_NIM_PROPOSALS`（truthy）與非空 `NVIDIA_API_KEY`。實測（`probe_env.py`，只印遮蔽預覽）：

```
module-level app provider type: NvidiaNimProposalProvider
provider holds a non-empty api key: True
masked preview: nvapi-...e_
create_app() (no env_file) provider type: NvidiaNimProposalProvider
```

  也就是說：**任何 `import kai_mind.web.app`（包含 `uv run pytest` 的收集階段）都會把真實 NVIDIA key 讀進記憶體，並建立一個可以發網路請求的 client**，即使那個 process 根本不打算起 API。`CLAUDE.md` 的 local-first privacy 原則與「core 是 read-only、deterministic-first」的定位下，這是不必要的攻擊面 / 意外呼叫外部服務的風險。

  （補充：`LocalJsonStateStorage.__init__`（`src/kai_mind/core/providers/local_json_state_storage.py:26-29`）只做 `resolve()`，**不 mkdir**，所以 import 不會寫磁碟；且 `tests/conftest.py:22-23` 在 module level 就設了 `KAI_MIND_STATE_DIR`，測試不會污染真實 `~/.kai-mind`。這兩點是好的，不是問題。）

- **建議改法**

  刪掉 `src/kai_mind/web/app.py:267` 的 `app = create_app()`。若擔心有人用 `uvicorn kai_mind.web.app:app`（目前查無此用法），可在 README / `docs/API-GUIDE.md:76` 旁邊補一句「本專案一律用 `--factory`」。

  若真的想保留一個 module-level entry，改成 lazy：

  ```python
  def __getattr__(name: str) -> LocalApiApp:   # PEP 562 module-level __getattr__
      if name == "app":
          return create_app()
      raise AttributeError(name)
  ```
  但既然查無消費者，直接刪最乾淨。

- **影響面**
  - 僅 `src/kai_mind/web/app.py:267`
  - grep 確認無任何 import 端（見上）
  - `scripts/dev.py:53`、`docs/API-GUIDE.md:76` 已經用 `--factory`，不需改

- **相關測試**
  - **不需修改**任何現有測試（沒有測試讀 module-level `app`）。
  - **新增（建議）**：`tests/web/test_local_api_hardening.py` 或新的 `tests/unit/web/test_app_import_purity.py` → `test_importing_web_app_does_not_build_an_application`（用 `subprocess` 跑一個乾淨 interpreter，量測 `import kai_mind.web.app` 不會讀 `.env`）。

- **嚴重度**：P2（不必要的副作用 + 隱私攻擊面；但目前無實際功能錯誤）

- **風險**：**低**。刪一行，且 grep 已證實無消費者。

---

### A-10. `env_file` 預設是 CWD 相對的 `Path(".env")` —— 行為依賴 process 啟動目錄，且讓約 40 個測試呼叫點的行為取決於開發者本機的 `.env`

- **位置**：`src/kai_mind/web/app.py:155-163`

- **現況**

```python
    app.state.mapping_proposal_service = (
        mapping_proposal_service
        or MappingProposalService(
            provider=nvidia_nim_provider_from_env(
                env_file=env_file or Path(".env"),
            ),
            manual_mapping_service=app.state.manual_mapping_service,
        )
    )
```

  `nvidia_nim_provider_from_env`（`src/kai_mind/core/providers/llm_proposal_provider.py:206`）→ `_dotenv_values(env_file or Path(".env"))`，而 `_dotenv_values`（`:262-264`）用 `path.is_file()` 判斷，找不到就回 `{}`（無警告）。

- **為什麼是問題**

  1. **CWD 依賴**：`Path(".env")` 相對於 process 的工作目錄。`scripts/dev.py:167` 用 `cwd=ROOT` 起 uvicorn，所以 dev 路徑剛好對；但使用者若自己在別的目錄跑 `uvicorn kai_mind.web.app:create_app --factory`，`.env` 會**靜默失效**（`_dotenv_values` 找不到就回空 dict，沒有任何 log/warning）。跨平台上這更難察覺（Windows 上服務化啟動的 CWD 常是 `C:\Windows\System32`）。這與 `CLAUDE.md` 的「Cross-platform (macOS/Windows) 相容性」要求相衝突。

  2. **測試不確定性**：`grep -rn "create_app()" tests/` 顯示有數十個呼叫點沒帶 `env_file=`，它們全部會讀開發者的真實 `.env`。本機實測（見 A-9 的 `probe_env.py`）證實 `create_app()` 在這台機器上真的會產生一個 `NvidiaNimProposalProvider`；在 CI（無 `.env`）則是 `None`。**同一組測試在本機與 CI 走的是不同分支**。

     `tests/web/test_nvidia_provider_app_wiring.py` 這兩條寫得很好（都明確傳 `env_file=tmp_path/".env"`），但其他測試沒有這個保護 —— 例如 `tests/web/test_mapping_proposal_routes.py` 若有任何路徑會呼到 provider，本機跑就可能真的發出網路請求。

  3. **Plan 1 不會解決這件事**：Plan 1 Task 1 Step 4 的 `build_app_services()` 原文照抄 `env_file=env_file or Path(".env")`，而且 Plan 1 明訂「行為必須完全不變」。所以這條需要獨立處理。

- **建議改法**

  1. 把預設從 CWD 相對改成明確的專案根或明確的 opt-in：
     - 方案 A：`env_file: Path | None = None` 時**不讀任何 `.env`**，只讀 `os.environ`；`.env` 的載入交給啟動端（`scripts/dev.py` 用 `--env-file`，或呼叫端明確傳）。這是 12-factor 的做法，也讓測試預設乾淨。
     - 方案 B：保留自動載入，但改成從一個明確的 anchor 解析（例如 `Path(__file__).resolve().parents[3] / ".env"`），並在找不到時 `safe_log_event` 記一筆。
  2. 無論哪個方案，`tests/conftest.py` 應加一個 autouse fixture，把 `.env` 探測導向 `tmp_path`（與現有 `isolate_default_state_root`（`tests/conftest.py:35-43`）對稱），讓所有測試預設不受本機 `.env` 影響。

- **影響面**
  - `src/kai_mind/web/app.py:135`（`env_file` 參數）、`:158-160`
  - Plan 1 執行後：`src/kai_mind/web/app_services.py` 的 `build_app_services(..., env_file=...)`
  - `src/kai_mind/core/providers/llm_proposal_provider.py:196-207`、`:262-269`
  - `scripts/dev.py:44-62`（若採方案 A，需在此明確載入 `.env`）
  - `.env.example`、`docs/API-GUIDE.md`（若載入方式改變需同步）

- **相關測試**
  - **不需修改**：`tests/web/test_nvidia_provider_app_wiring.py:11` `test_app_does_not_wire_nvidia_provider_without_explicit_flag`、`:23` `test_app_wires_nvidia_provider_when_enabled_from_dotenv`（兩條都已明確傳 `env_file`，正是正確寫法）。
  - **新增**：`tests/conftest.py` 的 autouse fixture（隔離 `.env`）—— 這是**修改**既有 conftest。
  - **新增**：`tests/web/test_nvidia_provider_app_wiring.py` → `test_create_app_without_env_file_does_not_read_repo_dotenv`

- **嚴重度**：P2（跨平台正確性 + 測試不確定性；本機已可觀察到分支差異）

- **風險**：**中**。方案 A 會改變「repo 根放 `.env` 就自動生效」的既有開發體驗，需要同步更新 `scripts/dev.py` 與文件，否則開發者會覺得 LLM proposal 突然失效。

---

### A-11. `save_committed_build_projection` 把三種例外吞掉且完全不 log

- **位置**：`src/kai_mind/web/session_store.py:53-67`

- **現況**

```python
def save_committed_build_projection(
    store: SessionStore,
    result: MapBuildResult,
    *,
    project_id: str,
) -> MapBuildResult:
    try:
        store.save_build_result(result, project_id=project_id)
    except (OSError, RuntimeError, ValueError):
        warning = "session_projection_save_failed"
        if warning not in result.warnings:
            return result.model_copy(
                update={"warnings": [*result.warnings, warning]}
            )
    return result
```

- **為什麼是問題**

  `except` 區塊完全沒有 log —— 連 `safe_log_event` 都沒有（對比 `middleware.py:106` 有記）。使用者只會在回應的 `warnings[]` 看到一個 `session_projection_save_failed` 字串，開發者連例外類別都不知道。

  另外 `ValueError` 這個捕捉範圍值得留意：`BuildArtifactLoadError` 繼承自 `ValueError`（`src/kai_mind/core/services/build_manifest_service.py:54`），所以真正的 artifact digest 失效也會被歸進這個籠統的 warning，與 A-6 的問題互相掩蓋。

- **建議改法**

  `src/kai_mind/web/session_store.py`：

  ```python
  except (OSError, RuntimeError, ValueError) as exc:
      safe_log_event(
          logger, logging.WARNING, "session_projection_save_failed",
          stage="web_session_store",
          project_id=project_id,
          exception_type=exc.__class__.__name__,
      )
  ```
  並考慮把 `ValueError` 縮小成明確的例外型別，避免與 `BuildArtifactLoadError` 混淆。

- **影響面**
  - `src/kai_mind/web/routes/scan_routes.py:67`（import）、`:339`（呼叫）
  - `src/kai_mind/web/routes/detail_scan_routes.py:33`、`:109`
  - `src/kai_mind/web/routes/map_build_routes.py:32`、`:70`
  - 回應 payload 不變（`warnings[]` 語意不動）

- **相關測試**
  - **新增**：`tests/unit/web/test_session_store.py` → `test_save_committed_build_projection_logs_the_failure`（用 `caplog` + 一個 `save_build_result` 會拋 `OSError` 的假 store）
  - 現有測試皆不受影響（回應不變）

- **嚴重度**：P3（可觀測性）

- **風險**：**低**。只加 log。

---

### A-12. `SessionStore` Protocol 的兩個實作對同樣的參數行為不一致（參數被靜默丟棄）

- **位置**：`src/kai_mind/web/session_store.py:150-173`（`import_project`）、`179-189`（`save_build_result`）

- **現況**

```python
    def import_project(
        self,
        *,
        project_path: Path,
        source_type: str,
    ) -> ProjectRecord:
        resolved = project_path.expanduser().resolve()
        ...
        state = ProjectState(
            project_id=f"project:{uuid4()}",
            project_name=resolved.name or "project",
            source_type="local_path",       # <- 第 167 行，參數 source_type 被無視
            canonical_path=str(resolved),
            ...
        )
```

```python
    def save_build_result(
        self,
        result: MapBuildResult,
        *,
        project_id: str | None = None,     # <- 完全沒被用到
    ) -> None:
        self._latest_build_result = result
        if result.viewer_load_result is not None:
            self.save_viewer_payload(
                ViewerPayload(viewer_load_result=result.viewer_load_result)
            )
```

  對照 `InMemorySessionStore`（`:92-97`、`:104-116`）：兩個參數都有實際使用。

- **為什麼是問題**

  同一個 Protocol 的兩個實作，對同樣的呼叫給出不同語意，而型別系統與 lint 都抓不到：`pyproject.toml` 的 ruff `select = ["E", "F", "I", "UP", "B"]` **沒有啟用 `ARG`**（unused-arguments），mypy strict 也不檢查 unused parameter。

  實測（`probe_store.py` 第 4 行）：

```
4. save_build_result(project_id='project:A') then build_result('project:A') reads repo, ignoring what was saved: A
```

  目前尚未造成使用者可見的錯誤：`src/kai_mind/web/routes/project_routes.py:29,48` 兩處都把 `source_type` 硬寫成 `"local_path"` 回應，`build_result()` 也永遠改讀 repository。但這是「兩層都各自硬寫死」的巧合，不是設計。

- **建議改法**

  二選一：
  - **收斂 Protocol**：既然 `source_type` 只支援 `local_path`、`project_id` 在 persistent 實作沒有意義，就從 `SessionStore` Protocol（`:31-50`）拿掉這兩個參數，讓兩個實作簽名一致。
  - **讓實作真的用它**：`PersistentSessionStore.import_project` 改成 `source_type=source_type`；`save_build_result` 至少把 `project_id` 記進 `_latest_build_result` 的 key（配合 A-5 的重構）。

  另外建議在 `pyproject.toml` 的 `[tool.ruff.lint] select` 加上 `"ARG"`，讓這類「宣告了但沒用」的參數在 pre-commit 就被擋下。

- **影響面**
  - `src/kai_mind/web/routes/project_routes.py:37-51`（`POST /api/projects/import` 傳 `source_type=payload.source_type`）
  - `src/kai_mind/web/schemas.py`（`ProjectImportRequest.source_type` / `ProjectImportResponse.source_type`）
  - `src/kai_mind/web/routes/scan_routes.py:339`、`detail_scan_routes.py:109`、`map_build_routes.py:70`（都經 `save_committed_build_projection` 傳 `project_id`）
  - 若加 `ARG` rule：需先全 repo 跑一次 `uv run ruff check src tests --select ARG` 評估既有違規量

- **相關測試**
  - **新增**：`tests/unit/web/test_session_store.py` → `test_import_project_records_requested_source_type`
  - **檢查**：`tests/web/test_project_scan_routes.py`（`POST /api/projects/import` 的既有覆蓋）—— 目前應該只驗回應的 `"local_path"`，若 Protocol 收斂則需同步。
  - `tests/web/test_detail_scan_routes.py:78`、`tests/web/test_trace_routes.py:169,229` 直接對 `InMemorySessionStore` 呼叫 `import_project(...)`，簽名若改要一起改。

- **嚴重度**：P3（一致性 / LSP；目前無使用者可見錯誤）

- **風險**：**低**。改 Protocol 簽名會牽動 3 個測試檔，但都是機械式修改。

---

### A-13. `InMemorySessionStore` 在生產路徑已經是死碼，但 module docstring 與兩份未完成計畫仍以它為主體

- **位置**：`src/kai_mind/web/session_store.py:1`、`70-131`

- **現況**

```python
"""In-memory session state for the local development API."""
```

  但 `create_app()`（`src/kai_mind/web/app.py:233-237`）預設組的是 `PersistentSessionStore`：

```python
    app.state.session_store = session_store or PersistentSessionStore(
        repository=repository,
        manifest_service=manifest_service,
        projection_service=app.state.viewer_session_service,
    )
```

  `grep -rn "InMemorySessionStore" src/ tests/` 的 `src/` 命中數為 **0**（只有 `session_store.py` 自己的定義）；使用者只有 `tests/web/test_detail_scan_routes.py:13,77` 與 `tests/web/test_trace_routes.py:17,168,206,228`。

- **為什麼是問題**

  1. Module docstring（第 1 行）描述的是 62 行的 `InMemorySessionStore`，不是 112 行的 `PersistentSessionStore` —— 讀者第一眼會誤判整個檔案的定位。
  2. 兩份 open 的實作計畫把力氣投在錯的類別上：
     - `docs/work/Timmy/schedule/plan/unfinish/final-phase-hardening/150-fix-inmemory-session-store-growth-bound.md`（記憶體 DoS）
     - `docs/work/Timmy/schedule/plan/unfinish/final-phase-hardening/174-make-inmemory-session-store-thread-safe.md`（thread safety）

     兩份的 Primary file 都是 `src/kai_mind/web/session_store.py`，但目標都寫 `InMemorySessionStore` —— 而它在生產環境根本不會被實例化。真正需要這兩個保護的是 `PersistentSessionStore`（見 A-14）。

- **建議改法**

  1. 更新 `src/kai_mind/web/session_store.py:1` 的 docstring，改成描述整個檔案（Protocol + 兩個實作 + projection helper）。
  2. 決定 `InMemorySessionStore` 的去留：
     - 若只服務測試 → 移到 `tests/helpers/`（例如 `tests/helpers/session_store.py`），生產程式碼不再攜帶它。
     - 若要保留為「無 state dir 的輕量模式」→ 在 `create_app()` 加一個明確的 opt-in（例如 `KAI_MIND_EPHEMERAL_SESSION=1`），並在 docstring 說清楚。
  3. 把 #150 / #174 兩份計畫的目標類別更正為 `PersistentSessionStore`（或標記為 obsolete）。

- **影響面**
  - `tests/web/test_detail_scan_routes.py:13,75,77,91`
  - `tests/web/test_trace_routes.py:17,168,206,228`
  - `docs/work/Timmy/schedule/plan/unfinish/final-phase-hardening/150-*.md`、`174-*.md`
  - `docs/design/epic1-phase2.md:195`、`docs/spec/draft/epic1-phase2.md:131`、`docs/work/Timmy/meeting/web-adapter/00-web-adapter-overview.md:82`（都還在描述 in-memory 為生產行為，已過時）

- **相關測試**
  - **修改**（若搬家）：`tests/web/test_detail_scan_routes.py`、`tests/web/test_trace_routes.py` 的 import 路徑
  - **不需新增**測試（純位置/文件調整）

- **嚴重度**：P3（一致性 / 文件同步；`AGENTS.md` 有「不要把 roadmap 描述成已交付」的要求，這裡是反向的「已淘汰的描述還留著」）

- **風險**：**低**。純搬移與文件更新。

---

### A-14. `PersistentSessionStore` 的可變快取在 FastAPI threadpool 下沒有任何同步保護

- **位置**：`src/kai_mind/web/session_store.py:145-148`、`185`、`192`、`227`

- **現況**

```python
        self._latest_viewer_payload = ViewerPayload(
            viewer_load_result=self._projection.empty()
        )
        self._latest_build_result: MapBuildResult | None = None
```
（寫入點：`:185` `save_build_result`、`:192` `save_viewer_payload`、`:227` `build_result`）

- **為什麼是問題**

  `create_app()` 只建一個 `PersistentSessionStore` 實例（`app.py:233`），由所有 request 共用。而 route handler 幾乎都是 **sync `def`**（例如 `src/kai_mind/web/routes/map_routes.py:24` `def build_map(...)`、`:39` `def get_api_map(...)`），FastAPI 會把它們丟進 anyio threadpool → **真正的多執行緒並行存取**。

  `save_build_result`（185-189 行）是「寫 `_latest_build_result` → 再寫 `_latest_viewer_payload`」的兩步操作，中間可被切換；配合 A-5 的 getter 副作用，`_latest_build_result` 與 `_latest_viewer_payload` 可能對應到不同的 build。

  現有計畫 `174-make-inmemory-session-store-thread-safe.md` 只針對 `InMemorySessionStore`（見 A-13），**沒有涵蓋這個生產類別**。

- **建議改法**

  `src/kai_mind/web/session_store.py`：`PersistentSessionStore.__init__` 加 `self._lock = threading.RLock()`，把 `save_build_result` / `save_viewer_payload` / `latest_build_result` / `latest_viewer_payload` 的快取讀寫包起來。
  更好的做法是配合 A-5 直接**移除**這兩個可變欄位（無狀態就無 race），只保留 repository 那層的檔案鎖（`LocalJsonStateStorage.project_lock`，已用 `filelock`）。

- **影響面**
  - `src/kai_mind/web/routes/map_routes.py:23,39,47,77`
  - `src/kai_mind/web/routes/scan_routes.py:94,158`
  - `src/kai_mind/web/routes/detail_scan_routes.py:51,133`
  - `src/kai_mind/web/routes/map_build_routes.py:49,116`
  - `src/kai_mind/web/routes/viewer_routes.py:26`
  - `src/kai_mind/web/routes/trace_routes.py:35`、`mapping_proposal_routes.py:65`、`project_routes.py:24,39`

- **相關測試**
  - **新增**：`tests/unit/web/test_session_store.py` → `test_concurrent_save_and_read_keeps_latest_pointer_consistent`（`ThreadPoolExecutor` 併發打 `save_build_result` / `latest_build_result`）
  - 這正是 `174-*.md` Task 1 描述的測試檔（`tests/unit/web/test_session_store.py`），目前**尚未建立**

- **嚴重度**：P3（併發正確性；local 單使用者情境觸發機率低，但 `AGENTS.md` 的 release-readiness 關注點涵蓋這類）

- **風險**：**低**（加鎖）／**中**（若選擇移除快取，與 A-5 綁在一起，效能與行為都會變）

---

### A-15. `RequestSizeLimitMiddleware` 沒看 `Content-Length`，且方法白名單漏掉帶 body 的其他方法

- **位置**：`src/kai_mind/web/middleware.py:18`、`40-45`

- **現況**

```python
HTTP_BODY_METHODS: Final = {"POST", "PUT", "PATCH"}
```

```python
        if (
            scope["type"] != "http"
            or scope.get("method") not in HTTP_BODY_METHODS
        ):
            await self.app(scope, receive, send)
            return
```

- **為什麼是問題**

  1. **沒有 `Content-Length` 提早拒絕**：對一個宣告 500MB 的 request，這段 code 仍會實際讀進 1MB + 一個 chunk 才拒絕。`scope["headers"]` 裡的 `content-length` 是現成的，先檢查可以零 buffering 直接回 413。
  2. **方法白名單**：目前 repo 沒有 `router.delete` / `router.put`（`grep -rn "router.delete\|router.put" src/kai_mind/web/routes/` 無輸出），所以現在不會漏；但白名單是「加新方法就會忘記同步」的寫法。更穩的判斷是「有 `content-length` 或 `transfer-encoding` header 就檢查」，而不是列方法。

- **建議改法**

  `src/kai_mind/web/middleware.py`，`RequestSizeLimitMiddleware.__call__` 開頭：

  ```python
  declared = Headers(scope=scope).get("content-length")
  if declared is not None and declared.isdigit():
      if int(declared) > self._max_request_body_bytes:
          await _json_response({"detail": "request_too_large"}, status_code=413, ...)
          return
  ```
  並把方法判斷改成「非 GET/HEAD/OPTIONS 一律走檢查」或直接依 header 判斷。

- **影響面**
  - 只有 `src/kai_mind/web/middleware.py`；`app.py:240-243` 的掛載不變。
  - 所有 POST/PATCH route 的行為在合法 request 下完全不變。

- **相關測試**
  - **不需修改**：`tests/web/test_local_api_hardening.py:13` `test_large_request_returns_413_with_cors_header`（會繼續通過，只是走更早的分支）
  - **新增**：`tests/web/test_local_api_hardening.py` → `test_oversized_content_length_is_rejected_without_reading_body`（斷言 `receive()` 呼叫次數為 0）

- **嚴重度**：P3（防禦深度）

- **風險**：**低**。純提早拒絕，不改變合法請求路徑。

---

## 我確認沒問題的部分

以下是我逐行看過、認為**寫法正確、不需要改**的地方，避免主 agent 誤判：

1. **`src/kai_mind/web/__init__.py`（1 行 docstring）與 `src/kai_mind/web/routes/__init__.py`（1 行 docstring）**
   看起來「空」，但這是**這個 repo 的一致慣例**：`src/kai_mind/core/__init__.py`、`cli/__init__.py`、`core/services/__init__.py`、`core/providers/__init__.py` 全部都只有 docstring，只有 `storage/__init__.py` 做 re-export（因為它真的有一組穩定的 public 型別）。`web/` 是 adapter 邊界、沒有對外提供 library API（消費者只有 uvicorn factory 與測試），**不需要 `__all__`**。加 re-export 反而會製造新的 import 循環風險（`app.py` → `routes/*` → `dependencies.py` → `session_store.py`）。
   `from kai_mind.web.routes import detail_scan_routes, ...`（`app.py:61-71`）雖然 `routes/__init__.py` 沒 import 它們，Python 的 `from package import submodule` 語法本來就會觸發 submodule import，**寫法正確**。

2. **`core/` 沒有依賴 `web/`（分層規則遵守）**
   `grep -rn "kai_mind.web" src/kai_mind/cli/ src/kai_mind/core/` 無輸出。`web/` 只單向依賴 `core/`，符合 `CLAUDE.md` 的 `Web / CLI adapters -> Core services -> Providers / Models`。

3. **錯誤回應 envelope 與 routes 層一致**
   `middleware.py:134-143` 的 `_json_response` 產出 `{"detail": "<stable_code>"}`；routes 全部用 `HTTPException(detail=...)`，FastAPI 序列化後也是 `{"detail": ...}`。兩者 **shape 一致**（唯一的例外是 A-7 指出的、逃到 `ServerErrorMiddleware` 的 plain-text 路徑）。

4. **遮蔽後的錯誤回應沒有 leak secret 或本機路徑**
   `middleware.py:88-121` 回傳的都是固定字串常數（`resource_not_found` / `project_state_busy` / `internal_server_error`），從不把 `str(exc)` 放進 body。`tests/web/test_local_api_hardening.py:34-61,63-84` 已明確斷言 `sk-live-secret-value` 與 `/Users/linjunting` 不出現在回應中。這一點符合 `CLAUDE.md` 的 local-first privacy。
   （注意：routes 層有多處 `HTTPException(detail=str(exc))`，例如 `map_build_routes.py:57,64`、`mapping_routes.py:55,76`、`scan_routes.py:265` —— 那不在我這一區，請交給負責 routes 的稽核。）

5. **`_ReplayReceive`（`middleware.py:124-131`）**
   把已消耗的 ASGI message 重播給下游、耗盡後回一個 `{"type":"http.request","body":b"","more_body":False}` 終止訊息，這個實作是正確的（下游 `Request.body()` 會正常結束）。問題只在上游的 buffering 迴圈（A-1），不在這個類別。

6. **`default_state_dir()`（`app.py:83-87`）**
   `Path(configured).expanduser()` + `Path.home() / ".kai-mind"` 是正確的跨平台寫法（Windows 上 `Path.home()` 解析到 `%USERPROFILE%`），也正確支援 `KAI_MIND_STATE_DIR` 覆寫。

7. **測試不會污染真實 `~/.kai-mind`**
   `tests/conftest.py:22-23` 在 module level（早於任何 `kai_mind` import）就設 `os.environ["KAI_MIND_STATE_DIR"]`，加上 `:35-43` 的 autouse `isolate_default_state_root` fixture 逐 test 再隔離一次。搭配 `LocalJsonStateStorage.__init__`（`src/kai_mind/core/providers/local_json_state_storage.py:26-29`）不做 mkdir，**module-level `app = create_app()` 不會寫任何檔案**。A-9 講的是 import 成本與 provider 副作用，**不是**狀態污染。

8. **CORS 設定本身**
   `app.py:77-80` 的 `DEFAULT_ALLOWED_ORIGINS` 只有兩個 loopback origin，`allow_credentials=False`，`allow_methods` / `allow_headers` 都是明確白名單而非 `["*"]`。`tests/web/test_map_routes.py:152` 有回歸測試防止退化成 wildcard。**設定正確**，A-8 質疑的是「掛載方式」而不是「設定值」。

9. **`ProjectRecord`（`session_store.py:22-28`）是 `@dataclass(frozen=True)`**
   不可變 value object，正確。

10. **`PersistentSessionStore.import_project` 的 path digest 去重**（`session_store.py:156-163`）
    `expanduser().resolve()` 後才算 `sha256`，並用 `find_project_by_path_digest` 做 idempotent 重用（`reused=True`）。這解掉了舊 `InMemorySessionStore` 每次 import 都給新 UUID 的問題，`tests/web/test_local_json_restart_recovery.py:81` `test_reimport_same_canonical_path_reuses_project_identity` 有覆蓋。**寫法正確**。

11. **`safe_log_event` 的 masking / path redaction 管線**（`src/kai_mind/core/services/logging_service.py`）
    對 mapping / sequence 遞迴處理，且正確排除 `bytes | bytearray`。A-3 的問題是 middleware **傳給它的欄位太少**，不是它本身有缺陷。

12. **`create_app()` 的 CORS `allow_methods` 不含 `DELETE`/`PUT`**
    與實際路由集合吻合（`grep -rn "router.delete\|router.put" src/kai_mind/web/routes/` 無輸出），不是遺漏。

---

## 建議的修復順序（給主 agent 排程用）

| 順序 | 條目 | 理由 |
|---|---|---|
| 1 | A-1 | 獨立、低風險、堵住唯一的 DoS 路徑 |
| 2 | A-6 | 本機已可重現的 500，且是 A-5 的前置（A-5 修完會更常讀檔） |
| 3 | A-5 + A-14 | 同一組欄位，必須一起改 |
| 4 | A-4 | 需先定契約（改 code 還是改 API-GUIDE） |
| 5 | A-2 + A-3 + A-7 | 同一組 middleware，一起重寫成 Starlette 標準做法最省事 |
| 6 | **Plan 1**（`phase2.5/1.md`） | 服務組裝重構 |
| 7 | A-8 | 動 `create_app()` 回傳型別，排在 Plan 1 之後避免衝突 |
| 8 | A-9 + A-10 | Plan 1 執行後這兩條會搬到 `app_services.py`，一起收尾 |
| 9 | A-11 ~ A-13, A-15 | 一致性 / 文件 / 防禦深度，可批次處理 |
