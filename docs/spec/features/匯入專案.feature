Feature: 匯入專案
  使用者在掃描前匯入既有 AI system repo 或 workflow artifacts，建立穩定的本機 project identity。

  Rule: 匯入專案後必須建立 stable project_id

    Example: 匯入本機專案
      Given 使用者有一個既有 AI system project
      When 使用者呼叫 "POST /api/projects/import" 匯入專案
      Then 回傳資料包含欄位
        | field      |
        | project_id |

  Rule: 匯入不得修改目標專案

    Example: 匯入唯讀專案
      Given 目標專案的 Git working tree 狀態已被記錄
      When 使用者呼叫 "POST /api/projects/import" 匯入專案
      Then 目標專案的 Git working tree 狀態與匯入前相同

  Rule: 重新匯入相同 resolved path 必須重用 project identity

    Example: 匯入既有專案路徑
      Given 一個 resolved path 已登錄為 project_id "project:existing"
      When 使用者呼叫 "POST /api/projects/import" 匯入相同 resolved path
      Then 回傳的 project_id 為 "project:existing"
      And 回傳的 reused 為 true

  Rule: 相同 project name 的不同路徑不得自動合併

    Example: 匯入同名但路徑不同的專案
      Given 一個 project name 已由其他 resolved path 使用
      When 使用者呼叫 "POST /api/projects/import" 匯入新的 resolved path
      Then 回傳的 project_id 不等於既有 project_id
      And 回傳的 reused 為 false
