# 前端同步：Capability Overlay UI

Last updated: 2026-07-07（UA 整合決策對齊）

## 目的（Purpose）

Plan `02`、`03`、`04`、`06`、`10`、`11` 將 profile 定義為可堆疊的
**capability overlays**，而非互斥的 RAG types。

Frontend 應渲染 backend 提供的 profile/capability 資訊。不得從 graph nodes infer
profile、labels、axes 或 implementation depth。

## 資料邊界（Data Boundary）

Backend 負責：

- `profile_signals.json`
- capability profile registry
- Step 6 `ProfileInferenceService`：以純 Python 讀 validated system map + TOML metadata，直接定案
  `detected`、`partial`、`undetermined`、`not_detected`、`conflicted`
- Plan 17 `AssessmentOrchestrator` / AI semantic candidate flow deferred
- activation 計算：`enabled`、`disabled`、`conditional`、`unknown`、`conflicted`、`not_applicable`
- implementation depth 與 reason
- related component / evidence / risk refs
- Step 7 投影至 `GraphViewModel` 的 fixed reference map + repo overlay

Frontend 負責：

- 解析目前 payload；
- 渲染 profile overlay nodes 或 panels；
- 唯讀 detail 呈現；
- sidecar 不可用時的 degraded warning UI。

## Status 語意

不要在前端新增 `confidence`。

使用 backend status 與文案：

| Status | UI 意義 |
|---|---|
| `detected` | backend 有足夠 evidence 支持此 capability |
| `partial` | 有部分 evidence 或 indirect evidence，但不足以完整定案 |
| `undetermined` | 有相關 evidence 或 coverage gap，但 scanner 不應定案 |
| `not_detected` | coverage gate 已完成，且沒有足夠支持 evidence |
| `conflicted` | 同一欄位有互相矛盾的 evidence |

若 backend 日後暴露 coverage/depth/missing signals，作為說明渲染，不要當
confidence score。

## Graph Projection

Frontend 應消費 backend projection。若 backend 發出 profile attachment nodes：

- 以 `semantic_kind="profile_attachment"` 渲染 distinct compact visual；
- base graph nodes 與 profile/capability overlay nodes 視覺上區分；
- 不要在 attachment 與 anchor 之間建立 synthetic graph edges；
- 若 backend 提供 anchor metadata，不要將 profile attachments 放進 ELK main graph layout。

若 backend 尚未發出 attachment nodes，frontend 不得自行從
`profile_signals.json` 建立 profile nodes。

Profile/reference node 對位已在 backend Step 6 完成，attachment / overlay 位置已在 Step 7
projection 決定。Frontend 不得用 profile id、node label、dependency 或 layout 自行推定
reference node mapping。

2026-07-07 UA 整合決策不新增 frontend 欄位；不要在 profile UI 讀取或顯示
`ua-analysis-result.json`、semantic candidate confidence 或 signal origin。Semantic sidecar
是 reserved nullable slot，Phase2 active path 不產生、不消費。

## Detail Panel

Profile/capability details 為唯讀。顯示 backend 提供的：

- display name / label；
- status；
- description；
- implementation depth；
- evidence ids；
- related components / candidates / risk refs；
- recommended next checks。

Profile detail 不要顯示 accept/edit/reject/confirm actions。

## Sidecar Degraded Load

一般 viewer load 不應僅因 `profile_signals.json` 或 `readiness_report.json`
missing/invalid 而失敗。Base graph 可在 warning 下載入。

Frontend 行為：

- `ai_system_map.json` 有效時顯示 base graph；
- missing/invalid sidecar 顯示 warning；
- 不要 invent 空的 profile results；
- 不要在 browser 跑 transient inference。

Strict build/CI validation 可 fail closed，但一般 viewer UX 應 degrade。

## Filters

若 backend 提供 `filter:profile_attachments`，使用既有 positive filter 行為：

- 預設不 active；
- highlight 符合的 profile overlay nodes；
- dim 不符合的 nodes/edges；
- 不要 hide 或 remove nodes；
- 不要 mutate payload。

## 驗收標準（Acceptance Criteria）

- [ ] Frontend 解析 backend profile/capability payload，不 hard-code profile metadata。
- [ ] Profile overlay nodes（若有）使用 distinct visual。
- [ ] Sidecar missing 時 base graph 仍可載入並顯示 warning。
- [ ] Profile detail 為唯讀。
- [ ] 無 frontend-generated profile inference。
- [ ] 無 frontend-generated profile graph edge。
- [ ] 不在 frontend canonical/profile contract 新增 `confidence` field。

## 禁止事項（Do Not Do）

- 不要將 repo 分類為單一 RAG type。
- 不要 hard-code profile labels、axes 或 depth 文案。
- 不要顯示 profile mutation actions。
- 不要用 profile overlay infer runtime path。
- 不要將 profile findings write back 到 `ai_system_map.json`。
