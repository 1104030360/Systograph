# Phase 2 Plan 13 ai-system-map/v2 Active Cutover TODO

## 目標

依 `phase7.md` 與 Plan 13 完成 backend generic `ai-system-map/v2` active cutover。先修復
00A compatibility gate，再以 TDD + BDD 遷移 producer／consumer、legacy mapping、
extension write surface 與 10-artifact atomic visibility；保留 v1 dual-read 與隔離的
operator rollback writer，且不修改被掃描的 target project。依後續ownership指示，frontend
維持原始版本並另列handoff，不算backend完成範圍。

## 已確認基線

- [x] 閱讀 `AGENTS.md`、Linus rule、Phase 7、Plan 13、00A 與相關 reports。
- [x] worktree 為乾淨 `main...origin/main`；使用者已要求直接完成本 goal，因此在既有工作區
  執行，不另建旁支 worktree。
- [x] backend baseline：`972 passed`；Ruff 與 Mypy 通過。
- [x] frontend baseline：`3 files / 7 tests passed`；TypeScript/Vite build 與 ESLint exit 0。
  既有 Fast Refresh warning 與 Vite chunk warning另行記錄，不冒充本次 regression。
- [x] Stage A 起始 blocker 已重現：native-v2 manifest reload 失敗、paired readiness
  regression 與 executable consumer allowlist 尚不存在。
- [x] 00A gate 已修復：native v1/v2 reload、normalized Viewer projection、paired canonical
  facts/readiness、51-hit allowlist、完整 backend/Ruff/Mypy 均通過；Plan 13 可進入
  `ready`。

## 實作邏輯

1. `CanonicalMapLoader` 是唯一 schema dispatch owner；所有 active consumer只接
   normalized `AiSystemMapV2` 或 `GraphViewModel`。
2. 正常 build只產生一份 v2 canonical map；v1只能由 process-level operator rollback
   setting啟用，且 process內仍立即 normalize成 v2。
3. Legacy extension mapping先以隔離 DTO dry-run／apply migration，再從backend active enum/API
   停寫；缺資料或 extension edges一律 quarantine，不猜測 canonical truth。Frontend停寫另由
   前端負責人承接。
4. Artifact-set publish與 latest promotion是兩個獨立 visibility boundary；10 siblings先在
   same-parent staging完成驗證，再 publish directory、persist complete manifest、CAS promote。
5. 每個 production behavior先寫 Given／When／Then測試並觀察正確 RED，再以最小程式碼
   轉 GREEN；scanner、migration report與 logs不得輸出完整 secret、evidence snippet或
   absolute path。

## 執行階段與步驟

### 階段 A：計畫與 00A gate

- [x] 以 live code、tests與 runtime probe更新 Plan 13 blocker evidence。
- [x] RED：補 native-v2 manifest/restart reload與 paired grounded readiness equivalence tests。
- [x] GREEN：讓 manifest／Viewer normalized path先經唯一 loader，補齊 00A Task 4/5。
- [x] 建立 executable direct-consumer allowlist，重跑 quality gates並把 Plan 13改為 `ready`。
- [x] 建立本階段 Report，附 red/green、reload與 census digest證據。
- [x] Final audit repair：paired fixtures 比較完整 canonical facts；census 納入 frontend JSON
  與 scripts；non-object root、雙向 manifest badge mismatch 均 fail closed。
- [x] 抽離 Viewer v1 compatibility helpers 前先補 recommended-next-check characterization，
  並把 Viewer 收斂至 250 LOC 以下。

### 階段 B：Canonical producer 與 active consumers

- [x] RED：鎖定 v2 default、單一 `MapBuildResult.ai_system_map`、public v1 selection拒絕、
  operator env與 rollback fail-closed contract。
- [x] GREEN：正常 producer直接建立 v2，隔離 `LegacyV1RollbackService`，移除 process內雙真相。
- [x] RED/GREEN：遷移 manifest、viewer、detail scan、query trace、profile/readiness、renderers、
  CLI/API與 session consumers。
- [x] 建立本階段 Report與 focused/full regression證據。

### 階段 C：Persisted mapping 與 extension write retirement

- [x] RED：覆蓋 dry-run零寫入、apply/restart、idempotence、backup、digest、lock、crash recovery、
  missing fields、quarantine與 secret redaction。
- [x] GREEN：實作 migration-only DTO/service/CLI與 owner-only atomic backup/replace流程。
- [x] RED/GREEN：backend API拒絕`new_extension_component`，active enum移除`NEW_EXTENSION`，
  normal backend producer/consumer不再建立legacy extension。
- [x] 以 executable allowlist證明backend保留hit只在rollback/migration/test boundary。
- [x] 依ownership要求把7個既有frontend檔案與3個新增檔案完整還原。
- [ ] Frontend contract的5筆active legacy hits等待前端負責人遷移。

### 階段 D：10-artifact atomic visibility

- [x] RED：覆蓋 staging每個 write boundary、directory rename、manifest、pointer CAS、stale
  revision、concurrent reader與 restart recovery。
- [x] GREEN：建立 `BuildCommitService`，讓 initial scan、apply與 detail scan共用同一 state
  machine與 complete-manifest/latest-pointer contract。
- [x] 驗證 7 JSON + 3 render共用 scope ids、digests、schema status與 evidence references。
- [x] 建立本階段 Report與 fault-injection matrix。

### 階段 E：Rollback、Manual QA 與文件

- [x] 實跑 CLI `--help`、v2 happy path、bad input、public v1拒絕、operator v1 rollback、
  invalid env、v1/v2 reload與切回 deterministic v2。
- [x] 啟動 live FastAPI，以 HTTP 驗證 scan/viewer/detail/trace/history/latest與 10-artifact lifecycle。
- [x] 執行完整 backend/frontend tests、Ruff、Mypy、build、lint、contract search與 portability gates。
- [x] 逐檔盤點 `scripts/` 並只同步實際受 cutover contract影響的腳本。
- [x] 更新 `docs/work/Timmy/learn/architecture.md` ASCII全景圖、00A/Plan 13 checkboxes/status與
  final cutover Report。
- [x] 執行 review-work、三個 runtime debugging hypotheses與secret/path/schema regression，
  backend blocker清零。
- [ ] Frontend cutover與fresh visual QA等待frontend handoff；先前暫時cutover的Playwright結果
  不作current completion evidence。

## 驗收重點

- `MapBuildResult` 只有 normalized v2 canonical truth；normal output預設 v2且不 dual-write。
- v1 artifacts仍由唯一 loader/adapter可讀；operator rollback預設關閉、可稽核、不可由 public
  request選擇，v2-only facts fail closed。
- Active backend code/API不建立或接受legacy extension；persisted rows依固定矩陣安全遷移。
- Frontend維持原始版本；5筆active legacy hits已明確列為`migrate`，不是backend完成證據。
- Supported readers永遠看不到 partial artifact set；history與 latest visibility boundary可由
  fault-injection/restart tests證明。
- 所有新增backend行為都有先紅後綠的BDD測試、完整regression與實際CLI/API觀察證據。

## Backend完成／Frontend待接手證據

- Cutover report：`docs/work/Timmy/schedule/report/2026-07-17-phase2-plan13-v2-cutover-REP.md`
- Backend：`1031 passed`；scoped Plan 13 gate：`977 passed`；Ruff／Mypy通過。
- Frontend：worktree對`HEAD`零diff；原始Vitest為`3 files / 7 tests passed`，build／lint
  exit 0。
- Executable census：`35 records / 35 hits`；`migrate=5`、`migration_only=22`、
  `operator_rollback=8`，SHA-256
  `59fa4f066a0e37c9f73ce488e64da96cccab7c8a9e6a429b0c073a738544714b`。
