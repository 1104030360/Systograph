# 前端同步：P0 Artifact Output Contract

Last updated: 2026-07-07（UA 整合決策對齊）

## 目的（Purpose）

Plan `03` 與 dynamic `00` 定義 multi-artifact output contract。Frontend 不應假設所有
資料都在 `ai_system_map.json` 內。

2026-07-07 UA 整合決策不改變 P0 public artifact 集合，也不新增 frontend JSON schema 欄位。

## Artifact 集合

Phase2 P0 可能產出：

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

JSON artifacts 為 independent sibling files，各自有 schema、writer、validation，
以及未來的 DB table 候選。

`ua-analysis-result.json` 是 `ScanSnapshot` 的 reserved nullable **snapshot internal sidecar**
slot，不屬於 P0 輸出集、不是 frontend public artifact，frontend 不得依賴或 fetch。Phase2
active path 不執行 `file-analyzer` bounded LLM，因此不產生、不消費 semantic sidecar；Step 6
不讀取它。

它們是 output artifacts，不會自動變成獨立的 frontend API responses。Backend 透過
project latest 或指定 `build_id` 的 build-scoped viewer payload 聚合選定 artifacts；Phase2
build/scan API 以安全 `ArtifactRef` 回傳 public artifacts。Internal UA sidecar 不得列入
public artifact references。

## Frontend 影響

Frontend 應將 artifacts 視為獨立 surface：

| Artifact | Frontend 用途 |
|---|---|
| `ai_system_map.json` | canonical graph facts 與 evidence refs |
| `evidence_table.json` | 可查詢的 evidence table / evidence detail 來源（若對外暴露） |
| `profile_signals.json` | capability overlay details |
| `readiness_report.json` | readiness findings 與 report cards |
| `call_graph.json` | static call graph view（若啟用） |
| `dataflow_hints.json` | shallow dataflow 說明 |
| `execution_paths.json` | static inferred execution path view |
| `system_map.mmd` | system map 渲染輸出 |
| `execution_map.mmd` | static execution map 渲染輸出 |

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
- [ ] Evidence detail UI（若實作）可使用 stable evidence ids。
- [ ] Missing optional sidecar/execution artifacts 以 warning 降級。
- [ ] Frontend 不將 `ai_system_map.json` 視為所有 reports 的 aggregate output。

## 禁止事項（Do Not Do）

- 不要將 artifact data 打包成 frontend-only aggregate JSON。
- 不要在 frontend 產生 evidence ids。
- 不要因 optional public sidecar missing 就宣稱 scan 失敗（若 base map 有效）。
- 不要將 Mermaid artifacts 當 JSON table 資料來源。
