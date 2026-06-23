# 2026-06-23 Phase 139 Query Trace SSRF Egress Policy REP

## 結論

已將 Query Trace 的 SSRF egress policy 接到共用 `EndpointCallProvider` boundary。Web `/api/trace` 與 CLI `kai-mind trace` 都透過同一路徑受到保護。

本次採 **Track A baseline**：

- request 前解析 URL、hostname、port、DNS 與所有 IPv4/IPv6 結果。
- safe mode 預設阻擋 metadata、loopback、private、link-local、unspecified、multicast、reserved 與其他 non-global address。
- DNS 失敗或任一 DNS answer 不安全時 fail closed。
- redirect 與環境 proxy 明確停用。
- blocked case 保持 `query_sent=false`，不呼叫 HTTP client，也不產生 `request_sent` event。

Track A 不等於 pinned-IP transport。DNS TOCTOU 剩餘風險已寫入安全文件，沒有宣稱完整關閉 DNS rebinding。

## 階段一：安全規則與 TDD/BDD 測試

### 實作邏輯

先使用 Given/When/Then 語意的測試名稱鎖定外部可觀察行為，再建立 production module。DNS 使用 fake resolver，測試不依賴外部網路。

### 步驟

1. 建立 `tests/unit/core/security/test_egress_policy.py`。
2. 先確認 module 不存在與 `NotImplementedError` 的 RED。
3. 涵蓋 URL parse、scheme、userinfo、hostname、port、IPv4/IPv6、IPv4-mapped IPv6。
4. 涵蓋 metadata、RFC1918、link-local、CGNAT、documentation、benchmark、reserved、multicast 與 alternate numeric hostname。
5. 涵蓋 DNS mixed answer、DNS failure、public endpoint 與 local-dev exact allowlist。

### 測試方式與結果

RED：

```text
ModuleNotFoundError: No module named 'kai_mind.core.security'
```

建立最小 API skeleton 後：

```text
1 failed: NotImplementedError
```

GREEN：

```text
tests/unit/core/security/test_egress_policy.py
46 passed
```

## 階段二：EgressPolicy 實作

### 實作邏輯

- `src/kai_mind/core/security/egress_policy.py` 負責純安全決策。
- `SocketHostResolver` 使用 `socket.getaddrinfo(..., SOCK_STREAM)` 收集全部 IPv4/IPv6 address。
- IP literal 不經 DNS，直接使用 `ipaddress` 分類。
- IPv4-mapped IPv6 會再用 mapped IPv4 分類，避免 `::ffff:127.0.0.1` bypass。
- local-dev 僅在 host、port 與 loopback opt-in 全部吻合時放行；private network、metadata、unspecified 仍阻擋。
- decision 不包含 URL credentials、query string 或 request body。

### 遇到的問題與解法

- Python 不同版本對 special-use range 的 `is_private` 判斷可能不同。
  - 解法：RFC1918/ULA、metadata、loopback、link-local、unspecified 使用明確規則，最後再以 `is_global` 做 default-deny。
- DNS rebinding 無法只靠 preflight 完整關閉。
  - 解法：明確標示 Track A，將 pinned transport / network-layer deny 留作更強控制，不做不實安全聲明。

## 階段三：EndpointCallProvider 強制邊界

### 實作邏輯

- 新增 provider status `blocked_endpoint`。
- `EndpointCallProvider.call()` 在 `_request()` 前執行 policy。
- blocked result 固定：
  - `query_sent=false`
  - `error_type="egress_policy_blocked"`
  - sanitized policy reason
- default client 使用 `httpx.Client(follow_redirects=False, trust_env=False)`。
- 每次 request 也傳入 `follow_redirects=False`，避免 injected client 的預設值改變安全行為。

### 測試方式

- blocked endpoint 使用會主動丟 AssertionError 的 fake client，證明 client 沒有被呼叫。
- injected client 即使建立時 `follow_redirects=True`，3xx 仍只發生一次 request。
- monkeypatch HTTPX constructor，驗證 default client 明確設定 redirect/proxy policy。
- public endpoint 使用真實 `EgressPolicy` + fake resolver + MockTransport，證明安全 public request 仍可送出。

## 階段四：QueryTraceService、Web 與 CLI

### 實作邏輯

- 保留既有 top-level `TraceRunResult.status="partial"`，避免 public schema breaking change。
- blocked endpoint 只產生一個：
  - `event_type="error"`
  - `status="blocked"`
  - `query_sent=false`
- `error_reason` 固定為 `egress_policy_blocked`。
- Web 與 CLI 不重複實作 policy，直接使用 shared provider。
- scanned project `pyproject.toml` 仍只控制 retrieved chunk keys；即使加入 `[tool.kai-mind.trace.security]` 也不能取得 egress 控制權。

### 測試方式

- `tests/unit/core/test_query_trace_service.py`
- `tests/web/test_trace_routes.py`
- `tests/cli/test_trace_command.py`
- `tests/unit/core/test_query_trace_config_loader.py`
- `tests/unit/core/test_query_trace_boundaries.py`

## 階段五：文件

### 完成內容

- 更新 `docs/API-GUIDE.md`：
  - safe mode 規則
  - blocked response contract
  - redirect/proxy policy
  - scanned project config trust boundary
- 建立 `docs/security/query-trace-egress-policy.md`：
  - threat boundary
  - operator-controlled local-dev 注入範例
  - Track A DNS TOCTOU 限制
  - focused verification commands

## 最終驗證

Baseline：

```text
.venv/bin/pytest
469 passed in 5.70s
```

Focused phase 139：

```text
78 passed in 0.52s
```

Full pytest：

```text
.venv/bin/pytest
523 passed in 3.95s
```

Mypy：

```text
.venv/bin/mypy src tests
Success: no issues found in 145 source files
```

Phase 139 changed-file Ruff + format：

```text
All checks passed!
9 files already formatted
```

Diff whitespace：

```text
git diff --check
passed
```

## 非本次變更造成的既有問題

全 repo `ruff check src tests` 仍被工作目錄中既有的 `src/kai_mind/core/services/risk_hint_service.py` 修改擋住：

```text
4 x E501 line-too-long
```

這四個錯誤都位於既有 Chroma 說明註解，不屬於 phase 139，也不是本次新增。為避免覆蓋使用者既有修改，本次沒有調整該檔。

## 外部依據

- OWASP SSRF Prevention Cheat Sheet：
  https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- HTTPX redirect behavior：
  https://www.python-httpx.org/compatibility/#redirects
- HTTPX environment variables：
  https://www.python-httpx.org/environment_variables/
- Python `ipaddress`：
  https://docs.python.org/3/library/ipaddress.html
- IANA special-purpose address registries：
  https://www.iana.org/assignments/iana-ipv4-special-registry/iana-ipv4-special-registry.xhtml
  https://www.iana.org/assignments/iana-ipv6-special-registry/iana-ipv6-special-registry.xhtml

## 殘餘風險

- Track A 的 DNS preflight 與 HTTP transport connect 之間仍可能有 DNS TOCTOU。
- 若部署目標要求完整 DNS rebinding closure，下一步必須加入 pinned-IP transport 或 network-layer egress deny。
- CLI 目前只有 safe mode；local-dev opt-in 僅能由可信任的 app startup dependency injection 提供。

## Security review

- 已委派 `security-privacy` subagent 唯讀審查 phase 139 diff。
- 結果：無 actionable finding。
- 審查確認 default-deny、redirect/proxy、blocked no-call、service event semantics 與 local-dev exact allowlist。
- 唯一 informational risk 為上述已文件化的 DNS TOCTOU；subagent 未修改檔案。
