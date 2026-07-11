# Step 9 — Review / Apply（可選）

Last updated: 2026-07-11（current durable decision / Apply contract）

ambiguous evidence 的 review 流程。**不阻塞**第一次 scan 顯示；decision 在 **下次 Apply / rescan** 套用。

詳細邊界見 `docs/design/epic1-phase2.md` §12。

## Proposal 與 Manual mapping（誰是選項、誰是結果）

| | **Proposal** | **Manual mapping** |
|---|--------------|-------------------|
| 是什麼 | Scanner 的 **建議包 + 選項**（待決工單） | 使用者選完後 **存檔的決策** |
| API | `POST /api/mapping-proposals` → response | `POST /api/mapping-proposals/{id}/decision` → 寫入 `mappings/` |
| 白話 | **問題 + candidates[]** | **你選了什麼**（`confirmed` 等） |

```text
Proposal → 使用者 decision → ManualMapping 存檔 → Apply 重算 → 新 build_id
```

Proposal **不能**直接改 profile status；Apply 才會把 confirmed mapping 反映進 B2 報告。
2026-07-07 UA 整合後，Step 9 MappingProposal 流程與 API 不變；Apply 不重跑 UA sidecar，
而是重放同一 `ScanSnapshot.scan_result` 的 structural facts/evidence，重跑 Step 4～7；
`ua-analysis-result` internal sidecar 保持不變且不被 Phase2 消費，
並產生新的 `build_id`。

---

## frontend-mapping-proposal-sample.json

`MappingProposal` — `POST /api/mapping-proposals` **response**。

| 欄位 | 白話 |
|------|------|
| `proposal_id` | 這次 review 提案 ID |
| `source_unmapped_id` | 來自 map 的哪個 unmapped |
| `status` | current pending enum：`pending_user_confirmation` |
| `evidence_packet` | 給使用者看的 evidence 摘要包 |
| `candidates[]` | **可選方案**（確認為 capability candidate、skip…） |
| `candidate_type` | 如 `non_baseline_capability_candidate`、`skip_for_now` |
| `available_actions` | UI 按鈕：`accept` / `edit` / `reject` / `skip_for_now` |

---

## frontend-manual-mapping-create-capability-candidate-sample.json

`ManualMappingCreate` — `POST /api/mapping-proposals/{id}/decision` **request body**（**決策內容**，不是 Proposal 本身）。

| 欄位 | 白話 |
|------|------|
| `mapping_type` | 決策類型（sample 為 `non_baseline_capability_candidate`） |
| `decision` | `confirmed` / `rejected` / … |
| `source_unmapped_id` | 對應哪個 unmapped |
| `capability_candidate_*` | 確認後的 candidate 命名 |
| `proposal_id` | 連回哪個 proposal |
| `decision_source` | 如 `proposal_accept` |

Apply 時 backend 重用同一 `ScanSnapshot` 建 **B2**，不重掃 repo、也不重跑 UA sidecar。見
`docs/work/Meeting-Sync/meeting_sync_2026_07_05/rescan-vs-apply.md`。

Reject / skip 也會建立 durable `ManualMapping` audit record；兩者不 materialize、不能放進
`applied_mapping_ids`。Apply 只接受 non-empty、unique、同 project 的 confirmed mappings，
且 base build 必須仍是 latest。
