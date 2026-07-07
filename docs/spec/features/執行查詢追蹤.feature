Feature: 執行查詢追蹤
  使用者對既有 build 執行 opt-in Query Trace；結果保持 transient，不能成為 canonical/profile artifact。

  Rule: Active Phase2 Query Trace request 必須綁定 build_id

    Example: 對 B2 執行 Query Trace
      Given build "B2" 已 publish
      When 使用者呼叫 "/api/trace" 執行 Query Trace
      Then Query Trace request 的 build_id 為 "B2"
      And Trace result 的 source_build_id 為 "B2"
      And Trace result 的 source_scan_id 與 build "B2" 的 scan_id 相同

  Rule: Query Trace 不得建立或修改 build artifacts

    Example: B2 Query Trace 完成
      Given build "B2" 的 canonical 與 profile artifacts 已 publish
      When 使用者呼叫 "/api/trace" 執行 Query Trace
      Then persisted child build 數量為 0
      And build "B2" 的 ai_system_map.json 與 Query Trace 前相同
      And build "B2" 的 profile_signals.json 與 Query Trace 前相同

  Rule: Query Trace 結果必須保持 transient

    Example: Query Trace 回傳 runtime steps
      Given 使用者已對 build "B2" 啟動 opt-in Query Trace
      When Query Trace 完成
      Then Trace result 的 persistence 狀態為 "transient"

  Rule: Query Trace 結果只保留於目前 Viewer session

    Example: 同一個 Viewer session 可檢視 Trace result
      Given 使用者已對 build "B2" 完成 opt-in Query Trace
      When 使用者仍在同一個 Viewer session 檢視 Trace panel
      Then UI 顯示該次 Query Trace result
      And persisted trace artifact 數量為 0

    Example: 頁面 reload 後清除 Trace result
      Given 使用者已對 build "B2" 完成 opt-in Query Trace
      When 使用者 reload Viewer 頁面
      Then UI 不顯示 reload 前的 Query Trace result
      And persisted trace artifact 數量為 0
