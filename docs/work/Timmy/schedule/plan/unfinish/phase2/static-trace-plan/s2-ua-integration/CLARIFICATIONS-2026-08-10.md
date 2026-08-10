# S2 UA 整合 — 動工前釐清問題與裁定紀錄

> **來源：** 2026-08-10 五路查核（16A/16E/16G 精讀、Gate/排程一致性、boundary doc 權威比對、
> 16C/16D codebase 主張逐條驗證、九檔 fresh-eyes 掃描），關鍵結論已由主 agent 親驗。
> **用途：** 逐條向 plan owner 提問並記錄裁定；裁定後由對應計畫檔落實，本檔保留決策軌跡。
> **基準：** HEAD `52931d6`（#277）。s2 全部文件最後更新 2026-08-06，早於 #277 合併。

---

## 0. 查核已確立的事實（不需提問，提問以此為前提）

| # | 事實 | 證據 |
|---|------|------|
| F1 | **13.7 / 13.8 皆已完成**（`finish/s1-v2-cutover/` Status: done）；13.8 端點約束已在 `profile_finding_assembler.py:214-217`（含 `required_component_ids.isdisjoint` 檢查與註解），回歸測試 `test_profile_finding_endpoint_constraint.py` 存在 | 親驗 |
| F2 | **`system_map_materialization_service.py`（v1 寫入路徑）已在 #277 刪除**——16G §4「唯一動工前決策點」（v1 A/B 選項）、門檻 6、Task 3 Files 的該列全部指向已消失的檔案 | 親驗（git log 末筆＝52931d6） |
| F3 | **`RELATIONSHIPS` 有 4 個 16G 未列出的消費者**：`profile_relationship_alias_loader.py:18,82,112`、`profile_relationship_alias.toml:16`、`models/system_map.py:150,165`（註解）、`MODEL-CONTRACT.md:458` | 親驗 loader |
| F4 | `CanonicalEdge`＋v2 JSON schema **已經**支援 `status: observed/detected/undetermined` 與 `undetermined_reason`——16C Task 5 只需改 `system_map.py` 的 `Edge`（現無 status 欄），不動 schema | Agent D 驗證 |
| F5 | `ParseIssue.scan_stage` 是封閉 6 值 Literal；16E 已裁定 **AST provider 沿用 `code_pattern_scan`**，但 **UA sidecar adapter 的 stage 無任何文件覆蓋**——adapter 第一筆 ParseIssue 會 ValidationError | 親驗 model＋16E:151-153 |
| F6 | 上層 README 的 **Gate-2 定義少了 Task 8（CLI）**（2026-08-05 Q4 裁定已把 CLI 納入 Gate-2 關鍵路徑）；README 也完全未收錄 16F/16G，並仍稱 16 為「7 個 Task」 | Agent B |
| F7 | **CONTRACT-AUDIT Plan 01 未解項**（REJECT/SKIP 不建 ManualMapping，Task 8 未勾）位於 Gate-1 要求的 Step 9 decision 路徑上，是整條 S2 鏈的隱形傳遞前置；s2 沒有任何文件提到它 | Agent B |
| F8 | boundary doc 與計畫有一件實質衝突：**BD §3.1 明文要求 `systograph-analyze.mjs` wrapper，計畫已裁定不做**（Q1 2026-08-04），裁定從未回寫 BD；work-dir（BD「Systograph 自己的 work directory」vs 計畫「系統暫存」）與 G1/G3 Python 補充 provider（違 BD §9「import/call 結構＝UA」職責表）同樣需要 BD 修訂 | Agent C |
| F9 | `ref-opensource/CLAUDE.md` **完全未做 Systograph 更名**（14 行 18 處，含錯誤 schema id `kai-mind-ua-*`、斷鏈 `kai-mind-...boundary.md`、死路徑 `src/kai_mind/`）；BD 本身只剩 `:415/:425` 兩個 Mermaid 標籤未改；s2 README `:230/:258` 引用「最高權威」的檔名是斷鏈；Plan 18 有 3 處 `src/kai_mind/` | Agent C＋親驗 |
| F10 | 大量行號漂移（#277 後）：`scan_routes.py:294→210`、`normalize :153→:183`（5 份文件同一錯）、`materialization :87→:89 / :124→:126`、`connects_to :51→:87-90`、`code_pattern_provider :122→:128` 等；16E「12 個 extractor」實為 11（swift 無 functionStack） | Agents A/D/E |

---

## 1. 問題清單與裁定

> 狀態：`⏳ 待問`｜`❓ 已問待答`｜`✅ 已裁定`。裁定寫在各題「裁定」欄，含日期。

### P0 — 擋住「現在唯一可動工」的 16E G3+G1

**Q1. `ast_construction_provider.py`（G1+G3）的歸屬** — `✅ 已裁定`
README 稱它是唯一不等 Gate 可動工的項目，但它的「owner」16E 自我宣告非實作計畫：沒有 Task 清單、沒有 Files、沒有驗收條件；16C §8 還把它寫成「Plan 16 adapter 層，**或**獨立 AST 掃描」二選一未定。
建議預設：新開 `16H-ast-construction-provider.md` 實作計畫（規格全部從 16E §2.3/§4.3/§7 抽取）。
**裁定（2026-08-10）：新開 `16H-ast-construction-provider.md` 實作計畫**——規格自 16E §2.3/§4.3/§7 抽取為 Task＋Files＋驗收；16C §8 與 16E 補上 owner 指向 16H；不動 Gate 結構（16H 不等 Gate）。

**Q2. `Evidence.evidence_kind_hint` 硬化的歸屬與時序（併：G2 路線變更）** — `✅ 已裁定`
16C 稱它是 L1/L2 分級「正確性前提」但明言不屬本計畫；16E 給了完整 diff 但非實作計畫——雙方 disclaim，無人排程。
釐清過程確認：Phase 2 原三條路（G1/G3 目擊、G2 人工確認）都不產「推論行號」，hint 原屬保險。plan owner 進一步裁定**改變 G2 路線**，hint 因此變為必需。
**裁定（2026-08-10）：G2 改走確定性程式推論（取代 16E 決策 2 的「人工確認為主」）：**
1. G2 由確定性 AST 推論解（追進工廠函式，深度上限自 16E 建議 `MAX_FACTORY_HOPS=3` 起），**非 LLM**；範圍併入 **16H**（provider 範圍由 G1+G3 擴為 G1+G2+G3）——16E 決策 2 與決策 4 需書面取代性修訂。
2. **`evidence_kind_hint` 為必需前置**，作為 **16H Task 1**（加性欄位＋`canonical_evidence_service` 優先採 hint＋契約測試，含「推論不得宣告 direct」反向斷言）。
3. 誠實性三鎖：分支不塌縮（每分支各一筆 fact）；全部標推論（hint→indirect）；**節點最多 partial、邊為 `undetermined`＋專屬 `undetermined_reason`（如 `factory_inference`）**，不進 profile 接線證據（`profile_finding_assembler.py:214` 閘門不變）。
4. 明示後果（plan owner 已知悉）：推論邊不會讓 profile 卡前進——選項買到的是圖的完整性（虛線），卡片翻綠仍靠 L1 真呼叫點。
5. 人工確認通道**不刪**，降為可選旁路（殘量與推論否決時仍可用）；使用者不 review 也能得到完整（含推論標記）的圖。
6. 防假陽性測試列為 16H 驗收必備。

**Q3. UA adapter 的 `ParseIssue.scan_stage` 值** — `✅ 已裁定`
見 F5。16E 只裁定了 AST provider 那半邊；UA sidecar 的 warnings/filesSkipped/stderr → ParseIssue 需要一個合法 stage 值。
**裁定（2026-08-10）：Literal 加第 7 個值 `"ua_structural_scan"`**（Plan 16 Task 1 順帶，一行加性變更）；AST provider（16H）依 16E 既有裁定沿用 `code_pattern_scan`。

**Q4. `code_pattern_rules.toml` 的 `symbol` 欄位落點** — `✅ 已裁定`
16E（每列加可選 `symbol`）、16C §5（regex 目錄與 AST 符號目錄共用 source of truth）、16 Task 3（語彙目錄演進版）三份各描述一個版本，實際 TOML 今天零 `symbol` 鍵；「bridge 13 條零改動」的宣稱依賴 provider 沿用既有 rule_id/kind＋這張表不漂移。
**裁定（2026-08-10）：`symbol` 欄併入 16H PR 落地**（16H 開工即需要；避免臨時私有清單造成字彙漂移）；Plan 16 Task 3 屆時只在**同一張表**再加 `ua_*` 對照欄。
釐清紀錄：字彙表（TOML）只是「符號→(rule_id, kind) 身份證」的翻譯字典，供 regex／16H AST／UA adapter 三個生產者共用；「什麼變成 component」仍由 Step 4 bridge（typed Python 13 條）獨占決定——bridge 認得 `ua_*` 靠 Task 3 既定的鏡射項，非本題新增。

### P1 — 影響 Gate-1／Plan 16 開工前提

**Q5. 13.7/13.8 已完成——六處硬前置表改標「已滿足」？** — `✅ 已裁定`
見 F1。`16:38-43`、`16A §2.4＋:204-211`、`16C:18-24（:23 與自身 :184/:204 矛盾）`、`16D:103-107`、`16F:350-354`、s2 README:104 六處仍把它們列為擋路前置；讀者無法判斷 Gate-1 前真正剩什麼。
**裁定（2026-08-10）：直接修**——六處全改標「✅ 已滿足（2026-07-29 done；由回歸測試守護）」；16C:23 矛盾句修正；16A §2.4 標註「已落地、假陽性示範不可重現」。不動任何 code。

**Q6. 「G3 先於 adapter」的強度統一** — `✅ 已裁定`
三種說法：16:33「**應**先於」／s2 README:129「**建議**先於」／16E §8 只排順序（G3=step 1，先於「Plan 16 到 Gate-2」而非先於 adapter）。G3 先做會改變 parity 基線（外部 import 從 indirect 升 direct），落在基線之後會污染 diff——順序其實有實質後果。
**裁定（2026-08-10）：統一為硬前置**——「16H 的 G3 部分為 16 Task 3 硬前置」，三處（16:33／s2 README:129／16E §8）同步改寫，理由標明＝parity 基線一致性。Q1 裁定後 16H 立即開工、Plan 16 等 Gate-1，此硬前置實務上零成本。

**Q7. candidate observed_kind 字彙對位歸屬** — `✅ 已裁定`
`reranker_candidate`／`router_like_evidence` 不在 `capability_type_node_map.toml` 39 鍵內 → candidates 永遠無法把 reranker/router 抬到 partial（查表靜默作廢）。16 的移交補記說「UA 字彙工作需一併裁定」，但 Task 1–8 無人承接。
**裁定（2026-08-10）：對位，併入 16 Task 3**——`capability_type_node_map.toml` 加兩列（`reranker_candidate = ["reranker"]`、`router_like_evidence = ["router"]`），並加護欄測試「bridge 產出的 observed_kind 必須全部可查表（或列名豁免）」。效果：此類弱訊號可把該兩格抬到 partial（僅 partial，candidate 封頂不變）。

**Q8. 16G §4 因 #277 作廢的處置＋RELATIONSHIPS 消費者補列** — `✅ 已裁定`
見 F2/F3。§4 的 A/B 選項、門檻 6、Task 3 Files 該列建立在已被 #277 刪除的 v1 檔案上；RELATIONSHIPS 有 4 個未列消費者（含 13.8 alias 驗證器直接 import）。
**裁定（2026-08-10）：照修**——①§4 改寫為「v1 阻擋點已由 #277 解除」、A/B 選項刪除、門檻 6 降為確認性項目；②Task 3 Files 補列 `profile_relationship_alias_loader.py`／`profile_relationship_alias.toml:16` 註釋／`models/system_map.py` 註解／`MODEL-CONTRACT.md:458`，alias 驗證器的合法關係名來源改為 `edge_relationship_rules.toml`（16C Task 2 新表）；③16G:78／:272「屬 13.7」誤標一併修正（該項實為無人認領，見 Q15 追蹤）。

**Q9. CONTRACT-AUDIT Plan 01 缺口的處置** — `✅ 已裁定`
見 F7。REJECT/SKIP 不建 ManualMapping、Plan 01 Task 8 未勾，而 Gate-1 明文要驗 Step 9 decision＋Apply。
**裁定（2026-08-10）：不擋 Gate-1**——Gate-1 驗收範圍明文界定為「不含 reject/skip 持久化路徑」（該界定寫進上層 README 的 Gate-1 定義）；缺口本身留在 Plan 01 Task 8 待修，不列 S2 前置。已知風險（owner 知悉）：修復前，同一提案在後續 build 可能反覆冒出、拒絕決策無 audit trail。

**Q10. boundary doc 回寫修訂＋ref-opensource/CLAUDE.md 更名** — `✅ 已裁定並執行`
見 F8/F9。三項實質修訂該回寫 BD（no-wrapper 裁定、work-dir=系統暫存、G1/G3 Python 補充 provider 的 §9 職責例外＋RC:56 install-time patch 豁免條款）；RC 的 18 處更名與兩個 Mermaid 標籤屬衛生。
**裁定（2026-08-10）：整份重寫（比「附加修訂」更進一步）**——owner 指示「根據最新 repo 狀態重新撰寫、把舊資訊刪掉」。已執行：
- `systograph-understand-anything-integration-boundary.md` 全文重寫：§0 決策表擴為 13 項（含 no-wrapper／work-dir／patch 機制／Native／CLI／ua_* 命名／16H G1+G3／G2 確定性推論／evidence_kind_hint）；§3.1 wrapper 指令刪除改為 Python 直接 spawn＋六項膠水責任；§3.3 wrapper contract 補 stats 定型核心＋extra 逃生欄＋structured warnings；§4.1 補「UA 不得做成普通 provider」與 16H 並行；§4.2 補 rule_id 前綴欄、三條硬規則、`scan_stage="ua_structural_scan"`、禁輸出需契約測試；§5/§6 圖更新（KAI→Systograph、加 16H 節點）；§7 補 patch 定案與 pin 紀律；§8 加第 8 條 vendored-tree 豁免條款；§9 職責表補 16H 與工廠推論列；§10 同步。章節編號 §0–§10 保持穩定（16B/16E 的引用不斷鏈）。
- `ref-opensource/CLAUDE.md` 全文重寫：18 處 KAI-Mind→Systograph、schema id 修正（systograph-ua-*）、`src/kai_mind/`→`src/systograph/`、boundary doc 檔名修正、arch-graph 檔名修正（systograph_architecture/flow）、補 pin `73559a1`、補 install-time patch 豁免與「勿 stage gitlink」語意、`src/` 零引用聲明改為含 Plan 16 Task 4 落地後的前瞻敘述。

**Q11. Plan 16 補強三項** — `✅ 已裁定`
①BD §4.2 禁輸出（plane_id/reference node id/五態/confidence/runtime 結論）在 s2 無專屬契約測試；②BD §10「Rescan 重跑 UA」在 16 的 AC 無對應驗收；③README「7 個 Task」與 16F 全文漏 Task 8（CLI）。
**裁定（2026-08-10）：全做**——①禁輸出契約測試寫進 16 Task 5（逐條釘五項）；②16 驗收條件加一行「Rescan 重跑 sidecar＋16H、產新 snapshot」；③README／16F 的 Task 數與模組清單同步補 Task 8（併入衛生批執行）。

### P2 — 擋 16C/16D 設計定案

**Q12. 邊合併鍵：`(from,to)` vs `(from,to,relationship)`** — `✅ 已裁定`
16C 三處用元件對，16D Task 1 用三元組；三元組會允許同一對元件同時掛 observed＋undetermined 平行邊，正是 16C §4 明文禁止的。今天兩者恰好等價（relationship 由 (from_kind,to_kind) 查表唯一決定），但 TOML 一旦允許一組合多關係名就分岔。
**裁定（2026-08-10）：`(from,to)` 元件對為合併鍵**——一對元件最多一條邊、最高級勝出；16C Task 2 的 `edge_relationship_rules.toml` 加約束＋契約測試「同一 `(from_kind,to_kind)` 只准一個 `relationship`」（兩種寫法永久等價）；16D Task 1 的「同 `(from, to, relationship)`」措辭同步改為「同 `(from, to)`」。

**Q13. 敗者 evidence 合併政策** — `✅ 已裁定`
16C §4 表寫「取 L1，evidence 合併」，§3.3 偽碼卻是 L2 直接 skip（不合併）；L3 完全沒寫。L3 的 evidence 是「兩端元件證據聯集」——併進 observed 邊會重建 16A §5.2／16 Task 3 明文禁止的假接線證據。
**裁定（2026-08-10）：一律不合併**——勝出等級的邊只帶自己的 evidence_ids；被淘汰等級記入 warnings 計數（可觀測、不靜默）；16C §4 表的「evidence 合併」措辭修正為「不合併」，與 §3.3 偽碼對齊；L3 明文同規。效果：`observed ⇒ 全部證據皆為目擊」成為可直接斷言的契約測試。

**Q14. 16D §8 三項未決** — `✅ 已裁定（三項全）`
Q1 Plan 14 是否硬性要求 16D；Q2 CI fixture 是否預設 `off`；Q3 前端虛線 polish 是否另開。
**裁定（2026-08-10）：**
- ①**硬性**——Plan 14 final validation 必須等 16D 完成才能出報告（與先前「建議」語氣相反，屬正式改判）：16D §8 Q1、16D:118-119、上層 README:387 的「建議」措辭全部改為硬前置；Plan 14 的依賴區補列 16D。排程後果（owner 知悉）：S3（14→18→15）整條被 16D 拖住。
- ②**CI fixture 預設 `off`**（產品預設維持 on 不動）——UA/16H 退化當天現形、16G 六道門檻的 off/on 對照數據由 CI 常態產生；一次性成本＝既有斷言基線調整。**附嚴重警告（已寫入根 CLAUDE.md Engineering Principles）：off 模式暴露缺口時，禁止以「為了讓測試過」的 code 應對——不得寫 fixture 特化 hack、不得捏造 facts/evidence、不得在掃描器加只為過測試的路徑；唯二合法解＝真實能力改進或明文記錄的基線調整；違者 review P1。誠實的空圖勝過造假的滿圖。**
- ③**另開 frontend-only task**——已寫入 `docs/work/Meeting-Sync/meeting_sync_2026_08_10/frontend-edge-status-dashed-rendering.md`（觸發點＝16C Task 5 合併後；含 `types.ts:74` 舊註解修正項）。
- 釐清紀錄：owner 確認開關 off ≡ 16G 拆除後的邊行為（彩排→拆台）；開關與 CI 設定行於 16G Task 4 一併刪除（陪葬，明文）；「拔掉 rag template」全集 ⊃ 開關範圍（開關只管 C2 邊，C1/C4/C5/C7 另有排程）。

**Q15. L3 開關名稱凍結** — `✅ 已裁定`
三種拼法並存：16D:189「名稱待實作時定（例 `SYSTOGRAPH_TEMPLATE_FLOW_EDGES`）」、16D:269 `template_flow_edges`、16G:77 直接把 `SYSTOGRAPH_TEMPLATE_FLOW_EDGES` 寫進刪除清單（無 hedge）。
**裁定（2026-08-10，經驗證後由 owner 授權）：凍結為 `SYSTOGRAPH_TEMPLATE_FLOW_EDGES`**。
驗證紀錄：三種拼法屬實；`src/` 零出現（凍結零成本）；名稱符合既有 `SYSTOGRAPH_*` 慣例；失效路徑實在（16G 照名搜刪、完整性檢查不 grep 變數名，取錯名會漏刪）。落實：16D:189 拿掉「待實作時定」、16D:269 拼法修正、16G:222 拿掉「（或實作時定的名稱）」hedge；實作照 `canonical_output_configuration.py` 的 env 模式。

**Q16. 邊數上限 50/2000 定為規範值？** — `✅ 已裁定`
16C §4.1 是「建議」，Task 6 卻要「實作 §4.1 的兩層上限」，驗收表無上限列——不可測。
**裁定（2026-08-10）：定為規範常數**——單一元件對外 50／全圖 2000，超限保留序 L1＞L2＞L3；16C §4.1 拿掉「建議」字樣、§7 驗收表補一列「超限時 warnings 記錄丟棄數量與級別」（No silent caps）。日後調整需留文字紀錄。

**Q17. Plan 14／18 銜接三件** — `✅ 已裁定`
①「Tier A」術語衝突（14＝外部真實 repo；18＝「Tier A fixtures」）；三套語料（Tier A repos／Phase4 Plan 31 fixtures／rag_projects）被互換使用；②14 的 10+1 E2E gate 與「UA 呼叫次數=1」計數器無 s2 任務承接；③18 把 `ua_*`↔legacy 對照的產出者誤標為 Task 7（實為 Task 3），且 18 的報告格式（per-provider 五分類）14 的報告表格裝不下。
**裁定（2026-08-10）：照修**——①「Tier A」唯一定義寫死在 Plan 14（＝外部真實 repo），三套語料各自標明用途（退役門檻 vs 日常基線），Plan 18 過關條件改引用正確語料；②「掃描／UA／parity 各只跑 1 次」計數器歸 Plan 16 Task 7（parity harness），Plan 14 驗收引用之；③Plan 18 產出者標註改為 Task 3、退役報告格式與 Plan 14 報告格式對齊（14 的表格補 per-provider provenance／分類欄或 18 明定另檔）。16 Task 7 的 Files 補列 Plan 14／18 修訂。

### P3 — 純衛生（一次批修）

**Q18. 衛生批次授權** — `✅ 已授權（2026-08-10）`
內容：s2 README（KAI-Mind×6、斷鏈×2、行數表、2900/2100、7→8 Task）；上層 README（補 16F/16G/16H、六份→十份、Gate-1 範圍界定、Gate-2 定義補 Task 8、Gate-3 補 16D 硬性、s3-retirement 15 已搬走、`download.md` 索引）；行號 sweep（F10 全表，改用符號錨點敘述）；16B/16F「仍待裁定」→「已裁定」同步；16:291 Plan 14 路徑補 `s3-validation/`；Plan 18 `src/kai_mind/`×3；16E「12 個 extractor」→11；16C:500「16A §5.3」引用修正；16B §2.1 錨點 :294→:210；16 的「待裁定」標題改「已全數裁定」；＋Q1–Q17 全部裁定寫回對應計畫檔（含新建 16H）。
**裁定：授權執行，硬限制＝只改計畫/文件檔（.md），零程式碼、零 commit。** 執行方式：6 個 subagent 分檔平行修正（①16H 新建＋16E；②16＋16B；③16C＋16D；④16G＋16A＋16F；⑤s2 README＋上層 README；⑥Plan 14＋Plan 18），主 agent 總 review 後回報 diff 摘要。

---

## 2. 落實追蹤（2026-08-10 批次執行）

| # | 檔案 | 內容 | 狀態 |
|---|---|---|---|
| 1 | `16H-ast-construction-provider.md`（新建，470 行） | G1/G2/G3 實作計畫；Task 1=evidence_kind_hint；Task 2=symbol 欄；驗收 14 列＋紅線引用根 CLAUDE.md | ✅ |
| 2 | `16E` | 檔頭取代性修訂 blockquote、§7 決策 2/4 刪除線改判、12→11 extractor、§5.3 owner=16H、§8 依 16H Task 重排、§9 補 16H 列、行號校正 | ✅ |
| 3 | `16` | 硬前置改標已滿足、Q3（scan_stage）/Q6（G3 硬前置）/Q7（字彙對位入 Task 3）/Q11（禁輸出測試＋Rescan AC）/Q17（Task 7 Files 補 14/18＋計數器）寫回、Plan 14 路徑修正、「待裁定」→「已裁定」 | ✅ |
| 4 | `16B` | §2.1 錨點 :294→:210／:55→:57／:86→:88／:261-264→:186-188、§2.2 :155-161→:157-163、§5.2 補 ua_structural_scan 注記 | ✅ |
| 5 | `16C` | 硬前置 :23 矛盾句修正＋改標、Q12（合併鍵＋TOML 約束）/Q13（evidence 不合併＋驗收列）/Q16（上限規範化＋驗收列）寫回、§5/§8 owner=16H、G2 連動注記、行號全數校正、§5.3→§5 引用修正 | ✅ |
| 6 | `16D` | 硬前置改標、Task 1 合併鍵改 (from,to)、Q14①硬性/②CI off＋嚴重警告/③另開連結、Q15 開關名凍結、§8 全拍板 [x] | ✅ |
| 7 | `16G` | §4 整段改寫（#277 解除、A/B 刪除）、門檻 6 改確認性、Task 2 改 HEAD 再確認、Task 3 補 4 個 RELATIONSHIPS 消費者＋alias 改接新表、:78/:272 誤標修正、:222 hedge 移除、Task 4 補變數名 sweep、行號校正（MODEL-CONTRACT 錨點實測 :459） | ✅ |
| 8 | `16A` | §2.4 已解注記（示範不可重現）、§7.1 改標、:202 行號校正 | ✅ |
| 9 | `16F` | 主清單擴 N1–N6（補 Task 8 CLI＋16H）、§6 開工順序重繪、Q3~Q5 敘述修正、:68 錨點校正、§5 同步 | ✅ |
| 10 | s2 `README.md` | KAI-Mind×6 清零、斷鏈×2 修復、十份文件／行數實測、16H＋CLARIFICATIONS 收錄、§4 依賴圖加 16H 框、§6.2 裁定摘要節、「唯一可動工」改 16H | ✅ |
| 11 | 上層 `README.md` | S2 表補 16F/16G/16H、執行順序補 16H/16G、Gate-1 範圍界定（Q9）、Gate-2 補 Task 8、Gate-3 補 16D 硬性、s3-retirement 地圖修正、download.md 收錄 | ✅ |
| 12 | Plan 14 | 16D 硬前置（雙處）、Tier A 唯一定義＋三套語料用途表、計數器歸 16 Task 7、報告格式補 per-provider 分類表、AC 補兩條 | ✅ |
| 13 | Plan 18 | kai_mind×3→systograph、產出者=Task 3、Tier A 用語修正、G1 parity 退役準則、報告格式改「14 產出、18 凍結消費」、KAI_MIND_* env 名修正 | ✅ |
| — | （先前已完成） | boundary doc 全文重寫、ref-opensource/CLAUDE.md 全文重寫、根 CLAUDE.md 加 anti-test-gaming 原則、Meeting-Sync 前端計畫 | ✅ |
| — | 主 agent 收尾（2026-08-10） | s2 README:228 錨點 :153→:183；「Phase4 31 fixtures」→「Phase4 Plan 31 fixtures」（16:342／18:319／本檔）；16E §9 補 16H 列；全 tree 殘留掃描（舊名／舊錨點／小寫開關名＝0，僅本檔歷史引述合法保留）；git status 確認本批只動 .md（工作區其餘 src/tests/scripts 變更屬 owner 另一 session 的 download.md 批次，未觸碰） | ✅ |

**批次完成（2026-08-10）。** 18 題全數裁定、13+4 份文件落實、零程式碼變更——已於 PR #280 提交。

---

## 3. PR #280 review 回應（2026-08-10 追加）

**R1. 16H Task 1 會造成循環相依（Codex review，屬實）** — `✅ 已修`
原 Task 1 只列「`system_map.py` 加欄位」，但欄位型別 `AssessmentEvidenceKind` 住在
`ai_system_map_v2.py:57`，而該模組已在 `:31` import `system_map.Evidence`——反向 import
即循環相依，**兩個 model 模組都載不進來、掃描器起不來**。計畫本身的步驟缺漏，非程式碼問題。
**處置（owner 核可）：** Task 1 拆為三步——①`AssessmentEvidenceKind` 移入新中立 module
`core/models/evidence_kind.py`（不 import 任何 systograph model）→ ②`ai_system_map_v2.py`
改 re-export（既有兩個消費者零改動）→ ③`Evidence` 加欄位。另加「中立 module 不得有
model 相依」的迴圈防護測試。判例＝07-28 `RecommendedNextCheck` 同型死結的既有解法。

**釐清紀錄（owner 提問串，供 Plan 15 動工時參考）：**
- **兩個 model 檔不是「新舊版本」，是流水線兩階段**：`Evidence`（掃描時的事實，21 個
  active 檔在用）→ `canonical_evidence_from_scan()` → `CanonicalEvidence`（發布時的契約）。
  轉換過程會**加上掃描器無從得知的資訊**：`evidence_kind` 判定、`no_snippets` build 選項、
  `json_pointer`/`config_key` 拆解——故不可由 provider 直接產出 v2 型別。
- **不可全併入 `ai_system_map_v2.py`**：①分層倒轉（Step 3 掃描器將相依輸出契約模組）
  ②快照被綁上輸出版本（Apply 重放的基礎）③出 v3 時三條路都不好走。若確定 v2 為終局契約
  而選擇合併，**檔名必須改為版本中立**，否則重演今天「`Evidence` 住在 v1 檔」的誤導。
- **Plan 15 待搬清單的判準（owner 提出，本次實證）：** 問「拿掉 rag-core-v1 之後它還在嗎？」
  - 還在 → 中立，搬家：`Evidence`／`Endpoint`／`RiskHint`／`DetailScanResult`／
    `QueryTraceEvent`／`CodePathStep`／`UnmappedComponent`
    （實證：三個 provider 與 `ProjectScanService` 提及 template 次數皆為 0）
  - 不在 → 模板鷹架，隨 16G／C1 死，**不該進待搬清單**：`ComponentSlot`／`Flow`／`Edge`
    （實證：`ai_system_map_v2.py` 查無 `components_by_slot`／`flows` 欄位，v2 輸出早已
    攤平成 `components[]`／`edges[]`；此三者只是 Step 4 內部鷹架）
  → Plan 15 現行清單把 `Flow`／`Edge` 列為待搬中立 symbol，動工重新推導時應套用此判準。

---

## 2. 裁定後的落實追蹤

（裁定齊備後，在此列出各計畫檔的修改清單與完成勾稽。）
