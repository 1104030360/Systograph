Feature: 檢視靜態執行路徑
  使用者檢視 build 的 static inferred execution artifacts，了解 query 可能如何流經系統。

  Rule: 使用者可檢視 build 的 static execution path

    Example: 開啟 execution path panel
      Given build "B1" 已產生 execution_paths.json
      When 使用者開啟 static execution path panel
      Then UI 顯示 execution path 的 label 與 steps
      And UI 顯示 runtime_verified 為 false
      And frontend 建立的 synthetic execution step 數量為 0

  Rule: 使用者可檢視 call graph

    Example: 開啟 call graph view
      Given build "B1" 已產生 call_graph.json
      When 使用者開啟 call graph view
      Then UI 顯示 backend 提供的 call edges
      And 每個 call edge 保留 evidence refs 或 undetermined reason
      And frontend 推導的 call edge 數量為 0

  Rule: 使用者可檢視 shallow dataflow hints

    Example: 開啟 dataflow hints list
      Given build "B1" 已產生 dataflow_hints.json
      When 使用者開啟 dataflow hints list
      Then UI 顯示 backend 提供的 dataflow hints
      And frontend 推導的 dataflow hint 數量為 0

  Rule: 使用者可檢視 rendered execution map

    Example: 開啟 execution_map.mmd
      Given build "B1" 已產生 execution_map.mmd
      When 使用者開啟 execution map view
      Then UI 顯示 backend 提供的 Mermaid 內容
      And frontend 合成的 Mermaid 節點數量為 0

  Rule: 使用者可從 execution artifact drill-down 到 evidence

    Example: 點選 execution step 的 evidence ref
      Given execution path step 包含 evidence_ids
      And evidence_table.json 包含對應 evidence row
      When 使用者點選該 step 的 evidence ref
      Then Evidence Inspector 顯示對應 evidence detail

  Rule: Static execution 不得宣稱 runtime 已執行

    Example: 顯示 inferred path
      Given execution path 的 inference_kind 為 "static_inferred"
      And execution path 的 runtime_verified 為 false
      When 使用者檢視該 execution path
      Then UI 不得顯示 "executed"
      And UI 不得顯示 "traversed at runtime"
      And UI 不得顯示 "Runtime path confirmed"

  Rule: Partial 或 undetermined path 必須顯示 limitations

    Example: execution path 狀態為 undetermined
      Given execution path 的 status 為 "undetermined"
      And execution path 包含 limitations
      When 使用者檢視該 execution path
      Then UI 顯示 limitations
      And frontend 補齊的完整 pipeline step 數量為 0

  Rule: Static execution artifacts 缺失時必須 degraded load

    Example: execution_paths.json 不存在
      Given build "B1" 的 canonical map 可用
      And build "B1" 的 execution_paths.json 狀態為 "missing"
      When 使用者開啟 static execution path panel
      Then viewer 顯示 stable warning
      And frontend 合成的 execution path 數量為 0

  Rule: Frontend 不得將 static execution 轉成 runtime trace steps

    Example: 檢視 static execution path 後觸發 trace replay
      Given build "B1" 已產生 execution_paths.json
      And 使用者已開啟 static execution path panel
      When 使用者檢視 runtime trace replay
      Then runtime trace 的 trace_steps 來源為 "/api/trace"
      And frontend 從 execution_paths 轉換的 trace_step 數量為 0

  Rule: Static execution 不得 mutate canonical graph

    Example: 檢視 call graph 後重新載入 build
      Given build "B1" 已產生 call_graph.json
      When 使用者開啟 call graph view
      And 使用者重新載入 build "B1"
      Then GraphViewModel 的 canonical nodes 與 edges 數量不變
      And artifact mutation 數量為 0

  Rule: Static execution view 不得混入 runtime trace latency 或 status

    Example: 僅有 static execution artifacts
      Given build "B1" 已產生 execution_paths.json
      And build "B1" 未提供 runtime trace payload
      When 使用者開啟 static execution path panel
      Then UI 不得顯示 runtime latency
      And UI 不得顯示 runtime step status

  Rule: Static execution view 與 Graph Studio lens 分離

    Example: 切換 Graph Studio lens 不影響 static execution panel
      Given 使用者已開啟 static execution path panel
      And 使用者已檢視 build "B1" 的 GraphViewModel
      When 使用者選擇 lens "Data"
      Then static execution path panel 仍顯示 execution_paths.json 內容
      And frontend 將 execution path 併入 lens membership 的次數為 0
