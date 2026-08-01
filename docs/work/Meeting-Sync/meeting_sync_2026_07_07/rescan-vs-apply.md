# Rescan vs Apply（重新 Scan 與套用確認）

Last updated: 2026-07-07（UA 整合決策對齊）

## 目的

釐清 Phase2 兩種「再產生 build」的路徑：**Explicit Rescan** 與 **Apply confirmed mappings**。
兩者都會產生新的 artifact set，但輸入、是否重掃 repo / 重跑 UA sidecar、以及
`scan_id` / `build_id` 行為不同。

**Contract 依據：** Plan `03A`（Apply / build lineage）、Plan `01`（mapping decision）、
Plan `01B`（Step 4 component bridge）、`00-phase2-pipeline-ascii-map.md`、
`docs/MODEL-CONTRACT.md`、`docs/work/Timmy/design/EPIC1/frontend-json-handoff/`。

---

## 一句話

Step 3 採 staged rollout：Phase A 為 Systograph scan TOML providers primary，UA sidecar 可為 null；
Phase B 為 UA structural primary + TOML parity；Phase C 為 UA only。以下 UA 行為適用於
Phase B/C，Phase A 仍須允許 `ua_analysis_result=null` 完成 initial build 與 Apply。

| 操作 | 一句話 |
|------|--------|
| **Rescan** | 重新讀 repo；Phase A 重跑 TOML providers，Phase B/C 重跑 UA → 新 scan snapshot → 新 build |
| **Apply** | 沿用舊 scan snapshot（UA sidecar 可為 null）+ 新 mapping 決策 → 新 build（**不重掃 repo、不重跑 UA**） |

---

## 對照表

| | **Explicit Rescan** | **Apply** |
|---|---------------------|-----------|
| **典型觸發** | `POST /api/scans`（使用者按「重新掃描」） | `POST /api/map-builds/{base_build_id}/apply`（「套用 N 項確認並建立新版本」） |
| **是否重掃 filesystem / 重跑 UA sidecar** | **是**：重新建立 inventory；Phase A 跑 TOML providers，Phase B/C 呼叫 `UnderstandAnythingAnalysisService` 產生新 UA sidecar | **否**：重用既有 `ScanSnapshot`；sidecar 可為 null，不呼叫 UA |
| **`scan_id`** | **新的** | **與 base build 相同** |
| **`build_id`** | **新的**（如 B1→B3） | **新的**（如 B1→B2） |
| **Build 輸入** | 新產生的 `ScanSnapshot`（Phase A UA sidecar 可為 null；Phase B/C 含新 UA sidecar） | 既有 `scans/{scan_id}/snapshot.json`（UA sidecar 可為 null） |
| **Mapping 輸入** | `mappings/` 內所有 **confirmed** 決策（自動套用） | 本次請求指定的 **confirmed** `mapping_id` 列表 |
| **是否沿用 B1 的 `ai_system_map.json`** | **否** | **否** |
| **是否沿用 B1 的 profile / readiness / graph** | **否** | **否** |
| **Boundary gate** | 重新跑 preflight（fingerprint 變更要再確認） | 不重跑 scan boundary；decision 須對 snapshot 內 evidence 仍有效 |

---

## 共同點：都會走完整 materialization

兩者 **都不** 直接 patch 上一版 JSON。從 **Step 4 materialization** 起重新 materialize，
包含 4-1 component bridge、4-2 confirmed mapping replay、normalize/validate 與
Step 6–7 全部衍生／投影。

```text
                    Rescan                    Apply
                      │                         │
 filesystem inventory + staged scanner            │ 讀既有 snapshot
                      ▼                         ▼
              persist ScanSnapshot S*     load ScanSnapshot S1
                      │                         │
                      └──────────┬──────────────┘
                                 ▼
                    Step 4-1 component bridge
                                 ▼
                    Step 4-2 apply confirmed mappings
                                 ▼
                    endpoint / risk / edge / flow derivation
                                 ▼
                    normalize + validate          ← Step 4，兩者都會跑
                                 ▼
                    profile / readiness / static execution / graph
                                 ▼
                    寫入 output/{新 build_id}/ 全套 sibling artifacts
                                 ▼
                    immutable Build + 更新 latest viewer
```

**重點：** Apply 跳過的是 **Step 3 掃描 repo / 重跑 UA sidecar**，不是跳過 Step 4～7。
Mapping 在 Step 4 replay 生效，再進 normalize、Step 6 assessment 與 Step 7 projection。
Step 6 由 `ProfileInferenceService` 讀 validated map + TOML metadata，以純 Python 定案；
Plan 17 `AssessmentOrchestrator` / AI semantic candidate flow deferred。Snapshot internal UA
semantic sidecar 是 reserved nullable slot，Phase2 active path 不產生、不消費。

---

## 用什麼當 build 輸入（不是 handoff sample）

### Rescan 輸入

```text
project path（repo）
  → boundary complete
  → filesystem inventory
  → Phase A：Systograph scan TOML providers primary，ua_analysis_result=null 可接受
  → Phase B/C：UnderstandAnythingAnalysisService
       extract-import-map → compute-batches → extract-structure
       → file-analyzer / ua-analysis-result deferred（不執行）
  → 新 snapshot.json（raw ProjectScanResult + nullable internal ua-analysis_result）
  → mappings/ 內 confirmed 決策（若有）
```

### Apply 輸入

```text
scans/{scan_id}/snapshot.json     ← 唯一 raw scan truth（internal UA sidecar 可為 null）
  + mappings/{mapping_id}.json    ← 本次 apply 選中的 confirmed 決策
  + base_build_id（lineage）
```

### 兩者皆 **不是** build 輸入

- 上一版 `output/{build_id}/ai_system_map.json`
- `profile_signals.json`、`readiness_report.json`、`graph_view_model`
- `frontend-json-sample.json`（ViewerLoadResult，僅 viewer 顯示用）
- Step 9 mapping **proposal** response（須先寫成 confirmed mapping 才影響 build）

State 目錄 layout（Plan 03A target）：

```text
~/.systograph/projects/{project_id}/
├── scans/{scan_id}/snapshot.json
├── mappings/{mapping_id}.json
├── builds/{build_id}/manifest.json
└── latest.json
```

---

## Identity 與 lineage

```text
scan_id  = 一次 filesystem scan 的 immutable snapshot
build_id = 從某 snapshot materialize 出來的一組 artifacts

B1: scan_id=S1, build_id=B1, build_reason=initial_scan
B2: scan_id=S1, build_id=B2, based_on_build_id=B1, applied_mapping_ids=[…]
B3: scan_id=S2, build_id=B3, build_reason=explicit_rescan   ← repo 有變才會新 S2
```

- B1、B2 **共用** `scan_id`；artifact 目錄不同，B1 **不可** 被 Apply 覆寫。
- Rescan 若 repo 或 boundary 結果改變 → 新 `scan_id`；舊 snapshot 仍保留供追溯。

---

## Mapping 決策如何影響兩者

| Decision | Rescan | Apply |
|----------|--------|-------|
| `non_baseline_capability_candidate`（confirmed） | 新 scan 時 component detection 套用 | replay detection 套用 → 新 B2 profile / graph |
| `existing_slot_mapping`（confirmed） | 同上 | 同上 |
| `skip_for_now` / `rejected` | 不進 `applied_mapping_ids` | 不可被 apply 選入 |
| 僅 proposal、尚未 confirmed | 不影響 | 不影響；須先 POST decision |

Apply **不得** 僅更新被 mapping 直接碰到的 JSON 欄位；必須重算 readiness、static execution、Mapping Completeness 等，避免 B1 stale state 殘留。

---

## Frontend UX 暗示

| 情境 | 建議 UI / 文案方向 |
|------|-------------------|
| 使用者確認 reranker 為 capability candidate | **Apply** — 「套用 N 項確認並建立新版本」；說明 **不會** 重掃 repo，也不會重跑 UA sidecar |
| repo 程式碼已改、要反映最新檔案 | **Rescan** — 「重新掃描專案」 |
| 首次 scan 後 | 先顯示 B1 + optional review queue；**不** 要求 review 完才顯示 |
| Apply 完成 | 切換到 B2 的 `ViewerLoadResult` / latest；B1 仍可在 build history 查看 |

不要寫成「Apply = 重新 scan」；Apply 是 **同一證據快照下的新版本 build**，對 frontend
contract 透明。

---

## 與 ViewerLoadResult 的關係

- Rescan / Apply **產出** 新的 `outputs/{build_id}/` 與（可選）新的 `viewer_load_result`。
- Viewer **讀** latest build 的聚合 payload；**不** 把 ViewerLoadResult 當 build 輸入。

詳見 `docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-08-viewer/README.md`。

---

## 實作狀態（2026-07-05）

- **Target contract：** Plan `03A` — `build_from_snapshot()`、Apply 不重掃 / 不重跑 UA、B1→B2 lineage。
- **現況：** Manual mapping 已可 persistence；部分 flow 仍描述為「下次 **scan** 套用 confirmed mapping」。實作收斂後 Apply 應符合本文件，Rescan 仍走完整 scan + 新 snapshot。

驗收時需同時覆蓋：Phase A `ua_analysis_result=null` 的 B1 / Apply B2；以及 Phase B/C 的 B1
只呼叫一次 UA、Apply B2 不再呼叫 UA，component detection 為 B1 + B2 各一次。

---

## 相關文件

- `docs/work/Timmy/schedule/plan/unfinish/phase2/static-trace-plan/03A-implement-apply-build-lineage-and-local-json-persistence.md`
- `docs/work/Timmy/design/EPIC1/frontend-json-handoff/step-09-review-apply/README.md`
- `docs/work/Meeting-Sync/meeting_sync_2026_07_05/frontend-mapping-capability-candidates.md`
