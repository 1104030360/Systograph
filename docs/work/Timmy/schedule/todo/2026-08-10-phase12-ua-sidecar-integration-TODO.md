# 2026-08-10 Phase 12 UA Sidecar 整合 — TODO

對應驅動：`docs/work/Timmy/schedule/dev-prompt/phase2/phase12.md`（本機忽略檔）

## 目標一句話

以確定性、read-only、fail-closed 的兩階段分析接入 Understand-Anything（UA），
先完成 16H 的 Python AST 補充事實，再通過 Gate-1、接入 sidecar、推導可追溯的
元件與邊，最後在實證門檻通過後退役模板猜測邊；全程不讓 LLM 進入掃描路徑。

## 實作邏輯

1. **計畫先於程式碼**：先以 HEAD `da0d402`、UA pin `73559a1` 與 live codepath
   逐份校正 16、16A～16H；不存在的 `16G-new-module-implementation-flow.md`
   正規化為 canonical `16G-retire-template-flow-derivation.md`，不建立相容空殼。
2. **誠實 gate**：Gate-1 沒有完整 Viewer／E2E／手動證據前，Plan 16 維持 blocked；
   targeted green 不視為 Gate-1 完成。16H 是唯一可先動工項目。
3. **TDD + BDD**：每一個可觀察行為先寫 Given／When／Then 失敗測試，保留
   RED 命令與原因，再寫最小實作到 GREEN；單元、整合與真實 CLI/API 各有證據。
4. **證據不膨脹**：import-only 與工廠推論不得因有行號而升成 direct；只有實際
   call/constructor 目擊可產生 observed 邊。空專案可以誠實產生零條 repo 邊。
5. **單一邊真相**：canonical edges 是 materialization、static execution、profile
   與 viewer projection 的共同來源；狀態與 undetermined reason 不得在投影時遺失。
6. **退役是最後一步**：只有 16G 六道可重現 gate 全過才刪
   `FlowDerivationService` 與過渡開關；否則保留並記錄哪一道 gate 未通過。

## 階段與步驟

### 階段 1：計畫與契約稽核（plan-audit）

- [x] 逐一更新 16、16A、16B、16C、16D、16E、16F、canonical 16G、16H。
- [x] 修正 G3 import-only 假陽性、typed UA fact payload、relationship discriminant、
  viewer edge status、合法零邊 fixture 與 Gate-1 證據邊界。
- [x] 記錄 UA submodule pin、Node/runtime 與三支 script I/O 的 live 驗證結果。
- [x] 產出 `2026-08-10-phase12-plan-audit-REP.md`。

### 階段 2：16H AST 補充 provider（ast-provider）

- [x] Task 1：先加 `evidence_kind_hint` 中立型別與 contract test。
- [x] Task 2：凍結逐規則 symbol catalog，不為湊數強迫 13 條都有 symbol。
- [x] Task 3：G1 import-time constructor 目擊。
- [x] Task 4：G3 import-only 事實，禁止單靠 import 點亮 component。
- [x] Task 5：G2 深度上限 3 的 factory inference，保留 branch 與 provenance。
- [x] 將 provider 接入 deterministic scan 並驗證 snapshot/Apply replay。
- [x] 產出 `2026-08-10-phase12-ast-provider-REP.md`。

### 階段 3：Gate-1 closure（gate1）

- [x] 依 static-trace README 的 Gate-1 acceptance matrix 執行 Step 1～7、viewer、
  inventory path 與 Apply B1/B2；不把 reject/skip persistence 缺口偷算完成。
- [x] 保存 CLI/API、schema、fixture、Viewer/manual QA 的可重現證據。
- [x] Gate-1 全過後才把 Plan 16 由 blocked 改為 in progress。
- [x] 產出 `2026-08-10-phase12-gate1-REP.md`。

### 階段 4：UA sidecar 與 adapter（ua-sidecar）

- [x] FileInventory enrichment、typed request/result schema、Node preflight。
- [x] Python 直接 spawn 三支 UA script，暫存工作目錄、timeout、path allowlist、
  stdout/stderr 分離與 fail-closed result validation。
- [x] install-time patch/setup script，驗證 pin 且不 stage submodule gitlink。
- [x] typed UA structural payload → ScanFact/Evidence/ParseIssue adapter。
- [x] parity service、單次呼叫計數器、non-interactive CLI gate、Rescan/Apply lineage。
- [x] 產出 `2026-08-10-phase12-ua-sidecar-REP.md`。

### 階段 5：元件歸屬、邊與 consumer cutover（edge-cutover）

- [x] ComponentResidenceIndex 與 typed call/import/symbol payload。
- [x] deterministic relationship rule/discriminant、stable edge id、merge/cap tie-break。
- [x] L1 observed、L2/G2 undetermined，敗者 evidence 不混入勝者。
- [x] materialization/static execution/profile/viewer 共用 canonical edges。
- [x] backend GraphViewModel 投影 `status`／`undetermined_reason`；frontend diff 維持空。
- [x] `SYSTOGRAPH_TEMPLATE_FLOW_EDGES=off` fixture 彩排與真實 Viewer smoke。
- [x] 產出 `2026-08-10-phase12-edge-cutover-REP.md`。

### 階段 6：安全退役與文件收尾（retirement-wrapup）

- [x] 執行 16G 六道門檻；門檻 1、2 FAIL，依規則維持 NO-GO，未刪除模板邊
  service、關係常數、過渡開關或舊測試。
- [x] 同步 scripts、API／MODEL contracts、plan checkbox/status。
- [x] 更新 `docs/work/Timmy/learn/architecture.md` 的完整 ASCII 全景圖。
- [x] 執行 Python/Frontend 全量 lint、type、test、build 與真實 CLI/API/browser QA。
- [x] 由既有獨立 agent 對 baseline SHA 加 current unstaged diff 做 evidence-backed
  review（本階段依發布邊界不建立新 commit）；最終 verdict：
  `APPROVED — no P0/P1/P2 findings`。
- [x] 產出 `2026-08-10-phase12-final-acceptance-REP.md`。

## 驗收矩陣

| Gate | 必須看到的結果 | 狀態 |
|---|---|---|
| Plan-first | 九份 canonical 計畫均反映 live code 與阻擋條件 | ✅ |
| TDD | 每個新行為都有先紅後綠的命令、原因與結果 | ✅ |
| Read-only | 掃描前後 target repo digest／檔案集合一致 | ✅ |
| Secret-safe | stdout、stderr、report、snapshot 不含完整 secret | ✅ |
| Deterministic | 同輸入重跑產物 byte-stable，排序與 ID 穩定 | ✅ |
| Honest evidence | import-only/factory inference 不成為 direct observed | ✅ |
| Sidecar | 真實 Node sidecar、schema、timeout/path boundary 通過 | ✅ |
| Consumer | canonical/static/profile/viewer 邊集合與 status 一致 | ✅ |
| Retirement | 16G 證據完整；門檻 1、2 FAIL，結論為 NO-GO、保留 L3 | ⚠️ NO-GO |
| Regression | Python 與 frontend 全量 gates 綠，manual QA 通過 | ✅ |

## 執行約束

- 不 push。
- 不修改 frontend production code；若 live browser 驗證發現獨立前端 defect，記錄並
  留給既有 frontend-only 計畫，除非它直接阻擋 Phase 12 的 backend contract。
- 不為測試捏造 fact/evidence，不加入 fixture 特化分支。
- 不把 ignored 的 phase prompt 或 `CLAUDE.md` 納入產品 commit；tracked `AGENTS.md`
  已提供本階段所需長期規則。
