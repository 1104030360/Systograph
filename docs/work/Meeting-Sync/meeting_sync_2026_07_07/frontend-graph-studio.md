# 前端同步：Graph Studio

Last updated: 2026-07-07（UA 整合決策對齊）

> 對象：Hardy／Frontend。Graph Studio 的新增與調整事項只在本 Meeting Sync 維護；
> 不直接修改 `docs/work/Hardy/` 底下的既有 plan。Hardy 可依本文件與 versioned backend
> contract 安排實作，若有衝突先回到 Meeting Sync 對齊。

## 目的（Purpose）

Graph Studio 是 evidence-backed system map 的主要檢視與探索工作區。它把 backend
提供的固定 reference map、目前 repo overlay、readiness 與 evidence projection 組合成
一致的 frontend experience，但不在 browser 內重新理解 repository 或推論架構。

`DeepResearch` 內的網頁只作視覺方向與互動參考。Frontend 不得直接複製其中的
HTML、CSS、JavaScript、資料模型或 hard-coded sample；正式實作必須使用本 repo 的
design tokens、components、backend contract 與測試 fixtures。

## Backend Projection Contract

Backend 是 graph truth 與 projection 的 owner。Frontend 只消費 backend 提供的：

- stable node、edge、evidence 與 detail ids；
- `GraphViewModel` nodes、edges、details、filters 與 labels；
- reference-map identity、repo overlay membership 與 activation；
- five-state mapping/readiness result；
- Mapping Completeness 所需的 numerator、denominator、scope 與 limitations；
- readiness findings、profile findings 與 safe limitation/reason text；
- lens/filter membership；
- Evidence Inspector 所需的 evidence refs、source locations、reasons 與 warnings。

Frontend 不得從 file names、dependencies、graph topology、profile signals 或缺少的欄位
自行產生上述資料。Backend 欄位名稱與 enum 以 versioned sample/API contract 為準；若
payload 不支援某項能力，UI 應 disabled 或 degraded，不得猜測。

### Step 6 / Step 7 boundary

Graph Studio 的直接輸入是 **Step 7 GraphViewModel / projection payload**。Step 6 的
repo facts ↔ 10 planes / 52 reference nodes 對位、五態、activation、Mapping
Completeness 都已由 backend 完成：

```text
Step 6 ProfileInferenceService（純 Python）
  -> 直接讀 validated system map + TOML metadata
  -> 定案 reference node assessment + related refs
  -> Plan 17 AssessmentOrchestrator / AI semantic candidate flow deferred
Step 7 GraphProjectionService
  -> fixed reference nodes + repo overlay + lens memberships
Frontend Graph Studio
  -> render only
```

UA semantic sidecar 是 reserved nullable snapshot internal slot，Phase2 active path 不產生、
不消費，也不是 Graph Studio input；frontend 只看 Step 7 已發布的 `GraphViewModel` /
projection payload。

Frontend 不要從 `profile_signals.json`、`ai_system_map.json`、dependency list、node label
或 layout 重新建立 reference-node mapping。若 projection 缺少 mapping / anchor / lens
membership，UI 應顯示 degraded 或 unsupported state。

## Reference Map 與 Repo Overlay

Graph Studio 使用同一張固定底圖，並以切換按鈕控制目前 repo assessment overlay：

```text
Fixed reference map
  = backend 定義的期待架構／能力參考座標

Repo overlay
  = backend 依目前 scan_id/build_id evidence 投影的 repo 狀態
```

- Reference map 的 topology、labels 與 ids 由 backend 提供，frontend 不得改寫。
- 切換視角時保留同一份底圖與 stable layout，只改變 overlay、lens、highlight 與 detail
  presentation，不切換成另一套 graph surface。
- Repo overlay 必須保留 `scan_id` / `build_id` lineage，避免把不同 scan 結果混在一起。
- Overlay 只描述 backend 已投影的狀態，不等同 runtime observation。
- Overlay missing 時可顯示 reference map 與 degraded explanation，但不得填造 repo facts。
- Apply/rescan 後必須以 backend 回傳的新 build payload 取代目前 overlay，不 in-place
  mutate canonical artifacts。

## Five-State 與 Activation

Graph Studio 應能呈現 backend contract 定義的五種結果語意：

| State | 使用者語意 |
|---|---|
| `detected` | 有足夠直接 evidence 支持目前 repo 已具備此能力 |
| `partial` | 只有 indirect evidence，或直接 evidence 顯示實作／wiring 尚不完整 |
| `undetermined` | scanner coverage 未完成或現有 evidence 不足以可靠判定 |
| `not_detected` | 相關 scanner coverage 已成功完成，且沒有找到支持 evidence |
| `conflicted` | 同一 scope、同一欄位存在無法消解的明確矛盾 evidence |

State 與 activation 必須分開：state 回答「evidence 支持什麼」，activation 回答「此
能力在目前 build/environment 是否為 `enabled`、`disabled`、`conditional`、`unknown` 或
`conflicted`」。只有 metadata 宣告 activation 不適用的 reference node 才使用
`not_applicable`；activation 不影響 capability state，也不改變 Mapping Completeness
denominator。

Frontend 只渲染 backend 提供的 state、activation、reason 與 limitations，不從顏色、節點
連線或其他欄位推導。不得將 `undetermined` 顯示為成功，也不得將 `not_detected` 自動升級為 finding。

## Readiness Findings

Frontend 顯示 backend-provided `readiness_report.json.findings[]` 與 GraphViewModel 的
readiness projection。Readiness findings 用來呈現交付前缺口，例如 source traceability、
coverage gap、static execution limitation 或安全/隱私風險。

- Finding status 使用統一五態，不新增 domain-specific summary status。
- Finding 必須顯示 title、category、severity、status、reason/description、evidence refs
  與 recommended next checks。
- Evidence Inspector 可從 finding 回查 components、edges 與 evidence refs。
- Frontend 不得自行從 dependency、file name、node label 或 graph topology 判斷 repo
  是否 RAG，也不得自行產生 readiness finding。

## Mapping Completeness

Mapping Completeness 是 backend 計算並附帶 scope 的 assessment completeness，不是 readiness、
品質分數，也不是 frontend 自行計數的百分比。固定權重為 `detected=1`、
`not_detected=1`、`partial=0.5`、`undetermined=0`、`conflicted=0`；denominator 是 catalog
中的全部固定 reference nodes，activation 不參與公式。UI 至少應顯示：

- backend 提供的 value 與顯示 label；
- numerator、denominator 與納入範圍；
- 五態權重與 activation 不參與公式的說明；
- `scan_id` / `build_id` identity；
- limitations 或 degraded reason。

若 payload 缺少 denominator、scope 或 lineage，UI 不得產生看似精準的百分比；應顯示
「目前無法計算」與 backend 提供的原因。

## Lenses

Lenses 是同一份 backend projection 的檢視方式，不是另一份 frontend truth。初始工作項目
支援 backend 已提供 membership 的 `Data`、`Control`、`Evidence`、`Governance`、`Source`、
`Risk` 六種 lenses。

- Lens 切換可 highlight、dim、調整 panel 與圖例，不刪除 canonical nodes/edges。
- Lens 不得建立 synthetic edges、profile attachments 或 execution paths。
- Static execution 若由既有獨立 surface 顯示，必須標示 inferred /
  `runtime_verified=false`；它不列入本工作項目的六個固定 lenses。
- Unsupported lens 應 disabled 並解釋缺少的 artifact/contract。

## Evidence Inspector

Evidence Inspector 以 selected node、edge、reference item 或 finding 的 stable refs 查閱
backend evidence。至少涵蓋：

- evidence id、type、reason 與來源位置；
- related component/edge/finding refs；
- state、activation 與 limitations 的 backend explanation；
- source path 的安全、redacted 顯示；
- 無 evidence、missing sidecar 或 invalid ref 的 degraded state。

Inspector 不執行 source parsing、不補 evidence、不顯示完整 secret，也不把 evidence edit
直接寫回 canonical map。Ambiguous evidence 的使用者 decision 仍走既有 review queue／
Apply contract。

## UI States

Graph Studio 必須明確處理：

- loading：保留可辨識的 workspace skeleton 與進度文字；
- empty：區分尚未 scan、有效但沒有 active items、以及 lens 無 matching items；
- error：顯示可採取行動的安全錯誤，不留下半殘或混用舊 build 的 graph；
- degraded：base projection 可用但 readiness、profile、evidence 或 execution sidecar 缺失；
- stale/build changed：project、`scan_id` 或 `build_id` 改變時要求重新載入對應 payload。

Degraded UI 必須指出缺少哪一種資料，以及哪些 view 仍可信。不得把 optional sidecar missing
描述成整個 scan 失敗。

## Accessibility 與 Responsive

- 所有 state/lens 不可只靠顏色區分，需有文字、icon 或 pattern。
- Graph、lens controls、legend、Evidence Inspector 與 error actions 應可鍵盤操作。
- Focus order、focus indicator、Escape/close 與 screen-reader labels 必須可測。
- Graph canvas 應提供非視覺替代清單或可讀摘要，避免資訊只存在於 canvas。
- 窄螢幕將 Inspector 轉為可關閉 sheet/panel；controls 可換行且不可遮住主要狀態。
- 大圖需維持可操作性，但 performance 優化不得改變 backend ids 或 evidence semantics。

## Frontend 任務

1. 以 versioned sample 建立 Graph Studio parser 與 view-model adapter。
2. 在既有 React Flow/ELK viewer 上組合 reference map 與 repo overlay，不重建 graph engine。
3. 實作 backend-driven five-state、activation、legend 與 Mapping Completeness summary。
4. 實作 readiness findings panel 與 Evidence Inspector drilldown。
5. 實作 lenses 與 unsupported/degraded behavior。
6. 實作 Evidence Inspector 與安全 source/evidence presentation。
7. 補齊 loading、empty、error、degraded、stale build UI。
8. 沿用既有 zoom、pan、fit-view、minimap，並增加帶 build/scope 標示且經 redaction 的 export。
9. 補 component/integration/regression tests，以及 keyboard、responsive 與 accessibility checks。

## 驗收標準（Acceptance Criteria）

- [ ] Graph Studio 只消費 backend projection，不從 repo evidence 自行 inference。
- [ ] Fixed reference map 與 repo overlay 有清楚視覺、identity 與語意區隔。
- [ ] 五態與 activation 分開顯示，且不由 frontend 推導。
- [ ] Readiness findings 使用 backend payload；frontend 不建立 product-specific readiness card。
- [ ] Mapping Completeness 使用 backend value/scope；缺 contract 時不顯示假精準百分比。
- [ ] Lens 不刪除 canonical graph，也不建立 frontend-only nodes/edges。
- [ ] Evidence Inspector 使用 stable refs，且不顯示 raw secret。
- [ ] Loading、empty、error、degraded、stale build 均有測試。
- [ ] State/lens 不只依賴顏色，主要流程可用鍵盤操作。
- [ ] 主要 desktop 與窄螢幕 viewport 不遮蔽核心狀態或操作。
- [ ] Zoom、minimap 與 export 維持 backend identity/redaction，不改寫 canonical artifacts。
- [ ] Sample mode 與 API mode 使用相同 active contract。

## 不包含範圍（Out Of Scope）

- Validation Simulator。
- Runtime trace 與 runtime latency/status。
- Backend scanner、graph projection、profile/readiness inference 或 Mapping Completeness 計算。
- 直接複製或執行 `DeepResearch` 網頁的 HTML、CSS 或 JavaScript。
- Frontend-only schema、node、edge、state、lens membership 或 evidence inference。

## 禁止事項（Do Not Do）

- 不要從 static graph 宣稱 runtime path。
- 不要從 missing evidence 自動推導 `not_detected` 或 `conflicted`。
- 不要自行判斷 repo 類型或產生 frontend-only readiness check。
- 不要以 activation 改寫 capability state 或 Mapping Completeness denominator。
- 不要在 frontend 重建 reference topology 或 Mapping Completeness。
- 不要將 profile、readiness、execution 或 evidence 資料 write back 到 canonical artifacts。
- 不要為了符合 `DeepResearch` 畫面而繞過本 repo contract、components 或 design tokens。
