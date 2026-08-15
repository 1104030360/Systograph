# 2026-08-10 Phase 12 UA Sidecar 最終驗收 — REP

- 驅動：`docs/work/Timmy/schedule/dev-prompt/phase2/phase12.md`
- Baseline：`da0d402e931a4b286022f6581f41e78342214351`
- Branch：`codex/phase12-ua-sidecar`
- UA pin：`73559a160645359c57be44c174935899dec9f9f2`
- 最終判定：**Phase 12 GO；16G 模板邊退役 NO-GO**

## 實作邏輯

Phase 12 維持 Two-Phase Analysis：Systograph 先以 inventory、Python AST 與 pinned
Understand-Anything scripts 產生 deterministic structural facts，再由既有 Step 4～7
進行 component、evidence、profile、risk 與 Viewer materialization。LLM semantic
analysis 仍是 nullable/deferred，不參與 release-readiness 判定。

核心邊界如下：

```text
CLI non-interactive gate ─┐
                          ├─> approved FileInventory ─> ScanSnapshot
Web preflight + review ───┘                              │
                                                        v
        Python AST G1/G2/G3 + UA sidecar structural result
                              │
                              v
             typed ScanFact / Evidence / ParseIssue
                              │
                              v
                 component residence + edge derivation
                    L1 observed > L2 undetermined
                              > L3 template undetermined
                              │
                              v
        one canonical edge set ─> static artifacts / profile / Viewer
```

L3 只在 `SYSTOGRAPH_TEMPLATE_FLOW_EDGES=on` 時作過渡備援；16G 六道門檻未全過，
所以沒有刪除 `FlowDerivationService`、`template_adjacency_only` 或 feature flag。

## 實作步驟與結果

1. 先以 live code、baseline tests 與 UA pin 稽核九份計畫。prompt 指向的
   `16G-new-module-implementation-flow.md` 不存在，依 canonical source of truth
   校正為 `16G-retire-template-flow-derivation.md`，沒有建立相容空殼。
2. 以 TDD 完成 16H：中立 `evidence_kind_hint`、G1 constructor、G2 bounded factory、
   G3 import-only 與 frozen typed payload；接入 deterministic scan、snapshot 與 Apply。
3. 完成 FileInventory enrichment、request/result schema、Node preflight、三階段 script
   編排、timeout/path allowlist、secret masking、暫存 work-dir cleanup 與 fail-closed
   validator。production path 不呼叫會自行 walk repo 的 `scan-project.mjs`。
4. 完成 CLI/Web 共用 Step 2→3 管線、non-interactive boundary gate、snapshot lineage、
   parity report 與一次性 invocation counters。
5. 完成 `ComponentResidenceIndex`、relationship TOML、L1/L2 derivation、穩定 edge id、
   cap/tie-break 與 L1>L2>L3 merge；敗者 evidence 不混入勝者。
6. canonical、GraphViewModel 與四個 static artifacts 保留 `status` /
   `undetermined_reason`；`execution-paths/v2` 直接存完整 canonical edge record，profile
   只接受 direct `observed` 關係證據。
7. 執行 12-fixture 16G on/off 量測與 live Viewer gate；門檻 1、2 FAIL，因此停在
   NO-GO，保留過渡期程式碼與測試。
8. 同步 MODEL contract、Phase 4 pipeline、Plan 14/18、TODO/Reports 與完整 ASCII
   architecture。`docs/work/Timmy/learn/architecture.md` 依現行 `.gitignore` 屬本機文件，
   已更新但不會出現在一般 `git status`。

## TDD / BDD 證據

- Gate-1 真實 CLI 先暴露四個 static JSON 缺少 `trace_kind=static_inferred` /
  `runtime_verified=false`；required-field tests 先紅，再修 producer 到綠。
- parity 先得到 missing module／missing compare seam，再加入 frozen report model、四分類、
  雙邊 provenance 與 deterministic serialization。
- API component risk-lens regression 先以 AST on/off probe 定位到全域 first-evidence
  竊取 anchor；focused test 先紅，再改成 owned evidence anchor，沒有弱化原測試。
- legacy v1 read adapter 曾把無 direct evidence 的 edge 標成 `observed`；contract tests
  先紅，修為 direct-only observed、compatibility read 維持 detected。
- 獨立複核先抓到 execution paths 遺失 status/reason/evidence、undetermined reason 可空、
  AST resolve→read symlink race 與 16F stale 狀態；各項先補 RED，再以 v2 edge record、
  reason invariant、descriptor-pinned no-follow safe-open 與文件 live sync 修到 GREEN。
- v2 上線後 13 個 artifact routes 先因 validator 仍把 edge dict 當 node-id list 而紅；
  修成 endpoint/evidence reference validation 後，build-commit focused `22 passed`，再由
  全量 suite 驗證。
- 二次複核再以合法 references 篡改 sibling reason/relationship，證明 publish 尚未做
  semantic parity；新增 ArtifactEdge invariant 與三份 sibling 對磁碟 canonical 的完整
  ordered equality gate。root-directory replacement 測試也先讀出替代 Qdrant fact，再以
  pinned root dirfd、逐層 `openat`/no-follow 與 identity check 修到零 fact。
- 三次複核以同 inode／同長度／還原 mtime 的暫時內容置換，證明 descriptor read 尚未
  綁定 approved bytes；現在 decode/parse 前必須同時符合 inventory size 與 SHA-256。
  非 POSIX pathname fallback 也已移除，缺少 safe-open primitive 時逐 Python 檔
  structured fail closed、零 facts/evidence。
- 四次複核再重現 internal-module pathname absence/restore race；module roots 改由
  approved inventory 的合法 Python 相對路徑直接推導，並以 ABA regression 鎖定不會把
  internal import 誤發成 external evidence。
- 每個 stage 的 RED/GREEN 命令與數量分別記錄於 plan-audit、Gate-1、AST、sidecar、
  edge-cutover 與 retirement reports。

## 測試方式與最終結果

| Gate | 命令／操作 | 結果 |
|---|---|---|
| Python 全量 + branch coverage | `.venv/bin/pytest --cov=systograph --cov-branch --cov-report=term-missing:skip-covered` | `1340 passed, 1 skipped in 101.97s`；`90.77%`，高於 85% 門檻 |
| Python lint | `.venv/bin/ruff check src tests scripts` | PASS |
| Python format | `.venv/bin/ruff format --check src tests scripts` | `397 files already formatted` |
| Python types | `.venv/bin/mypy src tests` | `381 source files` 無問題 |
| Setup shell | `bash -n scripts/setup_ua_sidecar.sh` | PASS |
| Frontend | `pnpm test -- --run` | `38 files / 199 tests passed` |
| Frontend build | `pnpm build` | PASS；僅既有 `web-worker` external warning |
| Sidecar lifecycle | clean pin → setup → focused live tests → reverse patch | `10 passed`，最終 pin clean |
| CLI surface | `systograph map --help` | 顯示 non-interactive gate 與 Web review 邊界 |
| CLI runtime | `systograph map basic_qdrant_ollama_rag` | 10 個 P0 artifacts；map v2；execution paths v2；target SHA-256 不變 |
| API runtime | TestClient import → preflight → scan → latest build | completed；61 nodes / 1 edge；edge status/reason contract PASS |
| 16G current-code rerun | `measure_template_flow_retirement.py` + `cmp` | 12 fixtures；與保存 JSON byte-identical；on 4 / off 2；required L1 0/13 |
| Viewer on | pgvector API import/preflight/scan | 60 nodes / 2 edges；console `[]` |
| Viewer off | malformed API import/preflight/scan | 52 nodes / 0 edges；console `[]` |

Viewer on-mode 逐 edge 目擊：

- `Retriever → pgvector / queries_vector_store`：`Assessment=Observed`（L1 direct）。
- `OpenAI Embeddings → pgvector / stores_vectors`：`Assessment=Undetermined`
  （L3 template fallback）。
- API mode 顯示 reference projection active，沒有 frontend schema error；
  `git diff frontend/` 為空。

Sidecar 最終 lifecycle：setup script 套用 repo 內 patch、建構 pinned core、live tests
通過後反套 patch；submodule HEAD 保持 `73559a160645...` 且 worktree clean。未執行 setup
時 preflight 會以 `ua_patch_not_applied` fail closed，符合 install-time contract。

## 16G 退役門檻

量測 artifact：`phase12-template-flow-retirement-measurement.json`。

| 門檻 | 結果 | 證據 |
|---|---|---|
| 1：edge-bearing fixture 不失邊 | FAIL | 12 fixtures 的 on 4 edges → off 2 edges |
| 2：required relationship 有 L1 | FAIL | required profile vocabulary `0/13` |
| 3：profile 卡不退步 | PASS | 15 張卡 on/off 差異為 0 |
| 4：合法空 topology Viewer | PASS | off-mode malformed 52 nodes / 0 edges，console 空 |
| 5：Apply/Rescan | PASS | lineage、stable evidence 與 stale-edge removal tests |
| 6：owner 簽字 | NOT SIGNED | 門檻 1、2 已先阻擋刪除 |

因此 16G 的正確完成狀態是 **NO-GO**，不是強行刪除後宣稱完成。後續只有在補足
edge-bearing fixture 與 13 個 required L1 relationship coverage 後，才可重跑門檻並
考慮移除 L3。

## 遇到的問題與處理

1. **計畫檔名不存在**：改用同目錄 canonical 16G retirement plan，未建立假檔。
2. **static artifact metadata 缺口**：以 required schema/contract 先紅，補 producer。
3. **risk hint 被 additive AST evidence 改掛**：改用 owned component evidence anchor。
4. **legacy adapter 語意膨脹**：observed 收斂成所有 evidence 都 direct 才成立。
5. **Ruff formatter/linter 交界**：formatter 產生 81 字元 test name；縮短名稱後 lint、
   format 與全量 tests 重新通過。
6. **clean submodule 的 sidecar test fail-closed**：依產品 lifecycle 先執行 setup，驗證
   live tests，再反套 patch；沒有把 runtime patch 留成 submodule dirty state。
7. **execution paths 語意遺失**：由 node pair 升為 v2 canonical edge records，保留
   relationship、status、reason 與 evidence。
8. **undetermined 缺 reason**：validator 改為無條件要求 reason，不能靠 evidence 存在
   規避可解釋性契約。
9. **AST symlink check-to-open race**：從 pinned root dirfd 逐層以 `openat` +
   `O_NOFOLLOW` 開啟；leaf descriptor 必須是 regular file、size 符合 inventory，
   實際讀到的 bytes 也必須通過 approved SHA-256 才能 parse。
10. **v2 build manifest 回歸**：reference validator 改讀 edge source/target 並驗
    execution path evidence IDs，13 個 web route 回復全綠。
11. **合法 reference 仍可篡改 sibling 語意**：ArtifactEdge 自身要求 undetermined
    reason，publish 再將 call graph、dataflow、execution paths 與磁碟 canonical edge
    records 做完整有序比對。
12. **整棵 project root replacement race**：collect 起點先釘 root directory fd 與
    device/inode；後續每一層以 `openat` + `O_NOFOLLOW` 從該 fd 開啟，root pathname
    identity 改變時在讀取前 fail closed。
13. **16F frontend 契約敘述過廣**：限縮為 GraphViewModel 欄位與 frontend production
    code 未變，明載 execution paths v1→v2 是 breaking static handoff migration。
14. **同 inode transient content replacement**：descriptor payload 在 decode 前比對
    `FileRecord.size_bytes` 與 `content_fingerprint`；內容不符只產 structured read issue。
15. **非 POSIX pathname TOCTOU**：移除 pathname fallback；缺少 POSIX safe-open
    primitive 時每個 Python 檔各產 read issue，零 AST facts/evidence。
16. **internal-module pathname ABA**：internal roots 不再查詢 live pathname 是否存在，
    只採 approved inventory path；暫時 rename/restore 不會把 internal import 升成 G3。

## 已知但未擴張修正

額外執行的 `.venv/bin/mypy src tests scripts` 在 Phase 12 與 baseline main 都得到相同
兩個 `scripts/dev.py` POSIX type errors：`subprocess.CREATE_NEW_PROCESS_GROUP` 與
`signal.CTRL_BREAK_EVENT`。本階段的 canonical type gate 是 `mypy src tests`，已通過；
這兩項是既有跨平台 typing debt，並非 Phase 12 regression。

## 獨立複核

同一位第三方 agent 已完成五輪複核：初次 3 個 P1、1 個 P2；二次 2 個 P1、1 個
P2；三次 2 個 P1；四次 2 個 P1、1 個 P2。所有 findings 均依上節完成
RED→GREEN，並補齊 non-POSIX `collect()` 的零 facts/evidence、逐檔 read issue 與
`os.open` 零呼叫永久契約。第五輪在 current worktree 重跑 content/root/leaf/internal
ABA、unsupported primitive 與 fd lifecycle probes，最終 verdict：
**`APPROVED — no P0/P1/P2 findings`**。

本階段依發布邊界不建立新 commit，因此 review 綁定 baseline SHA
`da0d402e931a4b286022f6581f41e78342214351` 加 current unstaged diff，而不是捏造一個
不存在的 final commit SHA。

## 發布邊界

- 未 commit、未 stage、未 push、未建立 PR。
- branch/worktree 保留供 owner review。
- debug journal、暫存 state、CLI outputs 與 browser tabs 已清理。
