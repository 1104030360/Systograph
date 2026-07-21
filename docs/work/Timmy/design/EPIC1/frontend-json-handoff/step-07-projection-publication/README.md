# Step 7 — Projection / Publication

Last updated: 2026-07-15（backend projection current；ArtifactRef target 分離）

Step 7 有兩個不同 surface：

1. `GraphProjectionService` 產生 ephemeral `GraphViewModel`，已在 current backend 上線。
2. Publisher 寫出同 build 的 10 個 public siblings；安全的 `ArtifactRef[]` API index 尚未上線。

Frontend 只 render backend 給的 status、identity、relationships、filters 與 lenses，不從 graph
topology 重算 assessment 或 Mapping Completeness。

## frontend-graph-view-model-sample.json

這份 sample 通過 current `GraphViewModel` Pydantic model，但刻意是
`partial_projection_fragment`，只示範 contract，不假裝是完整 runtime graph。

正式 runtime projection 會包含：

- 固定 10 planes／52 個 `reference_capability` nodes。
- Evidence-backed `repo_component` nodes。
- Optional `unmapped_component`、`capability_candidate`、`profile_attachment` overlays。
- Canonical topology `edges[]` 與非 runtime topology 的 semantic `relationships[]`。
- `reference_assessments_by_id`、`profile_findings_by_id` 等 detail lookup。
- Backend-owned filters 與 6 個 lenses：data、control、evidence、governance、source、risk。

| 欄位 | 白話 |
| --- | --- |
| `reference_map_version` | 52-node catalog 版本 |
| `mapping_completeness` | Backend 依 52 格計算；`status_counts` 必須合計 52 |
| `nodes[].semantic_kind` | `reference_capability` / `repo_component` / `unmapped_component` / `capability_candidate` / `profile_attachment` |
| `nodes[].assessment_scope` | Reference／profile assessment 所屬 build、scan、environment |
| `nodes[].activation` | 與 assessment status 分開 |
| `edges[].from` / `to` | Graph node id，不是 component id |
| `relationships[]` | Reference mapping、profile anchor、candidate source 等語意關係 |
| `details` | Evidence、risk、reference assessment、profile、candidate lookup |
| `filters.available` / `filters.lenses` | Backend 已算好的 highlight sets |

Sample 只放 5 個節點，不能被 frontend 用來補造其餘 47 個 reference nodes。完整性只能相信
backend runtime payload。

## Current API envelope

Current `GET /api/projects/{project_id}/map-builds/latest` 與
`GET /api/map-builds/{build_id}` 回傳 `MapBuildScopedResponse`：

```text
project_id / scan_id / build_id / lineage
build_result
  active_schema_version / requested_schema_version
  profile_inference_result / readiness_report
viewer_load_result
  ai_system_map / graph_view_model
```

`POST /api/viewer/load` 與 process-wide `/api/map` 則回 `ViewerPayload` 包裝的
`viewer_load_result`。Frontend 目前仍使用後者；project-scoped migration 尚未完成。

## frontend-map-build-result-sample.json

這份檔案是 **future safe artifact index target**，不是 current Pydantic／OpenAPI response。

| 欄位 | 白話 |
| --- | --- |
| `artifacts[]` | Stable id、type、basename、media type、digest、size |
| `generated_from_build_id` | 必須等於本次 `build_id` |
| `based_on_build_id` / `applied_mapping_ids` | Apply lineage |
| `viewer_load_result` | 可選擇 inline 或另由受控 API 載入 |

Target response 不得暴露 `output_run_dir` 或 `*_path`。Lazy load 必須使用受控
`artifact_id` endpoint；frontend 不可直接讀 server-local filesystem path。直到正式 schema、
route 與 tests 完成前，這份 sample 只能用於 API design，不可交給 runtime parser。

## Publication invariant

每個成功 build 必須 atomic publish 10 個 siblings：

```text
ai_system_map.json
evidence_table.json
call_graph.json
dataflow_hints.json
execution_paths.json
profile_signals.json
readiness_report.json
ai_system_map.md
system_map.mmd
execution_map.mmd
```

`GraphViewModel` 是 +1 ephemeral projection，不列入 sibling count。
