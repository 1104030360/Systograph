# Step 7 — 投影 + 發布

Build 完成後的 **Plan 06 target API 索引** 與 **richer canvas 投影**。Frontend 只
render backend 投影，不自行推 status。這兩份 sample 不是 current S1 OpenAPI shape。

---

## frontend-map-build-result-sample.json

Later `MapBuildResult` + `ArtifactRef` target。Current S1 `POST /api/scans` 建 initial build、
Apply endpoint 建 child build，但 response 使用 `MapBuildScopedResponse`：lineage 在外層、
profile/readiness 在 `build_result`、base graph 在 `viewer_load_result`，尚無 `artifacts[]`。

| 欄位 | 白話 |
|------|------|
| `status` | `ok` 或錯誤 |
| `generated_from_build_id` | 必須等於這次 result 的 `build_id` |
| `artifacts[]` | Stable `ArtifactRef` 清單；只含 id/type/basename/media type/digest/size |
| `viewer_load_result` | 可能為 `null`（只給 artifact references）或內嵌完整 viewer payload |
| `warnings` / `error` | 非致命警告或失敗原因 |

Phase2 target response 不回傳 `output_run_dir` 或 `*_path` 等 server-local path；這些欄位只
屬於 current compatibility contract。Frontend lazy load 必須以 `artifact_id` 呼叫受控 API。

---

## frontend-graph-view-model-sample.json

`graph-view-model/v1` — **畫布直接吃的資料**（nodes / edges / details / filters）。

> **Fixture boundary：** `frontend-graph-view-model-sample.json` 只是一份局部 projection
> fixture，用來示範 repo overlay / profile / review node 的欄位，不是完整正式 payload。
> 正式 Phase2 `GraphViewModel` 必須由 backend 依 reference catalog emit 完整 10 planes / 52
> 個 `reference_capability` nodes，再疊加 evidence-backed `repo_component` nodes。Frontend
> 不得用本 fixture 的少量 nodes 推導或補造其餘 reference nodes。

| 欄位 | 白話 |
|------|------|
| `nodes[]` | 畫布上的節點（component、profile attachment、unmapped review…） |
| `reference_map_version` | backend 使用的 52-node catalog 版本 |
| `mapping_completeness` | backend 從完整 52 格計算的 numerator / denominator / value / weights |
| `summary.fixture_scope` | sample 固定 `partial_projection_fragment`，明示不是完整 52-node payload |
| `activation` | 與 assessment 五態分開的啟用狀態 |
| `semantic_kind` | 節點語意：`canonical_component` / `profile_attachment` / `unmapped_component` |
| `source_id` | 對回 map 或 profile 的 ID |
| `badges` | UI 小標（detected、grounding、review…） |
| `anchor_node_ids` | profile 或 review 節點掛在哪個 component 旁 |
| `edges[]` | 畫布連線（`from` / `to` 是 **node id**，不是 component id） |
| `details.evidence_by_id` | 點 evidence 時顯示的詳情 |
| `details.profile_findings_by_id` | 點 profile 時顯示的摘要 |
| `filters` | 圖上篩選器狀態 |

**規則：** 不要從 topology 自己算 status / completeness；全部用 backend 給的值。
