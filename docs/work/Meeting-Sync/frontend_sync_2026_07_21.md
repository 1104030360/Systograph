# KAI-Mind Frontend Sync：Plan 13 v2 contract 對齊與 Dialog 收尾（2026-07-21）

本文件對應 `codex/phase2-plan06-contract` 對 `main` 的 frontend PR #252。

```text
目標：將既有十層 architecture viewer 對齊 Timmy 最新 ai-system-map/v2 與 build-scoped contract，
並完成 DeepResearch 彩色圖示、Readiness Markdown 預覽、Mapping Profile Dialog 與 node card 視覺收尾。
範圍：frontend + frontend sync；不修改 scanner 或 backend runtime 行為。
```

## 1. Timmy backend 同步基線

本分支已合併 `origin/main` 至 `0a68ccd`，包含：

- `0e48727`：Phase2 S1 index/projection backend（PR #250）。
- `70e7f89`：profile registry 遷移到 TOML catalog、finding 組裝重構（PR #251）。
- `2e78f68`：frontend JSON handoff、static trace plan 與 shell 相容性文件（PR #253）。
- `8cb772f`：build manifest service test 移至 integration layer（PR #254）。
- `e10f737`：inventory selection 與 frontend API contract 同步（PR #256）。
- `0a68ccd`：Plan 13 `ai-system-map/v2` active cutover（PR #257）。

Frontend 目前以 build-scoped response 為主，讀取 backend 發布的 canonical map、graph projection、profile inference 與 readiness report。Frontend 不推論缺少的 plane、lens、assessment 或 lineage。

## 2. PR scope

### DeepResearch 彩色圖示語言

- BrandMark 與 favicon 恢復 `DeepResearch/index.html` 的藍、綠、橘、紫 palette。
- 16 個 Filter Views 與十層 plane headers 使用 prototype 的 CSS-drawn semantic icons。
- Node Inspector 的 backend-declared plane chip 使用同一套 prototype registry。
- 搜尋、關閉、資訊等一般操作按鈕仍使用 lucide；semantic architecture icons 與通用 actions 維持不同職責。

### Readiness Markdown Dialog

- Readiness 改為 accessible modal dialog，支援背景點擊、Escape、focus return。
- backend `readiness_report` 存在時顯示 build-scoped 真實資料。
- selected build 未提供 report 時，顯示明確標示為 UI sample、不是本次掃描結果的預覽。
- 提供 Preview 與 Markdown source tabs；Markdown 以純文字 `<pre>` 顯示，不注入 HTML。

### Mapping Profile Dialog

- Mapping Profile 不再取代主畫面，改為置中的 modal dialog。
- Dialog 保留既有 inventory/profile workflow，並支援 Escape、backdrop close、focus return。
- 390px viewport 不產生 dialog 或內頁水平 overflow。

### Node 與 mapping contract 收尾

- Repo component node 移除左側彩色修飾條，改為低干擾的頂部 accent；unmapped component 使用 dashed outline。
- Mapping proposal candidate 對齊新版 contract：
  - `existing_slot_mapping`
  - `non_baseline_capability_candidate`
  - `needs_more_information`
  - `skip_for_now`
- 移除 frontend `new_extension_component` 與 `ui_extension` 殘留。
- Viewer contract tests 改由 Timmy step-04、step-06、step-07 source-of-truth fixtures 組合 v2 build payload。
- Active viewer/profile/readiness/build schemas 僅接受 `ai-system-map/v2`；歷史 v1 只保留在隔離的 compatibility sample/adapter，不再成為 active contract consumer。

## 3. Superseded PR disposition

- PR #252：保留並更新；作為目前十層 architecture viewer 與 v2 contract 主線。
- PR #198：關閉；舊 Detail Scan flow 在成功後刷新 `/api/map`，需改為 child build / build-scoped response。
- PR #199：關閉；stack 在 #198 且使用舊 extension mapping contract，需以新版 proposal candidate types 重做。
- PR #218：關閉；Query Trace 需重新確認 project/build scope 與 Timmy static trace contract。
- PR #227：關閉舊 scope；不得恢復 server-local path loader。安全的 report preview/download 另以 build-scoped artifact flow 實作。

關閉代表 implementation 被新版 contract 取代，不代表 Detail Scan、Mapping Proposal、Query Trace 或 Report Artifact 功能取消。

## 4. Validation

在 2026-07-21 最終工作樹執行：

```powershell
pnpm --dir frontend test
# 22 files / 86 tests passed

pnpm --dir frontend test --run src/components/DetailPanel.test.tsx src/components/ArchitectureViewNav.test.tsx src/components/ReadinessPanel.test.tsx src/components/MappingProfileDialog.test.tsx src/contracts/viewer.test.ts
# 5 files / 24 tests passed（最後 registry refactor 後）

pnpm --dir frontend lint
# 0 errors；1 個既有 BoundaryDecisionModal fast-refresh warning

pnpm --dir frontend build
# tsc -b && vite build passed

git diff --check
# passed
```

完整 repo pre-commit hooks 在 Windows / Python 3.14 另有 backend baseline failure：`os.O_NOFOLLOW`、`os.O_DIRECTORY` 與 `os.mkfifo` 不存在，連帶造成 inventory safety、detail/apply/trace route tests 失敗。這些失敗位於 Timmy 最新 backend inventory safety 範圍，未由本 frontend PR 修改；本 PR 另外執行並通過 `tests/contracts/test_v2_cutover_consumer_allowlist.py`。因此 final frontend commit 僅跳過已證實不相干且 baseline 失敗的 `mypy` / full `pytest` hooks，沒有跳過上述 frontend 與 v2 contract validations。

Browser QA 已確認：

- Mapping Profile 為 modal，不再進行 full-page route replacement。
- Readiness 的 Preview / Markdown tabs、sample honesty notice 與 focus / Escape 行為正常。
- 390px viewport 下 Mapping Profile dialog 與 route content 無水平 overflow。
- Filter 與 BrandMark palette 符合 prototype 原始色值。
- 最後一次 dev-server 重載受到 in-app browser localhost URL policy 限制；最後 registry refactor 由 TypeScript build 與 24 個相關 regression tests 覆蓋。

## 5. Known limitations / next work

- `frontend/src/data/frontend-json-sample.json` 仍是刻意保留的 `ai-system-map/v1` compatibility sample；不能只改 version string，應另以完整 v2 shape 建立 canonical sample。
- 真實 readiness report 已可由 build-scoped response 內嵌提供；獨立 `.md` report artifact preview/download 仍需安全的 project/build-scoped artifact endpoint。
- Mapping Profile dialog shell 已完成，後續需接 current inventory selection 與 profile inference 資料。
- Runtime、Variants、Reasoning Mode 仍等待 backend typed membership metadata。
- Edge legend 仍只區分 declared flow 與 backend mapping；更細的 edge taxonomy 需要 backend contract。
- `BoundaryDecisionModal.tsx` 的 fast-refresh warning 為既有限制。

## 6. Submodule 與 handoff

`ref-opensource/Understand-Anything` 主專案 pin 與本機 checkout 均為：

```text
73559a160645359c57be44c174935899dec9f9f2
```

換電腦或重新 pull 後執行：

```bash
git submodule update --init --recursive
```

也可以使用 `git pull --recurse-submodules`。

`docs/work/Hardy/frontend-review-2026-07-02.md` 是使用者本機既有未追蹤筆記，不屬於 PR #252，未 stage、未 commit。
