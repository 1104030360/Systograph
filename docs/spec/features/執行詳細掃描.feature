Feature: 執行詳細掃描
  使用者針對既有 build 執行 Detail Scan，產生新的 immutable child build，而不覆寫來源 build。

  Rule: Active Phase2 Detail Scan request 必須綁定 build_id

    Example: 對 B2 執行 Detail Scan
      Given build "B2" 已 publish
      When 使用者針對 build "B2" 執行 Detail Scan
      Then Detail Scan request 的 build_id 為 "B2"

  Rule: Detail Scan 必須建立 immutable child build

    Example: B2 Detail Scan 建立 B3
      Given build "B2" 已 publish
      When 使用者針對 build "B2" 執行 Detail Scan
      Then 新 build 的 based_on_build_id 為 "B2"
      And 新 build 的 build_reason 為 "detail_scan"
      And build "B2" 的 artifacts 與 Detail Scan 前相同

  Rule: Detail Scan atomic publish 成功後必須切換 latest 與 Viewer

    Example: B2 Detail Scan 成功後顯示 B3
      Given build "B2" 為 project latest build
      When 使用者針對 build "B2" 執行 Detail Scan 且 child build "B3" atomic publish 成功
      Then project latest_build_id 為 "B3"
      And Viewer 顯示 Detail Scan response 的 viewer_load_result
      And Viewer 顯示的 build_id 為 "B3"

  Rule: Target file fingerprint 改變時必須要求 explicit rescan

    Example: B2 snapshot 後 target file 已變更
      Given target file fingerprint 與 build "B2" 的 source snapshot 不相符
      When 使用者針對 build "B2" 執行 Detail Scan
      Then 回傳 HTTP status 為 409
      And 回傳錯誤碼為 "scan_snapshot_stale"
      And persisted child build 數量為 0
