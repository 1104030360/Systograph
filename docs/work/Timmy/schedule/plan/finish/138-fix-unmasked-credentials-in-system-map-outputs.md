# GitHub #138 Unmasked Credentials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**GitHub Issue:** https://github.com/1104030360/Systograph/issues/138

**Goal:** 補齊 secret masking，避免 DSN URL userinfo、`PASSWD` / `PWD`、無底線 `APIKEY` 等機密以明文進入 `ai_system_map.json`、Markdown、Viewer、trace 或 proposal evidence。

**Architecture:** 修補 shared `SecretMaskingService`，並讓 canonical validation 阻止明文落盤。此 issue 可和 #153、#154 同 branch 實作，但仍需保留本 issue 的 regression tests。

**Tech Stack:** Python regex, pytest, Pydantic validation, existing scanner providers.

---

## 問題摘要（2026-06-22 查證）

### 白話結論

問題不是「完全沒有做遮罩」，而是：

> 遮罩器只認得部分憑證長相；沒認出的憑證又會通過使用相同規則的安全驗證，最後被當成普通文字寫進所有輸出。

### 資料流

```text
.env / YAML / Compose
        ↓
解析出 key + value
        ↓
SecretMaskingService 沒認出
        ↓
明文進入 Evidence.value
        ↓
Validation 使用同一套規則，也沒認出
        ↓
status = ok
        ↓
JSON / API / Viewer / Markdown / proposal / trace
```

### 根本原因

1. **憑證名稱規則不完整** — `SECRET_KEY_MARKERS` 只有 `API_KEY`、`TOKEN`、`SECRET`、`PASSWORD`、`BEARER`、`AUTH`；`DB_PASSWD`、`DB_PWD`、`MYAPIKEY` 等變形未命中。
2. **Key 比對太字面** — 只做 `key.upper()` 後 substring 比對，未先移除 `_`、`-`、`.` 等分隔符再正規化。
3. **不認得 URL 內嵌帳密** — `postgresql://user:pass@host`、`redis://:pass@host` 等 DSN userinfo 未處理；key 叫 `DATABASE_URL` 時名稱也不像 secret。
4. **Validation 不是獨立防線** — `SystemMapValidationService` 仍呼叫同一個 `SecretMaskingService.contains_unmasked_secret()`；mask 漏的，validation 也會漏。
5. **Canonical map 下游直接信任** — normalize → JSON / Viewer / Markdown / proposal / trace 皆複製已進 map 的 evidence value。

### 規則存放位置（Python vs TOML）

Secret masking 規則 **不在 TOML**，直接寫死在 Python：

- `src/systograph/core/services/secret_masking_service.py` — `SECRET_KEY_MARKERS`、`KEY_VALUE_RE`、`SECRET_PATTERNS`

專案 TOML rule catalog（如 `risk_hint_rules.toml`）主要用於 component detection、risk hints 等；**#138 預期仍直接修改 `SecretMaskingService`**，不把 masking 規則外部化到 TOML（安全核心，fail-closed 優先；見 Task 5 / plan 12a 共識）。

---

## Marker 機制說明

### Marker 是什麼

**Marker** 是一組用來判斷「config key 名字是否像 secret/credential」的 **關鍵字片段**，不是完整 env var 名稱清單。

現行實作（`secret_masking_service.py`）：

```python
SECRET_KEY_MARKERS = ("API_KEY", "TOKEN", "SECRET", "PASSWORD", "BEARER", "AUTH")

def _is_secret_key(key):
    normalized = key.upper()
    return any(marker in normalized for marker in SECRET_KEY_MARKERS)
```

### 硬比對 vs 語意

| 類型 | 現況是否如此 | 說明 |
|------|-------------|------|
| 精確 key 名比對 | 否 | 不是只認 `OPENAI_API_KEY`；含 `API_KEY` 子字串即可 |
| 硬 substring 比對 | **是** | 字串包含 marker 即命中；無 NLP / 同義詞 |
| 語意比對 | 否 | `PASSWD` 不會因「語意像 PASSWORD」而命中 |

**設計意圖**是用 marker **代表 credential 語意類別**；**實作**仍是規則 + 字串 substring。Issue #138 漏網，多半是 substring 太字面，而非缺少某個特定 key 名。

### 為何不是「一直列舉所有 key 名」

| 做法 | 維護對象 | 規模 |
|------|---------|------|
| 列舉完整 key 名 | `OPENAI_API_KEY`, `AZURE_KEY`, `NVIDIA_KEY`… | 無限，每 repo 不同 |
| Marker family + 正規化 | `APIKEY`, `TOKEN`, `SECRET`, `PASSWD`, `PWD`… | 有限，十幾到幾十個語意類 |

正規化後可一次覆蓋命名變形，例如：

- `DB_PASSWD` → `DBPASSWD` → 含 `PASSWD`
- `MYAPIKEY` → `MYAPIKEY` → 含 `APIKEY`
- `openai-api-key` → `OPENAIAPIKEY` → 含 `APIKEY`

Marker 清單仍需偶爾維護，但維護的是 **類別**，不是每個專案的 env var 名。

### Masking 雙通道（OR 邏輯）

1. **Key marker** — key 名字像 secret → mask value（即使 value 看起來普通）
2. **Value pattern** — value 像 `sk-...`、`ghp_...`、URL userinfo 等 → mask（不管 key 名）

Issue #138 漏網 case 通常是 **兩通道都不命中**。

---

## 修復策略（三層防線）

本 issue 聚焦 Task 1–2；完整防線可與 #153、#154 同 branch 實作。

| 層級 | 手段 | 處理對象 | 備註 |
|------|------|---------|------|
| 第 1 層 | Key 正規化 + 擴充 marker | `DB_PASSWD`、`MYAPIKEY`、`SESSION_COOKIE` | 本 issue Task 2 Step 1 |
| 第 2 層 | URL userinfo / token pattern | `postgresql://user:pass@host` | 本 issue Task 2 Step 2；key 名不像 secret 時兜底 |
| 第 3 層 | 獨立 validation heuristics | masking 共同盲點 | #154；不可只呼叫 `SecretMaskingService` |

### 保守策略與刻意不做的事

- **寧可多 mask，不要漏 secret** 進 report / log / snapshot（Task 5 原則）。
- **不可誤 mask** release-readiness evidence：`QDRANT_URL=http://localhost:6333`、model name、route name 等。
- URL userinfo：**只 mask password segment**，保留 scheme/host 供 readiness 判讀。
- **不做**：entropy detection、LLM 判斷 secret、git history scan、TOML 外部化 masking 規則（Phase 5 / #154 scope 外或另 issue）。

### 無法 100% 不漏的殘餘風險

自訂 key 名（例如 `X7=foo`）且 value 不像已知 pattern 時，仍可能漏網。目標是關閉 #138 已確認的 Critical 路徑，並以 regression test 累積已知 blind spot，而非宣稱 enterprise DLP 等級。

---

## Source

- GitHub issue #138, assignee Timmy.
- Origin: `docs/work/Timmy/schedule/fable-5/find-error/report/2026-06-12-backend-security-ai-findings.md` C-1.
- Primary files: `src/systograph/core/services/secret_masking_service.py`, `src/systograph/core/services/system_map_validation_service.py`.

### Task 1: Reproduce the leaked secret cases

**Files:**
- Modify: `tests/unit/core/test_secret_masking_service.py`
- Modify: `tests/integration/test_phase5_secret_masking_behaviors.py`

- [ ] **Step 1: Add failing tests for key marker variants**

Cases: `DB_PASSWD`, `DB_PWD`, `MYAPIKEY`, `ACCESSKEY`, `SESSION_COOKIE`.

- [ ] **Step 2: Add failing tests for URL userinfo**

Cases: PostgreSQL, Redis, MongoDB, and HTTP service URLs with `user:password@host`.

- [ ] **Step 3: Add map-build regression fixture**

Create synthetic fixture values only; never use real credentials.

### Task 2: Fix shared masking behavior

**Files:**
- Modify: `src/systograph/core/services/secret_masking_service.py`

- [ ] **Step 1: Normalize key markers before matching**

Normalize by uppercasing and removing separators so `API_KEY` and `APIKEY` are both secret-like.

- [ ] **Step 2: Mask URL userinfo password segments**

Preserve scheme/host where useful, but never preserve the full password.

- [ ] **Step 3: Ensure recursive JSON-like masking uses the same path**

`mask_value`, `mask_text`, and `mask_json_like` must share the fixed behavior.

### Task 3: Block unsafe canonical output

**Files:**
- Modify: `src/systograph/core/services/system_map_validation_service.py`
- Test: `tests/unit/core/test_system_map_validation.py`

- [ ] **Step 1: Add validation tests for raw DSN credentials**
- [ ] **Step 2: Reject unmasked URL userinfo in evidence values/snippets**
- [ ] **Step 3: Verify validation error messages do not echo the raw secret**

## Verification

```bash
.venv/bin/pytest tests/unit/core/test_secret_masking_service.py tests/unit/core/test_system_map_validation.py tests/integration/test_phase5_secret_masking_behaviors.py -v
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy
git diff --check
```

## Acceptance Criteria

- Raw DSN passwords, `DB_PASSWD`, `DB_PWD`, and `MYAPIKEY` values do not appear in JSON, Markdown, viewer payload, trace, proposal evidence, logs, or snapshots.
- Existing `CLIENT_SECRET` behavior remains protected.
- Canonical validation catches unsafe output before artifact write.
