Feature: 重新載入專案狀態
  使用者在 backend restart 後重新開啟既有 project，繼續檢視與操作先前保存的 Phase2 state。

  Rule: Backend restart 後必須恢復 project、mapping、build history 與 latest pointer

    Example: B1 Apply 成功建立 B2 後重新啟動 backend
      Given project 已保存 confirmed mappings、scan snapshot、build "B1" 與 build "B2"
      And project 的 latest_build_id 為 "B2"
      When backend restart 後使用者呼叫 "GET /api/projects/{project_id}/map-builds/latest"
      Then 回傳的 build_id 為 "B2"
      And build "B1" 仍可讀取
      And confirmed mappings 仍可讀取

  Rule: Restart recovery 不得產生新的 project identity

    Example: 重新開啟已登錄專案
      Given project state 已寫入 local JSON store
      When backend restart 後使用者重新載入該 project
      Then project_id 與 restart 前相同

  Rule: Corrupted local JSON state 只阻擋受損 project 並 fail closed

    Example: Project state JSON 損壞
      Given project "P1" 的 persisted local JSON 無法通過驗證
      And project "P2" 的 persisted local JSON 驗證通過
      When backend restart 後使用者重新載入 project "P1"
      Then project "P1" 操作失敗
      And project "P1" 的 latest_build_id 不被覆寫
      And project "P2" 仍可重新載入
