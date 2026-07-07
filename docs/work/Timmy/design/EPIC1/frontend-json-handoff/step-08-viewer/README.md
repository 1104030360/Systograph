# frontend-json-sample.json 欄位說明

`ViewerLoadResult` — Phase2 primary API 為
`GET /api/projects/{project_id}/map-builds/latest` 或
`GET /api/map-builds/{build_id}` 的 viewer payload。
**第一次 build 完成即可顯示**，不等待 Step 9 review。

Process-wide `GET /api/map` 只保留為單專案 demo / legacy compatibility path，不可作為
project history 或多專案載入的正式入口。

## 這包資料從哪來？

**是，但不等於「把所有 JSON 貼成一大包」。**

Pipeline 在磁碟上仍會寫出 **多個 sibling 檔**（Step 4 map、Step 6 六份 sidecar、Step 7 graph 等）。
`ViewerLoadResult` 是 **給 Viewer 第一次載入用的 API 聚合**，把「畫面立刻需要」的內容 inline，其餘只給安全的 `ArtifactRef` 供之後 lazy load。

| 來源步驟 | 磁碟 artifact | 在 sample 裡怎麼出現 |
|----------|---------------|---------------------|
| Step 4 | `ai_system_map.json` | **inline** → `ai_system_map` |
| Step 6 | `profile_signals.json` | **inline** → `profile_inference_result`（欄位名不同，內容同 schema） |
| Step 6 | `readiness_report.json` | **inline** → `readiness_report` |
| Step 6 | `evidence_table.json` | 僅 **reference** → `artifact_refs[]` |
| Step 6 | `call_graph.json` 等三件套 | 僅 **reference** → `artifact_refs[]` |
| Step 7 | `graph_view_model`（投影，非獨立 sidecar 檔名慣例） | **inline** → `graph_view_model` |
| Step 7 | `MapBuildResult` | **不在** ViewerLoadResult 內；build API 另一層，可選填 `viewer_load_result` |
| Step 9 | mapping proposal | **不在**；review 走獨立 API |

```
Build 產物（磁碟，多檔）          ViewerLoadResult（API 聚合）
─────────────────────────        ─────────────────────────────
ai_system_map.json        ──────► ai_system_map          [inline]
profile_signals.json      ──────► profile_inference_result [inline]
readiness_report.json     ──────► readiness_report       [inline]
(map + profile 投影)       ──────► graph_view_model       [inline]
evidence_table.json       ──────► artifact_refs[]       [safe reference]
call_graph / dataflow / paths ──► artifact_refs[]       [safe reference]
*.md / *.mmd              ──────► artifact_refs[]       [safe reference]
```

**重點：**

- `graph_view_model` 是 backend **從 map + profile 等投影出來**的，不是把 Step 6 sidecar 原樣 merge。
- handoff sample 為方便前端開發 **選擇 inline 四塊**；正式載入仍必須以 response 的
  `project_id` / `build_id` 驗證 scope。Lazy load 必須透過受控 API 解析 `artifact_id`，
  frontend 不可直接讀 server-local path。
- static 三件套（call / dataflow / paths）P0 主畫面不一定需要；路徑先備著，Inspector 或進階面板再載。

## 頂層

| 欄位 | 白話 |
|------|------|
| `loaded` | 是否成功載入 |
| `project_id` / `scan_id` / `build_id` | 目前 payload 所屬 project、scan 與 build identity |
| `based_on_build_id` / `applied_mapping_ids` | Apply build 的 lineage；initial build 可為 `null` / 空陣列 |
| `environment_id` | assessment environment scope |
| `error_reason` | 失敗原因（成功為 `null`） |
| `artifact_refs` | Stable artifact id/type、basename、media type、digest 與大小；不含 server-local path |
| `ai_system_map` | 可 inline 整份 map，或只靠 path 再載 |
| `profile_inference_result` | inline 的 `profile-signals/v1`（同 Step 6 sidecar） |
| `readiness_report` | inline 的 `readiness-report/v1` |
| `graph_view_model` | inline 的 canvas 投影（同 Step 7 sample） |

## 注意

- 內嵌的 map / profile / readiness / graph 可改為只給 `ArtifactRef`，實際 API 行為以
  backend 為準；reference fetch 也必須維持同一 `project_id` / `build_id` scope。
- Frontend **不**從這包資料 write back；review decision 走 Step 9 API，下次 build 才更新。
