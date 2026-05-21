Feature: 檢視 RAG 系統地圖
  Viewer 是 `ai_system_map.json` 的呈現層，不是 scanner。

  Rule: Viewer 載入有效 map

    Example: 顯示 graph
      Given 使用者提供有效的 "ai_system_map.json"
      When viewer 載入 map
      Then graph 顯示 component slots
      And graph 顯示 flows and edges
      And node detail panel 可以顯示 evidence

  Rule: Viewer 不重新掃描 project folder

    Example: map 中沒有的 component 不得自行補上
      Given "ai_system_map.json" 沒有 llm component
      When viewer 顯示 graph
      Then viewer 不得自行推論 llm component
      And viewer 不得讀取 project folder 來補資料

  Rule: 無效 map 顯示錯誤狀態

    Example: map JSON 格式錯誤
      Given 使用者提供無效的 map JSON
      When viewer 載入 map
      Then viewer 顯示 error state
      And viewer 不顯示半完成 graph

  Rule: Filter 保留完整 graph，只高亮符合項目

    Example: 套用 risk hint filter
      Given viewer 已顯示完整 graph
      When 使用者套用 filter "risk hint"
      Then 符合條件的 items 被高亮
      And 不符合條件的 items 仍保留在 graph 中
