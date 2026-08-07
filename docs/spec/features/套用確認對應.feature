Feature: 套用確認對應
  使用者把已保存的 confirmed mappings 套用到同一份 immutable snapshot，完整重算並建立新的 child build。

  Rule: Apply 不得重新掃描 repo

    Example: 從 B1 套用 confirmed mapping
      Given build "B1" 有一筆 confirmed mapping
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then filesystem provider scan 執行次數為 0
      And provider collection 執行次數為 0

  Rule: Apply 必須保留 base build 不變

    Example: B1 套用後建立 B2
      Given build "B1" 已 publish
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then build "B1" 的 artifacts 與 Apply 前相同

  Rule: Apply 必須從 component detection 起完整重算 sibling artifacts

    Example: 套用 capability candidate mapping
      Given build "B1" 有一筆 confirmed non-baseline mapping
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 新 build 包含 artifacts
        | artifact_name          |
        | ai_system_map.json     |
        | profile_signals.json   |
        | readiness_report.json  |
        | evidence_table.json    |
        | call_graph.json        |
        | dataflow_hints.json    |
        | execution_paths.json   |
        | ai_system_map.md       |
        | system_map.mmd         |
        | execution_map.mmd      |

  Rule: Apply 必須沿用 base build 的 scan 與 snapshot

    Example: B1 產生 B2
      Given build "B1" 已關聯一個 scan_id
      And build "B1" 已關聯一個 snapshot_id
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 新 build 的 scan_id 與 build "B1" 的 scan_id 相同
      And 新 build 的 snapshot_id 與 build "B1" 的 snapshot_id 相同

  Rule: Apply 必須建立 immutable child build

    Example: B1 產生 B2
      Given latest build_id 為 "B1"
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 新 build 的 based_on_build_id 為 "B1"
      And 新 build 的 build_reason 為 "apply_confirmations"
      And 新 build 的 build_id 不等於 "B1"

  Rule: Apply 必須使用非空且唯一的 confirmed mappings

    Example: Apply 未提供 confirmed mapping
      Given base build_id 為 "B1"
      And confirmed mapping 數量為 0
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 操作失敗

  Rule: Apply 必須拒絕 cross-project mapping

    Example: Mapping 屬於另一個 project
      Given build "B1" 與 mapping "mapping-1" 屬於不同 project_id
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 回傳 HTTP status 為 422
      And persisted build 數量與 Apply 前相同

  Rule: Apply 必須拒絕 unconfirmed mapping

    Example: Mapping 尚未 confirmed
      Given mapping "mapping-1" 的 decision 不等於 "confirmed"
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 回傳 HTTP status 為 422
      And persisted build 數量與 Apply 前相同

  Rule: Apply 必須拒絕 duplicate mapping ids

    Example: Request 重複 mapping id
      Given Apply request 的 mapping_ids 為
        | mapping_id |
        | mapping-1  |
        | mapping-1  |
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 回傳 HTTP status 為 422
      And persisted build 數量與 Apply 前相同

  Rule: Apply 必須拒絕 stale base build

    Example: B1 已不是 latest
      Given latest build_id 為 "B2"
      And base_build_id 為 "B1"
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 回傳 HTTP status 為 409
      And 回傳錯誤碼為 "base_build_not_latest"

  Rule: 相同 Apply retry 必須 idempotent

    Example: 重送相同 base 與 mapping digests
      Given base_build_id、sorted mapping_ids 與 mapping digests 與前次成功 request 相同
      When 使用者再次呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then persisted child build 數量與 retry 前相同

  Rule: Apply 驗證或 publish 失敗不得切換 latest

    Example: B2 validation 失敗
      Given latest build_id 為 "B1"
      And child build validation 狀態為 "failed"
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then latest build_id 為 "B1"
      And published partial child artifact 數量為 0

  Rule: Apply 成功後 capability candidate 必須出現在 derived overlay

    Example: 確認 reranker 為 non-baseline capability
      Given confirmed mapping 將 reranker 標記為 "non_baseline_capability_candidate"
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 新 build 的 profile overlay 包含 reranker capability candidate
      And 新 build 的 graph overlay 包含 reranker capability candidate

  Rule: UI 必須分開顯示尚未套用的 confirmed mappings

    Example: 三筆 confirmed mappings 尚未 Apply
      Given 使用者已確認 3 筆 mappings
      And 這 3 筆 mapping_ids 尚未出現在 latest build 的 applied_mapping_ids
      When 使用者檢視 Apply 操作區
      Then UI 顯示 "3 項確認尚未套用"
      And UI 主要操作文字為 "套用 3 項確認並建立新版本"
      And UI 顯示 "將沿用目前的掃描資料更新分析結果，不會重新掃描專案。"

  Rule: Apply 成功後必須以 response viewer_load_result 原子更新 Viewer

    Example: B1 Apply 成功建立 B2
      Given Viewer 目前顯示 build "B1"
      And Apply request 包含多筆 confirmed mapping_ids
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply" 且建立 build "B2"
      Then Viewer 顯示 Apply response 的 viewer_load_result
      And Viewer 顯示的 build_id 為 "B2"
      And 只有 response applied_mapping_ids 中的 mappings 被清除
      And Viewer 額外發出的 map 重新載入請求次數為 0

  Rule: Stale base Apply 失敗後必須保留 pending confirmations

    Example: Apply 回傳 base_build_not_latest
      Given Viewer 目前顯示 build "B1"
      And latest build_id 已變更為 "B2"
      And 使用者有尚未套用的 confirmed mappings
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply"
      Then 回傳 HTTP status 為 409
      And 回傳錯誤碼為 "base_build_not_latest"
      And Viewer 重新載入 project latest build "B2"
      And pending confirmed mapping_ids 與 Apply 前相同

  Rule: 其他 Apply 失敗不得清除目前 graph 或 pending confirmations

    Example: Apply build 發生安全錯誤
      Given Viewer 已顯示目前 latest graph
      And 使用者有尚未套用的 confirmed mappings
      When 使用者呼叫 "POST /api/map-builds/{base_build_id}/apply" 且 server 回傳 retryable 為 true
      Then Viewer 顯示的 graph 與 Apply 前相同
      And pending confirmed mapping_ids 與 Apply 前相同
      And Viewer 顯示 retryable error

  Rule: Apply retry UI 必須依 server 明示 retryable 欄位判定

    Example: Server 標記可重試錯誤
      Given 使用者有尚未套用的 confirmed mappings
      When Apply response 的 retryable 為 true
      Then Viewer 顯示 retry action
      And pending confirmed mapping_ids 與 Apply 前相同

    Example: Server 標記不可重試錯誤
      Given 使用者有尚未套用的 confirmed mappings
      When Apply response 的 retryable 為 false
      Then Viewer 不顯示 retry action
      And Viewer 顯示 server 提供的修正或重新載入指引
      And pending confirmed mapping_ids 與 Apply 前相同
