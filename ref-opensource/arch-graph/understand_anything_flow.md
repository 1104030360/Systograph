# Understand-Anything 完整運作流程圖 (Operational Flow)

> Source: `ref-opensource/Understand-Anything/understand-anything-plugin/`
> （submodule pin `73559a1`、plugin 2.8.2、MIT）
> 詳細架構圖見：`understand_anything_architecture_detailed.md`
> **Canonical 可視化總圖見：`understand_anything_pipeline_visual.md`**
> 與 KAI-Mind 的流程對照見：`kai_mind_flow.md`

---

## 一、使用者視角（最簡流程）

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Install the plugin                                                       │
│   Claude Code : /plugin install  (marketplace)                           │
│   14 other CLI/IDE agents : install.sh  (install.ps1 = 13, no vibe)      │
│   -> symlink / junction of skills/ into the host's skills dir            │
└──────────────────────────────────────────────────────────────────────────┘
   │  user types the slash command
   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ /understand [path]      (skills/understand/SKILL.md)                     │
│ Claude Code orchestrates Phase 0 -> 7 (see section 2)                    │
└──────────────────────────────────────────────────────────────────────────┘
   │  deterministic scripts + LLM subagents
   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ <project>/.understand-anything/knowledge-graph.json                      │
│   + fingerprints.json + meta.json + config.json                          │
└──────────────────────────────────────────────────────────────────────────┘
   │  auto-invoked only if validation passed
   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ /understand-dashboard                                                    │
│   GRAPH_DIR=<project> npx vite --host 127.0.0.1   (background)           │
└──────────────────────────────────────────────────────────────────────────┘
   │  prints a URL that ALREADY carries the token
   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ http://127.0.0.1:5173/?token=<16-byte hex>                               │
│   relay the token to the user, or they hit the TokenGate screen          │
└──────────────────────────────────────────────────────────────────────────┘
   │  browser only reads JSON - no AI re-run
   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Interactive knowledge graph (React 19 + @xyflow/react)                   │
│   click a node -> GET /file-content.json?token=...&path=...              │
└──────────────────────────────────────────────────────────────────────────┘
```

| 步驟 | 誰做 | 產物 / 重點 |
|------|------|-------------|
| 安裝 | 使用者 | **Claude Code 走 marketplace**（`/plugin install`），Claude Code 直接索引 `skills/` + `agents/`（plugin **沒有 `commands/` 目錄**；`/understand` 這個 slash command 來自 `skills/understand/SKILL.md` frontmatter 的 name）；其餘 14 個 agent 平台（gemini、codex、opencode、pi、openclaw、antigravity、vibe、vscode、hermes、cline、kimi、trae、nanobot、kiro）用 `install.sh` 建 symlink，Windows 的 `install.ps1` 支援 13 個（少 `vibe`）、改用 junction |
| `/understand` | Claude agent 依 SKILL.md 編排 | `.understand-anything/knowledge-graph.json`（+ `fingerprints.json`、`meta.json`）|
| `/understand-dashboard` | Claude 背景啟動 Vite dev server | 本機 URL（**非** Claude 內嵌畫面）|
| 瀏覽 | 使用者瀏覽器 | 讀既有 JSON 渲染圖（**不重跑 AI**）|

> **token 是必要條件**：dashboard 每個 process 產生一組 16-byte 隨機 hex `ACCESS_TOKEN`（可用 `UNDERSTAND_ACCESS_TOKEN` 覆寫），`/knowledge-graph.json`、`/meta.json`、`/file-content.json` 等端點沒帶 `?token=` 一律 403。把 URL 轉給使用者時**必須連 token 一起給**，否則前端會停在 TokenGate 畫面要求手動貼上。

---

## 二、技術流程（Phase 0–7 + Dashboard）

> SKILL.md 實際有**十個 phase 段落**（0 / 0.5 / 1 / 1.5 / 2 / 3 / 4 / 5 / 6 / 7），但顯示給使用者的進度字串一律是 `N/7`——包含字面上的 `[Phase 1.5/7]`。

```text
  User: /understand [path]      PROJECT_ROOT = CWD or the given path
        │
        ▼
┌─ Phase 0 - Pre-flight  (no agents) ────────────────────────────────────────────────────────────┐
│ deterministic: git-worktree redirect -> build @understand-anything/core if missing             │
│                git rev-parse HEAD ; mkdir .understand-anything/{intermediate,tmp}              │
│                purge .trash-* dirs older than 7 days (find -mtime +7)                          │
│                python merge-subdomain-graphs.py  ──▶ MAY REWRITE knowledge-graph.json          │
│                        (auto-discovers *knowledge-graph*.json subdomain files)                 │
│                git diff / dir tree / README + manifest capture                                 │
│ LLM only     : arg parsing, output language, full | incremental | review decision              │
│ HARD GATE    : graph exists AND commit unchanged                                               │
│                -> ask user (a) full rebuild  (b) --review  (c) do nothing [STOP]               │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 0.5 - Ignore Configuration  (no agents) ────────────────────────────────────────────────┐
│ script  : generate-ignore.mjs ──▶ .understand-anything/.understandignore                       │
│           (output path HARDCODED inside the target repo; idempotent)                           │
│ GATE 1  : file just generated -> 'review it, then confirm'      [BLOCKING]                     │
│ GATE 2  : file already exists -> 'review it, then confirm'      [BLOCKING]                     │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 1/7 - SCAN (full analysis only)   agent: project-scanner x1 ────────────────────────────┐
│ 1) scan-project.mjs       ──▶ file inventory (git ls-files + walk, .understandignore)          │
│ 2) extract-import-map.mjs ──▶ importMap (tree-sitter, per-language resolution)                 │
│    both deterministic, run by the SAME agent, in this order, no LLM fallback                   │
│ 3) LLM only: name / description / frameworks synthesized from README + manifest                │
│    ──▶ intermediate/scan-result.json          soft gate when totalFiles > 100                  │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 1.5/7 - BATCH  (no agents, 100% deterministic) ─────────────────────────────────────────┐
│ compute-batches.mjs : Louvain communities, MAX_COMMUNITY_SIZE 35, MIN_BATCH_SIZE 3,            │
│                       count fallback batchSize 12, 1-hop neighborMap capped at 50              │
│ HARDCODED paths     : reads intermediate/scan-result.json ──▶ intermediate/batches.json        │
│ non-zero exit       = HARD FAILURE, no retry, pipeline stops here                              │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 2/7 - ANALYZE   agent: file-analyzer x N batches, up to 5 concurrent ───────────────────┐
│ per batch : extract-structure.mjs ──▶ tmp/ua-file-extract-results-<i>.json (AST facts)         │
│             LLM semantic pass     ──▶ intermediate/batch-<i>.json                              │
│             naming is per batchIndex ONLY - no fusion; fused names are silently                │
│             dropped by the merge regex batch-(\d+)(-part-\d+)?.json                            │
│ after all : python merge-batch-graphs.py ──▶ intermediate/assembled-graph.json                 │
│             normalize ids, dedupe, drop dangling, tested_by linker,                            │
│             ~25% of edges recovered from scan-result.json importMap                            │
│ incremental: compute-batches.mjs --changed-files + intermediate/batch-existing.json            │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 3/7 - ASSEMBLE REVIEW   agent: assemble-reviewer x1 (LLM only, no script) ──────────────┐
│ input : assembled-graph.json + batch-*.json + merge stderr + importMap                         │
│ output: intermediate/assemble-review.json                                                      │
│         AND edits intermediate/assembled-graph.json IN PLACE                                   │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 4/7 - ARCHITECTURE   agent: architecture-analyzer x1 ───────────────────────────────────┐
│ prompt = base + languages/<id>.md + frameworks/<id>.md + locales/<code>.md (silent skip)       │
│ the agent WRITES AND RUNS its own throwaway tmp/ua-arch-analyze.js (NOT bundled)               │
│ ──▶ intermediate/layers.json   + 5-step normalization                                          │
│ this is the ONLY phase that gets framework/language context injected                           │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 5/7 - TOUR   agent: tour-builder x1 ────────────────────────────────────────────────────┐
│ the agent WRITES AND RUNS its own throwaway tmp/ua-tour-analyze.js (NOT bundled)               │
│ ──▶ intermediate/tour.json   5-15 steps + 5-step normalization                                 │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 6/7 - REVIEW   fork: deterministic (default) | LLM (--review) ──────────────────────────┐
│ orchestrator assembles the canonical KnowledgeGraph ──▶ assembled-graph.json                   │
│   default  : agent writes tmp/ua-inline-validate.cjs from the source EMBEDDED in               │
│              SKILL.md and runs it (required fields, duplicate ids, edge integrity,             │
│              mandatory layer coverage for the 9 file-level types, tour refs;                   │
│              orphan nodes = warning only)          ──▶ intermediate/review.json                │
│   --review : graph-reviewer agent (LLM + scan-result inventory + $PHASE_WARNINGS)              │
│                                                    ──▶ intermediate/review.json                │
│ both branches converge on the same artifact; auto-fix once, then re-validate once              │
│ critical issues still left -> SAVE ANYWAY but SKIP dashboard auto-launch                       │
│ the review-only path from Phase 0 jumps straight into this fork                                │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ Phase 7/7 - SAVE  (no agents; step order is LOAD-BEARING) ────────────────────────────────────┐
│ 1) write knowledge-graph.json                                                                  │
│ 2) build-fingerprints.mjs -> must exit 0 AND stdout must contain                               │
│    'Fingerprints baseline:'  otherwise ABORT (never reach step 3)                              │
│ 3) write meta.json  (only after step 2 succeeded)                                              │
│ 4) cleanup: mv intermediate/* + tmp/ into .trash-<epoch>/   (mv, NOT rm -rf)                   │
│    PRESERVING intermediate/scan-result.json for the next incremental run                       │
│ 5) report summary (files, nodes, edges, layers, tour steps, warnings)                          │
│ 6) invoke /understand-dashboard ONLY if final validation passed                                │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
        │  validation passed
        ▼
┌─ Dashboard  (separate skill, zero LLM) ────────────────────────────────────────────────────────┐
│ GRAPH_DIR=<project> npx vite --host 127.0.0.1   port 5173, next free port if taken             │
│ custom vite plugin serves /knowledge-graph.json /domain-graph.json /diff-overlay.json          │
│                          /meta.json /config.json /file-content.json from GRAPH_DIR             │
│ every request gated by ?token=<per-process 16-byte hex>  -> 403 without it                     │
│ /file-content.json: graph-derived path allowlist + 1 MB cap                                    │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 解說

- **Phase 0 不是空的**：它會先 purge 超過 7 天的 `.trash-*`，再跑 `merge-subdomain-graphs.py`——這支 Python 腳本在任何掃描開始前就可能覆寫 `knowledge-graph.json`，是舊版流程圖漏掉的一步。
- **兩道 blocking gate 在 Phase 0.5**：`.understandignore` 不論剛產生或已存在，都會停下來等使用者確認。
- **Phase 1 是一個 agent 跑兩支腳本**：先 `scan-project.mjs`，再 `extract-import-map.mjs`；LLM 只負責 README/manifest 的敘述欄位，不參與檔案清單與 import 解析。
- **Phase 1.5 沒有 retry**：非零 exit 直接硬失敗，與其他 phase「重試一次後跳過」的策略不同。
- **Phase 2 的檔名沒有 fusion**：batch 產物一律 `batch-<batchIndex>.json`；自行合併命名會被 `merge-batch-graphs.py` 的 regex 靜默丟棄。
- **Phase 3 會就地改圖**：`assemble-reviewer` 除了寫 `assemble-review.json`，也直接編輯 `assembled-graph.json`，並不是唯讀的 review。
- **Phase 4 / 5 的分析腳本不在 repo 裡**：agent 每次執行時自己把 `ua-arch-analyze.js` / `ua-tour-analyze.js` 寫進 `tmp/` 再跑。
- **Phase 6 預設是決定性驗證**：`ua-inline-validate.cjs` 的原始碼內嵌在 SKILL.md 裡，由 agent 寫檔後執行；只有 `--review` 才會叫 `graph-reviewer` 這個 LLM agent。
- **Phase 7 的順序不能換**：fingerprints 沒過就不能寫 `meta.json`，否則 auto-update 會把之後每個 commit 都升級成 FULL_UPDATE。

### 錯誤處理與 hooks

- Subagent dispatch 失敗 → 重試一次；記入 `$PHASE_WARNINGS`；第二次仍失敗 → 跳過該 phase 繼續，**永遠保存部分結果並在報告中列出被跳過的 phase**，絕不靜默吞掉。例外只有兩處：Phase 1.5 硬失敗、Phase 7 fingerprint abort。
- `hooks/hooks.json`：`PostToolUse`（Bash `git commit|merge|cherry-pick|rebase`）與 `SessionStart`（`meta.json.gitCommitHash != HEAD`）；需 `config.json` 的 `autoUpdate: true` 且圖已存在才觸發，只印出提示要求執行 `hooks/auto-update-prompt.md` 的 4-phase 增量更新流程（Phase 0–1 零 LLM token，用 SHA-256 + regex fingerprint diff 判定 SKIP / PARTIAL_UPDATE / ARCHITECTURE_UPDATE / FULL_UPDATE）。

---

## 三、資料演進（JSON 管線）

```text
┌────────────────────────────────────────────────────────────────────────────────────┐
│ intermediate/scan-result.json          files[] + importMap   (Phase 1)             │
└────────────────────────────────────────────────────────────────────────────────────┘
   │  compute-batches.mjs
   ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ intermediate/batches.json              Louvain batches       (Phase 1.5)           │
└────────────────────────────────────────────────────────────────────────────────────┘
   │  per batch: extract-structure.mjs
   ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ tmp/ua-file-extract-results-<i>.json   deterministic AST facts                     │
└────────────────────────────────────────────────────────────────────────────────────┘
   │  per batch: LLM semantic pass
   ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ intermediate/batch-<i>.json            semantic graph fragment                     │
└────────────────────────────────────────────────────────────────────────────────────┘
   │  merge-batch-graphs.py
   ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ intermediate/assembled-graph.json      merged graph                                │
└────────────────────────────────────────────────────────────────────────────────────┘
   │
   ├──▶ intermediate/assemble-review.json   (Phase 3, also edits the graph in place)
   ├──▶ intermediate/layers.json            (Phase 4)
   └──▶ intermediate/tour.json              (Phase 5)
   │
   ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ intermediate/review.json               inline-validate | graph-reviewer            │
└────────────────────────────────────────────────────────────────────────────────────┘
   │  Phase 7, gated order
   ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ knowledge-graph.json      <-- the product                                          │
│   ──▶ fingerprints.json   <-- must succeed first                                   │
│       ──▶ meta.json       <-- written only after fingerprints                      │
└────────────────────────────────────────────────────────────────────────────────────┘
   │  HTTP GET ?token=...
   ▼
┌────────────────────────────────────────────────────────────────────────────────────┐
│ Dashboard fetch: /knowledge-graph.json + /file-content.json                        │
└────────────────────────────────────────────────────────────────────────────────────┘
```

- 只有 `intermediate/scan-result.json` 會在 Phase 7 cleanup 中**刻意保留**（其餘 `intermediate/*` 與整個 `tmp/` 被 `mv` 進 `.trash-<epoch>/`），因為增量更新要靠它跳過 Phase 1 SCAN。
- `extract-structure-result.mjs` 是純模組、沒有 CLI，**不是管線中的一步**，只是被 `extract-structure.mjs` import。

---

## 四、角色分工（一圖看懂）

```text
┌─ AI layer - Claude Code (decides; never parses code itself) ───────────────────────────────┐
│ Host Orchestrator (follows skills/understand/SKILL.md) runs these DIRECTLY:                │
│     merge-subdomain-graphs.py      Phase 0                                                 │
│     generate-ignore.mjs            Phase 0.5                                               │
│     compute-batches.mjs            Phase 1.5                                               │
│     merge-batch-graphs.py          Phase 2 (end)                                           │
│     tmp/ua-inline-validate.cjs     Phase 6 default (runtime-authored)                      │
│     build-fingerprints.mjs         Phase 7                                                 │
│ Subagents dispatched by the orchestrator (6 of the 9 shipped agents):                      │
│     project-scanner x1 | file-analyzer xN (<=5 concurrent) | assemble-reviewer x1          │
│     architecture-analyzer x1 | tour-builder x1 | graph-reviewer (--review only)            │
└────────────────────────────────────────────────────────────────────────────────────────────┘
      │  dispatch / exec
      ▼
┌─ Script layer - deterministic, zero LLM ───────────────────────────────────────────────────┐
│ 9 bundled scripts on disk (skills/understand/):                                            │
│     Node   : generate-ignore, scan-project, extract-import-map, compute-batches,           │
│              extract-structure, extract-structure-result (module only, no CLI),            │
│              build-fingerprints                                                            │
│     Python : merge-subdomain-graphs (Phase 0), merge-batch-graphs (Phase 2)                │
│ runtime-authored into tmp/ on every run (NOT on disk, NOT in the repo):                    │
│     ua-arch-analyze.js (P4) | ua-tour-analyze.js (P5)                                      │
│     ua-inline-validate.cjs (P6 default) | ua-graph-validate.js (P6 --review)               │
└────────────────────────────────────────────────────────────────────────────────────────────┘
      │  uses
      ▼
┌─ Parser layer - @understand-anything/core ─────────────────────────────────────────────────┐
│ web-tree-sitter WASM, 14 language configs / 15 grammars (tsx has its own)                  │
│ missing grammar -> silent degradation (console.debug, empty result), never throws          │
└────────────────────────────────────────────────────────────────────────────────────────────┘
      │  writes
      ▼
┌─ Data layer - <project-root>/.understand-anything/ ────────────────────────────────────────┐
│ knowledge-graph.json | fingerprints.json | meta.json | config.json                         │
│ .understandignore | intermediate/scan-result.json | .trash-<epoch>/                        │
└────────────────────────────────────────────────────────────────────────────────────────────┘
      │  HTTP GET ?token=...
      ▼
┌─ UI layer - dashboard (zero LLM, read-only) ───────────────────────────────────────────────┐
│ npx vite --host 127.0.0.1 (port 5173+), React 19 + @xyflow/react + Zustand                 │
│ vite plugin serves the JSON files from GRAPH_DIR, token-gated -> 403                       │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Python 不是只在 Phase 2**：`merge-subdomain-graphs.py` 在 Phase 0 就會跑，而且它是唯一能在掃描開始前改寫 `knowledge-graph.json` 的腳本。
- **方向永遠是「上層 AI 叫腳本」**：腳本不會反過來呼叫 LLM，`extract-import-map.mjs` 連 LLM fallback 都沒有。
- **AI 也會寫腳本**：Phase 4/5/6 的分析與驗證腳本由 agent 當場寫進 `tmp/` 再執行；執行本身仍是決定性的，但這些檔案不在 repo 裡、每次內容可能不同。

---

## 五、重點釐清

| 常見誤解 | 實際 |
|----------|------|
| `.mjs` 腳本會產生可視化 HTML | ❌ 腳本只吐 JSON；UI 是 `packages/dashboard` 的 React 19 app，由 Vite dev server 即時提供 |
| 圖會嵌在 Claude 介面裡 | ❌ 獨立 Vite dev server + 系統瀏覽器 |
| dashboard 是 static HTML bundle | ❌ 是 **live Vite dev server**（`npx vite --host 127.0.0.1`，5173 被占用就往後找），且每個 process 一組 16-byte token，沒帶 `?token=` 就是 403 / TokenGate |
| `ua-inline-validate.cjs` 是 bundled script | ❌ **runtime-authored**：原始碼內嵌在 SKILL.md，agent 每次寫進 `tmp/` 再跑；`ua-arch-analyze.js`／`ua-tour-analyze.js`／`ua-graph-validate.js` 同理。磁碟上只有 9 支腳本 |
| Python 只在 Phase 2 出現 | ❌ 除了 `merge-batch-graphs.py`（Phase 2），`merge-subdomain-graphs.py` 在 Phase 0 就跑 |
| 流程只有 7 個 phase | ❌ SKILL.md 有十個 phase 段落，但進度字串一律 `N/7`（含字面上的 `[Phase 1.5/7]`）|
| `extract-structure-result.mjs` 是管線一步 | ❌ 純模組、無 CLI，只被 import |
| Phase 2 的 file-analyzer 有 framework 脈絡 | ❌ framework/language prompt 只注入 Phase 4 的 `architecture-analyzer`（upstream `frameworks/*.md` 的敘述有誤）|
| 只掃當前 repo | ⚠️ 預設 `PROJECT_ROOT` = CWD，可傳 `/understand /path`；git worktree 會在 Phase 0 被重導回主 repo |
| 腳本在底層叫 AI | ❌ **方向相反：上層 AI 叫腳本** |
| Dashboard 會重跑 scan | ❌ 只讀已存在的 JSON，不觸發任何 LLM |
| node/edge type 數量是固定的 | ⚠️ 依範圍不同：`/understand` 用 13 node / 26 edge；reviewer agents 16/29；`packages/core/src/schema.ts` 的 zod superset 21/35 |

---

## 六、與 KAI-Mind 對照

見 `kai_mind_flow.md`：KAI-Mind 由 **Python Core**（`MapBuildService`）線性編排；UA 由 **IDE 內的 AI agent** 依 Markdown 劇本編排，每個 phase 都可能停下來問使用者。

整合邊界（`ref-opensource/kai-mind-understand-anything-integration-boundary.md`，Accepted 2026-07-07 P0）：

- KAI-Mind 只採用本文 Phase 1–2 的**三支決定性腳本**：`extract-import-map.mjs` → `compute-batches.mjs` → 每個 batch 的 `extract-structure.mjs`，取得結構事實後**立即返回**，不執行 `file-analyzer`、semantic merge 或 Phase 3–7。
- `scan-project.mjs` **不執行**（會與 KAI Step 2 的 inventory policy 形成第二個掃描邊界）；language detection / fileCategory / line counts 三項 enrichment 改在 KAI Step 2 自行實作。
- Phase 3–7 的 assemble-reviewer、architecture-analyzer、tour-builder、knowledge-graph 組裝與 dashboard **一律不採用**；KAI-Mind Step 6 是純 Python 的 `ProfileInferenceService`（10 planes / 52 nodes），semantic 合併屬於 **Plan 17 deferred**。
- `compute-batches.mjs` 目前把 `intermediate/` 路徑寫死在目標 repo 內，違反 KAI-Mind 的唯讀保證，整合時必須改成顯式的 `--input`/`--output`/`--work-dir`。
- 現況：`src/` 底下尚無任何程式碼引用 `ref-opensource/`，sidecar 仍屬規劃階段。
