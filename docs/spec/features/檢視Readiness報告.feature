Feature: 檢視 Readiness 報告
  使用者檢視同一 build 的 evidence-backed readiness summary、release verdict 與交付前 findings。

  Rule: Readiness report 必須提供 summary、release verdict 與 findings

    Example: 檢視 B1 readiness report
      Given build "B1" 已產生 readiness_report.json
      When 使用者檢視 build "B1" 的 Readiness 報告
      Then UI 顯示 readiness summary
      And UI 顯示 backend 提供的 release verdict
      And UI 顯示 findings 清單

  Rule: Readiness findings 必須使用固定版本化 category 與 severity registry

    Example: Finding 使用 registry v1 欄位
      Given build "B1" 已產生 readiness_report.json
      When 使用者檢視 build "B1" 的 Readiness 報告
      Then readiness_report.json 的 finding_registry_version 為 "readiness-finding-registry/v1"
      And 每個 readiness finding 包含欄位
        | field    |
        | category |
        | severity |
      And 每個 readiness finding 的 category 來自 readiness-finding-registry/v1
      And 每個 readiness finding 的 severity 來自 readiness-finding-registry/v1

  Rule: Release verdict 必須由 backend 固定 policy 從同 build findings 推導

    Example: Backend 提供固定值域的 release verdict
      Given readiness_report.json 已依 backend 固定 readiness policy 評估同 build findings
      When 使用者檢視 Readiness 報告
      Then readiness_report.json 的 release_verdict 包含於
        | value        |
        | ready        |
        | needs_review |
        | blocked      |
      And UI 顯示 backend 提供的 release_verdict

  Rule: 每個 finding 必須可追溯到 evidence 或明確 reason

    Example: Finding 有直接 evidence
      Given readiness finding 包含 evidence_ids
      When 使用者檢視該 finding
      Then UI 顯示對應 evidence refs

    Example: Finding status 為 undetermined
      Given readiness finding 的 status 為 "undetermined"
      And readiness finding 包含 reason
      When 使用者檢視該 finding
      Then UI 顯示 reason

  Rule: Readiness report 必須顯示 recommended next checks 與 limitations

    Example: Finding 包含下一步與限制
      Given readiness finding 包含 recommended_next_checks 與 limitations
      When 使用者檢視該 finding
      Then UI 顯示 recommended_next_checks
      And UI 顯示 limitations

  Rule: 缺少 citation 或 source mapping 必須呈現 source_traceability finding

    Example: 系統沒有 citation 或 source mapping evidence
      Given source traceability evidence 未被偵測到
      When 使用者檢視 Readiness 報告
      Then findings 包含 category "source_traceability"

  Rule: Readiness report 不得只提供單一不透明總分

    Example: 檢視 readiness summary
      Given readiness_report.json 已產生
      When 使用者檢視 Readiness 報告
      Then readiness_report.json 包含欄位
        | field                    |
        | summary                  |
        | release_verdict          |
        | finding_registry_version |
        | findings                 |
      And UI 顯示的不透明單一總分數量為 0

  Rule: Network exposure finding 必須表達 static uncertainty

    Example: Static config 顯示可能存在 network exposure
      Given readiness finding 的 category 為 "network_exposure"
      And finding 只由 static config evidence 支持
      When 使用者檢視該 finding
      Then UI 顯示 uncertainty
      And UI 顯示的 runtime reachable verdict 數量為 0
