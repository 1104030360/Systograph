Feature: 檢視建置報告
  使用者檢視 project 的 build history、latest build 或特定 immutable build 報告。

  Rule: 使用者可列出 project-scoped build history

    Example: 查詢專案的 map builds
      Given 使用者指定一個既有 project_id
      When 使用者呼叫 "GET /api/projects/{project_id}/map-builds"
      Then 回傳的每個 build 的 project_id 與 request project_id 相同

  Rule: Build history 必須預設以新到舊 deterministic ordering 回傳

    Example: 多筆 builds 具有相同 generated_at
      Given project 有多筆 build history
      When 使用者呼叫 "GET /api/projects/{project_id}/map-builds"
      Then build history 先依 generated_at 由新到舊排序
      And generated_at 相同時依 build_id 由大到小排序

    Example: 最新 build 顯示在第一筆
      Given project latest build_id 為 "B3"
      And project 有 build "B1"、"B2" 與 "B3"
      When 使用者呼叫 "GET /api/projects/{project_id}/map-builds"
      Then build history 第一筆 build_id 為 "B3"

  Rule: 使用者可取得 project 的 latest build

    Example: 查詢最新 build
      Given request project 的 latest_build_id 為 "B2"
      When 使用者呼叫 "GET /api/projects/{project_id}/map-builds/latest"
      Then 回傳的 build_id 為 "B2"

  Rule: 使用者可取得指定 immutable build

    Example: 查詢 B1
      Given build_id "B1" 已 publish
      When 使用者呼叫 "GET /api/map-builds/{build_id}"
      Then 回傳的 build_id 為 "B1"

  Rule: Viewer 必須渲染 backend projection

    Example: 開啟 fixed reference map 與 repo overlay
      Given build "B1" 已產生 GraphViewModel
      When 使用者檢視 build "B1"
      Then frontend 顯示的 assessment status 等於 GraphViewModel 的 assessment status
      And frontend 顯示的 activation 等於 GraphViewModel 的 activation
      And frontend 顯示的 Mapping Completeness 等於 GraphViewModel 的 Mapping Completeness

  Rule: Frontend 不得自行重算 assessment status

    Example: topology 與 label 可供 frontend 讀取
      Given GraphViewModel 已包含 topology 與 label
      When 使用者檢視 build "B1"
      Then frontend 的 assessment calculation 次數為 0

  Rule: 使用者可在同一 canvas 切換 repo overlay 可見性

    Example: 關閉 repo overlay 仍保留 reference map
      Given 使用者已檢視 build "B1"
      And GraphViewModel 包含 fixed reference map 與 repo overlay
      When 使用者關閉 repo overlay
      Then canvas 仍顯示 fixed reference map
      And canonical nodes 與 edges 數量不變
      And frontend 的 assessment calculation 次數為 0
      And build identity 仍為 "B1"

    Example: 開啟 repo overlay 顯示 backend 投影狀態
      Given 使用者已檢視 build "B1"
      And GraphViewModel 包含 repo overlay assessment
      When 使用者開啟 repo overlay
      Then frontend 顯示的 assessment status 等於 GraphViewModel 的 assessment status
      And frontend 顯示的 activation 等於 GraphViewModel 的 activation
      And frontend 的 assessment calculation 次數為 0

  Rule: 切換視角不得重新載入 build 或替換 graph surface

    Example: 切換 lens 後仍使用同一 build payload
      Given 使用者已檢視 build "B1"
      And GraphViewModel 已載入完成
      When 使用者切換 viewer 視角
      Then 額外的 map API 呼叫次數為 0
      And build identity 仍為 "B1"
      And frontend 的 assessment calculation 次數為 0

  Rule: 使用者可切換 backend 提供的 lens 檢視

    Example: 切換到 Data lens
      Given build "B1" 的 GraphViewModel 包含 lens "Data" 與其 matches_node_ids
      When 使用者選擇 lens "Data"
      Then canvas 依 matches_node_ids highlight 或 dim 節點與邊
      And canonical nodes 與 edges 數量不變
      And frontend 的 assessment calculation 次數為 0

  Rule: 不支援的 lens 必須 disabled 且不得猜測 membership

    Example: payload 缺少 Governance lens membership
      Given build "B1" 的 GraphViewModel 不包含 lens "Governance"
      When 使用者檢視 build "B1"
      Then lens "Governance" 為 disabled
      And frontend 建立的 synthetic node 數量為 0
      And frontend 建立的 synthetic edge 數量為 0

  Rule: Profile sidecar 缺失時 normal viewer 必須 degraded load

    Example: profile_signals.json 不存在
      Given build "B1" 的 canonical map 可用
      And build "B1" 的 profile_signals.json 狀態為 "missing"
      When 使用者以 normal mode 檢視 build "B1"
      Then viewer payload 包含 canonical graph
      And viewer 顯示 stable warning

  Rule: Profile sidecar 損壞時 strict validation 必須 fail closed

    Example: profile_signals.json 格式無效
      Given build "B1" 的 profile_signals.json 狀態為 "invalid"
      When 使用者以 strict mode 檢視 build "B1"
      Then 操作失敗
      And 回傳 HTTP status 為 422
      And 回傳錯誤碼為 "profile_sidecar_contract_invalid"
      And viewer payload 為空

  Rule: Profile sidecar 損壞時 normal viewer 必須 degraded load

    Example: profile_signals.json 格式無效
      Given build "B1" 的 canonical map 可用
      And build "B1" 的 profile_signals.json 狀態為 "invalid"
      When 使用者以 normal mode 檢視 build "B1"
      Then viewer payload 包含 canonical graph
      And viewer 顯示 stable warning
      And load-time profile inference 執行次數為 0

  Rule: Mapping Completeness 必須使用固定 reference catalog 分母

    Example: Reference node activation 為 not_applicable
      Given fixed reference catalog 的 reference node 數量為 52
      And 一個 reference node 的 activation 為 "not_applicable"
      When 使用者檢視 build "B1"
      Then Mapping Completeness 的分母為 52

  Rule: Mapping Completeness 不得顯示為信心或品質分數

    Example: 顯示 assessment 摘要
      Given backend projection 包含 Mapping Completeness
      When 使用者檢視 build "B1"
      Then UI 指標名稱為 "Mapping Completeness"
