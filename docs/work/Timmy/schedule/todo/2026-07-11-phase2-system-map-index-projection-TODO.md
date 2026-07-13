# Phase 2 System Map Index / Projection TODO

## 目標

依 `phase4.md` 完成 Plan 05–09：先讓五份計畫與 2026-07-11 live code／contract
一致，再以 TDD + BDD 建立 read-only `SystemMapIndex`、共用 graph projection、selected
consumer migration 與 legacy lookup cleanup，且不破壞既有 v1 API/CLI 相容行為。

## 2026-07-12 範圍修正

- 本次只交付 backend；本輪曾做的 frontend 程式碼、測試、依賴與設計文件變更已全部
  撤回，`frontend/` 相對本次 baseline 無差異。
- Backend 仍需輸出完整 additive `GraphViewModel` 與 build-scoped sidecar contract，供
  frontend owner後續串接；frontend implementation與 browser visual QA不列入本次 gate。

## 已確認基線

- [x] 回收 backend truth audit：確認 `CanonicalMapLoader`、profile inference、readiness 與
  build lineage 已存在，但 `SystemMapIndex` / `GraphProjectionService` 尚未實作。
- [x] 回收 clean baseline：backend full suite `715 passed`；frontend `7 passed`；Ruff、
  scoped mypy 與 frontend build 通過。
- [x] 記錄既存問題：本機 `uv` 不在 `PATH`；`mypy .` 會掃到 vendored
  `ref-opensource/` 與 `scripts/dev.py`，目前為 `45 errors in 6 files`。
- [x] 使用者要求後續不再使用 subagent；後續由單代理執行與驗證。

## 實作邏輯

1. `CanonicalMapLoader` 是唯一 v1/v2 branching owner；下游只接 normalized
   `AiSystemMapV2`。
2. `SystemMapIndex` 只索引 canonical v2 fields：components、edges、evidence、endpoints、
   risks、unmapped components 與 candidate facts；不索引 profile/readiness/grounding
   sidecars，也不 validate、infer、persist 或 mutate。
3. `GraphProjectionService` 是 API graph topology 的單一 owner；五態、activation 與
   Mapping Completeness 只 surface Step 6 結果，不重新計算。
4. `reference_capability`、`repo_component`、`unmapped_component`、
   `capability_candidate`、`profile_attachment` 是不同 projection identities；mapping
   relation 不偽裝成 runtime topology edge。
5. `system_map.mmd` 與 `ai_system_map.md` 逐步改成消費同一 projection；
   `execution_map.mmd` 仍由 static execution owner 管理。
6. Plan 08 只遷移可證明 behavior-equivalent 的 read-only lookup；v1 detail child-map
   materialization 與 legacy proposal response 保留為明確 compatibility owner。
7. Plan 09 只刪除已被 characterization/equivalence tests 證明取代的 helpers，不以
   source grep 取代 runtime regression。

## 執行階段與步驟

### 階段 A：逐檔校正計畫

- [x] 更新並驗證 `05-add-read-only-system-map-index.md`。
- [x] 更新並驗證 `06-deepen-graph-projection-module.md`。
- [x] 更新並驗證 `07-expand-system-map-index-to-shared-lookup-contract.md`。
- [x] 更新並驗證 `08-migrate-mapping-consumers-to-system-map-index.md`。
- [x] 更新並驗證 `09-consolidate-legacy-system-map-lookups.md`。

### 階段 B：TDD/BDD 實作

- [x] RED：新增 `SystemMapIndex` found/missing/no-mutation/boundary tests，確認因
  module/behavior 缺失而失敗。
- [x] GREEN：實作最小 frozen read-only index，跑 focused + regression tests。
- [x] RED：補 `GraphProjectionService` normalized-v2、map-only degraded、profile overlay、
  filter 與 renderer scenarios，確認新 contract 先失敗。
- [x] GREEN：拆出 projection owner，接上 build/viewer/API/CLI 與共用 backend renderers。
- [x] RED/GREEN：擴充 shared lookup的 ordering/grouping/direction/location，遷移
  proposal/detail read-only seam，再清理已替換
  helpers；每個 consumer 都先有 v1/v2 equivalence characterization。

### 階段 C：驗收與文件

- [x] 跑 focused、full pytest、Ruff與 scoped mypy。
- [x] 以 CLI `--help`、valid map、invalid map 與 build-scoped API 做 Manual QA。
- [x] 以 valid/missing/invalid sidecar build-scoped payload 做 live HTTP API regression。
- [x] 完成 plan-compliance、code-quality、runtime-debug 三假設與 scope-fidelity review。
- [x] 每完成一個階段就更新本 TODO，並建立對應 REP；05–09 已在原路徑標示完成。
  `plan/finish` 目前已有同名 05–09 檔案，直接搬移會碰撞且破壞 phase2 relative links，
  因此依此 TODO允許的替代方式保留原位並加上完成狀態。

## 驗收重點

- Scanner 與 index 全程 read-only，不寫 target repo 或輸出完整 secrets。
- v1 API/CLI compatibility 與 JSON ordering/error text 不因 lookup migration 改變。
- Backend projection直接 surface topology、五態與 completeness，不要求 frontend重算。
- `SystemMapIndex` 不成為 god object，不吸收 validator、profile、readiness、render、
  persistence 或 runtime trace owner。
- 所有新 production behavior 都有先紅後綠的 Given/When/Then 測試證據。
