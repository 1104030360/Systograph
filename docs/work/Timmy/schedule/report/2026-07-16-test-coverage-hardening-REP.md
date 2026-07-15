# Test Coverage Hardening Report

## 結論

新增 30 個可收集案例，總測試由 819 增至 849。補測集中在真實 failure contract，沒有用
無意義的 getter/re-export 測試灌 coverage，也沒有改 production 行為來迎合測試。

## 實作邏輯

- 對 digest 與 schema validation 分層測試，避免只證明「檔案被改過」卻沒有證明
  「內容即使 digest 合法仍會 fail closed」。
- 對 optional sidecar 區分 missing/invalid/scope mismatch，確保 base graph degraded-but-usable。
- 對 packaged catalog 與 project config 驗證 malformed、missing、duplicate 與 identity drift。
- 以真實 CLI/FastAPI/state repository 驗證錯誤路徑，不把 service mock 當 integration。

## 主要變更

### Unit boundary

- `QueryTraceConfigLoader`
  - optional section default。
  - malformed TOML。
  - 非 table trace section。
  - empty/string/non-string/duplicate chunk keys。
- `CapabilityReferenceMapLoader`
  - packaged resource read error。
  - malformed/缺欄位 TOML。
  - catalog id/version 與 10 planes/52 nodes 固定 contract。

### Integration boundary

- 將 `test_build_manifest_service.py` 從 `tests/unit/core/` 搬到 `tests/integration/`；該檔
  實際跨越 MapBuildService、LocalJsonStateProvider、磁碟 artifact、canonical loader 與 viewer。
- 同步更新 active Plan 13 的測試路徑引用。
- 增加 valid-digest + invalid-content、optional artifact、profile/readiness missing/invalid/scope
  mismatch、persist preconditions。
- FastAPI detail scan 增加 cross-project build concealment 與 stale base build rejection。
- CLI map 增加 missing project、error report 與禁止 success artifacts。

## Red / Green 與 root-cause 證據

### Mutation red gate

暫時切換四個 production decision 後，新測試產生四個獨立失敗：

- CLI error exit code：期望 1、實際 0。
- duplicate trace key：預期 `QueryTraceConfigError`、實際未拋出。
- packaged catalog version：預期 fail closed、實際未拋出。
- missing optional artifact warning：stable warning 不相符。

四個 mutation 隨即完整還原；還原後同組 `8 passed`。

### Profile scope fixture

- 初始紅燈：預期 `profile_signals_scope_mismatch`，實際得到 generic invalid。
- runtime 證據：digest 一致，但 Pydantic 回報 top-level `build_id` 與
  `generated_from_build_id` 不一致。
- 修正：同步調整 generated/nested scope，建立內部合法但與 manifest 不一致的 sidecar。
- 結果：正確走 `profile_signals_scope_mismatch`；production 不需修改。

### Cross-project API status

- 初始預期 409，實際 404。
- runtime 證據：foreign build 可直接 GET 200，detail scan 回
  `404 project_build_mismatch`。
- 判讀：service 有辨識 mismatch，route 以 404 隱藏跨 project 資源存在性，屬合理
  fail-closed contract；修正測試預期，不改 production。

## 測試方式與結果

- affected tests：`61 passed in 3.63s`（加入最後五個案例前的 focused run）。
- `tests/integration/test_build_manifest_service.py`：`14 passed in 0.89s`。
- `tests/web/test_detail_scan_build_binding.py`：`6 passed in 2.04s`。
- changed tests Ruff：通過。
- changed tests Mypy：通過。
- 完整 coverage：`849 passed in 28.89s`。
- coverage：89.90%，高於新設 85% floor。

## Coverage 變化

- missing statements：724 → 680。
- partial branches：458 → 439。
- `BuildManifestService`：79% → 100%。
- `QueryTraceConfigLoader`：73% → 95%。
- `CapabilityReferenceMapLoader`：74% → 100%。
- CLI map command：68% → 88%。
- `DetailScanBuildService`：74% → 79%。

## 本階段完成時的測試分類

- unit：662
- integration：70
- contract：35
- web：68
- cli：12
- e2e：1
- smoke：1
- 合計：849

最終 regression verification 的 live API QA 另發現一個 macOS Bash 3.2 portability
缺口，補上一個 contract test 後總數為 850；完整結果記錄於同日 regression report。

## 剩餘風險

- `DetailScanBuildService` 的 publish/promotion race cleanup 仍主要靠較高層 apply/concurrency
  tests 間接保護；若 Plan 13 引入 BuildCommitService，應在該 owner 的計畫中補原子性測試，
  不在本任務預先重構。
- Egress resolver 的真 DNS path 未在 unit suite 連外，這是 deterministic/security 選擇；
  injected resolver 的 policy branches 已由現有測試保護。
- 89.90% 不代表零風險；85% floor 是 regression guard，不是 product completion 指標。
