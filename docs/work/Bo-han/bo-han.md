# Bo-Han 工作範圍 - Epic 1 呈現層

> 負責範圍：Viewer、graph UX、detail panel、filters

## 目標

Bo-Han 在 `ai-system-map/v1` 穩定後負責 presentation layer。Viewer 要協助使用者檢視 map，但不能變成第二套 scanner。

## 責任

- 實作 `kai-mind viewer <map_json>`。
- 載入並驗證 `ai_system_map.json`。
- 從 map data 建立 graph view model。
- 呈現 nodes、edges、endpoints、risk hints 與 missing slots。
- 顯示 node / edge detail panel。
- 顯示 evidence 與相關 risk hints。
- 實作 highlight-only filters。
- Invalid map input 顯示 error state。
- 新增 viewer and view-model tests。

## 不負責

- Filesystem scanning。
- Config、Docker Compose、dependency 或 code parsing。
- 判斷 component 是否存在。
- 創造 JSON 中不存在的 components。
- Runtime health checks。
- Epic 1 MVP 的 query trace replay。

## 必須交付

| 交付物 | 說明 |
|---|---|
| Viewer load flow | Valid map 顯示 graph；invalid map 顯示 error |
| Graph view model | 只從 `ai_system_map.json` 建立 |
| Detail panel | 顯示 slot、status、evidence、risk hints |
| Filters | 保留完整 graph，只高亮 matches |
| Tests | Valid map、invalid map、detail panel、filters、no full secret |

## 與 Timmy 的契約

Bo-Han 依賴：

- stable `ai-system-map/v1`
- sample maps
- evidence refs
- risk hint refs
- flow and edge fields
- human-readable labels

如果欄位不足，應請 Timmy 加進 schema，不要在 viewer 補假資料。

## Review 檢查清單

- Viewer 不讀取 project files。
- Viewer 不推論 JSON 中不存在的 components。
- Viewer 不顯示未遮罩 secrets。
- Filters 預設不隱藏 unmatched graph items。
- Invalid maps 不顯示 partial graphs。
