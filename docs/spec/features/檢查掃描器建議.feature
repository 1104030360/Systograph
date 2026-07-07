Feature: 檢查掃描器建議
  使用者在第一次報告已可檢視後，針對重要且模糊的 unmapped item 檢查 scanner 建議並保存決策。

  Rule: Proposal review 不得阻塞第一次掃描結果

    Example: Build 含有 needs_review item
      Given build "B1" 含有 status 為 "needs_review" 的 unmapped item
      When 使用者檢視 build "B1"
      Then viewer payload 包含 map
      And viewer payload 包含 readiness report
      And viewer payload 包含 graph

  Rule: Proposal 只能由 Step 9 Viewer/API 觸發

    Example: 對 unmapped item 建立建議包
      Given build "B1" 有 unmapped_id "unmapped-1"
      When 使用者呼叫 "POST /api/mapping-proposals"
      Then proposal 的 source_build_id 為 "B1"
      And proposal 的 unmapped_id 為 "unmapped-1"

  Rule: Proposal 必須提供問題證據與可選動作

    Example: 建立 reranker review proposal
      Given reranker evidence 的 assessment 為 "undetermined"
      When 使用者呼叫 "POST /api/mapping-proposals"
      Then proposal 包含欄位
        | field             |
        | evidence_summary  |
        | candidates        |
        | available_actions |

  Rule: Proposal evidence packet 必須 bounded 且 masked

    Example: Evidence 含有 secret-like value
      Given unmapped item 的 evidence 含有 secret-like value
      When 使用者呼叫 "POST /api/mapping-proposals"
      Then proposal 的 evidence_summary 不包含完整 secret value

  Rule: Proposal 不得直接決定 profile assessment status

    Example: Proposal candidate 為 non-baseline capability
      Given proposal 包含 candidate "non_baseline_capability_candidate"
      When 使用者檢視 proposal
      Then profile assessment status 與 proposal 建立前相同

  Rule: accept 或 edit decision 必須保存 ManualMapping

    Example: 使用者接受 proposal candidate
      Given proposal_id "proposal-1" 的 status 為 "needs_review"
      When 使用者呼叫 "POST /api/mapping-proposals/{id}/decision" 並選擇 "accept"
      Then proposal status 為 "accepted"
      And persisted ManualMapping 數量增加 1

  Rule: reject 或 skip 必須保存 ManualMapping 決策結果

    Example: 使用者略過 proposal
      Given proposal_id "proposal-1" 的 status 為 "needs_review"
      When 使用者呼叫 "POST /api/mapping-proposals/{id}/decision" 並選擇 "skip"
      Then proposal status 為 "skipped"
      And persisted ManualMapping 的 decision 為 "skipped"

    Example: 使用者拒絕 proposal
      Given proposal_id "proposal-1" 的 status 為 "needs_review"
      When 使用者呼叫 "POST /api/mapping-proposals/{id}/decision" 並選擇 "reject"
      Then proposal status 為 "rejected"
      And persisted ManualMapping 的 decision 為 "rejected"

  Rule: Client 只可提交可編輯的 decision 內容

    Example: 使用者確認 candidate
      Given proposal_id "proposal-1" 屬於 build "B1"
      When 使用者呼叫 "POST /api/mapping-proposals/{id}/decision"
      Then project_id 由 server 填入
      And source_build_id 由 server 填入
      And source_evidence_ids 由 server 填入
      And digest 由 server 填入
      And audit time 由 server 填入

  Rule: Proposal decision 不得跨 build 使用 evidence

    Example: B1 proposal 使用 B2 evidence
      Given proposal_id "proposal-1" 的 source_build_id 為 "B1"
      And decision 引用 build "B2" 的 evidence_id
      When 使用者呼叫 "POST /api/mapping-proposals/{id}/decision"
      Then 操作失敗

  Rule: 保存 review decision 不得直接修改 canonical map

    Example: 使用者確認 ManualMapping
      Given build "B1" 的 ai_system_map.json 已 publish
      When 使用者呼叫 "POST /api/mapping-proposals/{id}/decision" 並選擇 "accept"
      Then build "B1" 的 ai_system_map.json 與 decision 前相同
