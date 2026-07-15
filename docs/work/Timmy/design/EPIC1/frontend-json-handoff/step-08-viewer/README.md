# Step 8 — Viewer

Last updated: 2026-07-15（current `ViewerPayload` runtime fixture）

[`frontend-json-sample.json`](frontend-json-sample.json) 現在是 current backend
`ViewerPayload` contract，可由 `POST /api/viewer/load` 或 process-wide `GET /api/map` 回傳。
它已通過 current Pydantic model，不再混入尚未存在的 top-level profile、readiness 或
`ArtifactRef` 欄位。

## Fixture boundary

這份 sample 由 current `/api/viewer/load` 對 v1 fixture 的實際 response 收斂而來，保留完整
raw v1 `ai_system_map`，但把 graph 截短成 6 nodes／2 edges，並把重複的 serialized
`map_json` 與 compatibility path 設為 `null`，讓文件可讀：

- 1 個 `reference_capability`
- 3 個一般 `repo_component`
- 1 個 current legacy extension `repo_component`
- 1 個 `unmapped_component`

`graph_view_model.summary.fixture_scope="current_contract_fragment"` 明確標示它不是完整
runtime projection。原始 runtime response 有 67 nodes；正式 projection 仍必須 emit 全 52 個
reference nodes。Frontend 不可從 sample 的 node 數推導完整性。

## Current `ViewerPayload`

```text
viewer_load_result
  loaded / error_reason / map_json
  ai_system_map
  graph_view_model
```

| 欄位 | 白話 |
| --- | --- |
| `loaded` | Map 是否成功載入；失敗時仍回 bounded `error_reason` 與 empty graph |
| `map_json` | Optional serialized map compatibility 欄位；sample 設為 `null`，避免重複整份 map |
| `ai_system_map` | `/api/viewer/load` 載入的 raw public map；current default 是 v1 |
| `graph_view_model` | Backend 從 normalized map 投影的 richer canvas contract |

Current `ViewerLoadResult` **沒有** `project_id`、lineage、profile、readiness 或
`artifact_refs` top-level 欄位。Build identity 若存在，位於 graph；project／build lineage 則由
build-scoped envelope 擁有。

## Build-scoped current API

多專案／history 正式讀取 surface 是 current backend 的：

```http
GET /api/projects/{project_id}/map-builds/latest
GET /api/map-builds/{build_id}
```

它們回 `MapBuildScopedResponse`：

- 外層：`project_id`、`scan_id`、`build_id`、`based_on_build_id`、`build_reason`、
  `applied_mapping_ids`。
- `build_result`：schema versions、warnings、`profile_inference_result`、
  `readiness_report`。
- `viewer_load_result`：raw map + graph。

Frontend `viewerApi.ts` 目前仍呼叫 process-wide `/api/map`，尚未切到 project-scoped latest；
所以文件會保留這個 integration gap，不能把 backend endpoint 存在寫成 UI 已完成。

## 10 siblings 與 +1 projection

磁碟仍是 10 個 public siblings（7 JSON + 3 render）；Viewer 不把它們黏成一份新的 canonical
truth。`GraphViewModel` 是 +1 ephemeral API projection。Safe `ArtifactRef` lazy load 是 future
target，目前不能出現在 runtime parser。

## Frontend consumer 注意事項

- Current `frontend/src/types.ts` 能 parse sample，但只保留舊 node／detail／filter 子集合；
  rich identity、relationships、profile／reference details 與 lenses 仍會被 Zod 丟棄。
- Viewer 只 render backend status，不重算五態、activation 或 Mapping Completeness。
- Review decision 走 Step 9 API；Viewer 不 write back raw map，Apply 後載入新的 child build。
- Sample 中保留 legacy extension 是 current runtime truth，不代表 Plan 13 target 允許繼續寫入。

## 驗證

```bash
.venv/bin/python -m pytest \
  tests/web/test_viewer_routes.py \
  tests/web/test_map_routes.py -q
```
