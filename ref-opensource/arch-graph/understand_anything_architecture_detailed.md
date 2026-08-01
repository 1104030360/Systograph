# Understand-Anything 詳細架構與資料流圖

> Role: the **detailed, component-level** companion diagram.
> High-level overview: `understand_anything_architecture.md`.
> Canonical pipeline visual: `understand_anything_pipeline_visual.md`.
> Runtime/agent narrative: `understand_anything_flow.md`.
> Systograph side: `systograph_architecture.md`, `systograph_flow.md`, and the accepted
> boundary record `../systograph-understand-anything-integration-boundary.md`.
>
> Scope: the `/understand` codebase-analysis pipeline plus the local dashboard read path.
> Source of truth: pinned submodule `73559a16` (plugin 2.8.2) —
> `understand-anything-plugin/skills/understand/SKILL.md`, `agents/*.md`,
> `hooks/hooks.json`, `packages/dashboard/vite.config.ts`.
> All diagrams are ASCII; this file contains no Mermaid.

---

## 1. Layer Map

```text
┌─ Entry ──────────────────────────────────────────────────────────────────────────────┐
│ User ──▶ /understand [path] [--full] [--review] [--language <l>] [--auto-update]     │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ L0  Orchestrator — skills/understand/SKILL.md ──────────────────────────────────────┐
│ ten phase sections:  0 ▶ 0.5 ▶ 1 ▶ 1.5 ▶ 2 ▶ 3 ▶ 4 ▶ 5 ▶ 6 ▶ 7                       │
│ every progress string is labelled "N/7" — incl. the literal "[Phase 1.5/7]"          │
│ owns: arg parsing, user gates, agent dispatch, $PHASE_WARNINGS, save order           │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ L1  LLM agent layer  (9 agents on disk; 6 reachable from /understand) ──────────────┐
│ project-scanner        x1      Phase 1   name/description/frameworks ONLY            │
│ file-analyzer          xN      Phase 2   <= 5 concurrent, semantic nodes/edges       │
│ assemble-reviewer      x1      Phase 3   cross-check the merged graph                │
│ architecture-analyzer  x1      Phase 4   layers.json                                 │
│ tour-builder           x1      Phase 5   tour.json                                   │
│ graph-reviewer         x0..1   Phase 6   only under --review                         │
│ full run = 5 + N dispatches (N = batches); +1 with --review                          │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ L2  Deterministic layer ────────────────────────────────────────────────────────────┐
│ 9 bundled scripts in skills/understand/  (8 of them are pipeline steps)              │
│ 4 runtime-authored tmp/ helpers, written fresh from SKILL.md on every run            │
│ @understand-anything/core: TreeSitterPlugin, PluginRegistry, schema, search          │
│ web-tree-sitter WASM: 14 configs / 15 grammars; missing grammar = silent             │
│ degradation (console.debug + empty results), never a throw                           │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ L3  Artifacts — <project-root>/.understand-anything/ ───────────────────────────────┐
│ knowledge-graph.json   fingerprints.json   meta.json   config.json                   │
│ .understandignore      intermediate/       tmp/        .trash-<epoch>/               │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ L4  Dashboard  (read-only viewer) ──────────────────────────────────────────────────┐
│ live Vite dev server on 127.0.0.1:5173 behind a per-process ?token= gate             │
│ React 19 + @xyflow/react + Zustand; NEVER re-runs the pipeline                       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- L0 是 skill runtime（SKILL.md 本身），不是一支程式；它負責 phase 排序、user gate、
  agent dispatch、`$PHASE_WARNINGS` 累積，以及 Phase 7 的寫檔順序。
- Phase 章節共 **10 段**（0、0.5、1、1.5、2、3、4、5、6、7），但對使用者顯示的進度字串
  一律寫成 `N/7`，包含字面上的 `[Phase 1.5/7]`。這是上游刻意的 UX 簡化，不是筆誤。
- 9 個 agent 存在於磁碟上，但 `/understand` 只會用到其中 6 個；另外 3 個屬於
  `/understand-domain`、`/understand-knowledge` 與使用者手動呼叫的 helper。
- 節點/邊型別數量是 **scope-dependent**：SKILL.md 的 codebase 圖是 13 node types /
  26 edge types；reviewer agent 多帶 3 個 domain 型別（16 / 29）；
  `packages/core/src/schema.ts` 的 zod schema 是權威超集（21 / 35，含 knowledge-wiki）。
  本檔所有敘述以 **13 / 26** 為準。

---

## 2. Phase 0 / 0.5 — Pre-flight and the two blocking gates

```text
┌─ Phase 0  Pre-flight  (no agents) ───────────────────────────────────────────────────┐
│ 1 resolve PROJECT_ROOT — git-worktree redirect to the main checkout                  │
│ 2 ensure plugin built  — pnpm install + build @understand-anything/core              │
│ 3 git rev-parse HEAD ; mkdir .understand-anything/{intermediate,tmp}                 │
│ 4 purge .trash-* dirs older than 7 days  (find -mtime +7 -exec rm -rf)               │
│ 5 config.json — autoUpdate flag + outputLanguage (detect once, persist)              │
│ 6 python merge-subdomain-graphs.py $PROJECT_ROOT   <<< RUNS FIRST                    │
│     merges *knowledge-graph*.json siblings INTO knowledge-graph.json                 │
│     -> can rewrite the final artifact before a single file is scanned                │
│     output path is HARDCODED to .understand-anything/knowledge-graph.json            │
│ 7 read knowledge-graph.json + meta.json -> full / incremental / review               │
│ 8 collect README + manifest + dir tree + entry point for later injection             │
│                                                                                      │
│ HARD USER GATE: graph exists AND commit unchanged -> ask the user for                │
│                 (a) --full rebuild  (b) --review  (c) stop                           │
│ --review + unchanged commit: copy knowledge-graph.json into                          │
│                 intermediate/assembled-graph.json, JUMP TO Phase 6 step 3            │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ Phase 0.5  Ignore Configuration  (no agents) ───────────────────────────────────────┐
│ node generate-ignore.mjs $PROJECT_ROOT                                               │
│   -> .understand-anything/.understandignore  (plain text, HARDCODED path)            │
│                                                                                      │
│ BLOCKING GATE 1: file missing -> generate it, then wait for confirmation             │
│ BLOCKING GATE 2: file exists  -> ask for review, then wait for confirmation          │
│ both gates block the pipeline; the script itself is idempotent                       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- `merge-subdomain-graphs.py` 是**整條 pipeline 最早執行的腳本**，而且它的輸出路徑寫死成
  `.understand-anything/knowledge-graph.json`。也就是說：在 Phase 1 掃到任何一個檔案之前，
  最終產物就可能已經被 subdomain graph 覆寫過一次。任何「knowledge-graph.json 只由 Phase 7
  產生」的敘述都是錯的。
- `.trash-*` 的 7 天延遲清理與 Phase 7 的 `mv`-based cleanup 是一組設計：Phase 7 不做
  `rm -rf`（避免觸發 hardened host 的破壞性動作檢查），改由 Phase 0 在 7 天後回收。
- Phase 0.5 有 **兩個**都會 block 的使用者確認點（檔案不存在時產生後確認、檔案已存在時
  檢視後確認），不是單一 gate。

---

## 3. Phase 1 / 1.5 / 2 — Scan, Batch, Analyze

```text
┌─ Phase 1  SCAN  (full run only) — 1x project-scanner agent ──────────────────────────┐
│ ┌──────────────────────────┐   ┌────────────────────────────┐                        │
│ │ scan-project.mjs         │──▶│ extract-import-map.mjs     │                        │
│ │ git ls-files + fallback  │   │ tree-sitter, per-language  │                        │
│ │ applies .understandignore│   │ resolvers; no LLM fallback │                        │
│ └──────────────────────────┘   └─────────────┬──────────────┘                        │
│                                              ▼                                       │
│                                intermediate/scan-result.json                         │
│                                                                                      │
│ both scripts are deterministic; extract-import-map.mjs takes                         │
│ <input.json> <output.json> and has no hardcoded path                                 │
│ LLM contributes ONLY project name / description / frameworks, synthesised            │
│ from README + manifest. File inventory and import map are script output.             │
│ SOFT GATE: > 100 files -> warn the user, continue once confirmed                     │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ Phase 1.5  BATCH  (100% deterministic, no agents) ──────────────────────────────────┐
│ node compute-batches.mjs $PROJECT_ROOT [--changed-files=<a,b,c>]                     │
│   HARDCODED in : intermediate/scan-result.json                                       │
│   HARDCODED out: intermediate/batches.json                                           │
│   no --input/--output/--work-dir flags exist upstream                                │
│   graphology Louvain; MAX_COMMUNITY_SIZE 35; count fallback batchSize 12;            │
│   MIN_BATCH_SIZE 3; neighborMap = 1-hop capped at 50; file-count based               │
│   (no token budget)                                                                  │
│ HARD FAILURE: non-zero exit aborts the run — no retry, no recovery                   │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ Phase 2  ANALYZE  (file-analyzer x N batches, <= 5 concurrent) ─────────────────────┐
│ per agent: extract-structure.mjs <input.json> <output.json>  (both paths             │
│            configurable) -> tree-sitter structural facts                             │
│            then LLM semantic nodes/edges                                             │
│            -> intermediate/batch-<batchIndex>.json                                   │
│ NO framework / language context is injected here — Phase 4 only                      │
│                                                                                      │
│ then deterministic: python merge-batch-graphs.py $PROJECT_ROOT                       │
│   in : intermediate/batch-*.json  +  scan-result.json importMap                      │
│   out: intermediate/assembled-graph.json  +  stderr correction log                   │
│   normalize ids, dedupe, drop dangling edges, tested_by linker                       │
│   importMap recovers ~25% of the import edges the LLM batches miss                   │
│                                                                                      │
│ incremental path: compute-batches.mjs --changed-files + batch-existing.json          │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- Phase 1 的 project-scanner **不是**由 LLM 去「看檔案清單」：它先跑 `scan-project.mjs`
  取得 inventory，再跑 `extract-import-map.mjs` 產生 `importMap`，兩者都是 deterministic
  script；LLM 只負責從 README / manifest 合成 `name` / `description` / `frameworks`。
- `compute-batches.mjs` 的輸入輸出路徑都是**寫死**的（`intermediate/scan-result.json` →
  `intermediate/batches.json`），完全沒有 `--input` / `--output` / `--work-dir`。這正是
  Systograph 整合時必須改寫的第一個相容性缺口（見 boundary doc §3.2 / §7）。
- Phase 2 的 batch 檔名是 `batch-<batchIndex>.json`；`merge-batch-graphs.py` 以正規表示式
  `batch-(\d+)(-part-\d+)?.json` 收檔，**任何被合併過的自訂檔名都會被靜默丟棄**。
- 語言 / framework 的補充 prompt 只在 Phase 4 注入，Phase 2 的 file-analyzer 拿不到
  （上游 `frameworks/django.md` 的文件敘述與實作不一致，以 SKILL.md 實作為準）。

---

## 4. Phase 3 / 4 / 5 — Assemble Review, Architecture, Tour

```text
┌─ Phase 3  ASSEMBLE REVIEW  (1x assemble-reviewer, LLM end-to-end, no scripts) ───────┐
│ in : assembled-graph.json + batch-*.json + merge stderr + importMap                  │
│ out: intermediate/assemble-review.json                                               │
│      AND edits intermediate/assembled-graph.json in place                            │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ Phase 4  ARCHITECTURE  (1x architecture-analyzer) ──────────────────────────────────┐
│ prompt = agents/architecture-analyzer.md          (base template)                    │
│        + languages/<language-id>.md               (per detected language)            │
│        + frameworks/<framework-id>.md             (per detected framework)           │
│        + locales/<code>.md                        ($OUTPUT_LANGUAGE != en)           │
│          a missing file is SKIPPED SILENTLY                                          │
│ this is the ONLY place framework/language context enters the pipeline                │
│                                                                                      │
│ agent authors and runs tmp/ua-arch-analyze.js       [runtime-authored]               │
│ out: intermediate/layers.json   (5-step normalization)                               │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ Phase 5  TOUR  (1x tour-builder) ───────────────────────────────────────────────────┐
│ agent authors and runs tmp/ua-tour-analyze.js       [runtime-authored]               │
│ out: intermediate/tour.json — 5..15 ordered steps (5-step normalization)             │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- Phase 3 是唯一一個**完全沒有腳本**的階段：assemble-reviewer 直接讀 merge 的 stderr 與
  `importMap` 做交叉比對，並就地改寫 `assembled-graph.json`。
- Phase 4 / Phase 5 的分析腳本 **不在 plugin 的 9 支 bundled script 之內**：agent 每次執行
  時自己把 `tmp/ua-arch-analyze.js`、`tmp/ua-tour-analyze.js` 寫出來再跑，跑完隨 tmp/ 一起
  被丟進 `.trash-<epoch>/`。
- `extract-structure-result.mjs` 是被 import 的純模組、沒有 CLI，因此不應被畫成 pipeline
  的一個步驟。

---

## 5. Phase 6 — Validation Fork

```text
  Phase 6 entry: orchestrator assembles the canonical KnowledgeGraph
  {version, project, nodes, edges, layers, tour}, normalizes layer/tour
  refs, writes intermediate/assembled-graph.json
                                           │
                      ┌────────────────────┴────────────────────┐
           no --review│                                         │--review
                      ▼                                         ▼
   ┌─ DEFAULT path ───────────────────────┐  ┌─ --review path ──────────────────────┐
   │ tmp/ua-inline-validate.cjs           │  │ graph-reviewer agent (LLM)           │
   │ [runtime-authored]                   │  │ agents/graph-reviewer.md             │
   │ agent writes it from source that is  │  │ + scan-result.json file inventory    │
   │ embedded in SKILL.md, then runs it   │  │ + $PHASE_WARNINGS cross-validation   │
   │                                      │  │                                      │
   │ deterministic checks:                │  │ flags:                               │
   │   required fields, duplicate ids,    │  │   scanned files with no node,        │
   │   edge integrity, mandatory layer    │  │   nodes whose filePath is absent     │
   │   coverage for the 9 file-level      │  │   from the scan inventory,           │
   │   node types, tour references        │  │   semantic gaps                      │
   │ orphan nodes = WARNING, not issue    │  │                                      │
   └──────────────────────────────────────┘  └──────────────────────────────────────┘
                      │                                         │
                      └────────────────────┬────────────────────┘
                                           ▼
                     intermediate/review.json  {issues, warnings, stats}
                                           │
                                           ▼
  issues non-empty -> auto-fix (remove dangling edges, fill missing required
  fields with defaults, remove nodes with invalid types) -> re-validate ONCE
                                           │
                      ┌────────────────────┴────────────────────┐
                      ▼                                         ▼
                    clean                            critical issues remain
                      │                                         │
                      ▼                                         ▼
           Phase 7 runs, dashboard                  Phase 7 SAVES ANYWAY, but
                auto-launches                   dashboard auto-launch is SKIPPED
```

**解說**

- 兩條路徑**收斂到同一個 artifact**（`intermediate/review.json`），差別只在產生方式：
  預設是 deterministic 檢查、`--review` 是 LLM 審查。
- `ua-inline-validate.cjs` 同樣是 **runtime-authored**：它的原始碼內嵌在 SKILL.md
  （約 L599–663），agent 每次執行時寫進 `tmp/` 再跑，plugin 目錄裡找不到這支檔案。
- **Orphan node 只算 warning，不算 issue**，不會擋下 Phase 7。
- 自動修復只跑一輪；若仍有 critical issue，圖**照樣存檔**，但 dashboard 的自動啟動會被跳過。
- Phase 0 的 review-only 判定會直接跳到這裡的 fork（Phase 6 step 3），不重跑 Phase 1–5。

---

## 6. Phase 7 — Save Order (load-bearing)

```text
  (1) write  .understand-anything/knowledge-graph.json
        │
        ▼
  (2) node build-fingerprints.mjs intermediate/fingerprint-input.json
        │      output path HARDCODED -> .understand-anything/fingerprints.json
        │      MUST exit 0 AND stdout MUST contain "Fingerprints baseline:"
        ├───── fail ─ ─ ─▶  ABORT Phase 7, do NOT write meta.json  (issue #152:
        │                   a fresh commit hash with no baseline makes every
        │                   later auto-update escalate to FULL_UPDATE)
        ▼
  (3) write  meta.json {lastAnalyzedAt, gitCommitHash, version "1.0.0",
                        analyzedFiles}          <- only after (2) succeeded
        │
        ▼
  (4) cleanup by mv, never rm -rf  (issue #301: hardened hosts flag deletion
      of just-created dirs)
        intermediate/*  ──▶ .trash-<epoch>/   EXCEPT intermediate/scan-result.json
        tmp/            ──▶ .trash-<epoch>/   (Phase 0 purges trash after 7 days)
        scan-result.json deliberately survives so incremental runs skip Phase 1
        │
        ▼
  (5) summary: files by fileCategory, nodes/edges by type, layers, tour steps,
      accumulated $PHASE_WARNINGS
        │
        ▼
  (6) invoke /understand-dashboard  ─ ─ ─▶ ONLY if final validation passed
```

**解說**

- 這個順序是**契約級**的：`build-fingerprints.mjs` 必須先成功（exit 0 且 stdout 含
  `Fingerprints baseline:`）才能寫 `meta.json`。順序顛倒會讓 auto-update 看到新的 commit
  hash 卻沒有 baseline，把每個檔案都判成 STRUCTURAL，之後每次 commit 都升級成 `FULL_UPDATE`。
- cleanup 用 `mv` 而非 `rm -rf`，且**刻意保留** `intermediate/scan-result.json`——它是
  incremental run 得以跳過 Phase 1 的唯一依據（省下約 157k tokens / 158s）。

---

## 7. Dashboard Read Path

```text
┌─ /understand-dashboard  (backgrounded launch) ───────────────────────────────────────┐
│ GRAPH_DIR=<project-root> npx vite --host 127.0.0.1                                   │
│ live Vite 6 dev server, port 5173 (next free port when taken)                        │
│ ACCESS_TOKEN = crypto.randomBytes(16).toString("hex"), per process                   │
│                override with UNDERSTAND_ACCESS_TOKEN                                 │
│ NOT a static bundle. NEVER re-runs /understand and never mutates artifacts.          │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ custom Vite plugin — token gate + path safety ──────────────────────────────────────┐
│ ?token=<ACCESS_TOKEN> required on every data route, otherwise 403                    │
│ served from <GRAPH_DIR>/.understand-anything/ :                                      │
│   /knowledge-graph.json   /domain-graph.json   /diff-overlay.json                    │
│   /meta.json              /config.json         /file-content.json                    │
│ /file-content.json: allowlist derived from graph node filePath values,               │
│                     1 MB cap, no traversal, no absolute-path injection               │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ browser — React 19 + Vite 6 + Tailwind v4 ──────────────────────────────────────────┐
│ validateGraph() ──▶ Zustand store ──▶ @xyflow/react graph view                       │
│ layers / search / filters / tour / diff overlay / source preview                     │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- Dashboard **不是**打包好的靜態 bundle，而是現場起的 Vite dev server；CI 從不建置它。
- Token 是 per-process 隨機值，會印在啟動訊息與 `open` 的 URL 上；沒有 `?token=` 的請求
  一律 403。`UNDERSTAND_ACCESS_TOKEN` 可覆寫（例如做本機自動化測試時）。
- `/file-content.json` 的 allowlist 是從 graph 的 node `filePath` 推導出來的，加上 1 MB
  上限；它是 read-only 的原始碼預覽通道，不是任意檔案讀取。

---

## 8. Auto-Update Hooks

```text
┌─ hooks/hooks.json ───────────────────────────────────────────────────────────────────┐
│ PostToolUse(Bash)  matcher: git (commit|merge|cherry-pick|rebase)                    │
│ SessionStart       when meta.json.gitCommitHash != git rev-parse HEAD                │
│ both additionally require config.json autoUpdate:true AND an existing                │
│ knowledge-graph.json — otherwise the hook is a no-op                                 │
│ the hook only ECHOES an instruction; the agent then reads and executes               │
│ hooks/auto-update-prompt.md                                                          │
└───────────────────────────────────────────┬──────────────────────────────────────────┘
                                            ▼
┌─ hooks/auto-update-prompt.md — 4-phase incremental updater ──────────────────────────┐
│ Phase 0  pre-flight                    ZERO LLM tokens                               │
│ Phase 1  structural fingerprint check  ZERO LLM tokens                               │
│          SHA-256 + regex diff against fingerprints.json, classified as               │
│          SKIP | PARTIAL_UPDATE | ARCHITECTURE_UPDATE | FULL_UPDATE                   │
│ Phase 2  targeted re-analysis          minimal tokens, changed batches only          │
│ Phase 3  conditional architecture/tour update + lite validation + save               │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**解說**

- Hook 本身只是 shell 條件判斷 + `echo`，真正的更新邏輯在 `auto-update-prompt.md`；
  沒有 `config.json` 的 `autoUpdate:true` 與既有 graph，hook 直接短路成 no-op。
- Phase 0–1 完全不花 LLM token：純 SHA-256 + regex 比對 `fingerprints.json`，先分類再決定
  要不要進入需要 token 的 Phase 2/3。這也是 Phase 7 fingerprint gate 存在的理由。

---

## 9. Script Inventory — bundled vs runtime-authored

磁碟上只有 **9 支** bundled script（`skills/understand/`），另有 **4 支**由 agent 在執行期
寫進 `tmp/` 的一次性腳本。把後者畫成「plugin 附帶的元件」是錯的。

| Script | On disk? | Phase | Paths |
|---|---|---|---|
| `merge-subdomain-graphs.py` | bundled | 0 | output HARDCODED `knowledge-graph.json` |
| `generate-ignore.mjs` | bundled | 0.5 | output HARDCODED `.understandignore` |
| `scan-project.mjs` | bundled | 1 | `<projectRoot> <outputPath>` — output configurable |
| `extract-import-map.mjs` | bundled | 1 | `<input.json> <output.json>` — both configurable |
| `compute-batches.mjs` | bundled | 1.5 / incremental | **both paths hardcoded** |
| `extract-structure.mjs` | bundled | 2 | `<input.json> <output.json>` — both configurable |
| `extract-structure-result.mjs` | bundled | 2 | pure module, **no CLI** — not a pipeline step |
| `merge-batch-graphs.py` | bundled | 2 (end) | `<project-root>`, intermediate paths hardcoded |
| `build-fingerprints.mjs` | bundled | 7 | `<input.json>`; output HARDCODED `fingerprints.json` |
| `tmp/ua-arch-analyze.js` | **runtime-authored** | 4 | written by architecture-analyzer each run |
| `tmp/ua-tour-analyze.js` | **runtime-authored** | 5 | written by tour-builder each run |
| `tmp/ua-inline-validate.cjs` | **runtime-authored** | 6 (default) | source embedded in SKILL.md |
| `tmp/ua-graph-validate.js` | **runtime-authored** | 6 (`--review`) | written by graph-reviewer |

---

## 10. Artifact Lineage

```text
.understand-anything/knowledge-graph.json  (pre-existing, optional)
  ──▶ Phase 0  merge-subdomain-graphs.py
        merges *knowledge-graph*.json siblings back into knowledge-graph.json
        BEFORE any scanning happens

README / manifest / dir tree
  ──▶ Phase 1  project-scanner
        scan-project.mjs ──▶ extract-import-map.mjs   (deterministic)
        LLM adds only name / description / frameworks
  ──▶ intermediate/scan-result.json
        files[] {path, language, sizeLines, fileCategory} + importMap
  ──▶ Phase 1.5  compute-batches.mjs        (hardcoded in/out paths)
  ──▶ intermediate/batches.json
        per-batch files + batchImportData + neighborMap (1-hop, cap 50)
  ──▶ Phase 2  file-analyzer x N  (<= 5 concurrent)
        extract-structure.mjs ──▶ LLM semantics
  ──▶ intermediate/batch-<batchIndex>.json
  ──▶ merge-batch-graphs.py
        + scan-result.json importMap  (recovers ~25% of import edges)
  ──▶ intermediate/assembled-graph.json
  ──▶ Phase 3  assemble-reviewer
        intermediate/assemble-review.json  (+ in-place edits to assembled-graph)
  ──▶ Phase 4/5  architecture-analyzer + tour-builder
        intermediate/layers.json , intermediate/tour.json
  ──▶ Phase 6  inline validate  or  graph-reviewer (--review)
        intermediate/review.json
  ──▶ Phase 7  knowledge-graph.json ──▶ fingerprints.json ──▶ meta.json
        then mv leftovers to .trash-<epoch>/ , keeping scan-result.json
  ──▶ /understand-dashboard   (only when validation passed)
        token-gated, read-only rendering from a live Vite dev server
```

---

## 11. Correctness Gates

- **Phase 0 merge gate** — `merge-subdomain-graphs.py` can rewrite `knowledge-graph.json`
  before Phase 1; anything reading that file must assume it may already be a merged graph.
- **Phase 0 user gate** — existing graph + unchanged commit forces an explicit
  `--full` / `--review` / stop decision; there is no silent re-run.
- **Phase 0.5 double gate** — both the generate branch and the already-exists branch block
  on user confirmation before scanning.
- **Phase 1 soft gate** — more than 100 files warns and asks for confirmation.
- **Phase 1.5 hard gate** — a non-zero exit from `compute-batches.mjs` aborts the run with
  no retry; the script's own count-based fallback already covers recoverable cases.
- **Phase 2 merge invariants** — `merge-batch-graphs.py` normalizes ids, dedupes, drops
  dangling edges, relinks `tested_by`, and recovers ~25% of import edges from
  `scan-result.json#importMap`; its regex only matches `batch-<n>[-part-<k>].json`, so any
  fused/renamed batch file is silently dropped (a real data-loss mode, not a warning).
- **Phase 4/5 normalization** — both analyzers run a 5-step normalization before their
  artifact is accepted.
- **Phase 6 referential integrity** — node, edge, layer and tour references are validated
  before Phase 7; orphan nodes are warnings only. Auto-fix runs once; remaining critical
  issues still save the graph but suppress dashboard auto-launch.
- **Phase 7 fingerprint gate** — `meta.json` is written only after `build-fingerprints.mjs`
  exits 0 *and* prints `Fingerprints baseline:`.
- **Phase 7 retention** — cleanup moves (never deletes) scratch dirs and preserves
  `intermediate/scan-result.json`.
- **Dashboard gates** — bind to 127.0.0.1, per-process token on every data route, path
  allowlist derived from the graph, 1 MB source-preview cap.
- **Error handling everywhere else** — a failed agent dispatch retries once, then the phase
  is skipped and the run continues with partial results; every warning lands in
  `$PHASE_WARNINGS` and in the final report. Failures are never silently dropped.

---

## 12. Boundary Notes

- **L0 owns ordering, not analysis.** Phase sequencing, config bootstrap, ignore handling,
  cleanup and save order live in SKILL.md; the agents never decide when they run.
- **Deterministic first.** Every semantic step is preceded by a script that produces
  structural facts (`scan-project` / `extract-import-map` / `compute-batches` /
  `extract-structure` / `merge-batch-graphs` / `build-fingerprints`). LLM agents add
  semantics and review on top of those facts; they never replace them.
- **Runtime-authored helpers are not plugin components.** `ua-arch-analyze.js`,
  `ua-tour-analyze.js`, `ua-inline-validate.cjs` and `ua-graph-validate.js` exist only for
  the duration of one run and are discarded with `tmp/`.
- **Intermediates are scratch, with one exception.** Everything under `intermediate/` is
  moved to `.trash-<epoch>/` at the end of Phase 7 except `scan-result.json`; the shareable
  product is `knowledge-graph.json`.
- **The dashboard is a reader.** It renders graph artifacts and source previews and never
  re-runs `/understand` or mutates any artifact.
- **Systograph adopts only the deterministic middle.** Per the accepted boundary record, the
  integration uses exactly three scripts — `extract-import-map.mjs` → `compute-batches.mjs`
  → `extract-structure.mjs` — entering after Systograph's own Step 2 inventory approval and
  returning immediately **before** `file-analyzer`. `scan-project.mjs` is never executed
  (its language / `fileCategory` / line-count enrichment is ported into Systograph Step 2),
  and Phases 3–7 (assemble-reviewer, architecture-analyzer, tour-builder, knowledge-graph
  assembly, dashboard) are **not adopted**. Semantic merge is deferred to Plan 17.
- **Required upstream modifications for that integration**: `compute-batches.mjs` must gain
  explicit `--input` / `--output` / `--work-dir` instead of its hardcoded
  `.understand-anything/intermediate/` paths (it must never create that directory inside a
  scanned repo), `extract-import-map.mjs` needs an allowlist / path-validation wrapper, and
  `extract-structure.mjs` must keep all temp and output files inside Systograph's work dir.
