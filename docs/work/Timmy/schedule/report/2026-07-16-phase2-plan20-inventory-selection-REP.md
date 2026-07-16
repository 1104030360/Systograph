# Phase 2 Plan 20 Scan Inventory Selection 驗收報告

## 結論

Plan 20 Backend scope 已完成。KAI-Mind 現在會先建立 metadata-only inventory preflight，
讓 caller 以 project-relative exact file 或 bounded recursive directory 送出當次 delta；backend
重新枚舉並驗證 fingerprint 後，依 hard safety、exact file、deepest directory、ancestor
directory、default policy 的固定優先序建立唯一 final `FileInventory`。

Frontend implementation 與 UA integration 仍依 scope freeze 延後。本階段沒有修改
`frontend/src`，也沒有新增 UA request、service call、sidecar、`files[]` adapter 或 parity
runtime。

## 實作邏輯

1. Plan 19 的 `scan_inventory_rules.toml` 先產生 deterministic default outcome。
2. Candidate enumeration 保留 default included、soft excluded、hard blocked、missing 與 collapsed
   directory metadata；preflight 不讀候選內容。
3. Exact file 與 directory proposal 都使用 metadata／manifest fingerprint，API 不回 internal
   manifest entries、absolute root、snippet 或 secret value。
4. Directory expansion 以 5,000 files、500,000,000 bytes、64 depth、20 scopes 與 aggregate
   dedupe fail closed；整庫 default inventory 不受 recursive selection 上限誤傷。
5. Submit 時重新 enumeration；duplicate、conflict、scope mismatch、missing、stale、hard block 與
   over-limit 都回 stable typed error，且不建立 scan/snapshot/build。
6. 通過 decision 後才用 directory-handle traversal、`O_NOFOLLOW`、`fstat`、bounded binary probe
   與同一 file handle 的 SHA-256 做 post-decision safety；缺少必要 primitive 時 fail closed。
7. Final inventory 才交給 current providers；snapshot 保存 policy、candidate、decision、final、run
   digests、per-file audit 與 directory selection summary。
8. Apply 重用保存的 snapshot；Rescan 重新建立 inventory，不沿用前一次 one-run decision。

## 實作步驟

### 1. Candidate 與 preflight

- 新增 frozen Pydantic candidate、manifest、preflight、summary 與 selection models。
- 拆分 Git source、ignore、base enumeration、classifier、directory walker／resolver、risk、metadata、
  cursor 與 limit services，避免把新分支繼續堆進既有大型 provider。
- 支援 tracked-but-missing、`.git/info/exclude`、configured global exclude、nested `.gitignore`、
  project root `.`、collapsed ignored directory 與 explicit exact target。
- 新增 `POST /api/projects/{project_id}/scan-preflights` 與 bounded projection。

### 2. One-run decision 與安全 materialization

- 新增 decision normalization、precedence、proposal、post-decision safety、audit、result 與
  materializer services。
- Exact decision 勝過 directory；directory 間以 deepest scope 勝出；hard safety 永遠不可覆寫。
- Directory child binary／unreadable 可單筆阻擋並保留 audit；exact file post-decision block 則整次
  fail closed。
- Snapshot 前重新驗證 metadata 與 content fingerprint，避免 selection 後內容漂移進入保存狀態。

### 3. API、snapshot、CLI 與文件

- `POST /api/scans` additive 支援 `preflight_request_id` 與 selection summary；舊 sensitive
  decision flow 保持可用。
- API error detail 統一為 `{code, message, retryable, context}`；preflight 與 pre-snapshot error
  沒有 `scan_id`。
- CLI、history repository、snapshot manifest 與 scan result 保存 provenance；legacy optional fields
  仍可讀。
- 同步 `docs/API-GUIDE.md`、`docs/MODEL-CONTRACT.md`、`frontend/API_CONTRACT.md`、Phase 2
  pipeline ASCII map 與 `docs/work/Timmy/learn/architecture.md`。
- 新增 `scripts/trace_inventory_selection_preflight.sh`，實際驗證非法路徑 422、metadata-only
  preflight、directory scan、exact child skip、binary child block 與 target tree unchanged。

## TDD／BDD 測試方式

測試先以 Given／When／Then 鎖定行為，再補最小實作。主要情境包括：

- 5,000／5,001 files、500,000,000／500,000,001 bytes、64／65 depth、20／21 scopes。
- Parent／child overlap dedupe、non-overlap aggregate overflow、default inventory 超過 5,000 files。
- Required review 200／201、tracked missing、private／global exclude、unmatched ignore pattern。
- Preflight no-content-read、cursor project/digest binding、malformed cursor、bounded API projection。
- Duplicate／conflict／scope mismatch／hard block／missing／stale typed errors。
- Exact over directory、deepest directory、directory scan + exact skip、directory child post block。
- Missing safe-open primitive、open 後 `fstat` 漂移、同 handle content hash、snapshot content drift。
- No optional decision 與 Plan 19 parity、idempotence、Apply snapshot reuse、Rescan recompute。
- E2E target tree／Git status unchanged、snapshot audit count、no secret／root leakage。

## Review 與 runtime debugging audit

因本次明確禁止 subagent，`review-work` 的五條 review lane 由同一執行者逐條完成：

| Lane | 結果 | 主要證據 |
| --- | --- | --- |
| Goal／constraints | PASS | Plan 19 gate、Plan 20 Backend DoD 與 scope boundary 逐條回查 |
| Hands-on QA | PASS | 真實 FastAPI + curl trace；happy path 200、非法路徑 422 |
| Code quality | PASS | ruff、strict mypy；core 不 import web；selection responsibilities 拆分 |
| Security | PASS | no shell invocation、project-relative projection、safe-open/fstat/hash、secret/root contract tests |
| Context | PASS | 對照 Plan 19/20、API/MODEL contracts、Phase 2 pipeline 與相關 git history |

三個可推翻實作的 runtime hypotheses：

1. **H1：wheel 安裝後 catalog resource 遺失。** 直接 build wheel、檢查
   `kai_mind/core/rules/scan_inventory_rules.toml`，再從 `/tmp` 使用隔離 venv 載入安裝版
   `kai_mind`；觀察 `wheel_resource=ok`、17 rules。H1 refuted。
2. **H2：preflight 後的 metadata／content 漂移仍可混入 snapshot。** 執行 safe-open `fstat`
   change、snapshot content change 與 stale E2E；`7 passed`，changed target 回 409 且沒有
   snapshot/build。H2 refuted。
3. **H3：非法路徑或 one-run decision 會產生 artifact／修改 target。** 真實 API 回
   `422 inventory_selection_path_invalid` 且無 `scan_id`；完整 trace 回 200 completed，前後
   target digest 相同。H3 refuted。

Silent-failure audit 未發現新 selection runtime 的 bare `except`、`shell=True`、debug statement、
2xx error payload 或成功後 stale snapshot。Repo 內其他既有 service 的 broad exception handlers
不屬本階段變更，未擴張修改。

## 遇到的問題與解法

### 1. Existing provider 把 candidate 與 final inventory 混在一起

直接在 `FilesystemProvider` 增加 ignored-directory picker 會讓 preflight 提前讀內容，也會讓
downstream 看見尚未核准的檔案。解法是建立 metadata-only candidate pipeline，直到 decision 與
post-decision safety 完成後才 materialize final inventory。

### 2. Git source 有 tracked-missing 與 exclude source 差異

`git ls-files` 可能回傳 index 中存在但 worktree 已缺少的 path；`check-ignore -v` 的 source 又可能
是 relative private exclude 或 absolute global exclude。解法是把 missing 保存成 typed candidate，
並只投影 stable source enum，不回原始 source path／stderr。

### 3. Metadata fingerprint 不能單獨解決 TOCTOU

只在 open 前 `resolve/stat` 仍可能被 symlink swap 或內容替換。解法是逐層 directory handle
`openat` traversal、不 follow symlink、open 後比較 type／size／mtime／dev／inode，並在同一
handle 上 probe 與 hash；snapshot 前再比對 content fingerprint。

### 4. Directory 上限可能被 overlap 或多次 preflight 繞過

若只驗證單一 manifest，parent／child 或多個 individually-valid scope 可以超過 aggregate
budget。解法是在 preflight 與 submit 都以 canonical child path 去重後重算 aggregate，任何超限
都在 walker／materialization 前 fail closed，不回 partial approval。

### 5. Final wheel smoke 的第一次 probe 用錯 resource 名稱

第一次 probe 誤查不存在的 JSON 名稱；真實契約是 packaged TOML。確認 loader source 後改查
`kai_mind/core/rules/scan_inventory_rules.toml`，wheel build 與隔離安裝載入均成功，未做不必要的
packaging 修改。專案 `.venv` 沒有 `build`／`pip`，因此只在 temp venv 安裝 build tool，沒有污染
repo environment。

### 6. Manual QA shell 初次使用 zsh 保留變數 `status`

負向 curl driver 第一次在 zsh 因 read-only `status` 立即停止；改用 `http_status` 後重跑，取得
真實 422 typed response。產品 runtime 沒有失敗。

### 7. Frontend handoff completed sample 仍是舊 build shape

逐份用 current Pydantic 驗證 Step 2 JSON 時，completed response 的 `build_result` 仍使用舊的
`{status, build_id}`。依 current `MapBuildResult` 改為 `project_name + lineage.build_id`，補回
`preflight_request_id` 與 boundary actions，並同步 handoff README／Meeting-Sync 狀態。修正後
8 份 samples 全部通過 current Pydantic；這只代表 backend handoff ready，不冒充 frontend 已實作。

## 最終測試結果

```text
focused debug hypotheses                7 passed in 3.09s
Step 2 current Pydantic samples          8 passed
shell script portability                1 passed in 0.06s
full backend pytest                     972 passed in 62.15s
ruff check src tests                    All checks passed
mypy src                                181 source files, no issues
git diff --check                        passed
wheel build                             successfully built kai_mind-0.1.0 wheel
wheel installed loader smoke            17 rules loaded from installed package
live invalid preflight                  HTTP 422 inventory_selection_path_invalid
live happy path trace                   HTTP 200 preflight + HTTP 200 completed scan
target project side-effect check        unchanged
```

## 交付邊界

- 未修改 `frontend/src`；沒有執行 frontend test／lint／build，因其不是本 Backend DoD。
- 未新增或呼叫 UA runtime；既有 snapshot optional `ua_analysis_result` 欄位不是本階段整合。
- 未改 target repo、`.gitignore`、Git config、catalog runtime state或Manual Mapping。
- 未建立 commit、stage、push 或 PR；保留目前 worktree 供使用者審閱。
