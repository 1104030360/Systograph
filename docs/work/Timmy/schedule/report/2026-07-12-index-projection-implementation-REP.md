# System Map Index / Graph Projection Implementation Report

## 範圍與結果

完成 Plan 05、06、07 的 backend 實作：read-only `SystemMapIndex`、單一
`GraphProjectionService`、reference/profile overlays、六個 backend-owned lenses、共用
Mermaid/Markdown renderers，以及 build/viewer/manifest wiring。

## 實作邏輯

- `CanonicalMapLoader` 是 v1/v2 branching 的唯一 owner；projection 只接 normalized
  `AiSystemMapV2`。
- `SystemMapIndex` deep-copy canonical facts並回傳 copy，提供七組 singular lookup、
  type/layer grouping、edge direction、evidence batch與 stable location lookup。
- `GraphProjectionService` 只 surface canonical/Step 6 結果，不 validate、infer 或建立
  synthetic runtime mapping edge。
- 52 個 reference nodes、repo/unmapped/candidate/profile identities 分開；Mapping
  Completeness 直接沿用 `ProfileInferenceResult`。
- `system_map.mmd`、`ai_system_map.md` 與 API graph 共用相同 `GraphViewModel` ids。

## 步驟

1. 先寫 index found/missing/no-mutation/boundary tests，再實作 frozen index。
2. 先寫 normalized projection、map-only、profile overlay與 renderer failing tests。
3. 抽出 projection/filter/lens/overlay/renderers，縮小 `ViewerSessionService`。
4. 將 publisher與 manifest reload接到同一 normalized/profile input。
5. 新增 non-grounded LLM、tool agent、grounded RAG、grounded agent、workflow fixtures
   renderer matrix。
6. 補 v1 compatibility detail regression，保留 profile/reference/candidate details。

## 測試方式

- Focused index/projection/viewer/build/web/CLI matrix。
- `ruff check src tests`、`mypy src tests`。
- valid/missing/invalid profile sidecar build-scoped API與 CLI/manual artifact inspection。

## 遇到的問題與解法

- 問題：新 renderer 一度漏掉既有 Markdown `Slot Coverage` / next-check sections。
- 解法：先加 regression test，再由 `GraphViewModel` 恢復相容 sections。
- 問題：v1 detail compatibility enrichment整個覆寫 `GraphDetailsModel`，使 profile
  details消失。
- 解法：新增 RED test，改為只更新 legacy evidence/risk dictionaries，保留其他
  projection details。
- 問題：計畫要求 grounded agent scenario，但 repo 原先沒有對應 v2 fixture。
- 解法：新增最小 grounded-agent canonical fixture並納入五情境 renderer matrix。

## 測試結果

- Focused backend matrix：`118 passed`。
- Ruff：通過。
- Mypy：`247 source files`，0 issues。
- Full suite與最終 live API結果記錄於 validation report。
