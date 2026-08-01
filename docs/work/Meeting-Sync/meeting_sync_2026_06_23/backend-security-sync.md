# Systograph 後端安全進度同步（2026-06-23）

這份文件整理最近兩次 commit 的後端安全改動，讓團隊成員能快速了解目前狀態。

## 一句話摘要

```text
這兩個 commit 分別修補了 system map 輸出的密鑰外洩風險，
以及 Query Trace 的 SSRF 攻擊面。兩者都已有完整測試覆蓋。
```

---

## Commit 1：Secret Masking（Phase 138）

- PR: #193 `fix: prevent unmasked credentials in system map outputs`
- 日期：2026-06-22
- 異動：23 files, +1283 / -15

### 問題是什麼

舊的 secret masking 有盲點：

- `PASSWD`、`PWD`、`APIKEY`（無底線）等變形 key 沒被認出
- URL 裡的 `user:password@host` 或 `token@host` 沒被遮罩
- Validation 跟 masking 用同一套規則，盲點互相繼承
- QueryTrace error message 沒走 masking，形成另一條外洩路徑

結果：JSON report / Markdown / API / Viewer / log / snapshot 都可能帶著 raw credential 輸出。

### 怎麼修的

| 模組 | 改動 |
|---|---|
| `secret_masking_service.py` | 正規化 key 判斷、補齊 marker、新增 URL 結構化遮罩 |
| `secret_validation_service.py` | 新增獨立 URL credential validator（不依賴 masker） |
| `system_map_validation_service.py` | 先跑 URL credential check，再跑 key-based check |
| `query_trace_service.py` | error type/message 進 trace event 前先遮罩 |
| `path_safety_service.py` | 修正 Windows path regex 誤判 URL scheme 的問題 |

### 測試覆蓋

新增 12 個測試檔案，涵蓋 unit / integration / contract / snapshot，共 30+ 新 test cases。

### 驗證結果

```text
468 passed（原 438）| ruff ✓ | mypy ✓ | git diff --check ✓
```

---

## Commit 2：SSRF Egress Policy（Phase 139）

- PR: #194 `feat: add SSRF egress policy to query trace (#139)`
- 日期：2026-06-23
- 異動：20 files, +2526 / -572

### 問題是什麼

Query Trace 會對使用者指定的 URL 發 HTTP request，但沒有限制目標位址。攻擊者可以透過內部 metadata endpoint（如 `169.254.169.254`）、loopback、private network 等取得不應暴露的資訊（SSRF）。

### 怎麼修的

| 模組 | 改動 |
|---|---|
| `security/egress_policy.py`（新） | 純安全決策模組，檢查 URL/hostname/port/DNS，阻擋 metadata、loopback、private、link-local、multicast、reserved 等位址 |
| `endpoint_call_provider.py` | request 前執行 policy；blocked 時不呼叫 HTTP client，回傳 `query_sent=false` |
| `query_trace_service.py` | blocked endpoint 只產生 `error` event，不產生 `request_sent` event |

關鍵設計決策：

- **Default deny**：DNS 失敗或任一 IP 不安全時直接阻擋
- **Redirect/proxy 停用**：`follow_redirects=False`、`trust_env=False`
- **Local-dev 放行**：僅在 host + port + loopback opt-in 完全吻合時才放行
- **已知限制**：DNS TOCTOU（rebinding）風險已文件化，不做不實安全聲明

### 測試覆蓋

- `test_egress_policy.py`：46 cases（IP 分類、DNS、mixed answer、local-dev）
- Provider / Service / Web / CLI 測試共 78 passed

### 驗證結果

```text
523 passed（原 469）| ruff ✓ | mypy ✓ | git diff --check ✓
```

---

## 目前整體狀態

| 項目 | 狀態 |
|---|---|
| 全部測試 | 523 passed |
| Secret output 保護 | ✅ key marker + URL credential + independent validation |
| SSRF 保護 | ✅ egress policy + default deny + no redirect/proxy |
| 安全文件 | ✅ `docs/security/query-trace-egress-policy.md` |
| API 文件 | ✅ `docs/API-GUIDE.md` 已更新 |

## 殘餘風險

1. **DNS TOCTOU**：Track A preflight 與 HTTP connect 之間仍可能被 DNS rebinding。若需完整關閉，下一步需 pinned-IP transport 或 network-layer deny。
2. **`risk_hint_service.py`** 有 4 個既有 E501（行太長），不屬於這兩次 commit，未修改。

## 相關文件

- 完整 Phase 138 報告：`docs/work/Timmy/schedule/report/2026-06-22-phase138-secret-masking-REP.md`
- 完整 Phase 139 報告：`docs/work/Timmy/schedule/report/2026-06-23-phase139-query-trace-ssrf-egress-policy-REP.md`
- 安全設計文件：`docs/security/query-trace-egress-policy.md`
- API 指南：`docs/API-GUIDE.md`
