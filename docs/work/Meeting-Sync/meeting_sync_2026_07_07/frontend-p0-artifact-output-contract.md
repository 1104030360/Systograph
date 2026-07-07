# 前端同步：P0 Artifact Output Contract

Last updated: 2026-07-08（10+1 計數、state vs build output、ViewerLoadResult 載入策略）

## 目的（Purpose）

Plan `03` 與 dynamic `00` 定義 multi-artifact output contract。Frontend 不應假設所有
資料都在 `ai_system_map.json` 內。

2026-07-07 UA 整合決策不改變 P0 public artifact 集合，也不新增 frontend JSON schema 欄位。

## 對外計數（避免「11 個 artifact」）

| 類別 | 數量 | 說明 |
|------|:----:|------|
| Public sibling artifacts（atomic publish） | **10** | 7 JSON + 3 render |
| Ephemeral graph projection | **+1** | `graph_view_model` — API inline；**非**磁碟 sibling |

舊文件「11 sibling artifacts（7 JSON + 3 render）」為計數錯誤（7+3=10）。若含 build 投影，
應寫 **「10 public siblings + 1 ephemeral projection」**。

## Build output vs project state（不算進 7 JSON）

**7 JSON** 只指一次 build 在 `output/{build_id}/` 的 public siblings，**不包含**：

| 儲存 | Identity | 角色 |
|------|----------|------|
| `scans/{scan_id}/snapshot.json` | `scan_id` | Step 3 immutable scan truth；**build 輸入** |
| `mappings/{mapping_id}.json` | `mapping_id` | Step 9 manual mapping；**下次 build 輸入** |
| `project.json`、build manifest | project / build | state metadata |

Apply 重用同一 `snapshot.json`、新 `build_id`、新一套 10 siblings。Manual mapping 經
Step 4-2 replay 影響 map，**不**直接改既有 `ai_system_map.json` 檔。

## Artifact 集合（10 public siblings）

Phase2 P0 build output：

```text
JSON（7）
  ai_system_map.json
  profile_signals.json
  readiness_report.json
  call_graph.json
  dataflow_hints.json
  execution_paths.json
  evidence_table.json

Render（3）
  ai_system_map.md
  system_map.mmd
  execution_map.mmd
```

JSON artifacts 為 independent sibling files，各自有 schema、writer、validation，
以及未來的 DB table 候選。

### Render 三檔用途（非 source of truth）

| 檔案 | 用途 | Viewer 主流程 |
|------|------|---------------|
| `ai_system_map.md` | Epic 1 人類可讀報告；`GET /api/map/report` | 可選；lazy `artifact_refs` |
| `system_map.mmd` | Plan 06 架構 Mermaid export | **不**取代 `graph_view_model` canvas |
| `execution_map.mmd` | dynamic 00 static execution Mermaid | lazy；Inspector / export |

三者 **不參與 scoring**；缺了不應 blocking canonical map load。

`ua-analysis-result.json` 是 `ScanSnapshot` 的 reserved nullable **snapshot internal sidecar**
slot，不屬於 P0 輸出集、不是 frontend public artifact，frontend 不得依賴或 fetch。Phase2
active path 不執行 `file-analyzer` bounded LLM，因此不產生、不消費 semantic sidecar；Step 6
不讀取它。

它們是 output artifacts，不會自動變成獨立的 frontend API responses。Backend 透過
project latest 或指定 `build_id` 的 build-scoped viewer payload 聚合選定 artifacts；Phase2
build/scan API 以安全 `ArtifactRef` 回傳 public artifacts。Internal UA sidecar 不得列入
public artifact references。

## ViewerLoadResult 載入策略

| inline | lazy（`artifact_refs`） |
|--------|-------------------------|
| `ai_system_map` | `call_graph` / `dataflow_hints` / `execution_paths` |
| `profile_inference_result` | `evidence_table` |
| `readiness_report` | `*.md` / `*.mmd` |
| `graph_view_model`（非磁碟檔） | |

- **主畫布 ≠ merge 六份 Step 6 JSON**；只有 **6-1** 經 Step 7 進 canvas。
- Sidecar 缺失 → degraded load + warnings；不 blocking canonical map。

詳見 `docs/MODEL-CONTRACT.md` §9、`docs/API-GUIDE.md` § ViewerLoadResult、
[`frontend-sync-overview.md`](frontend-sync-overview.md)。

## Frontend 影響

Frontend 應將 artifacts 視為獨立 surface：

| Artifact | Frontend 用途 |
|---|---|
| `ai_system_map.json` | canonical graph facts 與 evidence refs |
| `evidence_table.json` | 可查詢的 evidence table / evidence detail 來源（lazy load） |
| `profile_signals.json` | 經 API 欄位 `profile_inference_result` inline；非直接讀 path |
| `readiness_report.json` | readiness findings 與 report cards（inline） |
| `call_graph.json` | static call graph view（lazy） |
| `dataflow_hints.json` | shallow dataflow 說明（lazy） |
| `execution_paths.json` | static inferred execution path view（lazy） |
| `ai_system_map.md` | 人類可讀 report export（lazy） |
| `system_map.mmd` | Mermaid export（lazy） |
| `execution_map.mmd` | static execution Mermaid export（lazy） |
| `graph_view_model` | 主 canvas（inline；非磁碟檔） |

## API 邊界

`frontend-json-handoff` 下的 frontend samples 是 API payload、artifact files、
request payloads 與未來 previews 的 contract 範例。不要假設一個 sample file 等於一個 API route。

預期存取模式：

- Phase2 target `POST /api/scans` 與 Apply response 回傳含安全 `ArtifactRef` 的
  `MapBuildResult`；current `POST /api/map/build` 僅是 demo / compatibility route，可能仍有
  server-local `*_path` 欄位。
- `GET /api/projects/{project_id}/map-builds/latest` 載入指定 project 的最新 build。
- `GET /api/map-builds/{build_id}` 載入指定歷史 build。
- Process-wide `GET /api/map` 只保留為單專案 demo / legacy compatibility，不是 Phase2
  build history 的正式讀取入口。
- Artifact JSON files 維持 independent backend outputs 與未來 DB table 候選。
- Review decision samples 是 mutation request payloads，不是 scan output artifacts。
- Manual mapping 走 `/api/mappings`；**不是** build artifact。

## Evidence Table 邊界

`evidence_table.json` 是真實 artifact，必須由 backend writers 產出。

它可重用 `ai_system_map.json.evidence[]` 的 ids，但獨立存在，讓 frontend/report/database
layers 可查 evidence rows，而不必遍歷各 artifact-specific structure。

Frontend 不得在 browser 內組裝 `evidence_table.json`。

## Degraded Load

一般 viewer load 規則：

- 有效的 `ai_system_map.json` 可渲染 base graph；
- missing 的 profile/readiness/execution artifacts 應變成 warnings 或 disabled panels；
- strict validation/build flows 可 fail closed；
- frontend 不得 fabricate missing artifacts。

## 驗收標準（Acceptance Criteria）

- [ ] Frontend 文件與 sample 假設引用 separate artifacts。
- [ ] 對外計數使用 **10 public siblings + 1 ephemeral projection**；不寫「11 sibling JSON」。
- [ ] 不把 `snapshot.json` 或 manual mapping 算進 build 7 JSON。
- [ ] ViewerLoadResult inline vs lazy 對齊上表；主畫布只消費 `graph_view_model`。
- [ ] Evidence detail UI（若實作）可使用 stable evidence ids。
- [ ] Missing optional sidecar/execution/render artifacts 以 warning 降級。
- [ ] Frontend 不將 `ai_system_map.json` 視為所有 reports 的 aggregate output。

## 禁止事項（Do Not Do）

- 不要將 artifact data 打包成 frontend-only aggregate JSON。
- 不要在 frontend 產生 evidence ids。
- 不要因 optional public sidecar missing 就宣稱 scan 失敗（若 base map 有效）。
- 不要將 Mermaid artifacts 當 JSON table 資料來源或主 canvas 輸入。
- 不要在 viewer load 時 merge Step 6 sibling JSON 建 graph。
