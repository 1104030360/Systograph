# Inventory Selection Policy Catalog（scan_inventory_rules.toml）實作計畫

Status: planned（ASCII map Step 2 📦 擴充點的 owner plan；Plan 16 request construction 的
hard prerequisite）

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:test-driven-development`，依 characterization → failing contract test →
> minimal implementation → regression 的順序逐 task 執行。步驟使用 checkbox（`- [ ]`）。
>
> 本計畫是 `phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md` Step 2 標示
> 「📦 `scan_inventory_rules.toml` 待建」的唯一 owner。

**Goal:** 建立 Step 2 的 `inventory selection policy catalog`，把 KAI-Mind 擁有的預設
path selection 規則從 Python 常數移到可驗證、可稽核、可重現的 TOML；使用者對可疑檔案的
`scan_this_run` / `skip_this_run` 決策仍由既有 boundary lifecycle 擁有。

**Architecture:** Candidate enumeration 仍分成 Git、recursive 與 Git failure fallback；三種
source 共用同一份 KAI inventory catalog 與不可覆寫的 filesystem safety checks。Catalog
只決定 Step 2 的 path selection，不做 Step 3 scan fact、component mapping 或 profile inference。

**Tech Stack:** Python 3.11、Pydantic v2、`tomllib`、`importlib.resources`、`pathspec.GitIgnoreSpec`、
pytest。

## Global Constraints

- Scanner 與 loader 必須 read-only，不寫 target repo。
- `max_file_size_bytes`、binary content detection 等數值／內容安全判斷留在 Python。
- TOML 不得包含 `plane_id`、`reference_node_id`、component/profile trigger 或 scan-fact
  `rule_id`。
- 所有 path 在匹配前正規化為 project-relative POSIX path；catalog v1 固定 case-sensitive，
  不依 Windows/macOS filesystem case behavior 改變結果。
- 不得把 invalid/missing catalog 解讀成空 inventory 或成功掃描。
- 新增 JSON 欄位必須 additive；既有 snapshot 仍可讀，新 snapshot 則必須寫入 policy version
  與 digest。

---

## 名詞決策：這是 policy catalog，不是純 metadata

`path_rules` 會直接決定檔案能否進入 scanner，因此它是 executable **inventory selection
policy**。只有 `inventory_limit_metadata` 的 binary/oversize 說明文字屬於純 metadata。

| 放進 TOML | 留在 Python |
| --- | --- |
| KAI default path rules：dependency/build/cache/generated/model-weight 等 path pattern | outside-root symlink、unreadable、binary content detection |
| `inventory_policy_id`、`action`、`pattern`、`reason`、`category`、`message` | `max_file_size_bytes`、binary probe bytes 等數值門檻 |
| binary/oversize 的描述 metadata | boundary proposal/decision/fingerprint lifecycle |
| catalog schema version | scan fact、component bridge、profile inference、projection |

`inventory_policy_id` 是 Step 2 audit id，不是 Step 3 provider 的 scan-fact `rule_id`。

## Runtime boundary 決策到底覆寫什麼

是，這裡的 runtime policy 就是 scanner 找到 `.env`、credential-like config 或 model/vector
persistence 等可疑檔案後，詢問使用者這次要不要掃描的流程。

目標流程固定為：

```text
Git / recursive candidate enumeration
  -> project ignore semantics
  -> non-overridable filesystem safety checks
  -> KAI inventory selection policy catalog
  -> eligible FileInventory
  -> ScanBoundaryReviewService 建立可疑檔案 proposals
  -> 使用者 decision
       scan_this_run -> 保留在 files，記錄 included audit
       skip_this_run -> 移到 skipped，記錄 skipped audit
       無 decision / fingerprint 過期 -> pending_boundary_review
  -> providers 只讀 final inventory
```

### 覆寫邊界

| 層級 | Owner | 可否由本次使用者 decision 覆寫 | 規則 |
| --- | --- | ---: | --- |
| Project source boundary | Git / nested `.gitignore` | 否 | 不重新加入 candidate source 沒列出的路徑 |
| Filesystem safety | Python | 否 | outside-root symlink、unreadable、binary、oversize 必須跳過 |
| KAI default path policy | TOML | 否 | 只有 catalog 內較後面的 `action="include"` 可反轉同 catalog 的 exclude |
| Boundary review | Python + user decision | 是，只限本層 | `scan_this_run` / `skip_this_run` 只處理已進入 eligible inventory 的可疑檔案 |

因此不再使用含糊的「runtime policy 與 TOML 衝突時一律優先」。正確 contract 是：runtime
decision 只覆寫 boundary-review 的 pending/skip 狀態，不得把 catalog 或 safety 已排除的路徑
重新加入。若未來要讓使用者臨時 override catalog，必須另開 plan，在 catalog filter 前保留
candidate inventory；本計畫不做。

Boundary-managed fixture（例如 `.env`）不得被 default catalog 先排除，否則使用者永遠看不到
proposal。必須用 contract test 鎖定「先進 eligible inventory，再等待 boundary decision」。

## 為什麼有 Git 與 recursive 兩種模式

`FilesystemProvider` 需要同時處理兩種真實輸入：

1. **Git mode**：目標路徑是 Git worktree。使用
   `git ls-files --cached --others --exclude-standard`，讓 Git 正確處理 tracked/untracked、
   nested `.gitignore`、`.git/info/exclude` 與 global excludes。
2. **Recursive mode**：解壓縮、複製或匯入的專案可能沒有 `.git`。使用 `os.walk`，並以
   `GitIgnoreSpec` 讀取 repo 內 nested `.gitignore`。
3. **Fallback mode**：偵測到 Git worktree，但 `git ls-files` 執行失敗時，改走 recursive，
   source 必須標成 `fallback_after_git_error` 並留下 warning。

三種模式共用 KAI catalog 與 filesystem safety，但 candidate source 有以下刻意差異：

| Case | Git mode | Recursive / fallback | Target contract |
| --- | --- | --- | --- |
| tracked file 後來被 `.gitignore` pattern 命中 | Git 仍列出，因為 tracked file 不受 ignore 排除 | 無 tracked 資訊，依 `.gitignore` 排除 | 保留此差異並以 fixture 說明 |
| `.git/info/exclude` / global excludes | `--exclude-standard` 會套用 | 不讀取 Git private/global state | 保留此差異；recursive 只信 target tree 內檔案 |
| KAI `dist/`、`node_modules/` 等 default policy | catalog 套用於 Git 列出的 path | catalog 在 walk pruning / file classification 套用 | included file set 必須一致；這是本計畫的 parity correction |
| outside-root symlink、binary、oversize | Python safety skip | Python safety skip | 結果一致且不可 override |
| skip audit granularity | Git 可能是逐 file | recursive 可記 directory summary | 允許粒度不同，但 source/rule/reason 必須可解釋 |

Parity 的意思不是兩種 source 永遠列出完全相同的 candidates，而是：排除上述已記錄的 source
差異後，同一 KAI policy 與 safety condition 必須得到相同 included file set。

## Glob contract

- Catalog 使用 ordered `path_rules[]`，不再同時維護語意重疊的 `ignore[]` 與
  `include_overrides[]`。
- 每條 rule 欄位固定為：`inventory_policy_id`、`action`（`exclude` / `include`）、
  `pattern`、`reason`、`category`、`message`。
- Pattern 採 Gitignore-style 語意：`/` 是 project root anchor、trailing `/` 只匹配 directory、
  `*` 不跨 `/`、`**` 可跨 directory。
- `action` 已表達 include/exclude，因此 pattern 不得以未 escape 的 `!` 開頭。
- Catalog 內多條 rule 命中時，最後命中的 rule 獲勝；`include` 只能反轉較早的 catalog
  `exclude`，不得反轉 project-source 或 filesystem-safety exclusion。
- Recursive walker 不得因 directory 命中 `exclude` 就無條件 prune。若後續 `include` pattern
  可能命中該 directory 的 descendant，walker 必須繼續 traversal、只對最終 file decision
  套用 last-match-wins；只有證明沒有任何後續 descendant include 時才可安全 prune。
- 匹配前一律把 `\\` 轉成 `/`；不接受 absolute path、`..` traversal 或空 pattern。
- Loader 必須保存 source order，不得用 set/dict 重排規則。

參考語意：Gitignore pattern specification、Semgrepignore v2 precedence 與專案現有
`GitIgnoreSpec`；實作不得自行發明第三套 glob DSL。

## Audit、fail-closed 與重現性 contract

### Audit model

只記錄 project-relative path 與 policy metadata，不記錄檔案內容、secret value 或 absolute
local path。

```text
InventoryPolicyAuditEntry
  path: str
  outcome: included | skipped | pending_review
  source: project_ignore | filesystem_safety | kai_inventory_catalog | runtime_boundary
  source_mode: git | recursive | fallback_after_git_error
  audit_scope: path | directory_summary
  reason: str
  matched_inventory_policy_ids: list[str]  # source order；只含 catalog matches
  effective_inventory_policy_id: str | null
  matched_pattern: str | null             # effective rule pattern only
  boundary_decision: scan_this_run | skip_this_run | null
  target_fingerprint: str | null
```

- `FileInventory` 攜帶 catalog schema version、SHA-256 digest 與 audit entries。
- `ProjectScanResult` 保存 audit entries，讓 snapshot 能回答「為什麼掃／為什麼沒掃」。
- Audit 只對 enumeration 曾觀察到的 path，以及 recursive 可確定 prune 的 directory summary
  提供完整理由。Git 未列出的 ignored/untracked path 不得假裝被逐檔 audit；要以
  `source_mode="git"` 與 candidate-source summary 清楚標示此邊界。
- `ScanSnapshot` 與 `ScanSnapshotManifest` 保存
  `inventory_policy_schema_version`、`inventory_policy_digest`、`inventory_run_digest` 與
  `inventory_source_mode`。
- 新欄位對舊 snapshot 為 optional/nullable；新 scan write path 必須填值。舊資料缺值時標成
  `legacy_inventory_policy_unknown`，不得假裝使用目前 catalog。
- Catalog digest 使用實際載入的 UTF-8 bytes 計算 `sha256:<hex>`；只要規則檔內容改變就產生
  新 digest，即使 inventory 結果剛好相同也不得沿用舊 digest。

### Reproducibility digest

`inventory_run_digest` 不等於 catalog digest。它以 sorted-key canonical JSON 序列化下列欄位後
計算 SHA-256；list 全部依 project-relative POSIX path、再依 stable id 排序：

```text
inventory_source_mode
candidate_set_digest       # enumeration 實際交給 policy 的 path + size/fingerprint
inventory_policy_digest    # 實際載入的 TOML bytes
filesystem_safety_version  # Python safety checks 的明確版本
boundary_decision_digest   # path + decision + target_fingerprint；無 decision 也有空集合 digest
final_inventory_digest     # included/skipped/pending + reason/id 的 canonical result
```

- 同一份 target state、source mode、catalog、safety version 與有效 decision set 必須產生相同
  audit ordering 與 digest；任一輸入改變就不得宣稱是同一次可重現 inventory。
- Git failure fallback 是另一個 `inventory_source_mode`，即使 final files 恰好相同也會產生不同
  run digest，並附 `git_enumeration_failed_fallback_used` warning。
- Digest 只納入 path、size、content/target fingerprint 等既有非內容 provenance；不得把完整
  file content、secret value、absolute root 或未遮蔽錯誤訊息放進 canonical JSON/audit。

### Fail-closed

`ScanInventoryRulesError` 對外只暴露穩定 code：

- `inventory_rules_unavailable`：packaged resource 缺失或不可讀。
- `inventory_rules_invalid`：TOML parse、schema version、unknown field、duplicate id、非法
  action/pattern 或其他 validation 失敗。

發生錯誤時：

- inventory build 立即中止；不得 fallback 到 Python hidden defaults 或空 catalog。
- 不建立 scan snapshot、canonical map 或成功 manifest。
- CLI/API 回傳穩定 error code；log/error artifact 必須遮蔽 absolute path 與 catalog content。
- loader unit test、service propagation test、CLI/API contract test都必須覆蓋。

Git enumeration failure 可依既有 contract 進入 recursive fallback，因為這不是 catalog
validation failure；但 fallback 必須留下上列 source mode、stable warning 與不同 run digest。
若 fallback 也無法建立 project-relative boundary 或無法安全解析 nested ignore source，則以
`inventory_enumeration_failed` 中止，不得用未稽核的 raw `os.walk` 結果繼續。

## 依賴

- 可與 S1 Track 其他工作並行實作，但 **Plan 16 request construction 不得在本計畫完成前
  定案**；UA `files[]` allowlist 必須保存同一份 inventory policy digest。
- 不影響 Plan 18 退役範圍；`scan_inventory_rules.toml` 是 Plan 18 明列的保留項。

## Task 1：定義 catalog schema、loader 與錯誤 contract

Files:

- Create: `src/kai_mind/core/rules/scan_inventory_rules.toml`
- Create: `src/kai_mind/core/services/scan_inventory_rule_loader.py`
- Modify: `src/kai_mind/core/models/errors.py`
- Create: `tests/unit/core/test_scan_inventory_rule_loader.py`

Interfaces:

- `ScanInventoryRuleLoader.load_default() -> ScanInventoryPolicyCatalog`
- `ScanInventoryRuleLoader.load(path: Path) -> ScanInventoryPolicyCatalog`
- `ScanInventoryPolicyCatalog.schema_version == "scan-inventory-policy/v1"`
- `ScanInventoryPolicyCatalog.catalog_digest == "sha256:<hex>"`

Steps:

- [ ] 先寫 valid catalog、packaged resource、source-order 與 digest tests。
- [ ] 寫 invalid TOML、unknown field、duplicate id、unsupported schema、absolute/traversal/blank
  pattern、未 escape `!` 與 invalid action 的 failing tests。
- [ ] 以 Pydantic `extra="forbid"` 建立 frozen typed catalog；`load_default()` 只用
  `importlib.resources` 讀 package-bundled TOML。
- [ ] 將 unavailable/invalid failure 對應到上述穩定 error code；不得在 message 印 catalog
  原文或 absolute resource path。
- [ ] 執行 built wheel resource smoke check，確認 wheel 內含
  `kai_mind/core/rules/scan_inventory_rules.toml` 且 installed import 可讀。

## Task 2：統一 Git／recursive 的 KAI policy application

Files:

- Modify: `src/kai_mind/core/models/filesystem.py`
- Modify: `src/kai_mind/core/providers/filesystem_provider.py`
- Modify: `src/kai_mind/core/models/scan.py`
- Modify: `src/kai_mind/core/services/project_scan_service.py`
- Test: `tests/unit/core/test_filesystem_provider.py`
- Test: `tests/integration/test_phase7_filesystem_provider_behaviors.py`

Steps:

- [ ] 先補 mode matrix characterization tests：Git、recursive、fallback × tracked/untracked ×
  file/directory × exclude/include。
- [ ] 對 tracked + ignored、`.git/info/exclude`、global exclude 建立 mode-specific expected
  tests，不把刻意差異誤判成 regression。
- [ ] 把 KAI-owned directory/suffix defaults 移入 ordered `path_rules`，Git path list 與
  recursive walk 共用同一 matcher；不得保留 hidden Python default list。
- [ ] 加入「directory 先 exclude、descendant 後 include」fixture，證明 recursive 不會因過早
  prune 漏檔，且與 Git mode 的 catalog decision 一致。
- [ ] 對 Git mode 目前未套用 directory defaults 的行為建立 failing parity test，再把它改成
  catalog-controlled skip；在 migration report 明列此 intentional delta。
- [ ] 保留 Python safety checks，並驗證 catalog `include` 不能重新納入 outside-root symlink、
  unreadable、binary、oversize。
- [ ] 產生 deterministic audit entries 與完整 `inventory_run_digest`；相同 target state、source
  mode、catalog bytes、safety version、decision 必須得到相同排序與 digest。
- [ ] Windows-looking `\\` path 與 POSIX path 需命中同一 rule；大小寫不同則不得命中。

## Task 3：收斂 runtime boundary overlay

Files:

- Modify: `src/kai_mind/core/services/scan_boundary_review_service.py`
- Modify: `src/kai_mind/core/models/scan_boundary.py`（只有 audit contract 需要時）
- Test: `tests/unit/core/test_scan_boundary_review_service.py`
- Test: `tests/unit/core/test_project_scan_service.py`

Steps:

- [ ] 先寫 `.env` / vector persistence fixture，證明它們先進 eligible inventory，再產生
  proposal；default catalog 不得先排除。
- [ ] `scan_this_run` 保留 file 並新增 included audit；`skip_this_run` 移到 skipped 並新增
  skipped audit。
- [ ] 無 decision、decision target fingerprint 不符或過期時，保持
  `pending_boundary_review`，不得沿用 stale approval。
- [ ] 證明 runtime decision 無法重新加入 catalog/safety skipped path。
- [ ] 同一 decision 重放必須 idempotent，audit 不得重複。

## Task 4：把 policy provenance 寫入 snapshot 與錯誤 surface

Files:

- Modify: `src/kai_mind/core/models/analysis_history.py`
- Modify: `src/kai_mind/core/services/scan_snapshot_service.py`
- Modify: `src/kai_mind/web/routes/scan_routes.py`
- Modify: `src/kai_mind/web/schemas.py`（若錯誤 response 有 typed schema）
- Test: `tests/integration/test_scan_snapshot_materialization.py`
- Test: `tests/web/test_project_scan_routes.py`

Steps:

- [ ] 新 snapshot/manifest 必須保存 policy schema version、catalog digest、source mode 與
  `inventory_run_digest`；舊 fixture 缺值仍可讀，並明確標示 legacy unknown provenance。
- [ ] Invalid/missing catalog 必須在 provider collection 前中止，API 回傳穩定 code，且 state
  repository 不存在新 snapshot/build/manifest。
- [ ] Git enumeration error 可 fallback 且有不同 source mode/digest；fallback 無法安全建 inventory
  時以 `inventory_enumeration_failed` 中止，並驗證沒有成功 artifact。
- [ ] 重放相同 snapshot 時使用 snapshot 保存的 provenance，不得把目前 catalog digest 冒充成
  歷史 scan 使用的 digest。
- [ ] 驗證 audit response 不含 absolute root、檔案內容或未遮蔽 secret。

## Task 5：文件對照更新

Files:

- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase4-scanner-expansion/00-phase2-pipeline-ascii-map.md`
- Modify: `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/README.md`
- Modify: `docs/MODEL-CONTRACT.md`

Steps:

- [ ] 把 ASCII map Step 2 的「待建」改成 policy catalog + digest + audit 現況。
- [ ] README 記錄 Plan 19 是 Plan 16 `files[]` provenance 的前置。
- [ ] MODEL-CONTRACT 記錄兩種 candidate source、刻意 mode 差異、runtime boundary
  override 範圍與 legacy snapshot provenance 語意。

## Acceptance Criteria

- [ ] `scan_inventory_rules.toml` 是 KAI Step 2 default path policy 的唯一 source of truth；
  Python 不保留 hidden path default list。
- [ ] TOML 名稱與文件一律使用 `inventory selection policy catalog`，不再把 executable
  path rules 稱為純 metadata。
- [ ] Git／recursive／fallback 的共同 policy 行為與刻意差異都有 characterization tests。
- [ ] Runtime user decision 只覆寫 boundary-review 狀態，不可越過 project source、catalog
  或 filesystem safety boundary。
- [ ] Invalid/missing catalog fail closed；不建立 snapshot/canonical/manifest，且有 loader、
  service、CLI/API tests。
- [ ] 每次新 scan 都可回讀 policy schema version、digest 與 deterministic audit trail。
- [ ] 每次新 scan 都可回讀 candidate/policy/safety/decision/final-result 組成的
  `inventory_run_digest`；Git fallback 不會冒充正常 Git enumeration。
- [ ] 新 audit/provenance 欄位 additive；legacy snapshot 仍可讀但標示 policy unknown。
- [ ] Windows/macOS 使用相同 POSIX-normalized、case-sensitive catalog matching contract。
- [ ] Plan 16 UA request 的 `files[]` 與 snapshot 保存相同 inventory policy digest。

## 邊界 / 不做事項

- 不改 boundary decision lifecycle（blocked → proposals / completed → inventory policy）。
- 不提供每次 scan 臨時 override catalog 的新 UI/API。
- 不新增 scan fact、component mapping、profile trigger 或第三份 rule DSL。
- 不把數值 threshold 或 binary content 判斷移入 TOML。
- 不寫 target repo；scanner 維持 read-only。

## 外部研究依據（2026-07-15）

- [Git `git-ls-files` 官方文件](https://git-scm.com/docs/git-ls-files) 明定
  `--cached` 會列 tracked files，`--exclude-standard` 會加入 nested `.gitignore`、
  `.git/info/exclude` 與 global excludes；[Git `gitignore` 官方文件](https://git-scm.com/docs/gitignore)
  也明定 tracked files 不受 ignore 影響，以及同 precedence 內最後命中規則勝出。這是兩種
  candidate mode 無法假裝完全等價的依據。
- [Semgrepignore v2 reference](https://docs.semgrep.dev/semgrepignore-v2-reference) 將 fixed
  target-safety rules、project ignore 與 configurable filters 分層，並提供 excluded target 的理由
  檢視；本計畫借用分層/可解釋性，不照搬其 CLI override precedence。
- [vercel-labs/deepsec Git source enumeration](https://github.com/vercel-labs/deepsec/blob/main/packages/deepsec/src/sandbox/upload.ts)
  是目前 open-source Git-list + non-Git fallback + symlink safety 的實例；
  [Grafana codeowners metadata](https://github.com/grafana/grafana/blob/main/scripts/codeowners-manifest/metadata.js)
  則示範對排序後的 Git candidate list 建 digest。本計畫另外要求 catalog、decision、safety
  version 與 final result 都進入 provenance，不能只 hash path list。
