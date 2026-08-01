# Audit D — `src/systograph/web/` 死碼盤點 + `tests/` web 耦合稽核

READ-ONLY 稽核。未修改任何程式碼或測試。
稽核時間點：`main` @ `0a68ccd`。

---

## web 檔案可刪除性判定表

`git ls-files src/systograph/web` = **19 個 tracked `.py`**（與任務描述一致）。

歷史刪除紀錄（`git log --diff-filter=D --name-only -- 'src/systograph/web/*'`）：

```
COMMIT 4ea4353 2026-06-12 [Epic 1][Backend Task 24] feat: simplify scan boundary same-run gate (#46) (#120)

src/systograph/web/routes/scan_boundary_routes.py
```

**web 層歷史上只被刪過這一個檔**，而且刪得乾淨：`git grep scan_boundary_routes` 在 `src/`、`tests/`、`scripts/`、`frontend/` **零命中**，只有 `docs/` 有 4 處歷史敘述。沒有殘留 import。唯一殘留是 `.gitignore` 已忽略的編譯快取 `src/systograph/web/routes/__pycache__/scan_boundary_routes.cpython-314.pyc`（`ls -la` 確認存在，日期 6月11日）。

| 檔案 | 行數 | 被誰 import（檔案:行號） | 內部死函式 | 判定 | 刪前須處理 |
|---|---|---|---|---|---|
| `web/__init__.py` | 1 | 隱含（所有 `from systograph.web...`） | 無（只有 docstring） | **必要** | — |
| `web/app.py` | 267 | `scripts/dev.py:55`（uvicorn `--factory`）、`scripts/lib/api_trace_common.sh:109`、`scripts/test_mapping_proposal_llm.sh:140`、20 個測試檔（`tests/web/*` 16 檔 + `tests/e2e/test_apply_confirmations_build_lineage.py:22`、`tests/e2e/test_inventory_selection_scan_flow.py:15`、`tests/integration/test_v2_active_cutover.py:23`、`tests/unit/core/test_profile_inference_boundaries.py:19`） | **`app = create_app()` (line 267) 全 repo 零引用**（`git grep "web.app:app"` / `from systograph.web.app import app` 皆 0 命中）；`create_app()` 19 個 kwargs 中 **10 個從未被任何呼叫端使用** | **必要（但內含死碼，見 D-1 / D-3）** | 刪 line 267 前確認沒有外部 `uvicorn systograph.web.app:app` 用法（repo 內三個入口都用 `--factory`） |
| `web/dependencies.py` | 135 | `routes/` 8 個模組（`scan_routes.py:40`、`map_routes.py:15`、`map_build_routes.py:18`、`detail_scan_routes.py:24`、`trace_routes.py:16`、`viewer_routes.py:12`、`mapping_routes.py:17`、`mapping_proposal_routes.py:22`） | **`build_manifest_service` (line 58-59) 死函式** — `grep -rn "\bbuild_manifest_service\b" src/systograph/web/routes/` 零命中；coverage 也標 `dependencies.py ... 98% Missing: 59` | **必要（含 1 個死函式）** | 刪 `build_manifest_service` 前確認 `app.state.build_manifest_service`（app.py:149）仍需保留給 `DetailScanBuildService` / `ApplyConfirmationsService` 建構使用（是，直接由 `create_app` 傳入，不經 Depends） |
| `web/inventory_error_response.py` | 85 | `routes/scan_routes.py:50` | 無。3 個 public function 全被 scan_routes 用到（`inventory_error_detail` @ 118/257/329、`project_not_found_detail` @ 100/165、`inventory_system_error_detail` @ 123/262/333）。coverage 100%（列在 "5 files skipped due to complete coverage"） | **必要** | — |
| `web/inventory_preflight_projection.py` | 115 | `routes/scan_routes.py:55` | 無。唯一 public function `project_inventory_preflight` 被 scan_routes.py:109 呼叫。coverage 100% | **必要** | — |
| `web/legacy_mapping_guards.py` | 38 | `routes/mapping_proposal_routes.py:26`、`routes/mapping_routes.py:18` | 無。`reject_legacy_mapping_type` 用於 `mapping_routes.py:42`、`mapping_proposal_routes.py:100` 的 `dependencies=[Depends(...)]` | **必要** | — |
| `web/middleware.py` | 143 | `app.py:56` | 無死函式，但 `_ReplayReceive.__call__` fallback（line 131）與三處 `if scope["type"] != "http": raise`（87/97/114）**零覆蓋** | **必要（測試缺口見 D-13）** | — |
| `web/routes/__init__.py` | 1 | `app.py:61` | 無（只有 docstring） | **必要** | — |
| `web/routes/detail_scan_routes.py` | 208 | `app.py:62/246` | 無死函式（`_find_detail_scan`、`_legacy_detail_scan` 皆被呼叫），但 `_legacy_detail_scan` 只在「build_result 無 lineage」的舊路徑才進入 | **必要** | — |
| `web/routes/map_build_routes.py` | 126 | `app.py:63/245` | 無 | **必要** | — |
| `web/routes/map_routes.py` | 80 | `app.py:64/244`、`tests/unit/core/test_query_trace_boundaries.py:6`（whitebox `inspect.getsource`） | `get_map_fallback`（`/map`，line 75-80）與 `get_api_map` 回傳完全相同 payload — 看似重複，但 **frontend 實際用到**：`frontend/src/services/viewerApi.ts:5` `const mapEndpoints = ["/api/map", "/map"]` | **必要（`/map` 不可刪）** | 若真要刪 `/map`，須先改 `frontend/src/services/viewerApi.ts:5` 並更新 `frontend/API_CONTRACT.md` |
| `web/routes/mapping_proposal_routes.py` | 129 | `app.py:65/247` | 無 | **必要** | — |
| `web/routes/mapping_routes.py` | 76 | `app.py:66/248` | 無 | **必要** | — |
| `web/routes/project_routes.py` | 53 | `app.py:67/249` | 無 | **必要** | — |
| `web/routes/scan_routes.py` | 359 | `app.py:68/250` | 無死函式，但 `create_scan` 內 line 267-273 的 `if proposals:` 分支在 line 253 `proposals = []` 之後**恆為 false**（死分支，coverage 標 268 未覆蓋） | **必要（含 1 段死分支）** | 刪 line 267-273 前確認 line 242-248 已涵蓋 pending 回傳路徑（是） |
| `web/routes/trace_routes.py` | 85 | `app.py:69/251` | 無 | **必要** | — |
| `web/routes/viewer_routes.py` | 34 | `app.py:70/252`、`tests/web/test_viewer_routes.py:8`（whitebox `inspect.getsource`） | 無。coverage 100% | **必要** | — |
| `web/schemas.py` | 432 | `inventory_error_response.py:9`、`inventory_preflight_projection.py:18`、`routes/` 7 個模組 | 無真死類別。`WebSchema`、`Phase2MapBuildResult` 只在 schemas.py 內部被引用（`Phase2MapBuildResult` 由 `MapBuildScopedResponse.from_core` line 161 / `ApplyConfirmationsResponse.from_domain` line 182 使用），屬正常內部型別 | **必要** | — |
| `web/session_store.py` | 246 | `app.py:72`、`dependencies.py:41`、`routes/` 6 個模組 | `InMemorySessionStore`（line 70-131）**production 完全沒用**——`create_app` 只建 `PersistentSessionStore`（app.py:233）；唯一使用者是 `tests/web/test_detail_scan_routes.py:13,77` 與 `tests/web/test_trace_routes.py:17,168,228`。等於「production package 裡的 test double」 | **必要（`InMemorySessionStore` 可考慮遷移到 `tests/helpers/`）** | 搬 `InMemorySessionStore` 前須改 2 個測試檔的 import，並確認 `SessionStore` Protocol（line 31-50）留在 `web/` |

### 一句話回答使用者的問題

> 「`src/systograph/web/` 裡是不是有舊檔案？直接刪會不會影響下層？」

**沒有可整檔刪除的舊檔案。** 19 個檔全部活著（都在 import 鏈上）。唯一被刪過的 `scan_boundary_routes.py` 已在 `4ea4353` 刪乾淨，沒有殘留 import、沒有殘留測試 import（`test_scan_boundary_routes.py` 現在測的是 `/api/scans`，見 D-7）。

真正的死碼是**檔案內部的**：`app.py:267` 的模組級 singleton、`dependencies.py:58` 的 `build_manifest_service`、`scan_routes.py:267-273` 的死分支、以及 `create_app()` 10 個從未被使用的注入參數。刪這些**不會影響 core**（依賴方向是 `web -> core`，core 不 import web），但會影響 5 個直接戳 `app.state` 的測試（見 D-6）。

---

## 目前測試現況

### 覆蓋率（實際指令輸出）

```
$ cd /Users/linjunting/Systograph && uv run pytest tests/web -q --cov=src/systograph/web --cov-report=term-missing -p no:randomly

........................................................................ [ 80%]
.................                                                        [100%]
================================ tests coverage ================================
______________ coverage: platform darwin, python 3.11.15-final-0 _______________

Name                                                 Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------------------------------------
src/systograph/web/app.py                                 92      2      8      2    96%   87, 168
src/systograph/web/dependencies.py                        54      1      0      0    98%   59
src/systograph/web/legacy_mapping_guards.py               19      3      6      1    84%   18, 32-33
src/systograph/web/middleware.py                          62      5     16      6    86%   53, 64->49, 87, 97, 114, 131
src/systograph/web/routes/detail_scan_routes.py           73     13     20      9    76%   56, 83, 98-102, 106, 138, 141, 156, 157->153, 158->157, 160, 173
src/systograph/web/routes/map_build_routes.py             44      4      2      1    89%   64, 66, 105, 119
src/systograph/web/routes/map_routes.py                   36      1      6      1    95%   58
src/systograph/web/routes/mapping_proposal_routes.py      46      2      8      0    96%   93-94
src/systograph/web/routes/mapping_routes.py               26      4      0      0    85%   70-76
src/systograph/web/routes/project_routes.py               19      1      2      1    90%   28
src/systograph/web/routes/scan_routes.py                 109     15     22      6    84%   206, 235->241, 243, 250, 264-265, 268, 315-337, 338->344
src/systograph/web/routes/trace_routes.py                 34      3      8      1    90%   56, 62-63
src/systograph/web/schemas.py                            210      1      4      1    99%   151
src/systograph/web/session_store.py                      120      6     28      7    91%   63->67, 111->113, 122, 125, 186->exit, 207, 210-214, 225, 234->232
------------------------------------------------------------------------------------------------
TOTAL                                                  992     61    134     36    91%

5 files skipped due to complete coverage.
Required test coverage of 85.0% reached. Total coverage: 91.39%
89 passed in 55.45s
```

- **全綠**：89 passed，0 failed，exit code 0。
- **總覆蓋率 91.39%**（gate 85%），耗時 55.45s。
- 完全覆蓋（被 `skip_covered` 隱藏）的 5 檔推定為：`web/__init__.py`、`web/routes/__init__.py`、`web/inventory_error_response.py`、`web/inventory_preflight_projection.py`、`web/routes/viewer_routes.py`。

### 測試數量分佈

| 目錄/檔案 | 行數 | `TestClient(` 出現次數 |
|---|---|---|
| `tests/web/test_detail_scan_build_binding.py` | 277 | 7 |
| `tests/web/test_detail_scan_routes.py` | 94 | 1 |
| `tests/web/test_inventory_preflight_routes.py` | 371 | 7 |
| `tests/web/test_legacy_mapping_write_rejection.py` | 119 | 2 |
| `tests/web/test_local_api_hardening.py` | 110 | 4 |
| `tests/web/test_local_json_restart_recovery.py` | 217 | 14 |
| `tests/web/test_map_build_apply_routes.py` | 230 | 6 |
| `tests/web/test_map_routes.py` | 172 | 8 |
| `tests/web/test_mapping_proposal_routes.py` | 351 | 2 |
| `tests/web/test_mapping_routes.py` | 180 | 5 |
| `tests/web/test_nvidia_provider_app_wiring.py` | 40 | 0（只驗 `app.state`，不發請求） |
| `tests/web/test_project_scan_routes.py` | 207 | 6 |
| `tests/web/test_scan_boundary_routes.py` | 242 | 5 |
| `tests/web/test_trace_build_binding.py` | 51 | 2 |
| `tests/web/test_trace_routes.py` | 253 | 2 |
| `tests/web/test_viewer_routes.py` | 66 | 2 |
| **合計** | **2980** | **73** |

### `create_app()` 注入參數實際使用率（AST 掃描 `tests/**/*.py`）

全 repo 測試共 **82 個 `create_app()` 呼叫點**，參數組合分佈：

```
 41x  ('state_dir',)
 29x  ()                      ← 完全不注入
  2x  ('session_store',)
  2x  ('env_file',)
  2x  ('scan_snapshot_service', 'state_dir')
  1x  ('max_request_body_bytes',)
  1x  ('query_trace_service', 'session_store')
  1x  ('manual_mapping_service', 'mapping_proposal_service', 'state_dir')
  1x  ('manual_mapping_service', 'mapping_proposal_service')
  1x  ('mapping_proposal_service',)
  1x  ('manual_mapping_service', 'map_build_service', 'scan_snapshot_service', 'state_dir')
```

**19 個 kwargs 中，10 個從未被任何測試（也未被任何 production 呼叫端）使用：**
`allowed_origins`、`apply_confirmations_service`、`build_commit_service`、`detail_scan_build_service`、`detail_scan_service`、`inventory_preflight_service`、`inventory_selection_service`、`map_build_query_service`、`scan_boundary_review_service`、`viewer_session_service`。

（`app.py:168` — `inventory_preflight_service` 的顯式注入分支 — 也因此是 coverage 缺口。）

---

## 逐條發現

### D-1. `app.py:267` 的模組級 `app = create_app()` 是零引用死碼，且有 import-time 副作用

- **位置**：`src/systograph/web/app.py:267`
- **現況**
  ```python
  # src/systograph/web/app.py:267
  app = create_app()
  ```
  三個 production 入口全部用 factory 形式，沒有一個用這個 singleton：
  ```
  scripts/dev.py:55                    "systograph.web.app:create_app",
  scripts/dev.py:56                    "--factory",
  scripts/lib/api_trace_common.sh:109  .venv/bin/uvicorn systograph.web.app:create_app --factory \
  scripts/test_mapping_proposal_llm.sh:140  ... uvicorn systograph.web.app:create_app --factory ...
  ```
  `git grep "web.app:app"` 與 `git grep "from systograph.web.app import app"` 皆 **0 命中**。
- **為什麼是問題**
  1. 每次 `import systograph.web.app`（包含 20 個測試檔的 import、以及 `tests/unit/core/test_profile_inference_boundaries.py` 的 AST 掃描間接觸發）都會完整建構整張服務圖。
  2. 其中 `create_app` → `nvidia_nim_provider_from_env(env_file=Path(".env"))`（app.py:158-160）→ `llm_proposal_provider.py:206` `_dotenv_values(env_file or Path(".env"))`，**在 import time 讀取相對於 process CWD 的 `.env`**。
  3. `create_app` 開頭是 `canonical_output_version_from_env()`（app.py:138），設錯環境變數會在 **import 時**丟 `CanonicalOutputConfigurationError` 而非呼叫時 —— `tests/integration/test_v2_active_cutover.py:153` 這個測試正是靠「呼叫 `create_app()` 才 raise」的語意。
- **建議**：**刪除**。這是 production code 的刪除，不是測試變更。刪除後 `create_app` 仍是唯一 public 入口。
- **觸發條件**：Plan 1 把組裝搬到 `build_app_services()` 時，這一行會變成「在 import time 呼叫新工廠」，副作用範圍不變但更難察覺。趁重構一起刪最省事。
- **嚴重度**：**P2**

---

### D-2. `dependencies.py:58-59` `build_manifest_service` 是死 FastAPI dependency

- **位置**：`src/systograph/web/dependencies.py:58-59`
- **現況**
  ```python
  # src/systograph/web/dependencies.py:58
  def build_manifest_service(request: Request) -> BuildManifestService:
      return cast(BuildManifestService, request.app.state.build_manifest_service)
  ```
  `grep -rn "\bbuild_manifest_service\b" src/systograph/web/routes/` → **零命中**。
  coverage 佐證：`src/systograph/web/dependencies.py  54  1  0  0  98%  59`。
- **為什麼是問題**：18 個 dependency helper 裡有 1 個永遠不會被 FastAPI 解析。Plan 1 要「移除 17 個 `cast()`」時，這一個會被無意義地一起搬進 typed container。
- **建議**：**刪除** `dependencies.py:58-59`（含 `dependencies.py:16` 的 import）。注意 `app.state.build_manifest_service`（app.py:149）**不能刪** —— `DetailScanBuildService`（app.py:224）、`ApplyConfirmationsService`（app.py:206）、`MapBuildQueryService`（app.py:214）、`PersistentSessionStore`（app.py:235）都直接吃這個實例，只是不透過 `Depends`。
- **觸發條件**：Plan 1 Task 3「`dependencies.py` 從容器讀 typed 欄位」。
- **嚴重度**：**P3**

---

### D-3. `create_app()` 19 個 kwargs 中 10 個是無人使用的注入縫

- **位置**：`src/systograph/web/app.py:116-137`
- **現況**（AST 掃描 82 個測試呼叫點的結果，見上節表格）從未被使用的參數：
  ```
  allowed_origins            (app.py:134)
  apply_confirmations_service(app.py:131)
  build_commit_service       (app.py:133)
  detail_scan_build_service  (app.py:122)
  detail_scan_service        (app.py:121)
  inventory_preflight_service(app.py:126)   ← 對應死分支 app.py:167-168
  inventory_selection_service(app.py:127)
  map_build_query_service    (app.py:132)
  scan_boundary_review_service(app.py:124)
  viewer_session_service     (app.py:128)
  ```
- **為什麼是問題**：這 10 個 `X | None = None` + `X or Default()` 各自貢獻一個分支，是「為了假想的可測性」而存在的複雜度。Plan 1 會把它們原封不動搬進 `build_app_services()` 的 16 個可選參數，把死縫帶進新檔。
- **建議**：**不要在 Plan 1 一次刪**（會擴大 diff、破壞「行為不變」保證）。建議做法是：Plan 1 照搬（保持簽名不變），另開一個 follow-up 任務把這 10 個縫收斂成「只保留有測試在用的 9 個」。若堅持保留，至少各補一個 characterization test 證明注入確實生效（見第四節）。
- **觸發條件**：Plan 1 Task 1（`build_app_services()` 的 16 個可選參數清單）。
- **嚴重度**：**P2**

---

### D-4. `InMemorySessionStore` 是只被測試使用的 production code

- **位置**：`src/systograph/web/session_store.py:70-131`（62 行）
- **現況**：production 路徑只建 `PersistentSessionStore`：
  ```python
  # src/systograph/web/app.py:233
  app.state.session_store = session_store or PersistentSessionStore(...)
  ```
  唯二使用者是測試：
  ```
  tests/web/test_detail_scan_routes.py:13,77
  tests/web/test_trace_routes.py:17,168,228
  ```
  coverage 也顯示它的 `latest_viewer_payload`（line 122）、`latest_build_result`（line 125）從未被呼叫 —— 那兩個測試只用 `import_project` / `save_build_result` / `build_result`。
- **為什麼是問題**：`src/` 裡放 test double，違反「core engine platform-independent / production 不含測試腳手架」的直覺。而且它讓 2 個 web 測試走「假 store」路徑，跟其他 14 個走真 `PersistentSessionStore` 的測試行為不一致（例如 `latest_viewer_payload` 的 fallback 語意在兩個實作裡不同）。
- **建議**：**搬家** — `src/systograph/web/session_store.py` 的 `InMemorySessionStore` → `tests/helpers/web.py`。`SessionStore` Protocol（line 31-50）與 `save_committed_build_projection`（line 53-67）留在原處。
  ```python
  # tests/helpers/web.py（建議新增）
  from systograph.web.session_store import ProjectRecord, SessionStore

  class InMemorySessionStore:  # 原封不動搬過來
      ...
  ```
  然後改 `tests/web/test_detail_scan_routes.py:13`、`tests/web/test_trace_routes.py:17` 的 import。
- **觸發條件**：Plan 1 把 `session_store` 放進 `AppServices` typed 欄位時，型別會標成 `SessionStore` Protocol，此時 `InMemorySessionStore` 住哪都不影響型別——正是最便宜的搬家時機。
- **嚴重度**：**P3**

---

### D-5. `routes/__pycache__/scan_boundary_routes.cpython-314.pyc` 是刪檔殘留

- **位置**：`src/systograph/web/routes/__pycache__/scan_boundary_routes.cpython-314.pyc`
- **現況**：`.py` 已於 `4ea4353`（2026-06-12）刪除；`.pyc` 日期 `6月11日 18:21`，早於刪除 commit，屬舊 interpreter（3.14）留下的快取。`.gitignore:2` `__pycache__/` 已忽略，不會進版控。
- **為什麼是問題**：只有一個實際風險 —— 若有人以舊 Python 3.14 直譯器、且該目錄在 `sys.path` 上跑，理論上 `.pyc` 不會被 import（Python 3.3+ 起 `__pycache__` 內的 `.pyc` 沒有對應 source 就不會被載入）。所以**實際上無害**，純粹是雜訊。
- **建議**：`find src tests -name '__pycache__' -type d -exec rm -rf {} +` 清一次即可，不需要任何測試變更。
- **觸發條件**：無（與重構無關）。
- **嚴重度**：**P3**

---

### D-6. 5 個測試直接戳 `app.state.<service>`，Plan 1 容器化後必壞

- **位置**（精確到行）
  | 檔案:行號 | 所屬測試函式（def 行） |
  |---|---|
  | `tests/web/test_nvidia_provider_app_wiring.py:19` | `test_app_does_not_wire_nvidia_provider_without_explicit_flag`（:11） |
  | `tests/web/test_nvidia_provider_app_wiring.py:39` | `test_app_wires_nvidia_provider_when_enabled_from_dotenv`（:23） |
  | `tests/web/test_scan_boundary_routes.py:60` | `test_committed_scan_survives_session_projection_failure`（:45） |
  | `tests/web/test_map_build_apply_routes.py:123` | `test_committed_apply_survives_session_projection_failure`（:110） |
  | `tests/web/test_detail_scan_build_binding.py:98` | `test_committed_detail_build_survives_session_projection_failure`（:82） |

  這是全 repo 唯五的 `.state.` 命中（`grep -rn "\.state\." tests --include='*.py'`）。
- **現況**（貼真實 code）
  ```python
  # tests/web/test_nvidia_provider_app_wiring.py:17-20
  app = create_app(env_file=env_file)

  service = app.state.mapping_proposal_service
  assert service.provider is None
  ```
  ```python
  # tests/web/test_map_build_apply_routes.py:118-126
  def fail_save(*args: object, **kwargs: object) -> None:
      del args, kwargs
      raise RuntimeError("injected session projection failure")

  monkeypatch.setattr(
      app.state.session_store,
      "save_build_result",
      fail_save,
  )
  ```
- **為什麼是問題**
  1. `app.state.X` 在 mypy strict 下型別是 `Any`（Plan 1 `1.md:25-30` 已實測記錄），`app.state.completely_made_up_name` 也不報錯 —— 測試對 typo 完全沒有保護。
  2. Plan 1 `1.md:81-84` 明列這 4 個檔要改成 `.state.services.session_store` / `.state.services.mapping_proposal_service`。若 Task 2 依 `1.md:467-489` 同時保留舊屬性名（`app.state.session_store = services.session_store`），這些測試**表面上不會壞**，但這正是危險處：測試不會告訴你舊屬性其實已經是「同一物件的第二個別名」，之後刪舊別名時才炸。
  3. `monkeypatch.setattr(app.state.session_store, "save_build_result", ...)` 依賴「路由拿到的 store 與 `app.state.session_store` 是同一個實例」。若 `AppServices` 是 `frozen dataclass` 而 `dependencies.session_store()` 改讀 `request.app.state.services.session_store`，仍是同一實例 → 仍會通過。但只要有人在容器裡加 `field(default_factory=...)` 或做 per-request 建構，這三個測試會**靜默失效**（不再注入失敗，卻仍然 pass，因為它們斷言的是 `"session_projection_save_failed" in warnings`——注入失敗後 warning 不會出現，測試才會紅）。
- **建議**：**修改 + 集中**。不要在 5 個地方各自戳 `app.state`，改成一個 helper：
  ```python
  # tests/helpers/web.py（建議新增）
  from systograph.web.app import LocalApiApp
  from systograph.web.session_store import SessionStore

  def app_session_store(app: LocalApiApp) -> SessionStore:
      """Single choke point for tests that need the wired session store.

      重構時只有這一個函式要跟著 app.state -> app.state.services 改。
      """
      return app.state.session_store  # Plan 1 後：app.state.services.session_store
  ```
  三個 `*_survives_session_projection_failure` 測試改成：
  ```python
  monkeypatch.setattr(app_session_store(app), "save_build_result", fail_save)
  ```
  `test_nvidia_provider_app_wiring.py` 同理加 `app_mapping_proposal_service(app)`。
- **觸發條件**：Plan 1 Task 2（`create_app()` 改用 `build_app_services()`）+ Task 4（測試遷移）。
- **嚴重度**：**P1**

---

### D-7. `tests/web/test_scan_boundary_routes.py` 測的 route 檔已於 `4ea4353` 刪除，檔名現在是謊言

- **位置**：`tests/web/test_scan_boundary_routes.py`（242 行，5 個測試）
- **現況**：檔名對應的 `src/systograph/web/routes/scan_boundary_routes.py` 已刪。刪除前它提供的是 `GET/POST /api/scan-boundary-proposals`：
  ```python
  # git show 4ea4353^:src/systograph/web/routes/scan_boundary_routes.py
  router = APIRouter(tags=["scan-boundary-proposals"])

  @router.get("/api/scan-boundary-proposals", ...)
  def list_scan_boundary_proposals(...)

  @router.post("/api/scan-boundary-proposals", ...)
  def create_scan_boundary_proposals(...)
  ```
  現在這個檔測的**全部是 `/api/scans`**（`scan_project()` helper，line 27-42，POST `/api/scans`）：
  | 測試函式 | 行號 | 實際打的 route |
  |---|---|---|
  | `test_committed_scan_survives_session_projection_failure` | :45 | `POST /api/scans` + `GET /api/map-builds/{id}` |
  | `test_scan_requires_boundary_decision_before_building_map` | :76 | `POST /api/scans`、`GET /api/map` |
  | `test_scan_this_run_decision_builds_map_for_current_scan_only` | :114 | `POST /api/scans` |
  | `test_skip_this_run_decision_builds_map_without_current_file` | :152 | `POST /api/scans` |
  | `test_scan_rejects_stale_or_removed_boundary_decisions` | :189 | `POST /api/scans` |

  檔案歷史（`git log -- tests/web/test_scan_boundary_routes.py`）顯示它在刪 route 之後又被改了 3 次（`4ea4353` → `577f15b` → `0a68ccd`），一路演化成 `/api/scans` 的 boundary-decision 測試，**檔名沒跟著改**。
- **為什麼是問題**
  1. 找不到東西：想改 `/api/scans` 的人不會去看 `test_scan_boundary_routes.py`。
  2. 與 `tests/web/test_inventory_preflight_routes.py`（371 行，同樣測 `POST /api/scans` + boundary_decisions）、`tests/web/test_project_scan_routes.py`（207 行，同樣測 `POST /api/scans`）三檔重疊，三處各自維護 `import_project` helper。
  3. Plan 1 `1.md:83` 已把它列進「Task 4 要改的檔」，重構時會再碰一次這個誤導性檔名。
- **建議**：**搬家 + 改名**。
  - 把 `:76 / :114 / :152 / :189` 這 4 個 boundary-decision 測試搬進 `tests/web/test_inventory_preflight_routes.py`（它已經是 `/api/scans` + preflight/selection 的主場），或另建 `tests/web/test_scan_routes.py`。
  - `:45` 的 `test_committed_scan_survives_session_projection_failure` 與 D-15 的另外兩個同型測試合併（見下）。
  - 刪除空掉的 `test_scan_boundary_routes.py`。
  - 建議的最終落點：
    ```
    tests/web/test_scan_routes.py                 ← POST /api/scans 全部行為（含 boundary decisions）
    tests/web/test_inventory_preflight_routes.py  ← POST /api/projects/{id}/scan-preflights
    tests/web/test_session_projection_failure.py  ← 三條 commit-vs-projection 分離測試（D-15）
    ```
- **觸發條件**：Plan 1 Task 4；或任何人要改 `/api/scans` 的 boundary decision 語意。
- **嚴重度**：**P2**

---

### D-8. `tests/unit/core/*_boundaries.py` 從 unit 層 import web，違反 core 不依賴 web

- **位置**
  - `tests/unit/core/test_profile_inference_boundaries.py:19` `from systograph.web.app import create_app`
  - `tests/unit/core/test_query_trace_boundaries.py:6` `from systograph.web.routes import map_routes`
- **現況**
  ```python
  # tests/unit/core/test_profile_inference_boundaries.py:27-33
  FORBIDDEN_IMPORT_PREFIXES: Final = (
      "systograph.core.services.manual_mapping",
      ...
      "systograph.web",          # ← 宣告 core 不得 import web
  )
  ```
  ```python
  # tests/unit/core/test_profile_inference_boundaries.py:234-243
  def test_web_contract_has_no_profile_mutation_route(tmp_path: Path) -> None:
      app = create_app(state_dir=tmp_path / "state")
      mutation_routes = [
          route.path
          for route in app.routes
          if "profile" in route.path.lower()
          and set(route.methods or ()) & {"POST", "PUT", "PATCH", "DELETE"}
      ]
      assert mutation_routes == []
  ```
  ```python
  # tests/unit/core/test_query_trace_boundaries.py:9-18
  def test_static_map_paths_do_not_depend_on_query_trace_runtime_callers() -> None:
      map_build_source = inspect.getsource(map_build_service)
      map_route_source = inspect.getsource(map_routes)
      assert "EndpointCallProvider" not in map_route_source
      assert "QueryTraceService" not in map_route_source
  ```
- **為什麼是問題**
  1. `tests/conftest.py:24-30` 依目錄自動加 marker，所以這兩個檔被標成 `unit`。`uv run pytest -m unit` 因此會**啟動整個 FastAPI app**（含 `LocalJsonStateProvider`、`nvidia_nim_provider_from_env` 讀 `.env`），unit 層不再是 unit。
  2. `test_profile_inference_boundaries.py` 一邊宣告「`systograph.web` 是 core 的 forbidden import」（line 32），一邊自己 import 它（line 19）—— 斷言本身沒錯（它掃的是 `src/` 的 import graph），但檔案位置讓「unit 不碰 web」這條線失守。
  3. Plan 1 一旦改 `create_app` 的組裝順序或 `app.routes` 的註冊方式，`tests/unit/` 會紅 —— 沒有人預期 unit 測試會被 web 重構打到。
- **建議**：**搬家**（斷言內容一字不改）。
  - `test_profile_inference_boundaries.py:234-243` 的 `test_web_contract_has_no_profile_mutation_route` → 搬到 `tests/web/test_route_contract.py`。
  - `test_query_trace_boundaries.py` 整檔 → 拆兩半：對 `map_build_service` 的斷言留 `tests/unit/core/`，對 `map_routes` 的斷言搬 `tests/web/`。或整檔搬到 `tests/contracts/`（該目錄 marker 為 `contract`，語意最貼近「架構邊界契約」）。
  - 建議骨架：
    ```python
    # tests/web/test_route_contract.py（建議新增）
    from __future__ import annotations
    import inspect
    from pathlib import Path

    from systograph.web.app import create_app
    from systograph.web.routes import map_routes, viewer_routes


    def test_web_contract_has_no_profile_mutation_route(tmp_path: Path) -> None:
        app = create_app(state_dir=tmp_path / "state")
        mutation_routes = [
            route.path
            for route in app.routes
            if "profile" in route.path.lower()
            and set(route.methods or ()) & {"POST", "PUT", "PATCH", "DELETE"}
        ]
        assert mutation_routes == []


    def test_map_routes_do_not_import_runtime_trace_callers() -> None:
        source = inspect.getsource(map_routes)
        assert "EndpointCallProvider" not in source
        assert "QueryTraceService" not in source
    ```
  - 其餘 4 個純 AST/import-graph 測試（`test_profile_modules_do_not_depend_on_mutation_lifecycles` 等）留在原檔，它們不需要 import web。**但要注意**：留下來就必須把 `test_profile_inference_boundaries.py:19` 的 `from systograph.web.app import create_app` 一起刪掉，否則搬了測試沒搬 import，unit 仍然依賴 web。
- **觸發條件**：Plan 1 Task 2 改 `create_app()` 內部組裝；或 Plan 任何一步移動 `map_routes` 的程式碼位置。
- **嚴重度**：**P2**

---

### D-9. `inspect.getsource()` 白箱斷言：任何搬程式碼的重構都會誤報

- **位置**
  - `tests/web/test_viewer_routes.py:59-66` `test_viewer_route_is_thin_adapter_without_project_scan_logic`
  - `tests/unit/core/test_query_trace_boundaries.py:9-18`（同 D-8）
- **現況**
  ```python
  # tests/web/test_viewer_routes.py:59-66
  def test_viewer_route_is_thin_adapter_without_project_scan_logic() -> None:
      source = inspect.getsource(viewer_routes)

      assert "ViewerSessionService" in source
      assert "ProjectScanService" not in source
      assert "FilesystemProvider" not in source
      assert "ConfigParseProvider" not in source
      assert "DockerComposeProvider" not in source
  ```
- **為什麼是問題**
  1. 這是對「原始碼字串」而非「行為」的斷言。它會被**註解、docstring、type-only import** 觸發假陽性；也會被「把 `ProjectScanService` 改名」造成假陰性。
  2. Plan 1 若在 `viewer_routes.py` 加一行 `from systograph.web.app_services import AppServices`，這個測試不會壞；但若有人在 docstring 寫「本模組不得使用 ProjectScanService」，測試立刻紅。這種「文件會讓測試失敗」的性質是明確的設計缺陷。
  3. 同樣的架構意圖，`tests/unit/core/test_profile_inference_boundaries.py:89-114` 已經有更嚴謹的做法（`ast.parse` + BFS import graph，能抓遞移依賴）。兩套機制並存，弱的那套沒有存在必要。
- **建議**：**修改** —— 把字串比對換成 AST import 檢查，重用既有工具。
  ```python
  # tests/web/test_route_contract.py（承 D-8 的新檔）
  import ast
  from pathlib import Path

  ROUTE_DIR = Path("src/systograph/web/routes")
  SCANNER_SYMBOLS = frozenset({
      "ProjectScanService", "FilesystemProvider",
      "ConfigParseProvider", "DockerComposeProvider",
  })

  def _imported_names(path: Path) -> set[str]:
      tree = ast.parse(path.read_text(encoding="utf-8"))
      names: set[str] = set()
      for node in ast.walk(tree):
          if isinstance(node, ast.ImportFrom):
              names.update(alias.name for alias in node.names)
          elif isinstance(node, ast.Import):
              names.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
      return names

  def test_route_modules_do_not_import_scanner_internals() -> None:
      offenders = {
          path.name: sorted(_imported_names(path) & SCANNER_SYMBOLS)
          for path in sorted(ROUTE_DIR.glob("*.py"))
          if _imported_names(path) & SCANNER_SYMBOLS
      }
      assert offenders == {}
  ```
  這版同時把保護範圍從 `viewer_routes` 一檔擴大到全部 9 個 route 模組，而且不再被註解影響。
- **觸發條件**：任何搬動 route 模組程式碼、加註解、或在 route 加 typed import 的重構（Plan 1 Task 3 直接命中 `dependencies.py`，Task 2 可能碰 route）。
- **嚴重度**：**P2**

---

### D-10. `tests/web/` 沒有 conftest / 沒有任何 fixture：82 個 `create_app()` 呼叫點，6 種建 app 寫法

- **位置**：`tests/web/`（無 `conftest.py`；`find tests -name conftest.py` 只有 `tests/conftest.py`）；`grep -rn "@pytest.fixture" tests/web/ tests/e2e/` → **零命中**
- **現況** —— 目前 repo 裡並存的 6 種建 app 寫法：
  | 寫法 | 代表位置 |
  |---|---|
  | 1. 裸 `TestClient(create_app())` | `tests/web/test_map_routes.py:12`、`test_mapping_routes.py:11`、`test_viewer_routes.py:20` |
  | 2. `TestClient(create_app(state_dir=tmp_path / "state"))` | `tests/web/test_map_build_apply_routes.py:72`、`test_detail_scan_build_binding.py:48`、共 41 處 |
  | 3. `TestClient(create_app(...), raise_server_exceptions=False)` | `tests/web/test_local_api_hardening.py:14-17, 47, 72, 105` |
  | 4. module-level factory function 回傳 client | `tests/web/test_mapping_proposal_routes.py:63` `create_deterministic_test_app()`、`test_detail_scan_routes.py:73` `create_detail_scan_test_client()`、`test_trace_routes.py:198` `create_trace_test_client()` |
  | 5. 自刻假服務 + 注入 | `tests/web/test_trace_routes.py:20-35` `RecordingEndpointProvider`、`test_project_scan_routes.py:25-27` `MissingInventoryRuleLoader`、`test_mapping_proposal_routes.py:17-27` `UnavailableProvider`、`tests/e2e/test_apply_confirmations_build_lineage.py:34-56` `CountingProjectScanService` |
  | 6. `with TestClient(...) as client:`（唯一會跑 lifespan 的寫法） | `tests/e2e/test_apply_confirmations_build_lineage.py:188, 240` |

  `tests/helpers/` **已經有** `fixtures.py`（`rag_project_fixture_path`）與 `profile_inference.py`，但 `tests/helpers/` 裡**沒有任何 web/app 相關工具**，所以每個 web 測試都自己刻。`tests/conftest.py` 也只提供 `isolate_default_state_root`（line 35-40）這一個 autouse fixture。
- **為什麼是問題**
  1. Plan 1 若要調整 `create_app()` 的行為（即使簽名不變），沒有任何單一改動點 —— 82 個呼叫點散在 20 個檔案。
  2. 寫法 1（不給 `state_dir`）依賴 `tests/conftest.py:40` 的 `SYSTOGRAPH_STATE_DIR` monkeypatch，而寫法 2 顯式給 `state_dir` —— 兩種隔離機制並存，新測試不知道該選哪個。
  3. 唯一會跑 lifespan 的是 e2e 的 `with TestClient(...)`；tests/web 全部用非 context-manager 形式，等於 **web 層從未測過 startup/shutdown 行為**（目前 `create_app` 沒有 lifespan handler，但 Plan 1 之後若把服務建構移進 lifespan，這個缺口會立刻變成真問題）。
- **建議**：**新增** `tests/web/conftest.py`，提供一個 `local_api_client` fixture，在重構前先把 41 個 `TestClient(create_app(state_dir=tmp_path / "state"))` 收斂掉。
  ```python
  # tests/web/conftest.py（建議新增）
  from __future__ import annotations
  from collections.abc import Iterator
  from pathlib import Path

  import pytest
  from fastapi.testclient import TestClient

  from systograph.web.app import LocalApiApp, create_app


  @pytest.fixture
  def local_api_app(tmp_path: Path) -> LocalApiApp:
      """Default wiring: persistent state under tmp_path, no service overrides."""
      return create_app(state_dir=tmp_path / "state")


  @pytest.fixture
  def local_api_client(local_api_app: LocalApiApp) -> Iterator[TestClient]:
      with TestClient(local_api_app) as client:   # context manager => lifespan runs
          yield client
  ```
  然後分批把寫法 2 的 41 處換成 `local_api_client`。寫法 3/4/5 保留（它們是真的需要客製注入）。
- **觸發條件**：Plan 1 Task 2 / Task 4；以及未來任何在 `create_app` 加 lifespan 的變更。
- **嚴重度**：**P1**（不是「現在會壞」，而是「沒有它，重構的每一步都要改 40+ 個地方」）

---

### D-11. web 測試 import 別的測試模組的 helper（含跨 unit → web），是隱形的相依網

- **位置**
  ```
  tests/web/test_detail_scan_routes.py:6      from tests.unit.core.test_detail_scan_service import (base_map, build_router_project)
  tests/web/test_trace_routes.py:7            from tests.unit.core.test_detail_scan_service import (base_map, build_router_project)
  tests/web/test_local_json_restart_recovery.py:8  from tests.web.test_detail_scan_build_binding import prepare_detail_scan
  tests/web/test_local_json_restart_recovery.py:9  from tests.web.test_map_build_apply_routes import apply, prepare_apply
  tests/web/test_trace_build_binding.py:6     from tests.web.test_map_build_apply_routes import prepare_apply
  ```
  （對照組：`tests/cli/test_trace_command.py:7` 也 import `tests.unit.core.test_detail_scan_service`，所以這不是 web 獨有問題，但 web 層最密集。）
- **現況**
  ```python
  # tests/web/test_trace_routes.py:6-10
  from fastapi.testclient import TestClient
  from tests.unit.core.test_detail_scan_service import (
      base_map,
      build_router_project,
  )
  ```
- **為什麼是問題**
  1. `tests/unit/core/test_detail_scan_service.py` 是一個 **test module**，不是 helper module。改它的 `base_map()` 會靜默改變 3 個 web 測試 + 1 個 cli 測試 + 1 個 unit 測試（`test_query_trace_service.py:5`）的固定裝置。
  2. `test_local_json_restart_recovery.py` 同時 import 兩個 sibling web 測試模組的 helper（`prepare_detail_scan`、`prepare_apply`、`apply`）—— 這代表 D-7 建議的「拆 / 搬 `test_scan_boundary_routes.py`」和「合併 session-projection 測試」時，必須同步檢查這條 import 鏈，否則會 `ImportError`。
  3. pytest 的 module import 機制下，`tests/web/test_map_build_apply_routes.py` 會因為被 import 而被 collect 兩次的風險（目前因 `tests/conftest.py:17-18` 把 REPO_ROOT 塞進 `sys.path`、且用絕對 package path，尚未發生）。
- **建議**：**搬家** —— 把跨檔共用的 fixture builder 集中到 `tests/helpers/`。
  ```
  tests/helpers/system_map.py   ← base_map(), build_router_project()（從 tests/unit/core/test_detail_scan_service.py 搬出）
  tests/helpers/web_flows.py    ← prepare_apply(), apply(), prepare_detail_scan()（從兩個 web 測試檔搬出）
  ```
  搬完後 5 條 `from tests.<test module> import` 全部變成 `from tests.helpers.* import`，`tests/helpers/` 目錄的既有慣例（`fixtures.py` / `profile_inference.py` 已經是這個模式）也得以一致。
- **觸發條件**：D-7 的檔案搬家、D-15 的測試合併，兩者都會動到被 import 的模組。
- **嚴重度**：**P2**

---

### D-12. `import_project` / `_decision` helper 在 5 個檔各刻一份

- **位置**
  | helper | 位置 | 差異 |
  |---|---|---|
  | `import_project(client, project_root) -> str` | `tests/web/test_scan_boundary_routes.py:15` | 有 `assert response.status_code == 200` |
  | `import_project(client, project_root) -> str` | `tests/e2e/test_apply_confirmations_build_lineage.py:79` | **與上面逐字相同** |
  | `_import_project(client, root) -> str` | `tests/web/test_inventory_preflight_routes.py:15` | 參數名不同，body 相同 |
  | `_import(client, root) -> str` | `tests/e2e/test_inventory_selection_scan_flow.py:28` | 名字不同，body 相同 |
  | inline `client.post("/api/projects/import", ...)` | 另外 20 處（`grep -rn "api/projects/import" tests` = 20 命中） | — |
  | `_decision(proposal, action)` | `tests/web/test_inventory_preflight_routes.py:24` | 先取 `context = proposal["selection_context"]` |
  | `_decision(proposal, action)` | `tests/e2e/test_inventory_selection_scan_flow.py:37` | 直接內嵌存取，**語意完全相同** |
  | `scan_project(...)` | `tests/web/test_scan_boundary_routes.py:27` / `tests/e2e/test_apply_confirmations_build_lineage.py:91` | 前者支援 `boundary_decisions`，後者強制 `status == "completed"` |
- **現況**
  ```python
  # tests/web/test_inventory_preflight_routes.py:24-31
  def _decision(proposal: dict[str, Any], action: str) -> dict[str, str]:
      context = proposal["selection_context"]
      return {
          "target_path": str(proposal["target"]["path"]),
          "fingerprint": str(proposal["target"]["fingerprint"]),
          "decision": action,
          "selection_scope": str(context["selection_scope"]),
      }
  ```
  ```python
  # tests/e2e/test_inventory_selection_scan_flow.py:37-45
  def _decision(proposal: dict[str, Any], action: str) -> dict[str, str]:
      return {
          "target_path": str(proposal["target"]["path"]),
          "fingerprint": str(proposal["target"]["fingerprint"]),
          "decision": action,
          "selection_scope": str(
              proposal["selection_context"]["selection_scope"]
          ),
      }
  ```
- **為什麼是問題**：`POST /api/projects/import` 的 request/response 契約若要改（例如加必填欄位），要同時改 4 個 helper + 20 處 inline。這是 API contract 變更的隱性成本。
- **建議**：**搬家 + 合併** —— 併入 D-11 建議的 `tests/helpers/web_flows.py`：
  ```python
  # tests/helpers/web_flows.py（建議新增）
  def import_project(client: TestClient, project_root: Path) -> str:
      response = client.post(
          "/api/projects/import",
          json={"source_type": "local_path", "project_path": str(project_root)},
      )
      assert response.status_code == 200
      return str(response.json()["project_id"])


  def boundary_decision(proposal: dict[str, Any], action: str) -> dict[str, str]:
      return {
          "target_path": str(proposal["target"]["path"]),
          "fingerprint": str(proposal["target"]["fingerprint"]),
          "decision": action,
          "selection_scope": str(
              proposal["selection_context"]["selection_scope"]
          ),
      }
  ```
- **觸發條件**：`ProjectImportRequest`（`schemas.py:73-76`）或 `ScanBoundaryDecisionRequest` 的欄位變更。與 Plan 1 無直接關係，但屬於「重構前先整平」的低風險前置。
- **嚴重度**：**P3**

---

### D-13. 覆蓋率缺口：middleware 例外路徑、commit 衝突路徑、restart 後 latest_build 掃描、多條 4xx

以下全部有 coverage missing 行號佐證（見第二節輸出）。按重要性排序：

#### D-13a. `scan_routes.py:315-337` — build commit 失敗的整段 except 從未執行

- **位置**：`src/systograph/web/routes/scan_routes.py:315-337`（coverage `84% Missing: ... 315-337`）
- **現況**
  ```python
  # src/systograph/web/routes/scan_routes.py:315-325
  except BuildCommitError as exc:
      status_code = (
          409
          if exc.code
          in {
              "build_output_conflict",
              "stale_latest_revision",
          }
          else 500
      )
      raise HTTPException(status_code=status_code, detail=exc.code) from exc
  ```
- **為什麼是問題**：`POST /api/scans` 的「同一 project 併發掃描 / output dir 已存在 / latest pointer 被搶先推進」三種失敗，在 web 層**零測試**。這正是 `BuildCommitService` 存在的理由（`app.py:144-147`），也是 MODEL-CONTRACT 的 build lineage 保證。相對照，`/api/map-builds/{id}/apply` 的 409 有測（`test_map_build_apply_routes.py:155` `test_apply_route_is_idempotent_and_rejects_stale_base`），`/api/scans` 卻沒有。
- **建議**：**新增**（characterization，見第四節 N-3）。
- **嚴重度**：**P1**

#### D-13b. `session_store.py:207, 210-214` — `PersistentSessionStore.latest_build_result()` 的跨 project pointer 掃描從未執行

- **位置**：`src/systograph/web/session_store.py:200-214`
- **現況**
  ```python
  # src/systograph/web/session_store.py:200-214
  def latest_build_result(self) -> MapBuildResult | None:
      if self._latest_build_result is not None:
          return self._latest_build_result
      candidates = []
      for project in self._repository.list_projects():
          pointer = self._repository.get_latest_pointer(project.project_id)
          if pointer is not None:
              candidates.append(pointer)
      if not candidates:
          return None                      # ← line 207，未覆蓋
      pointer = max(                       # ← line 210-214，未覆蓋
          candidates,
          key=lambda item: (item.updated_at, item.latest_build_id),
      )
      return self.build_result(pointer.project_id)
  ```
- **為什麼是問題**：這是 **restart 之後 `GET /api/map` 與 `GET /api/map/report` 唯一的資料來源**（`map_routes.py:42, 51`）。`tests/web/test_local_json_restart_recovery.py` 測了 restart 後的 `/api/projects/{id}`、`/api/mappings`、`/api/map-builds/latest`，**唯獨沒測 restart 後的 `/api/map`**。而 `/api/map` 是 frontend 的主要入口（`frontend/src/services/viewerApi.ts:5`）。
- **建議**：**新增**（見第四節 N-1）。
- **嚴重度**：**P1**

#### D-13c. `middleware.py` — 非 HTTP scope 的 re-raise 與串流 body 的大小限制

- **位置**：`src/systograph/web/middleware.py:53, 64->49, 87, 97, 114, 131`
- **現況**
  ```python
  # middleware.py:52-65（64->49 分支未覆蓋 = 多 chunk body 從未被測）
  if message["type"] != "http.request":
      continue                              # ← 53，未覆蓋
  total_bytes += len(message.get("body", b""))
  if total_bytes > self._max_request_body_bytes:
      ...
  if not message.get("more_body", False):
      break                                 # ← 64->49 分支未覆蓋
  ```
  ```python
  # middleware.py:85-95
  except InvalidStateIdError:
      if scope["type"] != "http":
          raise                             # ← 87，未覆蓋
  except ProjectStateBusyError:
      if scope["type"] != "http":
          raise                             # ← 97，未覆蓋
  except Exception as exc:
      ...
      if scope["type"] != "http":
          raise                             # ← 114，未覆蓋
  ```
  ```python
  # middleware.py:128-131
  async def __call__(self) -> Message:
      if self._messages:
          return self._messages.pop(0)
      return {"type": "http.request", "body": b"", "more_body": False}   # ← 131，未覆蓋
  ```
- **為什麼是問題**
  1. **串流 body 完全沒測**：`test_local_api_hardening.py:13` `test_large_request_returns_413_with_cors_header` 送的是單一 chunk（`content=b'{"project_path":"' + b"x"*80 + b'"}'`），走 `more_body=False` 一次就 break。多 chunk 累加超限的路徑（`64->49` 回圈）從未執行 —— 而這正是「攻擊者用 chunked encoding 繞過 body limit」的地方。
  2. `_ReplayReceive` 的耗盡 fallback（line 131）沒測：若下游 handler 重複呼叫 `receive()`（FastAPI 在某些 form/multipart 情境會），這行決定不會 hang。
  3. 三處 `scope["type"] != "http"` 的 re-raise 沒測：`/api/scan/events`（SSE，`scan_routes.py:354`）雖然是 http，但 SSE 在 `SafeUnhandledExceptionMiddleware` 內丟例外的行為完全沒驗證。
- **建議**：**新增**（見第四節 N-4、N-5）。
- **嚴重度**：**P2**

#### D-13d. 一票 4xx 路徑沒測

| route | 未覆蓋行 | 未測的行為 |
|---|---|---|
| `project_routes.py:28` | 28 | `GET /api/projects/{unknown}` → 404 `project_not_found`。（`test_local_json_restart_recovery.py:51,66` 只測 200 路徑） |
| `mapping_routes.py:70-76` | 70-76 | `PATCH /api/mappings/{unknown}` → 404 `mapping_not_found`；`PATCH` 帶非法 payload → 422。（`test_mapping_routes.py:93` 只測 200） |
| `map_build_routes.py:105` | 105 | `GET /api/projects/{id}/map-builds/latest` 的 `KeyError` → 404 `build_not_found`（現有測試打到的是 middleware 的 `resource_not_found`，不是這行） |
| `map_build_routes.py:119` | 119 | `GET /api/projects/{unknown}/map-builds` → 404 `project_not_found` |
| `map_build_routes.py:64, 66` | 64, 66 | apply 的 `ApplyValidationError` → 422、`ProjectStateBusyError` → 503 |
| `map_routes.py:58` | 58 | `map_markdown_path` 有值但檔案已被刪 → 404（現有 `test_map_report_route_before_build_returns_404` 打的是 `result is None` 那條） |
| `trace_routes.py:56` | 56 | `build_id` 屬於別的 project → 404 `build_not_found`（`test_detail_scan_build_binding.py:174` 有 detail-scan 版，trace 版沒有） |
| `trace_routes.py:62-63` | 62-63 | 專案 `pyproject.toml` 的 `[tool.systograph.trace]` 壞掉 → 400 `invalid_trace_config`（`test_trace_routes.py:133` 只測 happy path） |
| `detail_scan_routes.py:138, 141` | 138, 141 | `GET /api/detail-scans/{unknown}` → 404 `detail_scan_not_found`；`map_not_loaded` → 404 |
| `detail_scan_routes.py:106` | 106 | `detail_build_incomplete` → 500 |
| `mapping_proposal_routes.py:93-94` | 93-94 | `create_proposal` 的 `ValueError` → 422 |
| `schemas.py:151` | 151 | `MapBuildScopedResponse.from_core` 缺 lineage/viewer 時的 `ValueError` |
| `legacy_mapping_guards.py:18, 32-33` | 18, 32-33 | 非 dict payload；body 非合法 JSON 時的 `JSONDecodeError` 放行 |
| `app.py:87` | 87 | `SYSTOGRAPH_STATE_DIR` 未設時 fallback 到 `~/.systograph`（`tests/conftest.py:40` autouse 永遠設了它，所以這條**在測試環境中不可能執行**） |
| `app.py:168` | 168 | 顯式注入 `inventory_preflight_service=` 的分支（對應 D-3） |

- **嚴重度**：**P2**（單一條都不致命，但合起來代表「錯誤契約」這一層沒有回歸保護；`docs/API-GUIDE.md` 的錯誤碼目前沒有測試背書）

---

### D-14. `test_local_api_cors_does_not_use_wildcard_origin` 驗的是屬性，不是 CORS 行為

- **位置**：`tests/web/test_map_routes.py:152-157`
- **現況**
  ```python
  # tests/web/test_map_routes.py:152-157
  def test_local_api_cors_does_not_use_wildcard_origin() -> None:
      app = create_app()

      origins = app.allowed_origins
      assert "*" not in origins
      assert "http://127.0.0.1:5173" in origins
  ```
- **為什麼是問題**
  1. `app.allowed_origins` 是 `LocalApiApp.__init__`（`app.py:102`）存下來的 tuple，跟真正掛上去的 `CORSMiddleware(allow_origins=list(origins))`（`app.py:253-259`）之間沒有任何強制關聯。把 `app.py:255` 改成 `allow_origins=["*"]` 而不動 `allowed_origins`，這個測試**照樣綠**。
  2. 全 repo **沒有任何測試發過 OPTIONS preflight**，也沒有任何測試驗證「不在白名單的 Origin 拿不到 `access-control-allow-origin`」。現有 3 個 CORS 斷言（`test_local_api_hardening.py:29, 55, 80`）全部只驗「合法 Origin 會拿到 header」。
  3. `allow_methods=["GET", "PATCH", "POST", "OPTIONS"]`、`allow_headers=["Accept", "Content-Type"]`、`allow_credentials=False`（`app.py:256-258`）三個安全設定零測試。
- **建議**：**修改 + 新增**。把這個測試改成行為斷言，並補負面案例：
  ```python
  # tests/web/test_local_api_hardening.py（建議追加）
  def test_disallowed_origin_gets_no_cors_header() -> None:
      client = TestClient(create_app(), raise_server_exceptions=False)

      response = client.get("/api/map", headers={"Origin": "http://evil.example"})

      assert response.status_code == 200
      assert "access-control-allow-origin" not in response.headers


  def test_preflight_advertises_only_expected_methods_and_headers() -> None:
      client = TestClient(create_app(), raise_server_exceptions=False)

      response = client.options(
          "/api/map/build",
          headers={
              "Origin": "http://127.0.0.1:5173",
              "Access-Control-Request-Method": "POST",
              "Access-Control-Request-Headers": "content-type",
          },
      )

      assert response.status_code == 200
      allowed = {
          item.strip()
          for item in response.headers["access-control-allow-methods"].split(",")
      }
      assert allowed == {"GET", "PATCH", "POST", "OPTIONS"}
      assert "access-control-allow-credentials" not in response.headers
  ```
- **觸發條件**：Plan 1 若把 CORS wrapping 從 `create_app` 尾端（`app.py:253-264`）搬進 `AppServices` / 另一個工廠，現有測試不會察覺行為改變。
- **嚴重度**：**P2**

---

### D-15. 三個 `*_survives_session_projection_failure` 是同一條規則的三份拷貝，散在三個檔

- **位置**
  | 檔案:def 行 | route |
  |---|---|
  | `tests/web/test_scan_boundary_routes.py:45` | `POST /api/scans` |
  | `tests/web/test_map_build_apply_routes.py:110` | `POST /api/map-builds/{id}/apply` |
  | `tests/web/test_detail_scan_build_binding.py:82` | `POST /api/detail-scans` |
- **現況**：三者的注入片段**逐字相同**（唯一差別是 route 與斷言 warning 的位置）：
  ```python
  def fail_save(*args: object, **kwargs: object) -> None:
      del args, kwargs
      raise RuntimeError("injected session projection failure")

  monkeypatch.setattr(
      app.state.session_store,
      "save_build_result",
      fail_save,
  )
  ```
  它們驗的是同一條不變式：`session_store.save_committed_build_projection`（`session_store.py:53-67`）—— commit 成功後 projection 失敗只加 warning，不回滾 build。
- **為什麼是問題**
  1. 三份拷貝 = D-6 的 `app.state` 耦合被放大三倍。
  2. 三者都只測 `RuntimeError`；`save_committed_build_projection` 實際 catch 的是 `(OSError, RuntimeError, ValueError)`（line 61），另外兩型從未驗證。
  3. `session_store.py:63->67` 分支（warning 已存在時不重複加）未覆蓋 —— 三個測試都沒觸發。
- **建議**：**合併 + 搬家**到 `tests/web/test_session_projection_failure.py`，用 parametrize 收斂：
  ```python
  # tests/web/test_session_projection_failure.py（建議新增，取代三處拷貝）
  import pytest

  @pytest.mark.parametrize("error", [RuntimeError, OSError, ValueError])
  def test_commit_survives_any_projection_error(...) -> None:
      ...

  @pytest.mark.parametrize(
      "flow", ["scan", "apply", "detail_scan"],
  )
  def test_committed_build_is_readable_after_projection_failure(...) -> None:
      """三條 route 共用同一條 commit-vs-projection 分離不變式。"""
  ```
  三個 route 的 setup 分別重用 D-11 建議的 `tests/helpers/web_flows.py` 的 `prepare_apply` / `prepare_detail_scan`。
- **觸發條件**：Plan 1 Task 4（三個檔都被列在 `1.md:81-83` 的待改清單）。
- **嚴重度**：**P3**（不緊急，但和 D-6 一起改成本最低）

---

## 建議新增的測試清單

以下全部是**重構前先補**的 characterization test —— 目的不是找 bug，是把「現在的行為」釘住，讓 Plan 1 的「行為不變」有客觀依據。按優先序排列。

### N-1（P1）restart 之後 `/api/map` 仍能還原最新 build

- **測試檔**：`tests/web/test_local_json_restart_recovery.py`（追加，該檔已有 restart 情境）
- **測試函式**：`test_latest_viewer_payload_survives_restart`
- **要斷言什麼**
  ```python
  def test_latest_viewer_payload_survives_restart(tmp_path: Path) -> None:
      state_dir = tmp_path / "state"
      first = TestClient(create_app(state_dir=state_dir))
      project_id, base_build_id, _ = prepare_apply(first, tmp_path)
      before = first.get("/api/map").json()
      assert before["viewer_load_result"]["loaded"] is True

      second = TestClient(create_app(state_dir=state_dir))   # 全新 process，記憶體 store 是空的
      after = second.get("/api/map").json()

      assert after["viewer_load_result"]["loaded"] is True
      assert after == before
      report = second.get("/api/map/report")
      assert report.status_code == 200
  ```
- **為什麼現在沒有**：`PersistentSessionStore.latest_build_result()` 的 `_latest_build_result is None` fallback（`session_store.py:203-214`）在同一個 process 內永遠不會走到（`save_build_result` 已經填了快取）。只有「新 app 物件 + 舊 state_dir」才會觸發。現有 restart 測試（`test_local_json_restart_recovery.py:57-78`）只查 `/api/projects`、`/api/mappings`、`/api/map-builds/latest`，剛好全部繞過這條路。
- **觸發條件**：Plan 1 把 `session_store` 放進 `AppServices` 時，若 `PersistentSessionStore` 的建構時機或 `_latest_build_result` 初始值變了，這是唯一會抓到的測試。

### N-2（P1）`app.state` 對外契約的鎖定（Plan 1 的驗收基準）

- **測試檔**：`tests/web/test_app_wiring_contract.py`（新增）
- **測試函式**：`test_app_state_exposes_every_wired_service`
- **要斷言什麼**
  ```python
  EXPECTED_STATE_ATTRIBUTES = frozenset({
      "state_repository", "build_manifest_service", "build_commit_service",
      "state_dir", "manual_mapping_service", "mapping_proposal_service",
      "scan_boundary_review_service", "inventory_preflight_service",
      "inventory_selection_service", "map_build_service",
      "scan_snapshot_service", "apply_confirmations_service",
      "map_build_query_service", "detail_scan_service",
      "detail_scan_build_service", "query_trace_service",
      "viewer_session_service", "session_store",
  })

  def test_app_state_exposes_every_wired_service(tmp_path: Path) -> None:
      app = create_app(state_dir=tmp_path / "state")
      for name in EXPECTED_STATE_ATTRIBUTES:
          assert getattr(app.state, name, None) is not None, name


  def test_dependency_helpers_resolve_to_the_wired_instances(tmp_path: Path) -> None:
      """每個 Depends helper 拿到的必須是 create_app 建的同一個物件。"""
      app = create_app(state_dir=tmp_path / "state")
      request = SimpleNamespace(app=app)     # dependencies.py 只用 request.app.state
      assert dependencies.session_store(request) is app.state.session_store
      assert dependencies.map_build_service(request) is app.state.map_build_service
      # ...其餘 16 個
  ```
- **為什麼現在沒有**：目前只有 5 處零散的 `app.state.X` 斷言（D-6），且都是順帶驗證。沒有任何測試把「`create_app` 到底 wire 了哪 18 個服務」寫下來。Plan 1 `1.md:426-427` 承諾「`app.state` 上原有的 18 個屬性名稱與值也完全不變」—— **這個承諾目前沒有測試可以驗證**。
- **觸發條件**：Plan 1 Task 2 的整段替換（`1.md:441` 說要把 app.py 138-237 行整段換掉）。這是那一步唯一的安全網。

### N-3（P1）`POST /api/scans` 的 build commit 衝突回 409

- **測試檔**：`tests/web/test_scan_routes.py`（D-7 建議的新檔）
- **測試函式**：`test_scan_returns_409_when_build_output_conflicts`、`test_scan_returns_409_on_stale_latest_revision`
- **要斷言什麼**
  ```python
  def test_scan_returns_409_when_build_output_conflicts(tmp_path: Path) -> None:
      """覆蓋 scan_routes.py:315-325 的 BuildCommitError -> 409 分支。"""
      client = TestClient(create_app(state_dir=tmp_path / "state"),
                          raise_server_exceptions=False)
      project_id = import_project(client, make_project(tmp_path))
      # 讓 output dir 事先存在且不可寫 / 或注入會丟 BuildCommitError 的 build_commit_service
      response = client.post("/api/scans", json={"project_id": project_id,
                                                 "output": str(conflicting_output)})
      assert response.status_code == 409
      assert response.json()["detail"] in {"build_output_conflict",
                                           "stale_latest_revision"}
      # 且不得留下 snapshot / build manifest
      repository = LocalJsonStateProvider(tmp_path / "state")
      assert repository.list_build_manifests(project_id) == ()
  ```
  這也是 `create_app(build_commit_service=...)` 這個目前零使用的注入縫（D-3）的第一個正當用途。
- **為什麼現在沒有**：`scan_routes.py:315-337` 整段零覆蓋。`/api/map-builds/{id}/apply` 有等價測試（`test_map_build_apply_routes.py:155`），`/api/scans` 沒有——兩者用的是同一個 `BuildCommitService`，行為理應對稱。
- **觸發條件**：任何動到 `BuildCommitService` 或 `scan_routes.create_scan` 的重構。

### N-4（P2）串流／chunked body 的 413 上限

- **測試檔**：`tests/web/test_local_api_hardening.py`（追加）
- **測試函式**：`test_chunked_body_exceeding_limit_returns_413`
- **要斷言什麼**
  ```python
  def test_chunked_body_exceeding_limit_returns_413() -> None:
      """覆蓋 middleware.py 的 64->49 累加回圈（多 chunk 才會走到）。"""
      client = TestClient(create_app(max_request_body_bytes=32),
                          raise_server_exceptions=False)

      def chunks() -> Iterator[bytes]:
          for _ in range(8):
              yield b"x" * 16        # 每塊 16 bytes，第 3 塊時累計超過 32

      response = client.post(
          "/api/map/build",
          headers={"Content-Type": "application/json"},
          content=chunks(),
      )

      assert response.status_code == 413
      assert response.json() == {"detail": "request_too_large"}


  def test_body_at_exactly_the_limit_is_accepted() -> None:
      """邊界值：== limit 應該放行（現在的實作是 > 才擋）。"""
  ```
- **為什麼現在沒有**：`test_large_request_returns_413_with_cors_header`（`test_local_api_hardening.py:13`）送單一 chunk，一次 break，`more_body=True` 的累加路徑從未執行。這正是 body-limit middleware 最容易被繞過的地方。
- **觸發條件**：任何動 `RequestSizeLimitMiddleware.__call__`（`middleware.py:34-68`）的變更，包含 Plan 1 若調整 middleware 掛載順序。

### N-5（P2）SSE endpoint 在 middleware 下的行為

- **測試檔**：`tests/web/test_local_api_hardening.py`（追加）
- **測試函式**：`test_sse_stream_is_not_buffered_by_hardening_middleware`
- **要斷言什麼**
  ```python
  def test_sse_stream_is_not_buffered_by_hardening_middleware() -> None:
      """RequestSizeLimitMiddleware 只處理 POST/PUT/PATCH；GET SSE 必須直通。"""
      client = TestClient(create_app())
      with client.stream("GET", "/api/scan/events",
                         headers={"Origin": "http://localhost:5173"}) as response:
          body = "".join(response.iter_text())
      assert response.status_code == 200
      assert response.headers["x-accel-buffering"] == "no"
      assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
      assert "event: scan_progress" in body
  ```
- **為什麼現在沒有**：`test_map_routes.py:160` `test_scan_events_returns_sse_completed_event` 有測 SSE 內容，但**沒帶 Origin**，所以 SSE + CORS wrapping 的組合零驗證。而 `app.py:253` 是把整個 FastAPI app 包進 `CORSMiddleware` 再回傳，SSE 走的是這條包裝路徑。
- **觸發條件**：Plan 1 若改變 `app.add_middleware` 與 `CORSMiddleware(...)` 的相對順序（`app.py:239-243` vs `253-259`）。

### N-6（P2）錯誤契約回歸表（一次補齊 D-13d 的 4xx 缺口）

- **測試檔**：`tests/web/test_error_contract.py`（新增）
- **測試函式**：`test_documented_error_codes_are_stable`（parametrize）
- **要斷言什麼**
  ```python
  @pytest.mark.parametrize(
      ("method", "path", "payload", "status", "detail"),
      [
          ("GET",   "/api/projects/project:unknown",              None, 404, "project_not_found"),
          ("GET",   "/api/projects/project:unknown/map-builds",   None, 404, "project_not_found"),
          ("PATCH", "/api/mappings/mapping:unknown", {"decision": "rejected"},
                                                            404, "mapping_not_found"),
          ("GET",   "/api/detail-scans/detail:unknown",           None, 404, "detail_scan_not_found"),
          # ...
      ],
  )
  def test_documented_error_codes_are_stable(...) -> None:
      response = client.request(method, path, json=payload)
      assert response.status_code == status
      assert response.json()["detail"] == detail
  ```
  注意：要用**存在的 project/mapping id 格式**（`project:xxx`），否則會被 `SafeUnhandledExceptionMiddleware` 的 `InvalidStateIdError` 攔截成 `resource_not_found`（這正是 `test_local_api_hardening.py:100` 在測的另一條路）——兩條路的差異本身就值得寫下來。
- **為什麼現在沒有**：`docs/API-GUIDE.md` 定義的錯誤碼目前沒有集中的回歸測試；散落在各檔的 happy-path 測試順帶測到一部分，缺口見 D-13d 表。
- **觸發條件**：任何改 route 例外處理的重構；也是 `frontend/API_CONTRACT.md` 的後端側背書。

### N-7（P3）`session_store.save_committed_build_projection` 的三種例外型別

- **測試檔**：`tests/web/test_session_projection_failure.py`（D-15 建議的新檔）
- **測試函式**：`test_projection_failure_adds_warning_once`（parametrize `RuntimeError / OSError / ValueError`）
- **要斷言什麼**
  ```python
  @pytest.mark.parametrize("error_type", [RuntimeError, OSError, ValueError])
  def test_projection_failure_adds_warning_for_every_caught_type(error_type) -> None:
      """session_store.py:61 catch 三型，目前只有 RuntimeError 被測過。"""

  def test_projection_warning_is_not_duplicated() -> None:
      """覆蓋 session_store.py:63->67 分支：warning 已存在時不重複追加。"""
  ```
- **為什麼現在沒有**：三個現有測試（D-15）都只丟 `RuntimeError`；`session_store.py:63->67` 分支零覆蓋。
- **觸發條件**：Plan 1 若把 `save_committed_build_projection` 移進 `AppServices` 或改成方法。

---

## 附錄：重構前的最小安全網（如果只做三件事）

1. **N-2**（`test_app_wiring_contract.py`）—— Plan 1 Task 2 的整段替換沒有它就是裸奔。
2. **D-10**（`tests/web/conftest.py` 的 `local_api_client` fixture）—— 把 41 個重複的 app 建構收斂成一處，Task 4 的改動量從 40+ 降到 1。
3. **D-6**（`tests/helpers/web.py` 的 `app_session_store()` choke point）—— 5 個 `app.state` 直戳點收成 1 個，`.state.services` 遷移只改一行。

這三項全部是**加法**（新增檔案 + 改 import），不動任何斷言，可以在 Plan 1 Task 1 之前先合併，風險趨近於零。
