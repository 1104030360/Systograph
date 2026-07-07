Feature: 掃描專案
  使用者要求 scanner 以 deterministic facts first 的唯讀流程掃描已匯入的 AI system project。

  Rule: 無 boundary proposals 時掃描必須自動繼續

    Example: 無 boundary proposals
      Given boundary preflight 的 proposals 數量為 0
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then provider scan 執行次數為 1

  Rule: 有 boundary proposals 時必須一次提交全部 same-run decisions

    Example: 同一趟掃描尚有未提交的 boundary decision
      Given 同一個 scan_id 有多筆 boundary proposals
      When 使用者呼叫 "POST /api/scans" 且未提交全部 same-run decisions
      Then 操作失敗

  Rule: unresolved boundary decision 不得執行 provider scan

    Example: boundary decision 尚未完成
      Given boundary decision 狀態為 "unresolved"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then provider scan 執行次數為 0

  Rule: missing boundary decision 不得建立 snapshot 或 build

    Example: boundary decision 缺少
      Given boundary decision 狀態為 "missing"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then 回傳錯誤碼為 "requires_boundary_decision"
      And persisted snapshot 數量為 0
      And persisted build 數量為 0

  Rule: stale boundary decision 不得寫入 artifacts 或更新 latest viewer

    Example: boundary fingerprint 已過期
      Given boundary decision 狀態為 "stale"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then artifact mutation 數量為 0
      And latest viewer build_id 與掃描前相同

  Rule: boundary decision 只適用當次 scan

    Example: 使用前一次掃描的 boundary decision
      Given 一筆 boundary decision 屬於前一次 scan_id
      When 使用者以新的 scan_id 呼叫 "POST /api/scans"
      Then 操作失敗

  Rule: 掃描必須先產生 deterministic bounded facts 與 evidence

    Example: 完成 deterministic scan
      Given scanner 可讀取 AST、regex、config、dependency manifest 與 workflow JSON parser 的輸入
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then scan result 包含欄位
        | field    |
        | facts    |
        | evidence |

  Rule: evidence location 必須使用 project-relative representation

    Example: 掃描到檔案 evidence
      Given scanner 取得一筆檔案 evidence
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then evidence 的 file 不包含 unmanaged absolute path

  Rule: 原始碼不得整包交給 LLM

    Example: optional semantic assist 可用
      Given optional semantic assist 已啟用
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then semantic assist 的輸入類型為 "bounded masked fact packet"

  Rule: Optional LLM unavailable 不得阻塞 deterministic base scan

    Example: LLM provider 無法使用
      Given optional LLM provider 狀態為 "unavailable"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then deterministic scan 產生 bounded facts 與 evidence
      And proposal assist 回傳 bounded error

  Rule: 完成的 scan 必須建立一個 immutable snapshot

    Example: scan 完成並凍結 evidence
      Given provider collection 已完成
      When 使用者呼叫 "POST /api/scans" 且 provider collection 完成
      Then snapshot 的 scan_id 與本次 scan_id 相同
      And 本次 scan_id 的 snapshot 數量為 1

  Rule: parser 部分失敗必須保留 bounded warnings 且不得捏造 facts

    Example: 一個 parser 發生部分失敗
      Given 一個 parser 發生部分失敗
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then scan result 包含 bounded warnings
      And scan result 不包含捏造的 missing facts

  Rule: Canonical validation 失敗不得產生 downstream artifact 或切換 latest

    Example: ai_system_map validation 失敗
      Given canonical validation 狀態為 "failed"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then downstream artifact 數量為 0
      And latest build_id 與掃描前相同

  Rule: Derived artifact 失敗不得 publish core JSON set

    Example: profile_signals validation 失敗
      Given derived artifact validation 狀態為 "failed"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then published core JSON set 數量為 0
      And latest build_id 與掃描前相同

  Rule: 首次成功掃描必須 atomic publish 完整 immutable build

    Example: 首次掃描所有 core artifacts 驗證通過
      Given project 尚無 prior build
      And canonical 與 sibling core JSON validation 狀態為 "passed"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then build_reason 為 "initial_scan"
      And build 的 applied_mapping_ids 數量為 0
      And latest build_id 為新 build 的 build_id

  Rule: 同一 build 的 sibling artifacts 必須使用相同 scope identities

    Example: 初次掃描建立 sibling artifacts
      Given 初次掃描建立 build_id "B1"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then 每個 sibling artifact 的 build_id 為 "B1"
      And 每個 sibling artifact 的 snapshot_id 相同
      And 每個 sibling artifact 的 environment_id 相同

  Rule: Scanner 必須維持 target repo read-only

    Example: 掃描前後比較 target repo
      Given 目標專案的 Git working tree 狀態已被記錄
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then 目標專案的 Git working tree 狀態與掃描前相同

  Rule: Boundary proposal action 只能套用於本次 scan

    Example: 使用者提交全部 boundary decisions
      Given 本次 scan 的每筆 boundary proposal 都有相符的 target_path 與 fingerprint
      When 使用者提交每筆 action 為 "scan_this_run" 或 "skip_this_run"
      Then boundary completion 狀態為 "complete"

  Rule: Deterministic hard-skip targets 必須保留 audit trail

    Example: Scanner 遇到 large、binary、generated、cache 或 model-weight target
      Given target 符合 deterministic hard-skip 規則
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then boundary proposal 數量不因該 target 增加
      And Scan response 的 bounded skipped_items 包含該 target
      And skipped_items 使用 project-relative 或 redacted path representation
      And persisted skipped audit artifact 數量為 0

  Rule: requires_boundary_decision 必須表示等待 scope decision 而非 scan error

    Example: Boundary proposals 尚未全部確認
      Given 本次 scan 仍有未完成的 boundary proposals
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then 回傳狀態為 "requires_boundary_decision"
      And build_result 為空

  Rule: Explicit rescan 必須建立新的 scan、snapshot 與 initial build

    Example: B2 之後明確重新掃描 repo
      Given project latest build_id 為 "B2"
      And build "B2" 已關聯既有 scan_id 與 snapshot_id
      When 使用者呼叫 "POST /api/scans" 明確重新掃描 project
      Then 新 scan_id 不等於 build "B2" 的 scan_id
      And 新 snapshot_id 不等於 build "B2" 的 snapshot_id
      And 新 build 的 build_reason 為 "initial_scan"

    Example: Explicit rescan replay 仍可驗證的 confirmed mappings
      Given project latest build_id 為 "B2"
      And confirmed mapping "M1" 可由新 snapshot evidence 重新驗證
      And confirmed mapping "M2" 無法由新 snapshot evidence 重新驗證
      When 使用者呼叫 "POST /api/scans" 明確重新掃描 project
      Then 新 build 的 applied_mapping_ids 包含 "M1"
      And 新 build 的 applied_mapping_ids 不包含 "M2"
      And scan response 包含 stale mapping warning for "M2"
      And latest build_id 為新 build 的 build_id

  Rule: Standard mode 不得呼叫 LLM

    Example: 使用 Standard mode 掃描
      Given scan mode 為 "standard"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then LLM provider 呼叫次數為 0

  Rule: Deep mode semantic output 不得建立 canonical facts 或單獨提升 status

    Example: 使用 Deep mode 掃描
      Given scan mode 為 "deep"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then semantic assist 新增的 canonical component 數量為 0
      And semantic assist 新增的 canonical edge 數量為 0
      And semantic assist 新增的 canonical evidence 數量為 0
      And 僅由 semantic assist 提升的 assessment status 數量為 0

  Rule: 掃描不得啟動 target app、安裝 target dependencies 或發送外部 request

    Example: 掃描外部專案
      Given target project 尚未啟動且 dependencies 尚未安裝
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then target app 啟動次數為 0
      And target dependency 安裝次數為 0
      And 對外 request 次數為 0

  Rule: 掃描輸出不得包含完整 secret、raw source 或 unmanaged absolute path

    Example: Target project 包含 secret-like value 與本機絕對路徑
      Given scanner 取得包含敏感資料的 deterministic evidence
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then CLI output 不包含完整 secret value
      And logs 不包含完整 secret value
      And sibling artifacts 不包含完整 secret value
      And sibling artifacts 不包含 unmanaged absolute path

  Rule: 成功的新掃描必須輸出 active ai-system-map/v2

    Example: Phase2 active scan 完成
      Given canonical 與 sibling artifact validation 狀態為 "passed"
      When 使用者呼叫 "POST /api/scans" 掃描專案
      Then ai_system_map.json 的 schema_version 為 "ai-system-map/v2"
      And ai_system_map.json 的 system_type 為 "ai_system"
