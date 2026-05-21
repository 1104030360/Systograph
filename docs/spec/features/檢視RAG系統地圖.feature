# language: zh-TW
功能: 檢視 RAG 系統地圖
  Viewer 是 `ai_system_map.json` 的呈現層，不是 scanner。

  規則: Viewer 載入有效 map

    場景: 顯示 graph
      假設 使用者提供有效的 "ai_system_map.json"
      當 viewer 載入 map
      那麼 graph 顯示 component slots
      而且 graph 顯示 flows and edges
      而且 node detail panel 可以顯示 evidence

  規則: Viewer 不重新掃描 project folder

    場景: map 中沒有的 component 不得自行補上
      假設 "ai_system_map.json" 沒有 llm component
      當 viewer 顯示 graph
      那麼 viewer 不得自行推論 llm component
      而且 viewer 不得讀取 project folder 來補資料

  規則: 無效 map 顯示錯誤狀態

    場景: map JSON 格式錯誤
      假設 使用者提供無效的 map JSON
      當 viewer 載入 map
      那麼 viewer 顯示 error state
      而且 viewer 不顯示半完成 graph

  規則: Filter 保留完整 graph，只高亮符合項目

    場景: 套用 risk hint filter
      假設 viewer 已顯示完整 graph
      當 使用者套用 filter "risk hint"
      那麼 符合條件的 items 被高亮
      而且 不符合條件的 items 仍保留在 graph 中
